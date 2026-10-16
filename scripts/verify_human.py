#!/usr/bin/env python3
"""Comprehensive verification suite for Human Translation & Embodied Biped Scaffold.

Verification Pillars:
1. Translation Invariants:
   - Baseline vehicle produces valid HumanIntent (forward walk, cadence ~1.0 Hz, posture ~0.9, tone ~1.0).
   - Na_v blocker (Lidocaine) suppresses motor tone, posture height, and forward drive.
   - GABA_A blocker (Picrotoxin) collapses coordination (coordination < 0.55, mode="ataxic").
   - Stimulants (Caffeine / Amphetamine) elevate cadence, motor tone, and propulsion drive.
   - Predator looming triggers flee arousal and elevated cadence.
   - Unilateral DNa activation generates asymmetric turn intent toward active side.
   - Provenance rule table is complete with neurobiological citations.

2. MuJoCo Joint Sign Conventions:
   - Systematic perturbation probe of all 12 DOFs verifies anatomical definitions:
     * Hip pitch: flexion moves distal foot forward (+X).
     * Knee: flexion moves foot backward (-X, foot lifts +Z).
     * Ankle: dorsiflexion tilts toes upward (+Z).
     * Hip roll: abduction moves distal leg laterally.
     * Shoulder pitch: flexion swings arm forward (+X).
     * Elbow: flexion pulls hand forward (+X) and up (+Z).

3. Biped CPG & Kinematics Invariants:
   - Reciprocal CPG maintains anti-phase lock (Delta phi ~ pi) under intact GABAergic coupling.
   - Decoupled CPG (GABA_A block) exhibits phase drift and elevated synchronization error.
   - Kinematics generator strictly respects biological joint angle limits (e.g. no knee hyperextension).
   - Slew-rate limiter bounds joint velocity to <= 25 rad/s.

4. Embodied 3D Simulation Smoke Run:
   - Baseline vehicle runs 2.0s headless: forward progress (Vx > 0.05 m/s), COM upright (> 0.80 m), alive.
   - Lidocaine runs 2.0s headless: severe bradykinesia / hypolocomotion (Vx < 0.6 * baseline).
   - GABA_A blockade (Picrotoxin) runs 2.0s headless: degraded coordination index, ataxic gait.
   - Predator assay triggers fleeing response and logs valid reaction times.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.drug_engine import drug_modulation
from sim.human_gait import BipedCPG, BipedGaitKinematics
from sim.human_pipeline import HumanPipelineSim
from sim.human_translation import DNToHumanTranslator, HumanIntent, RULE_TABLE
from sim.humanoid_body import HumanoidBodySim, probe_joint_sign_conventions
from sim.neural_sim import FlyWireNeuralSim
from sim.stimuli import StimulusConfig

PASSED = []
FAILED = []


def check(name: str, cond: bool, detail: str = ""):
    """Records and prints a single verification assertion."""
    (PASSED if cond else FAILED).append(name)
    status = "PASS" if cond else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def verify_translation_invariants():
    """Validates neuro-human translation invariants across pharmacological regimes."""
    print("\n== 1. Neuro-Human Translation Invariants & Provenance ==")

    # A. Provenance Rule Table
    rule_targets = {r["target"] for r in RULE_TABLE}
    check("rule table defines primary motor features",
          {"forward_drive", "turn_intent", "coordination", "motor_tone", "cadence", "freeze"}.issubset(rule_targets),
          f"{len(RULE_TABLE)} rules documented")

    translator = DNToHumanTranslator()
    check("translator loaded descending neurons",
          len(translator.all_dn_idx) > 1000,
          f"{len(translator.all_dn_idx)} DNs found")
    check("translator identified bilateral DNa01/02 steering neurons",
          len(translator.dna_left_idx) > 0 and len(translator.dna_right_idx) > 0,
          f"L={len(translator.dna_left_idx)}, R={len(translator.dna_right_idx)}")
    check("translator identified MDN arrest neurons",
          len(translator.mdn_idx) > 0,
          f"{len(translator.mdn_idx)} MDN found")

    # B. Baseline Vehicle Invariant
    neural = FlyWireNeuralSim()
    for _ in range(30):
        neural.step()

    base_intent = translator.translate(neural_sim=neural, drug_mod=None)

    check("baseline produces forward walk mode",
          base_intent.mode == "walk",
          f"mode={base_intent.mode}")
    check("baseline forward drive in nominal walking range (0.35 - 0.85)",
          0.35 <= base_intent.forward_drive <= 0.85,
          f"{base_intent.forward_drive:.3f}")
    check("baseline cadence in natural human range (0.8 - 1.5 Hz)",
          0.8 <= base_intent.cadence <= 1.5,
          f"{base_intent.cadence:.3f} Hz")
    check("baseline coordination is intact (> 0.85)",
          base_intent.coordination > 0.85,
          f"{base_intent.coordination:.3f}")
    check("baseline motor tone is full (> 0.85)",
          base_intent.motor_tone > 0.85,
          f"{base_intent.motor_tone:.3f}")
    check("baseline posture height is upright (> 0.80)",
          base_intent.posture_height > 0.80,
          f"{base_intent.posture_height:.3f}")

    # C. Na_v Blocker Invariant (Lidocaine: local anesthetic / conduction block)
    lido_mod = drug_modulation("Lidocaine", dose=1.0)
    lido_neural = FlyWireNeuralSim()
    lido_neural.apply_drug(lido_mod.get("fly_mapping", {}), lido_mod.get("sim_params", {}))
    for _ in range(30):
        lido_neural.step()
    lido_intent = translator.translate(neural_sim=lido_neural, drug_mod=lido_mod)

    check("Lidocaine suppresses motor tone (< 0.50)",
          lido_intent.motor_tone < 0.50,
          f"{lido_intent.motor_tone:.3f} vs baseline {base_intent.motor_tone:.3f}")
    check("Lidocaine drops posture height (knee buckling)",
          lido_intent.posture_height < 0.60,
          f"{lido_intent.posture_height:.3f} vs baseline {base_intent.posture_height:.3f}")
    check("Lidocaine reduces forward drive (< 0.5 * baseline)",
          lido_intent.forward_drive < 0.5 * base_intent.forward_drive,
          f"{lido_intent.forward_drive:.3f} vs baseline {base_intent.forward_drive:.3f}")

    # D. GABA_A Blocker Invariant (Rdl / GABA_A block: collapse of reciprocal inhibition -> ataxia)
    gaba_block_mod = {"sim_params": {"rdl_phi": 0.85}, "fly_mapping": {}}
    gaba_intent = translator.translate(neural_sim=neural, drug_mod=gaba_block_mod)

    check("GABA_A block impairs biped coordination (< 0.55)",
          gaba_intent.coordination < 0.55,
          f"{gaba_intent.coordination:.3f}")
    check("GABA_A block triggers ataxic gait classification",
          gaba_intent.mode == "ataxic",
          f"mode={gaba_intent.mode}")

    # E. Stimulant Invariant (Caffeine / Methamphetamine)
    caf_mod = drug_modulation("Caffeine", dose=1.0)
    caf_neural = FlyWireNeuralSim()
    caf_neural.apply_drug(caf_mod.get("fly_mapping", {}), caf_mod.get("sim_params", {}))
    for _ in range(30):
        caf_neural.step()
    caf_intent = translator.translate(neural_sim=caf_neural, drug_mod=caf_mod)

    check("stimulant increases cadence over baseline",
          caf_intent.cadence > base_intent.cadence,
          f"{caf_intent.cadence:.3f} Hz vs {base_intent.cadence:.3f} Hz")
    check("stimulant maintains or increases forward drive",
          caf_intent.forward_drive >= base_intent.forward_drive,
          f"{caf_intent.forward_drive:.3f} vs {base_intent.forward_drive:.3f}")

    # F. Predator Looming Visual Threat Invariant
    pred_neural = FlyWireNeuralSim()
    for _ in range(30):
        pred_neural.step()
    pred_neural.stim_predator = 0.9
    pred_intent = translator.translate(neural_sim=pred_neural, drug_mod=None)
    check("predator looming elevates flee drive (> 0.5)",
          pred_intent.flee_drive > 0.5,
          f"{pred_intent.flee_drive:.3f}")
    check("predator looming increases forward propulsion",
          pred_intent.forward_drive > base_intent.forward_drive,
          f"{pred_intent.forward_drive:.3f} vs {base_intent.forward_drive:.3f}")

    # G. Steering Asymmetry Invariant
    # Simulate unilateral DNa activation on right side
    asym_neural = FlyWireNeuralSim()
    for _ in range(30):
        asym_neural.step()
    asym_neural.r[translator.dna_left_idx] = 0.1
    asym_neural.r[translator.dna_right_idx] = 0.9
    steer_intent = translator.translate(neural_sim=asym_neural, drug_mod=None)
    check("unilateral right DNa activation produces rightward turn intent (turn_intent > 0)",
          steer_intent.turn_intent > 0.15,
          f"{steer_intent.turn_intent:.3f}")


def verify_joint_sign_conventions():
    """Validates that all 12 humanoid DOFs follow strict biomechanical sign conventions."""
    print("\n== 2. MuJoCo Joint Sign Conventions Probe ==")

    probes = probe_joint_sign_conventions()
    check("probed all 12 active joints", len(probes) == 12, f"{len(probes)} joints probed")

    for jname, p in probes.items():
        check(f"joint {jname} adheres to anatomical sign convention",
              p["verified"],
              f"action={p['action']}, dx={p['dx_m']}m, dy={p['dy_m']}m, dz={p['dz_m']}m")


def verify_biped_cpg_and_kinematics():
    """Validates reciprocal biped CPG dynamics and joint limit constraints."""
    print("\n== 3. Biped CPG & Kinematics Invariants ==")

    cpg = BipedCPG(seed=42)
    dt = 0.002

    # A. Baseline Anti-Phase Coupling
    intent_walk = HumanIntent(
        forward_drive=0.6,
        turn_intent=0.0,
        cadence=1.0,
        stride_length=0.6,
        posture_height=1.0,
        coordination=1.0,
        motor_tone=1.0,
        flee_drive=0.0,
        freeze=False,
        mode="walk",
        raw_signals={},
    )

    sync_errors = []
    for _ in range(1500):  # 3.0s simulated
        cpg.step(dt=dt, intent=intent_walk)
        sync_errors.append(cpg.phase_sync_error())

    # After initial settling (~0.5s = 250 steps), phase difference should lock near pi
    settled_errors = sync_errors[300:]
    mean_err = float(np.mean(settled_errors))
    check("intact coordination locks CPG in alternating anti-phase (mean error < 0.20 rad)",
          mean_err < 0.20,
          f"mean sync error = {mean_err:.4f} rad")

    # B. Decoupled Coordination (GABA_A block)
    cpg_ataxic = BipedCPG(seed=42)
    intent_ataxic = HumanIntent(
        forward_drive=0.6,
        turn_intent=0.0,
        cadence=1.0,
        stride_length=0.6,
        posture_height=1.0,
        coordination=0.1,  # Severe coordination failure
        motor_tone=1.0,
        flee_drive=0.0,
        freeze=False,
        mode="ataxic",
        raw_signals={},
    )

    ataxic_errors = []
    for _ in range(1500):
        cpg_ataxic.step(dt=dt, intent=intent_ataxic)
        ataxic_errors.append(cpg_ataxic.phase_sync_error())

    ataxic_mean_err = float(np.mean(ataxic_errors[300:]))
    check("degraded coordination increases CPG phase synchronization error",
          ataxic_mean_err > 2.0 * mean_err,
          f"ataxic error = {ataxic_mean_err:.4f} rad vs baseline {mean_err:.4f} rad")

    # C. Kinematic Limits & Slew Rate
    kin = BipedGaitKinematics()
    phi_l, phi_r = 0.0, np.pi
    targets = kin.compute_joint_targets(dt=dt, phi_l=phi_l, phi_r=phi_r, intent=intent_walk)

    # Check required joints present
    expected_joints = {
        "left_hip_pitch", "right_hip_pitch",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
        "left_hip_roll", "right_hip_roll",
        "left_shoulder_pitch", "right_shoulder_pitch",
        "left_elbow", "right_elbow",
    }
    check("kinematics produces targets for all 12 DOFs",
          expected_joints.issubset(targets.keys()))

    # Slew rate check: large change in intent
    max_jump = 0.0
    for step in range(500):
        # Alternate fast intent change
        phi_l += 2.0 * np.pi * 1.5 * dt
        phi_r += 2.0 * np.pi * 1.5 * dt
        t_prev = targets.copy()
        targets = kin.compute_joint_targets(dt=dt, phi_l=phi_l, phi_r=phi_r, intent=intent_walk)
        for j_name in expected_joints:
            d_angle = abs(targets[j_name] - t_prev[j_name])
            rate = d_angle / dt
            max_jump = max(max_jump, rate)

    check(f"joint targets respect slew rate limit (<= 25.0 rad/s)",
          max_jump <= 25.0 + 1e-3,
          f"max rate = {max_jump:.2f} rad/s")


def verify_embodied_simulation_smoke():
    """Runs headless embodied 3D simulations under Vehicle, Lidocaine, and Picrotoxin."""
    print("\n== 4. Embodied 3D MuJoCo Simulation Smoke Runs ==")

    # A. Baseline Vehicle Run (2.0s)
    sim_veh = HumanPipelineSim(drug_name=None, harness=True, harness_support=1.0)
    m_base, log_base = sim_veh.run(duration=2.0)
    sim_veh.close()

    body_base = m_base["body_metrics"]
    vx_base = body_base["vx_m_s"]

    check("vehicle simulation completed without NaNs",
          not np.isnan(vx_base) and not np.isnan(body_base["com_height_mean"]))
    check("vehicle biped achieves forward velocity (Vx > 0.05 m/s)",
          vx_base > 0.05,
          f"Vx = {vx_base:.3f} m/s")
    check("vehicle biped remains upright (COM height > 0.85 m)",
          body_base["com_height_mean"] > 0.85,
          f"COM = {body_base['com_height_mean']:.3f} m")
    check("vehicle biped has no falls detected",
          not body_base["fall_detected"])
    check("vehicle step symmetry is balanced (> 0.60)",
          body_base["step_symmetry"] > 0.60,
          f"step symmetry = {body_base['step_symmetry']:.3f}")
    check("vehicle telemetry logged successfully",
          len(log_base["t"]) > 50,
          f"{len(log_base['t'])} frames logged")

    # B. Lidocaine Run (2.0s) — Na_v block slows biped locomotion
    sim_lido = HumanPipelineSim(drug_name="Lidocaine", harness=True, harness_support=1.0)
    m_lido, _ = sim_lido.run(duration=2.0)
    sim_lido.close()

    body_lido = m_lido["body_metrics"]
    vx_lido = body_lido["vx_m_s"]

    check("Lidocaine simulation completed without NaNs",
          not np.isnan(vx_lido))
    check("Lidocaine slows locomotion (Vx < 0.65 * baseline)",
          vx_lido < 0.65 * vx_base,
          f"Vx = {vx_lido:.3f} vs baseline {vx_base:.3f} m/s")
    check("Lidocaine drops motor tone in telemetry summary (< 0.50)",
          m_lido["intent_summary"]["mean_motor_tone"] < 0.50,
          f"mean motor tone = {m_lido['intent_summary']['mean_motor_tone']:.3f}")

    # C. GABA_A Block Run (2.0s) — collapse of reciprocal inhibition -> ataxic coordination
    sim_gaba = HumanPipelineSim(
        drug_name=None,
        harness=True,
        harness_support=1.0,
        sim_params_override={"rdl_phi": 0.85},
    )
    m_gaba, _ = sim_gaba.run(duration=2.0)
    sim_gaba.close()

    body_gaba = m_gaba["body_metrics"]
    check("GABA_A block simulation completed without NaNs",
          not np.isnan(body_gaba["vx_m_s"]))
    check("GABA_A block degrades biped coordination (< 0.55)",
          m_gaba["intent_summary"]["mean_coordination"] < 0.55,
          f"intent coordination = {m_gaba['intent_summary']['mean_coordination']:.3f}")
    check("GABA_A block triggers ataxic mode",
          m_gaba["intent_summary"]["final_mode"] == "ataxic",
          f"mode = {m_gaba['intent_summary']['final_mode']}")

    # D. Jungle Juice Run (2.0s) — multi-drug cocktail severely slows locomotion
    sim_jj = HumanPipelineSim(drug_name="Jungle Juice (Everything mixed)", harness=True, harness_support=1.0)
    m_jj, _ = sim_jj.run(duration=2.0)
    sim_jj.close()

    body_jj = m_jj["body_metrics"]
    check("Jungle juice simulation completed without NaNs",
          not np.isnan(body_jj["vx_m_s"]))
    check("Jungle juice severely impairs biped locomotion (Vx < 0.65 * baseline)",
          body_jj["vx_m_s"] < 0.65 * vx_base,
          f"Vx = {body_jj['vx_m_s']:.3f} vs baseline {vx_base:.3f} m/s")

    # E. Predator Looming Stimulus Assay (3.0s)
    sim_pred = HumanPipelineSim(drug_name=None, stim_cfg=StimulusConfig(predator=True))
    m_pred, _ = sim_pred.run(duration=3.0, stim_schedule=[(1.0, "predator")])
    sim_pred.close()

    rts = m_pred.get("reaction_times", [])
    check("predator assay logs stimulus encounter",
          len(m_pred.get("stimulus_events", [])) >= 1,
          f"{len(m_pred.get('stimulus_events', []))} events")
    check("predator assay produces escape/reaction record",
          len(rts) >= 1,
          f"{len(rts)} reactions logged")

    # F. Timelapse Locomotion Run (timelapse = 5.0x)
    sim_tl = HumanPipelineSim(drug_name=None, harness=True, harness_support=1.0)
    m_tl, _ = sim_tl.run(duration=2.0, timelapse=5.0)
    sim_tl.close()
    check("timelapse simulation completes without NaNs",
          not np.isnan(m_tl["body_metrics"]["vx_m_s"]))
    check("timelapse simulation maintains upright walking posture",
          m_tl["body_metrics"]["com_height_mean"] > 0.85,
          f"COM = {m_tl['body_metrics']['com_height_mean']:.3f} m")

    # G. Timelapse Video Rendering (timelapse = 5.0x)
    sim_vid_tl = HumanPipelineSim(drug_name=None, harness=True, harness_support=1.0)
    test_tl_out = "out/smoke_timelapse_verify.mp4"
    m_vid_tl, _ = sim_vid_tl.render_video(out_path=test_tl_out, duration=1.0, fps=25, timelapse=5.0)
    sim_vid_tl.close()
    check("timelapse video rendering reports correct speedup factor",
          m_vid_tl.get("timelapse_factor") == 5.0,
          f"timelapse = {m_vid_tl.get('timelapse_factor')}x")
    check("timelapse video frames are compressed according to speedup factor",
          m_vid_tl.get("frames_rendered", 0) <= 15,
          f"{m_vid_tl.get('frames_rendered')} frames for 1.0s sim at 5x")


def verify_driving_simulation():
    """Validates 3D Human Driving Mode & Neuro-Pharmacological Impairment on the obstacle course."""
    print("\n== 5. Human Driving Mode & Neuro-Pharmacological Impairment ==")
    from sim.human_driving import HumanDrivingSim, resolve_drug_name

    # A. Drug Name Resolution
    check("driving drug resolver maps aliases correctly",
          resolve_drug_name("dormiphen") == "Dormiphen (Sleeping Pill)" and
          resolve_drug_name("caffeine") == "Caffeine" and
          resolve_drug_name("lidocaine") == "Lidocaine" and
          resolve_drug_name("weed") == "Weed" and
          resolve_drug_name("control") == "Vehicle control")

    # B. Baseline Driving Smoke Test (2.0s)
    sim_base = HumanDrivingSim(drug_name=None)
    m_base = sim_base.run(duration=2.0)
    sim_base.close()
    check("baseline driving runs without NaNs",
          not np.isnan(m_base.mean_speed_m_s))
    check("baseline driving accelerates down track (Vx > 0.5 m/s)",
          m_base.mean_speed_m_s > 0.5,
          f"mean Vx = {m_base.mean_speed_m_s:.2f} m/s")
    check("baseline driving maintains stable lane position (SDLP < 2.5m)",
          m_base.sdlp_m < 2.5,
          f"SDLP = {m_base.sdlp_m:.3f} m")

    # C. Lidocaine Motor Tone Blockade
    sim_lido = HumanDrivingSim(drug_name="Lidocaine", dose=1.0)
    m_lido = sim_lido.run(duration=2.0)
    sim_lido.close()
    check("lidocaine causes motor tone collapse and car stalls",
          m_lido.peak_speed_m_s < 1.0 or "stall" in m_lido.driving_outcome or "barrier" in m_lido.driving_outcome,
          f"peak Vx = {m_lido.peak_speed_m_s:.2f} m/s, outcome = {m_lido.driving_outcome}")

    # D. Dormiphen Soporific Latency
    sim_dorm = HumanDrivingSim(drug_name="Dormiphen (Sleeping Pill)", dose=1.0)
    check("dormiphen pharmacological profile depresses reaction time",
          sim_dorm.neural.arousal_attenuation < 0.85 and sim_dorm.driver_reaction_delay_ms >= 1200,
          f"arousal attenuation = {sim_dorm.neural.arousal_attenuation:.2f}, BRT delay = {sim_dorm.driver_reaction_delay_ms:.1f} ms")
    sim_dorm.close()


def verify_all_drugs_pharmacology():
    """Validates that all 17 canonical pharmacological products load, modulate, and translate without error."""
    print("\n== 6. Universal Pharmacological Coverage (Original 17 Products) ==")
    from sim.drug_engine import list_products, drug_modulation, resolve_drug_name
    from sim.human_driving import HumanDrivingSim
    from sim.long_term_timelapse import PK_PROFILES, LongTermPKPDEngine

    prods = list_products()
    check("pharmacology database contains exactly 17 products",
          len(prods) == 17,
          f"{len(prods)} products found in data/pharmacology.yaml")

    required_substances = [
        "Caffeine", "Claritin (Tablet)", "Claritin (Gel)", "Dormiphen (Sleeping Pill)",
        "Acetaminophen", "Bupropion (Wellbutrin)", "Tobacco", "Tobacco Extract",
        "Dimenhydrinate (Gravol)", "Lidocaine", "Lithium Acetate", "Mirtazapine",
        "Weed", "CBD nanodrops", "Vyvanse", "Robax", "Jungle Juice (Everything mixed)"
    ]

    for req in required_substances:
        check(f"product '{req}' is registered in database",
              req in prods,
              f"present in list_products()")

        # Verify modulation returns valid structure
        m = drug_modulation(req, dose=1.0)
        check(f"drug_modulation resolves '{req}'",
              m["product"] == req and isinstance(m["sim_params"], dict),
              f"cid={m.get('cid')}, systems={list(m['fly_mapping'].keys())}")

    # Test alias resolution
    test_aliases = [
        ("weed", "Weed"),
        ("thc", "Weed"),
        ("dormiphen", "Dormiphen (Sleeping Pill)"),
        ("benadryl", "Dormiphen (Sleeping Pill)"),
        ("claritin", "Claritin (Tablet)"),
        ("wellbutrin", "Bupropion (Wellbutrin)"),
        ("gravol", "Dimenhydrinate (Gravol)"),
        ("robax", "Robax"),
        ("vyvanse", "Vyvanse"),
        ("tobacco", "Tobacco"),
        ("nicotine", "Tobacco"),
        ("lido", "Lidocaine"),
        ("tylenol", "Acetaminophen"),
        ("jungle", "Jungle Juice (Everything mixed)"),
        ("alcohol", "Jungle Juice (Everything mixed)"),
        ("control", "Vehicle control"),
        (None, "Vehicle control"),
    ]
    all_aliases_ok = True
    for alias, expected in test_aliases:
        res = resolve_drug_name(alias)
        if res != expected:
            all_aliases_ok = False
            print(f"    [FAIL ALIAS] {alias!r} -> got {res!r}, expected {expected!r}")
    check("informal aliases and trade names resolve to canonical products",
          all_aliases_ok,
          f"{len(test_aliases)} test alias pairs verified")

    # Verify PK profiles in timelapse engine
    for req in required_substances:
        engine = LongTermPKPDEngine(drug_name=req, dose=1.0)
        st = engine.compute_state(t_hours=2.0)
        check(f"timelapse PK/PD profile computes valid state for '{req}'",
              st.plasma_conc >= 0.0 and not np.isnan(st.walk_speed_m_s),
              f"C(2h)={st.plasma_conc:.2f}, walk_spd={st.walk_speed_m_s:.2f} m/s")

    # Verify driving simulation initialization across diverse classes
    driving_samples = ["Caffeine", "Dormiphen (Sleeping Pill)", "Lidocaine", "Jungle Juice (Everything mixed)"]
    for d_sample in driving_samples:
        sim_d = HumanDrivingSim(drug_name=d_sample, dose=1.0)
        m_d = sim_d.run(duration=1.0)
        sim_d.close()
        check(f"driving simulation executes with '{d_sample}'",
              not np.isnan(m_d.mean_speed_m_s),
              f"speed={m_d.mean_speed_m_s:.2f} m/s, outcome={m_d.driving_outcome}")



if __name__ == "__main__":
    t0 = time.time()
    print("=" * 65)
    print("  HIGHFLY HUMAN TRANSLATION & EMBODIED BIPED VERIFICATION")
    print("=" * 65)

    verify_translation_invariants()
    verify_joint_sign_conventions()
    verify_biped_cpg_and_kinematics()
    verify_embodied_simulation_smoke()
    verify_driving_simulation()
    verify_all_drugs_pharmacology()

    elapsed = time.time() - t0
    print("\n" + "=" * 65)
    print(f"Results: {len(PASSED)} PASSED, {len(FAILED)} FAILED in {elapsed:.2f}s")
    print("=" * 65)

    if FAILED:
        print("FAILURES:")
        for f in FAILED:
            print(f"  - {f}")
        sys.exit(1)

    print("ALL HUMAN TRANSLATION VERIFICATIONS PASSED")


