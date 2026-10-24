#!/usr/bin/env python3
"""Reflex Lab -- an interactive virtual-hospital mini-game.

The user examines a simulated patient (vehicle or any drug from the
catalog) and runs classic bedside reflex tests against a vehicle control
measured in the same session:

  [1] Patellar tendon tap (L2-L4 quadriceps reflex)   -- live MuJoCo biped
  [2] Pupillary light reflex (CN II / III)             -- pharmacology model
  [3] Looming visual threat (startle)                  -- live Fish1 network

Everything shown is produced by the same simulation stack that powers the
research benchmarks (Zebrafish Fish1 connectome rate network -> hindbrain
readout -> biped CPG -> MuJoCo humanoid physics). Values are model outputs,
not clinical measurements; the chart says so explicitly.
"""
import os
import sys
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sim.human_pipeline import HumanPipelineSim, PHYSICS_DT
from sim.drug_engine import list_products, drug_modulation, format_drug_name
from sim.fish_readout import HumanIntent

LINE = "-" * 62
SNAP_DIR = os.path.join(ROOT, "results", "reflex_lab")

# Clinical reference bands (healthy adult norms; Winter Ch. 4 / clinical texts)
NORM = {
    "tap_peak_dev_rad": 0.55,      # healthy swing after a tendon tap
    "tap_recovery_s": 0.45,        # healthy return half-time
    "pupil_latency_ms": 250.0,
    "pupil_amplitude_pct": 0.40,
    "startle_latency_ms": 280.0,   # looming escape (tachometric)
}


# ---------------------------------------------------------------- helpers
def _open_visual(path):
    """Opens the rendered exam media in the OS viewer (macOS `open`)."""
    try:
        if sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print(f"  saved          : {path}")


def _record_exam_gif(pipeline, tap_jid, tap_step, out_name, n_steps):
    """Renders the pedestal exam as an animated GIF (visual lab)."""
    import mujoco
    import imageio
    os.makedirs(SNAP_DIR, exist_ok=True)
    out_path = os.path.join(SNAP_DIR, out_name)
    b = pipeline.body
    renderer = mujoco.Renderer(b.mj_model, 480, 640)
    frames = []
    intent = None
    for step in range(n_steps):
        if step % 10 == 0:
            pipeline.neural.step()
            intent = replace(_intent_now(pipeline), mode="stand", freeze=True,
                             forward_drive=0.0)
        pl, pr = pipeline.cpg.step(PHYSICS_DT, intent)
        targets = pipeline.kin.compute_joint_targets(PHYSICS_DT, pl, pr, intent)
        if step == tap_step and tap_jid is not None:
            b.mj_data.qvel[b.mj_model.jnt_dofadr[tap_jid]] += 2.5
        b.step(targets)
        if step % 6 == 0:
            renderer.update_scene(b.mj_data, camera="trackcam")
            frames.append(renderer.render())
    imageio.mimsave(out_path, frames, fps=12, loop=0)
    renderer.close()
    return out_path


def _ask(prompt, default=None):
    try:
        raw = input(prompt).strip()
    except EOFError:
        return None
    return raw if raw else default


def _spark(vals, width=40):
    """ASCII trend of a scalar series."""
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1e-9
    ticks = " .'\"^~*oxOX#"
    idx = [min(len(ticks) - 1, int(abs(v - lo) / rng * (len(ticks) - 1))) for v in vals]
    return "|".join(ticks[i] for i in idx)


def _select_patient():
    """Menu: vehicle or any catalog drug. Returns (drug_name, dose)."""
    print(f"\n{LINE}\n CHECK-IN: choose a patient\n{LINE}")
    prods = list_products()
    for i, p in enumerate(prods, 1):
        print(f"  {i:2d}. {format_drug_name(p)}")
    print(f"  {len(prods) + 1:2d}. Vehicle control (no drug)")
    choice = _ask(f"\nPatient [1-{len(prods) + 1}]: ")
    try:
        idx = int(choice)
    except (TypeError, ValueError):
        idx = len(prods) + 1
    drug = None
    if 1 <= idx <= len(prods):
        drug = prods[idx - 1]
        doses = _ask("Dose (normal=1.0, e.g. 0.5 half / 2.0 double) [1.0]: ")
        try:
            dose = max(0.05, float(doses))
        except (TypeError, ValueError):
            dose = 1.0
    else:
        dose = 0.0
    return drug, dose


def _intent_now(pipeline):
    """Capture the drug state's current motor intent (network already warm)."""
    return pipeline.translator.translate(pipeline.neural, pipeline.mod,
                                         pipeline.stim_mgr)


def _intent_snapshot(pipeline):
    """Warm neural net and capture the drug state's motor intent."""
    for _ in range(40):
        pipeline.neural.step()
    return _intent_now(pipeline)


# ------------------------------------------------------- 1. patellar tap
def _knee_tap(drug, dose):
    """Runs a standing trial; taps the left patellar tendon mid-trial.

    The tap is a 2.5 rad/s knee-stretch impulse (tendon tap). The measured
    'reflex' is the stretch-hold response of the tone-scaled quadriceps
    servo: swing amplitude, time-to-peak, and recovery half-time.
    """
    p = HumanPipelineSim(drug_name=drug, dose=dose, harness=True)
    b = p.body
    jid = mujoco_name2id(b, "left_knee")
    qadr = b.mj_model.jnt_qposadr[jid]

    dur, tap_t = 2.6, 0.8
    n = int(dur / PHYSICS_DT)
    angles, times = [], []
    intent = HumanIntent(forward_drive=0.0, turn_intent=0.0, cadence=0.0,
                         stride_length=0.0, posture_height=1.0,
                         coordination=1.0, motor_tone=1.0, flee_drive=0.0,
                         freeze=True, mode="stand")
    for i in range(n):
        t = i * PHYSICS_DT
        if i % 10 == 0:                       # drug tone, 50 Hz like run()
            p.neural.step()
            intent = replace(
                _intent_snapshot(p), mode="stand", freeze=True,
                forward_drive=0.0)
        pl, pr = p.cpg.step(PHYSICS_DT, intent)
        targets = p.kin.compute_joint_targets(PHYSICS_DT, pl, pr, intent)
        if abs(t - tap_t) < PHYSICS_DT / 2:   # the tap itself
            b.mj_data.qvel[b.mj_model.jnt_dofadr[jid]] += 2.5
        b.step(targets)
        times.append(t)
        angles.append(float(b.mj_data.qpos[qadr]))

    pre = float(sum(angles[int(0.5 / PHYSICS_DT):int(tap_t / PHYSICS_DT)])
                / max(1, int(tap_t / PHYSICS_DT) - int(0.5 / PHYSICS_DT)))
    i_tap = int(tap_t / PHYSICS_DT)
    post = angles[i_tap:]
    post_t = times[i_tap:]
    devs = [a - pre for a in post]
    peak = max(devs) if devs else 0.0
    t_peak = post_t[int(devs.index(peak))] if peak > 0.02 else None
    half_dev = peak / 2.0
    t_half = None
    if peak > 0.02:
        for d, tt in zip(devs, post_t):
            if d <= half_dev:
                t_half = tt - post_t[0]
                break
    return {"peak_dev": peak, "t_peak": t_peak, "t_half": t_half,
            "trace": [a - pre for a in post[::12]],
            "released": b.actuators_released}


def mujoco_name2id(body, joint):
    import mujoco
    return mujoco.mj_name2id(body.mj_model, mujoco.mjtObj.mjOBJ_JOINT, joint)


def _rate_tap(patient, control):
    """Clinical grade for a tap result vs the session's vehicle control."""
    if control["peak_dev"] <= 0.02:
        return "uninterpretable (control tap failed)"
    ratio = patient["peak_dev"] / control["peak_dev"]
    if patient["released"]:
        return "ABSENT (flaccid -- no reflex arc response)"
    if ratio > 1.35:
        return "BRISK / hyperreflexia"
    if ratio > 0.75:
        return "NORMAL"
    if ratio > 0.35:
        return "SLUGGISH / hyporeflexia"
    return "ABSENT / areflexia"


def run_tap(patient, dose, control):
    res = _knee_tap(patient, dose)
    grade = _rate_tap(res, control)
    # Visual lab: render the bedside tap as an animation and open it.
    gif_p = HumanPipelineSim(drug_name=patient, dose=dose, harness=True)
    gif = _record_exam_gif(
        gif_p,
        tap_jid=mujoco_name2id(gif_p.body, "left_knee"),
        tap_step=int(0.8 / PHYSICS_DT),
        out_name=f"tap_{(patient or 'vehicle').replace(' ', '_')}.gif",
        n_steps=int(2.6 / PHYSICS_DT))
    print(f"\n{LINE}\n PATELLAR TENDON TAP  (L2-L4 quadriceps reflex)\n{LINE}")
    print(f"  post-tap swing : {_spark(res['trace'])}")
    print(f"  peak swing     : {res['peak_dev']:.2f} rad"
          f"   (healthy ~{NORM['tap_peak_dev_rad']:.2f})")
    if res["t_peak"] is not None:
        print(f"  time-to-peak   : {res['t_peak'] * 1000:.0f} ms")
    print(f"  recovery 1/2   : {res['t_half'] * 1000:.0f} ms"
          if res["t_half"] is not None else "  recovery       : none within window")
    _open_visual(gif)
    print(f"  vehicle control: {control['peak_dev']:.2f} rad swing"
          f"  -> amplitude ratio "
          f"{(res['peak_dev'] / max(0.02, control['peak_dev'])):.2f}")
    print(f"  interpretation : {grade}")
    return res, grade


# --------------------------------------------------- 2. pupillary reflex
def run_pupil(drug, dose, intent):
    tone = float(intent.motor_tone)
    coord = float(intent.coordination)
    # Modeled photomotor arc: latency grows with neural state degradation
    # (tone represents descending drive), amplitude with arousal reserve.
    lat = NORM["pupil_latency_ms"] * (1.0 + 1.6 * (1.0 - tone) + 0.6 * (1.0 - coord))
    amp = NORM["pupil_amplitude_pct"] * coord * (0.25 + 0.75 * tone)
    if lat > 2.0 * NORM["pupil_latency_ms"] or amp < 0.05 * NORM["pupil_amplitude_pct"]:
        grade = "ABSENT / fixed pupils"
    elif lat > 1.4 * NORM["pupil_latency_ms"] or amp < 0.6 * NORM["pupil_amplitude_pct"]:
        grade = "SLUGGISH"
    elif lat < 0.8 * NORM["pupil_latency_ms"]:
        grade = "BRISK (pinpoint/dilated per drug chart)"
    else:
        grade = "NORMAL"
    trace = _spark([1.0 - amp * min(1.0, k / 8.0) for k in range(11)])
    print(f"\n{LINE}\n PUPILLARY LIGHT REFLEX  (CN II -> CN III)\n{LINE}")
    print(f"  constriction   : {trace}")
    print(f"  latency        : {lat:.0f} ms   (healthy ~{NORM['pupil_latency_ms']:.0f})")
    print(f"  amplitude      : {amp * 100:.0f}% constriction"
          f"   (healthy ~{NORM['pupil_amplitude_pct'] * 100:.0f}%)")
    print(f"  interpretation : {grade}")
    print(f"  (modeled from the drug's receptor state; no photomotor arc is")
    print(f"   wired into the fish connectome -- disclosed as such)")
    return {"latency_ms": lat, "amplitude": amp}, grade


# ------------------------------------------------------ 3. looming startle
def run_startle(drug, dose):
    p = HumanPipelineSim(drug_name=drug, dose=dose, harness=True)
    m, _ = p.run(duration=3.0, stim_schedule=[(1.0, "predator")],
                 terminate_on="fall")
    resp = [h for h in m.get("stimulus_events", []) if h["event"] == "escape_response"]
    if resp:
        mode = resp[-1].get("mode", "?")
        lat = resp[-1].get("latency")
        lat = None if lat is None else float(lat) * 1000.0
    else:
        lat, mode = None, "none"
    if lat is None:
        grade = "NO STARTLE (frozen or drive arrested)"
    elif lat <= 0.75 * NORM["startle_latency_ms"]:
        grade = "BRISK / exaggerated startle"
    elif lat <= 1.4 * NORM["startle_latency_ms"]:
        grade = "NORMAL"
    else:
        grade = "SLOW / impaired"
    print(f"\n{LINE}\n LOOMING VISUAL THREAT  (retina -> tectum -> Mauthner)\n{LINE}")
    print(f"  escape latency : {'--' if lat is None else f'{lat:.0f} ms'}"
          f"   (healthy ~{NORM['startle_latency_ms']:.0f})")
    print(f"  response mode  : {mode}")
    print(f"  interpretation : {grade}")
    print(f"  (fullFish1 connectome pathway -- genuinely simulated)")
    return {"latency_ms": lat, "mode": mode}, grade


# ------------------------------------------------------------------ game
def _patient_card(drug, dose, intent):
    mod = drug_modulation(drug, dose)
    print(f"\n{LINE}\n PATIENT CARD\n{LINE}")
    print(f"  drug / dose   : {format_drug_name(drug) if drug else 'Vehicle control'}"
          f"  (dose {dose:.2f})", )
    print(f"  motor tone    : {intent.motor_tone:.2f}")
    print(f"  coordination  : {intent.coordination:.2f}")
    print(f"  posture       : {intent.posture_height:.2f}")
    print(f"  mapped systems: {', '.join(sorted((mod.get('fish_mapping') or {}).keys())) or 'none (vehicle-like)'}")


def main():
    print("\n" + "=" * 62)
    print("  WELCOME TO THE VIRTUAL NEURO-REFLEX LAB")
    print("  bedside reflex tests on a simulated patient")
    print("=" * 62)
    print("  [1] patellar tendon tap   [2] pupillary light reflex")
    print("  [3] looming startle       [p] new patient  [q] quit")

    patient, dose = _select_patient()
    control = _knee_tap(None, 0.0)          # session vehicle baseline
    pipeline_intent = None
    results = []
    p = HumanPipelineSim(drug_name=patient, dose=dose, harness=True)

    while True:
        pipeline_intent = _intent_snapshot(p)
        _patient_card(patient, dose, pipeline_intent)
        choice = _ask("\nEXAM [1/2/3/p/q]: ")
        if choice is None or choice.lower() == "q":
            break
        if choice == "p":
            patient, dose = _select_patient()
            control = _knee_tap(None, 0.0)
            p = HumanPipelineSim(drug_name=patient, dose=dose, harness=True)
            continue
        if choice == "1":
            res, grade = run_tap(patient, dose, control)
            results.append(("patellar tap", grade))
        elif choice == "2":
            res, grade = run_pupil(patient, dose, pipeline_intent)
            results.append(("pupil reflex", grade))
        elif choice == "3":
            res, grade = run_startle(patient, dose)
            results.append(("looming startle", grade))
        else:
            print("  choose 1, 2, 3, p or q")

    print(f"\n{LINE}\n DISCHARGE SUMMARY\n{LINE}")
    for k, g in results:
        print(f"  {k:16s} -> {g}")
    print(f"\nAll values are model outputs from the Fish1-driven humanoid")
    print("stack (simulated examination, not a real clinical measurement).")
    print("Goodbye!\n")


if __name__ == "__main__":
    main()
