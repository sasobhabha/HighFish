#!/usr/bin/env python3
"""Automated batch test runner across all 17 canonical pharmacological agents + Vehicle Control.

Evaluates each substance across 4 integrated tiers:
1. Molecular & Receptor Pharmacology (PubChem CID, targets, neurotransmitter systems)
2. FlyWire Neural Connectome & Humanoid Intent Translation (DN firing, gait mode, motor tone)
3. 3D Humanoid Bipedal Locomotion (Forward speed, step symmetry, coordination, fall detection)
4. 3D Obstacle Course Driving Impairment (Speed, SDLP lane weaving, brake reaction time, collisions, outcome)
5. Pharmacokinetic & Chronobiological Profile (Half-life, peak concentration, fatigue / arousal at 2h & 12h)
"""

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sim.drug_engine import (
    list_products,
    drug_modulation,
    get_chemical_name,
    get_brand_name,
    format_drug_name,
    load_pharmacology,
)
from sim.neural_sim import FlyWireNeuralSim
from sim.human_translation import DNToHumanTranslator
from sim.human_pipeline import HumanPipelineSim
from sim.human_driving import HumanDrivingSim
from sim.long_term_timelapse import PK_PROFILES, LongTermPKPDEngine


def run_all_drugs_battery(
    human_walk_duration: float = 2.0,
    driving_duration: float = 35.0,
    verbose: bool = True,
) -> dict:
    products = list_products()
    # Add Vehicle control as the baseline
    test_conditions = ["Vehicle control"] + products

    results = []
    print(f"=================================================================")
    print(f"  RUNNING BATCH PHARMACOLOGICAL TEST BATTERY ({len(test_conditions)} CONDITIONS)")
    print(f"=================================================================\n")

    start_total_time = time.time()

    for idx, drug in enumerate(test_conditions, 1):
        is_control = (drug == "Vehicle control")
        chem_name = "Vehicle control (Baseline)" if is_control else get_chemical_name(drug)
        brand_name = "Vehicle control" if is_control else get_brand_name(drug)

        if verbose:
            print(f"[{idx:2d}/{len(test_conditions):2d}] Testing: {chem_name} (Brand: {brand_name})...", end="", flush=True)

        t0 = time.time()

        # 1. Molecular Modulation
        mod = drug_modulation(None if is_control else drug, dose=1.0)
        cid = mod.get("cid")
        systems = sorted(list(mod.get("fly_mapping", {}).keys()))
        human_targets = mod.get("human", {}).get("targets", []) if mod.get("human") else []

        # 2. Connectome & Human Intent Translation
        neural_sim = FlyWireNeuralSim()
        if mod.get("fly_mapping"):
            neural_sim.apply_drug(mod["fly_mapping"], mod.get("sim_params", {}))
        for _ in range(80):
            neural_sim.step()
        translator = DNToHumanTranslator()
        intent = translator.translate(neural_sim, mod)

        # 3. Humanoid Bipedal Locomotion Physics (MuJoCo)
        human_sim = HumanPipelineSim(drug_name=None if is_control else drug, dose=1.0)
        human_metrics, _ = human_sim.run(duration=human_walk_duration)
        human_sim.close()
        bm = human_metrics.get("body_metrics", {})

        # 4. 3D Obstacle Course Driving Impairment
        driving_sim = HumanDrivingSim(drug_name=None if is_control else drug, dose=1.0)
        drive_metrics = driving_sim.run(duration=driving_duration)

        # 5. Pharmacokinetic & Chronobiological State
        pk_info = {}
        if not is_control and drug in PK_PROFILES:
            pk_engine = LongTermPKPDEngine(drug_name=drug, dose=1.0)
            st_2h = pk_engine.compute_state(t_hours=2.0)
            st_12h = pk_engine.compute_state(t_hours=12.0)
            pk = PK_PROFILES[drug]
            pk_info = {
                "t_half_elim_h": pk.t_half_elim_h,
                "t_max_h": pk.t_max_h,
                "conc_2h_pct": round(st_2h.plasma_conc * 100, 1),
                "fatigue_2h_pct": round(st_2h.perceived_fatigue * 100, 1),
                "state_2h": st_2h.state_label,
                "conc_12h_pct": round(st_12h.plasma_conc * 100, 1),
                "fatigue_12h_pct": round(st_12h.perceived_fatigue * 100, 1),
                "state_12h": st_12h.state_label,
            }
        else:
            pk_info = {
                "t_half_elim_h": 0.0,
                "t_max_h": 0.0,
                "conc_2h_pct": 0.0,
                "fatigue_2h_pct": 18.0,
                "state_2h": "NORMAL STEADY LOCOMOTION",
                "conc_12h_pct": 0.0,
                "fatigue_12h_pct": 60.0,
                "state_12h": "CIRCADIAN NIGHT / FATIGUED",
            }

        elapsed = time.time() - t0

        record = {
            "index": idx,
            "canonical_name": drug,
            "chemical_name": chem_name,
            "brand_name": brand_name,
            "pubchem_cid": cid,
            "systems": systems,
            "human_targets": human_targets,
            "neural_intent": {
                "forward_drive": round(intent.forward_drive, 3),
                "cadence_hz": round(intent.cadence, 3),
                "stride_length_m": round(intent.stride_length, 3),
                "posture_height": round(intent.posture_height, 3),
                "coordination": round(intent.coordination, 3),
                "motor_tone": round(intent.motor_tone, 3),
                "gait_mode": intent.mode,
            },
            "humanoid_locomotion": {
                "vx_m_s": round(bm.get("vx_m_s", 0.0), 3),
                "straightness_index": round(bm.get("straightness_index", 0.0), 3),
                "step_symmetry": round(bm.get("step_symmetry", 0.0), 3),
                "biped_coordination": round(bm.get("biped_coordination_index", 0.0), 3),
                "fall_detected": bm.get("fall_detected", False),
            },
            "driving_impairment": {
                "outcome": drive_metrics.driving_outcome,
                "mean_speed_m_s": round(drive_metrics.mean_speed_m_s, 2),
                "mean_speed_kmh": round(drive_metrics.mean_speed_m_s * 3.6, 1),
                "peak_speed_kmh": round(drive_metrics.peak_speed_m_s * 3.6, 1),
                "sdlp_m": round(drive_metrics.sdlp_m, 3),
                "brake_reaction_time_ms": round(drive_metrics.brake_reaction_time_ms, 1),
                "cone_collisions": drive_metrics.cone_collisions,
                "npc_collisions": drive_metrics.npc_collisions,
                "course_completed": drive_metrics.course_completed,
            },
            "pharmacokinetics": pk_info,
            "test_elapsed_s": round(elapsed, 2),
        }
        results.append(record)

        if verbose:
            print(f" DONE in {elapsed:.2f}s | Walk: {record['humanoid_locomotion']['vx_m_s']:.2f} m/s | Drive: {drive_metrics.driving_outcome} ({record['driving_impairment']['mean_speed_kmh']} km/h)")

    total_elapsed = time.time() - start_total_time
    print(f"\nCompleted test battery for all {len(test_conditions)} conditions in {total_elapsed:.2f}s!\n")

    summary_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_conditions": len(results),
        "total_elapsed_seconds": round(total_elapsed, 2),
        "conditions": results,
    }

    # Save to JSON
    out_dir = ROOT_DIR / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "all_drugs_test_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Structured JSON report saved to: {json_path}")

    # Save to Markdown
    md_path = out_dir / "all_drugs_test_report.md"
    md_content = generate_markdown_report(summary_data)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Formatted Markdown report saved to: {md_path}")

    # Also update artifact directory
    artifact_dir = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
    if artifact_dir.exists():
        (artifact_dir / "ALL_DRUGS_TEST_REPORT.md").write_text(md_content, encoding="utf-8")
        print(f"Artifact report saved to: {artifact_dir / 'ALL_DRUGS_TEST_REPORT.md'}")

    return summary_data


def generate_markdown_report(data: dict) -> str:
    lines = [
        "# HighFly Pharmacological Test Battery Report: All 17 Drugs + Baseline Control",
        "",
        f"- **Generated At**: `{data['timestamp']}`",
        f"- **Conditions Evaluated**: `{data['total_conditions']}` (17 Canonical Substances + Vehicle Baseline)",
        f"- **Total Benchmark Execution Time**: `{data['total_elapsed_seconds']:.2f}s`",
        f"- **Simulation Engine**: MuJoCo 3.9.0 + FlyWire v783 Connectome (139,255 Neurons | 1,305 DNs)",
        "",
        "---",
        "",
        "## 1. Executive Summary Table",
        "",
        "| # | Chemical Compound | Brand Name | PubChem CID | Biped Walk $v_x$ (m/s) | Gait Mode | Driving Outcome | SDLP (m) | Brake RT (ms) | Peak Drive (km/h) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for c in data["conditions"]:
        idx = c["index"]
        chem = c["chemical_name"]
        brand = c["brand_name"]
        cid = str(c["pubchem_cid"]) if c["pubchem_cid"] is not None else "N/A"
        walk_v = c["humanoid_locomotion"]["vx_m_s"]
        mode = c["neural_intent"]["gait_mode"]
        outcome = c["driving_impairment"]["outcome"]
        sdlp = c["driving_impairment"]["sdlp_m"]
        brt = c["driving_impairment"]["brake_reaction_time_ms"]
        peak_spd = c["driving_impairment"]["peak_speed_kmh"]
        lines.append(f"| {idx} | **{chem}** | *{brand}* | {cid} | {walk_v:.2f} | `{mode}` | `{outcome}` | {sdlp:.3f} | {brt:.0f} | {peak_spd:.1f} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Detailed Pharmacological & Locomotor Profiles",
        "",
    ])

    for c in data["conditions"]:
        chem = c["chemical_name"]
        brand = c["brand_name"]
        cid = c["pubchem_cid"]
        systems = ", ".join(c["systems"]) if c["systems"] else "none / no verified fly ortholog"
        targets = "; ".join(c["human_targets"][:4]) if c["human_targets"] else "None (Vehicle Control)"

        ni = c["neural_intent"]
        hl = c["humanoid_locomotion"]
        di = c["driving_impairment"]
        pk = c["pharmacokinetics"]

        lines.extend([
            f"### {c['index']}. {chem}",
            f"- **Brand Name**: *{brand}*",
            f"- **PubChem CID**: `{cid}`",
            f"- **Fly Receptor Systems**: `{systems}`",
            f"- **Human Molecular Targets**: {targets}",
            "",
            "#### Neural Intent & Bipedal Walking",
            f"- **Gait Mode**: `{ni['gait_mode']}` | **Motor Tone**: `{ni['motor_tone']:.2f}` | **Posture Height**: `{ni['posture_height']:.2f}`",
            f"- **Biped Forward Velocity**: `{hl['vx_m_s']:.3f} m/s` (Straightness: `{hl['straightness_index']:.2f}`, Step Symmetry: `{hl['step_symmetry']:.2f}`)",
            f"- **Coordination Index**: `{hl['biped_coordination']:.2f}` | **Fall Detected**: `{hl['fall_detected']}`",
            "",
            "#### 3D Obstacle Course Driving Impairment",
            f"- **Course Outcome**: `{di['outcome']}` (Course Completed: `{di['course_completed']}`)",
            f"- **Forward Speed**: Mean `{di['mean_speed_kmh']:.1f} km/h` (`{di['mean_speed_m_s']:.2f} m/s`) | Peak `{di['peak_speed_kmh']:.1f} km/h`",
            f"- **Lateral Lane Weaving (SDLP)**: `{di['sdlp_m']:.3f} m`",
            f"- **Emergency Brake Reaction Time (BRT)**: `{di['brake_reaction_time_ms']:.1f} ms`",
            f"- **Impacts**: Pylon/Cone Hits: `{di['cone_collisions']}` | NPC Bot Collisions: `{di['npc_collisions']}`",
            "",
            "#### Pharmacokinetics & Chronobiology",
            f"- **Elimination Half-life ($t_{{1/2}}$)**: `{pk['t_half_elim_h']}h` | **Time to Peak ($T_{{\\max}}$)**: `{pk['t_max_h']}h`",
            f"- **At $T+2.0\\text{{h}}$**: Plasma Conc: `{pk['conc_2h_pct']}%` | Perceived Fatigue: `{pk['fatigue_2h_pct']}%` | State: `{pk['state_2h']}`",
            f"- **At $T+12.0\\text{{h}}$**: Plasma Conc: `{pk['conc_12h_pct']}%` | Perceived Fatigue: `{pk['fatigue_12h_pct']}%` | State: `{pk['state_12h']}`",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


if __name__ == "__main__":
    run_all_drugs_battery()
