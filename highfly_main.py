#!/usr/bin/env python3
"""HighFly main CLI (invoked by the ./highfly bash launcher, which selects the
correct interpreter: .venv3/bin/python for headless modes, .venv3/bin/mjpython
for live-viewer modes on macOS)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def cmd_list(argv=None):
    import argparse
    from sim.drug_engine import load_pharmacology, format_drug_name

    ap = argparse.ArgumentParser(prog="highfly list")
    ap.add_argument("--brand", action="store_true", help="display commercial brand names instead of pure chemical names")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    ph = load_pharmacology()
    count = len(ph["products"])
    mode_str = "commercial brand names" if a.brand else "chemical compounds"
    print(f"Available {mode_str} ({count}) - fly-level receptor mapping:\n")
    for name, p in ph["products"].items():
        mapping = p["fly"].get("mapping") or {}
        systems = ", ".join(sorted(mapping)) if mapping else "no fly target (no-op)"
        cid = p.get("cid")
        display_name = format_drug_name(name, use_brand=a.brand)
        print(f"  {display_name:36s} PubChem CID: {str(cid):>10s}  ->  {systems}")
    print("\nAll mappings are citation-keyed in citations.md; entries marked")
    print("'no fly target' have NO verified Drosophila ortholog and are modeled")
    print("as vehicle controls rather than guessed effects.")


def _select_drug(use_brand: bool = False):
    from sim.drug_engine import list_products, format_drug_name
    prods = list_products()
    title = "Select a drug/product (Brand names):" if use_brand else "Select a drug/chemical:"
    print(f"\n{title}\n")
    for i, p in enumerate(prods, 1):
        print(f"  {i:2d}. {format_drug_name(p, use_brand=use_brand)}")
    print(f"  {len(prods)+1:2d}. Vehicle control (no drug)")
    while True:
        try:
            choice = input(f"\nChoice [1-{len(prods)+1}]: ").strip()
            idx = int(choice)
            if 1 <= idx <= len(prods):
                return prods[idx - 1]
            if idx == len(prods) + 1:
                return None
        except (ValueError, EOFError):
            pass
        print("  invalid choice, try again")


def _select_stimuli():
    print("\nEnvironment stimuli (reaction-time assays):")
    print("  1. none")
    print("  2. food (odor source - approach assay)")
    print("  3. predator (looming visual stimulus - escape assay)")
    print("  4. both")
    while True:
        c = input("Choice [1-4] (default 1): ").strip() or "1"
        if c in {"1", "2", "3", "4"}:
            return {"1": (False, False), "2": (True, False),
                    "3": (False, True), "4": (True, True)}[c]


def _run_viewer(drug, dose, duration, food, predator, timelapse=1.0, use_brand=False):
    from sim.body_sim import DrugBodySim
    from sim.stimuli import StimulusConfig

    cfg = StimulusConfig(food=food, predator=predator)
    schedule = []
    if food:
        schedule.append((1.0, "food"))
    if predator:
        schedule.append((4.0, "predator"))

    from sim.drug_engine import format_drug_name
    display_name = format_drug_name(drug, use_brand=use_brand)
    print(f"\nbuilding simulation (compound={display_name!r}, dose={dose}, "
          f"food={food}, predator={predator}, timelapse={timelapse}x)...")
    print("neural net: FlyWire v783 connectome | 139,255 neurons | 1,305 DNs")
    s = DrugBodySim(drug_name=drug, dose=dose, stim_cfg=cfg)

    import mujoco
    import mujoco.viewer
    print("opening live viewer - camera follows the fly; drag to orbit, "
          "scroll to zoom, close window to stop\n")
    metrics = None
    try:
        with mujoco.viewer.launch_passive(s.sim.mj_model, s.sim.mj_data) as v:
            # default free camera frames the whole 2-m arena -> a 1-mm fly is a
            # sub-pixel dot. Snap the view to the fly-following close-up camera.
            try:
                camid = mujoco.mj_name2id(s.sim.mj_model,
                                          mujoco.mjtObj.mjOBJ_CAMERA,
                                          s.track_cam_name)
                if camid >= 0:
                    v.cam.type = int(mujoco.mjtCamera.mjCAMERA_FIXED)
                    v.cam.fixedcamid = camid
            except Exception as e:  # noqa: BLE001 - cosmetic only
                print(f"(could not select tracking camera: {e})")
            try:
                metrics, _ = s.run(duration=duration, viewer=v,
                                   stim_schedule=schedule, terminate_on="any",
                                   timelapse=timelapse)
            except KeyboardInterrupt:
                print("\nstopped early")
    finally:
        pass
    if metrics is None:
        print("viewer closed early; computing metrics for the full duration headless...")
        s2 = DrugBodySim(drug_name=drug, dose=dose, stim_cfg=cfg)
        metrics, _ = s2.run(duration=duration, stim_schedule=schedule,
                            terminate_on="any", timelapse=timelapse)
        s2.close()

    print("\n=== Trial metrics (PDF Eqs. 9-13) ===")
    for k in ("vx_mm_s", "straightness_index", "tripod_coordination_index",
              "mean_dn_rate", "para_scale", "phi_gaba_effective"):
        if k in metrics:
            print(f"  {k:28s} {metrics[k]:.4f}")
    sp = metrics.get("speed_profile") or {}
    if sp:
        print(f"  {'speed mean/peak/p90':28s} {sp.get('mean_mm_s',0):.1f} / "
              f"{sp.get('peak_mm_s',0):.1f} / {sp.get('p90_mm_s',0):.1f} mm/s")
    sv = metrics.get("survival") or {}
    if sv:
        status = "DEAD" if not sv.get("alive", True) else "alive"
        print(f"  {'survival':28s} {status}"
              + (f" at t={sv['death_t']:.1f}s ({sv.get('death_cause')})" if not sv.get("alive", True) else ""))
        print(f"  {'flips / rightings / upright%':28s} {sv.get('n_flips',0)} / "
              f"{sv.get('n_rightings',0)} / {100*sv.get('upright_fraction',1):.0f}%")
    # trial verdict + per-trial data output
    print("\n=== TRIAL OUTCOME ===")
    if metrics.get("outcome") == "death":
        sv = metrics.get("survival") or {}
        print(f"  *** DIED ***  flipped (supine) >= 10 s — death at t={sv.get('death_t')}s"
              f"  [report: {metrics.get('report_path')}]")
    elif metrics.get("outcome") == "survived":
        reach = next((e["t"] for e in metrics.get("stimulus_events", [])
                      if e.get("event") == "food_reached"), None)
        print(f"  *** SURVIVED ***  reached the food at t={reach}s"
              f"  [report: {metrics.get('report_path')}]")
    else:
        print(f"  trial completed (no food reach, alive)  [report: {metrics.get('report_path')}]")

    if metrics.get("reaction_times"):
        print("  --- reaction times ---")
        for rt in metrics["reaction_times"]:
            lat = rt.get("latency")
            lat_s = f"{lat*1000:.0f} ms" if lat is not None else "no response (freeze)"
            print(f"  {rt['mode']:8s} at t={rt['t']:.2f}s  latency: {lat_s}")
    if metrics.get("stimulus_events"):
        print("  --- stimulus events ---")
        for e in metrics["stimulus_events"]:
            print(f"  {e['event']:18s} t={e['t']:.2f}s")


def cmd_run(argv=None):
    """Interactive (or flag-driven) selection, then live viewer."""
    import argparse
    ap = argparse.ArgumentParser(prog="highfly run")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=20.0)
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    ap.add_argument("--timelapse", "--speedup", dest="timelapse", type=float, default=1.0,
                    help="timelapse speedup multiplier (e.g., 2.0, 5.0, 10.0; default 1.0 = real-time)")
    ap.add_argument("--brand", action="store_true",
                    help="display commercial brand names in interactive menus")
    ap.add_argument("--no-prompt", action="store_true",
                    help="skip menus; use flags/defaults (viewer still opens)")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    drug, dose, duration, food, predator, timelapse = a.drug, a.dose, a.duration, a.food, a.predator, a.timelapse
    if not a.no_prompt:
        if drug is None and "--drug" not in sys.argv:
            drug = _select_drug(use_brand=a.brand)
        if "--drug" in sys.argv and drug is None:
            drug = None
        food2, predator2 = _select_stimuli()
        if not a.food and not a.predator:
            food, predator = food2, predator2
        d_s = input("Dose [0-1] (default 1.0): ").strip() or str(dose)
        t_s = input("Duration in simulated seconds (default 20): ").strip() or str(duration)
        tl_s = input("Timelapse speedup multiplier (default 1.0 = real time, 5.0 = 5x faster): ").strip() or str(timelapse)
        try:
            dose = max(0.0, min(1.0, float(d_s)))
            duration = max(1.0, float(t_s))
            timelapse = max(0.1, float(tl_s))
        except ValueError:
            pass

    _run_viewer(drug, dose, duration, food, predator, timelapse=timelapse, use_brand=a.brand)


def cmd_metrics():
    import argparse
    from sim.body_sim import DrugBodySim
    from sim.stimuli import StimulusConfig

    ap = argparse.ArgumentParser()
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--no-stim", action="store_true")
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    a = ap.parse_args()
    cfg = StimulusConfig(food=a.food and not a.no_stim,
                         predator=a.predator and not a.no_stim)
    s = DrugBodySim(drug_name=a.drug, dose=a.dose, stim_cfg=cfg)
    schedule = []
    if cfg.food:
        schedule.append((1.0, "food"))
    if cfg.predator:
        schedule.append((1.0, "predator"))
    m, _ = s.run(duration=a.duration, stim_schedule=schedule,
                 terminate_on=("any" if (cfg.food or cfg.predator) else "none"))
    print(json.dumps(m, indent=2))
    s.close()


def _run_human_viewer(drug, dose, duration, food, predator, harness=True,
                      harness_support=1.0, headless=False, out_path=None, timelapse=1.0,
                      use_brand=False):
    from sim.human_pipeline import HumanPipelineSim
    from sim.stimuli import StimulusConfig

    cfg = StimulusConfig(food=food, predator=predator)
    schedule = []
    if food:
        schedule.append((1.0, "food"))
    if predator:
        schedule.append((4.0, "predator"))

    from sim.drug_engine import format_drug_name
    display_name = format_drug_name(drug, use_brand=use_brand)
    print(f"\nbuilding humanoid 3D simulation (compound={display_name!r}, dose={dose}, "
          f"food={food}, predator={predator}, harness_support={harness_support}, timelapse={timelapse}x)...")
    print("neural net: FlyWire v783 connectome | 139,255 neurons | 1,305 DNs -> HumanIntent -> Biped CPG")
    s = HumanPipelineSim(drug_name=drug, dose=dose, harness=harness,
                         harness_support=harness_support, stim_cfg=cfg)

    metrics = None
    if out_path:
        print(f"rendering {duration}s of humanoid 3D simulation to {out_path} (timelapse={timelapse}x)...")
        metrics, _ = s.render_video(out_path=out_path, duration=duration,
                                    stim_schedule=schedule, timelapse=timelapse)
        s.close()
    elif not headless:
        import mujoco
        import mujoco.viewer
        print("opening live 3D humanoid viewer - camera tracks the humanoid body; drag to orbit, "
              "scroll to zoom, close window to stop\n")
        try:
            with mujoco.viewer.launch_passive(s.body.mj_model, s.body.mj_data) as v:
                try:
                    camid = mujoco.mj_name2id(s.body.mj_model,
                                              mujoco.mjtObj.mjOBJ_CAMERA,
                                              s.body.track_cam_name)
                    if camid >= 0:
                        v.cam.type = int(mujoco.mjtCamera.mjCAMERA_FIXED)
                        v.cam.fixedcamid = camid
                except Exception as e:
                    print(f"(could not select tracking camera: {e})")
                try:
                    metrics, _ = s.run(duration=duration, viewer=v,
                                       stim_schedule=schedule, terminate_on="any",
                                       timelapse=timelapse)
                except KeyboardInterrupt:
                    print("\nstopped early")
        except Exception as e:
            print(f"(could not open graphical viewer: {e}; falling back to headless execution)")
            headless = True

    if metrics is None:
        if headless:
            print(f"running humanoid simulation headless for {duration}s (timelapse={timelapse}x)...")
        metrics, _ = s.run(duration=duration, stim_schedule=schedule,
                           terminate_on="any", timelapse=timelapse)
        s.close()

    # Pretty-print metrics
    print("\n=== Humanoid Locomotion & Intent Metrics ===")
    bm = metrics.get("body_metrics", {})
    im = metrics.get("intent_summary", {})
    for k in ("vx_m_s", "straightness_index", "step_symmetry", "biped_coordination_index",
              "com_height_mean", "harness_load_mean_n", "fall_detected"):
        if k in bm:
            print(f"  {k:28s} {bm[k]}")
    for k in ("mean_forward_drive", "mean_cadence", "mean_stride_length",
              "mean_posture_height", "mean_coordination", "mean_motor_tone", "final_mode"):
        if k in im:
            print(f"  {k:28s} {im[k]}")
    if "timelapse_factor" in metrics:
        print(f"  {'timelapse_factor':28s} {metrics['timelapse_factor']}x")
    if "video_duration_s" in metrics:
        print(f"  {'video_duration_s':28s} {metrics['video_duration_s']}s")
    print(f"  {'mean_sync_error':28s} {metrics.get('mean_sync_error', 0.0)}")
    print(f"  {'outcome':28s} {metrics.get('outcome', 'completed')}")


def cmd_human(argv=None):
    """Interactive (or flag-driven) selection, then live 3D humanoid viewer."""
    import argparse
    ap = argparse.ArgumentParser(prog="highfly human")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=20.0)
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    ap.add_argument("--harness-support", type=float, default=1.0)
    ap.add_argument("--no-harness", action="store_true")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--timelapse", "--speedup", dest="timelapse", type=float, default=1.0,
                    help="timelapse speedup multiplier (e.g. 2.0, 5.0, 10.0; default 1.0 = real-time)")
    ap.add_argument("--brand", action="store_true",
                    help="display commercial brand names in interactive menus")
    ap.add_argument("--out", default=None, help="render offscreen to video file (.mp4 or .gif)")
    ap.add_argument("--no-prompt", action="store_true",
                    help="skip menus; use flags/defaults")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    drug, dose, duration, food, predator, timelapse = a.drug, a.dose, a.duration, a.food, a.predator, a.timelapse
    if not a.no_prompt and a.out is None:
        if drug is None and "--drug" not in sys.argv:
            drug = _select_drug(use_brand=a.brand)
        if "--drug" in sys.argv and drug is None:
            drug = None
        food2, predator2 = _select_stimuli()
        if not a.food and not a.predator:
            food, predator = food2, predator2
        d_s = input("Dose [0-1] (default 1.0): ").strip() or str(dose)
        t_s = input("Duration in simulated seconds (default 20): ").strip() or str(duration)
        tl_s = input("Timelapse speedup multiplier (default 1.0 = real time, 5.0 = 5x faster): ").strip() or str(timelapse)
        try:
            dose = max(0.0, min(1.0, float(d_s)))
            duration = max(1.0, float(t_s))
            timelapse = max(0.1, float(tl_s))
        except ValueError:
            pass

    _run_human_viewer(
        drug=drug,
        dose=dose,
        duration=duration,
        food=food,
        predator=predator,
        harness=not a.no_harness,
        harness_support=a.harness_support,
        headless=a.headless,
        out_path=a.out,
        timelapse=timelapse,
        use_brand=a.brand,
    )


def cmd_human_metrics(argv=None):
    import argparse
    from sim.human_pipeline import HumanPipelineSim
    from sim.stimuli import StimulusConfig

    ap = argparse.ArgumentParser(prog="highfly human-metrics")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--no-stim", action="store_true")
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    ap.add_argument("--harness-support", type=float, default=1.0)
    ap.add_argument("--no-harness", action="store_true")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    cfg = StimulusConfig(food=a.food and not a.no_stim,
                         predator=a.predator and not a.no_stim)
    s = HumanPipelineSim(drug_name=a.drug, dose=a.dose,
                         harness=not a.no_harness,
                         harness_support=a.harness_support,
                         stim_cfg=cfg)
    schedule = []
    if cfg.food:
        schedule.append((1.0, "food"))
    if cfg.predator:
        schedule.append((1.0, "predator"))
    m, _ = s.run(duration=a.duration, stim_schedule=schedule,
                 terminate_on=("any" if (cfg.food or cfg.predator) else "none"))
    print(json.dumps(m, indent=2))
    s.close()


def cmd_human_intent(argv=None):
    import argparse
    from dataclasses import asdict
    from sim.neural_sim import FlyWireNeuralSim
    from sim.human_translation import DNToHumanTranslator
    from sim.drug_engine import drug_modulation

    ap = argparse.ArgumentParser(prog="highfly human-intent")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--steps", type=int, default=100)
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    mod = drug_modulation(a.drug, a.dose)
    sim = FlyWireNeuralSim()
    if mod.get("fly_mapping"):
        sim.apply_drug(mod["fly_mapping"], mod.get("sim_params", {}))
    for _ in range(a.steps):
        sim.step()
    tr = DNToHumanTranslator()
    intent = tr.translate(sim, mod)
    out = {
        "drug": a.drug,
        "dose": a.dose,
        "steps": a.steps,
        "intent": asdict(intent),
    }
    print(json.dumps(out, indent=2))


def cmd_timelapse(argv=None):
    """Long-term pharmacokinetic & chronobiological drug timelapse across hours/days."""
    import argparse
    from sim.long_term_timelapse import generate_long_term_timelapse, PK_PROFILES
    from sim.drug_engine import format_drug_name

    ap = argparse.ArgumentParser(prog="highfly timelapse")
    ap.add_argument("--drug", default=None, help="Drug/chemical name (e.g., 'caffeine', 'diphenhydramine', 'lidocaine')")
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--hours", type=float, default=24.0, help="Total chronological hours to simulate (default 24.0)")
    ap.add_argument("--out", default=None, help="Output video file path (.mp4 or .gif)")
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--brand", action="store_true", help="display commercial brand names in selection menu")
    ap.add_argument("--no-prompt", action="store_true")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    drug = a.drug
    if not a.no_prompt and drug is None and "--drug" not in sys.argv:
        title = "Select a drug/product (Brand names):" if a.brand else "Select a chemical for long-term chronobiological timelapse:"
        print(f"\n{title}\n")
        keys = list(PK_PROFILES.keys())
        for i, k in enumerate(keys, 1):
            print(f"  {i:2d}. {format_drug_name(k, use_brand=a.brand)}")
        ch = input(f"\nChoice [1-{len(keys)}] (default 1): ").strip() or "1"
        try:
            drug = keys[int(ch) - 1]
        except (ValueError, IndexError):
            drug = "Caffeine"
    if drug is None:
        drug = "Caffeine"

    clean_name = drug.split()[0].lower()
    ext = ".gif" if (a.out and a.out.lower().endswith(".gif")) else ".mp4"
    out = a.out or f"out/long_term_{clean_name}_{int(a.hours)}h{ext}"

    generate_long_term_timelapse(
        drug_name=drug,
        dose=a.dose,
        total_hours=a.hours,
        fps=a.fps,
        out_path=out,
    )


def cmd_drive(argv=None):
    """3D Human Driving Mode: Neuro-pharmacological impairment on an obstacle course with NPC bots."""
    import argparse
    from sim.human_driving import HumanDrivingSim, resolve_drug_name
    from sim.drug_engine import format_drug_name

    ap = argparse.ArgumentParser(prog="highfly drive")
    ap.add_argument("--drug", default=None, help="drug/product to test (e.g. caffeine, dormiphen, gaba, lidocaine)")
    ap.add_argument("--dose", type=float, default=1.0, help="dose in (0, 1] (default: 1.0)")
    ap.add_argument("--duration", type=float, default=100.0, help="duration in simulated seconds (default: 100.0)")
    ap.add_argument("--timelapse", "--speedup", dest="timelapse", type=float, default=1.0,
                    help="timelapse speedup multiplier (default: 1.0 = real-time)")
    ap.add_argument("--brand", action="store_true", help="display commercial brand names in selection menu and metrics")
    ap.add_argument("--out", default=None, help="render offscreen to video file (.mp4 or .gif)")
    ap.add_argument("--headless", action="store_true", help="run headless without opening a window")
    ap.add_argument("--no-prompt", action="store_true", help="skip interactive menus; use flags/defaults")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    drug = a.drug
    dose = a.dose
    duration = a.duration
    timelapse = a.timelapse

    if not a.no_prompt and a.out is None and drug is None and "--drug" not in sys.argv:
        drug = _select_drug(use_brand=a.brand)
        d_s = input("Dose [0-1] (default 1.0): ").strip() or str(dose)
        t_s = input("Duration in simulated seconds (default 100): ").strip() or str(duration)
        tl_s = input("Timelapse multiplier (default 1.0 = real-time, 2.0 = 2x faster): ").strip() or str(timelapse)
        try:
            dose = max(0.0, min(1.0, float(d_s)))
            duration = max(1.0, float(t_s))
            timelapse = max(0.1, float(tl_s))
        except ValueError:
            pass

    resolved_drug = resolve_drug_name(drug)
    chem_display = format_drug_name(resolved_drug, use_brand=a.brand)
    print(f"\nInitializing 3D Human Driving Simulation for '{chem_display}' (dose={dose:.1f})...")
    sim = HumanDrivingSim(drug_name=drug, dose=dose)

    if a.out is not None:
        print(f"Rendering driving test offscreen to '{a.out}' (duration={duration}s, timelapse={timelapse}x)...")
        metrics, _ = sim.render_video(out_path=a.out, duration=duration, timelapse=timelapse)
    else:
        # GUI or headless execution
        viewer = None
        if not a.headless and os.environ.get("MUJOCO_HEADLESS", "0") != "1":
            try:
                import mujoco.viewer
                viewer = mujoco.viewer.launch_passive(sim.mj_model, sim.mj_data)
                try:
                    camid = mujoco.mj_name2id(sim.mj_model, mujoco.mjtObj.mjOBJ_CAMERA, "trackcam")
                    if camid >= 0:
                        viewer.cam.type = int(mujoco.mjtCamera.mjCAMERA_FIXED)
                        viewer.cam.fixedcamid = camid
                except Exception:
                    pass
                print("Running driving simulation in interactive 3D viewer (Press ESC in window to exit)...")
                metrics = sim.run(duration=duration, viewer=viewer, timelapse=timelapse)
            except Exception as e:
                print(f"(Could not launch graphical viewer: {e}; running headless)")
                metrics = sim.run(duration=duration, timelapse=timelapse)
        else:
            print(f"Running driving simulation headless for {duration}s...")
            metrics = sim.run(duration=duration, timelapse=timelapse)

    metric_hdr = "Drug / Brand" if a.brand else "Compound / Chemical"
    print("\n=== Clinical Driving Impairment Metrics (FDA / NHTSA Standards) ===")
    print(f"  {metric_hdr:28s} {format_drug_name(metrics.drug_name, use_brand=a.brand)} (Dose: {metrics.dose:.1f})")
    print(f"  {'Course Outcome':28s} {metrics.driving_outcome}")
    print(f"  {'SDLP (Lane Weaving)':28s} {metrics.sdlp_m:.3f} m")
    print(f"  {'Brake Reaction Time':28s} {metrics.brake_reaction_time_ms:.1f} ms")
    print(f"  {'Mean Forward Speed':28s} {metrics.mean_speed_m_s:.2f} m/s ({metrics.mean_speed_m_s*3.6:.1f} km/h)")
    print(f"  {'Peak Speed':28s} {metrics.peak_speed_m_s:.2f} m/s ({metrics.peak_speed_m_s*3.6:.1f} km/h)")
    print(f"  {'Pylon / Cone Collisions':28s} {metrics.cone_collisions}")
    print(f"  {'NPC Vehicle Crashes':28s} {metrics.npc_collisions}")
    print(f"  {'Off-Road Excursions':28s} {metrics.off_road_excursions}")
    print(f"  {'Course Completed':28s} {metrics.course_completed}")
    return metrics


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"run", ""}:
        cmd_run(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "_view":
        # legacy internal mode: behave like run with explicit flags
        cmd_run(sys.argv[2:])
    elif sys.argv[1] == "list":
        cmd_list(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "metrics":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        cmd_metrics()
    elif sys.argv[1] == "human":
        cmd_human(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "human-metrics":
        cmd_human_metrics(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "human-intent":
        cmd_human_intent(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "timelapse":
        cmd_timelapse(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "drive":
        cmd_drive(sys.argv[2:] if len(sys.argv) > 2 else [])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

