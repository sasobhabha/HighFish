#!/usr/bin/env python3
"""HighFish main CLI (invoked by the ./highfish bash launcher, which selects the
correct interpreter: .venv3/bin/python for headless modes, .venv3/bin/mjpython
for live-viewer modes on macOS).

Simulation stack:
  zebrafish Fish1 connectome rate network -> hindbrain readout -> HumanIntent
  -> 12-DOF humanoid biped CPG -> MuJoCo 3D physics.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def cmd_list(argv=None):
    import argparse
    from sim.drug_engine import load_pharmacology, format_drug_name

    ap = argparse.ArgumentParser(prog="highfish list")
    ap.add_argument("--brand", action="store_true", help="display commercial brand names instead of pure chemical names")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    ph = load_pharmacology()
    count = len(ph["products"])
    mode_str = "commercial brand names" if a.brand else "chemical compounds"
    print(f"Available {mode_str} ({count}) - zebrafish receptor mapping:\n")
    for name, p in ph["products"].items():
        mapping = p["fish"].get("mapping") or {}
        systems = ", ".join(sorted(mapping)) if mapping else "no fish target (no-op)"
        cid = p.get("cid")
        display_name = format_drug_name(name, use_brand=a.brand)
        print(f"  {display_name:36s} PubChem CID: {str(cid):>10s}  ->  {systems}")
    print("\nAll mappings are citation-keyed in citations.md; entries marked")
    print("'no fish target' have NO verified zebrafish ortholog and are modeled")
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


def _print_human_metrics(metrics: dict):
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


def _build_stim_cfg_schedule(food: bool, predator: bool):
    from sim.stimuli import StimulusConfig
    cfg = StimulusConfig(food=food, predator=predator)
    schedule = []
    if food:
        schedule.append((1.0, "food"))
    if predator:
        schedule.append((4.0, "predator"))
    return cfg, schedule


def _run_human_viewer(drug, dose, duration, food, predator, harness=True,
                      harness_support=1.0, headless=False, out_path=None, timelapse=1.0,
                      use_brand=False):
    from sim.human_pipeline import HumanPipelineSim

    cfg, schedule = _build_stim_cfg_schedule(food, predator)

    from sim.drug_engine import format_drug_name
    display_name = format_drug_name(drug, use_brand=use_brand)
    print(f"\nbuilding humanoid 3D simulation (compound={display_name!r}, dose={dose}, "
          f"food={food}, predator={predator}, harness_support={harness_support}, timelapse={timelapse}x)...")
    print("neural net: Fish1 zebrafish connectome (Petkova 2025) -> hindbrain readout -> HumanIntent -> Biped CPG")
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

    _print_human_metrics(metrics)


def cmd_run(argv=None):
    """Interactive (or flag-driven) selection, then live 3D humanoid viewer."""
    import argparse
    ap = argparse.ArgumentParser(prog="highfish run")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=20.0)
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    ap.add_argument("--harness-support", type=float, default=1.0)
    ap.add_argument("--no-harness", action="store_true")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--timelapse", "--speedup", dest="timelapse", type=float, default=1.0,
                    help="timelapse speedup multiplier (e.g., 2.0, 5.0, 10.0; default 1.0 = real-time)")
    ap.add_argument("--brand", action="store_true",
                    help="display commercial brand names in interactive menus")
    ap.add_argument("--out", default=None, help="render offscreen to video file (.mp4 or .gif)")
    ap.add_argument("--no-prompt", action="store_true",
                    help="skip menus; use flags/defaults (viewer still opens)")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    drug, dose, duration, food, predator, timelapse = a.drug, a.dose, a.duration, a.food, a.predator, a.timelapse
    if not a.no_prompt:
        if drug is None and "--drug" not in sys.argv:
            drug = _select_drug(use_brand=a.brand)
        if "--drug" in sys.argv and drug is None:
            drug = None
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


def cmd_human(argv=None):
    """Interactive (or flag-driven) selection, then live 3D humanoid viewer."""
    cmd_run(argv)


def cmd_human_metrics(argv=None):
    import argparse
    from sim.human_pipeline import HumanPipelineSim

    ap = argparse.ArgumentParser(prog="highfish human-metrics")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--no-stim", action="store_true")
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    ap.add_argument("--harness-support", type=float, default=1.0)
    ap.add_argument("--no-harness", action="store_true")
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    cfg = _build_stim_cfg_schedule(a.food and not a.no_stim,
                                   a.predator and not a.no_stim)[0]
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
    from sim.neural_sim import ZebrafishNeuralSim
    from sim.fish_readout import ZebrafishReadout
    from sim.drug_engine import drug_modulation

    ap = argparse.ArgumentParser(prog="highfish human-intent")
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--steps", type=int, default=100)
    a = ap.parse_args(argv if argv is not None else sys.argv[2:])

    mod = drug_modulation(a.drug, a.dose)
    sim = ZebrafishNeuralSim()
    if mod.get("fish_mapping"):
        sim.apply_drug(mod["fish_mapping"], mod.get("sim_params", {}))
    for _ in range(a.steps):
        sim.step()
    tr = ZebrafishReadout()
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

    ap = argparse.ArgumentParser(prog="highfish timelapse")
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


def _print_help() -> None:
    """Top-level usage summary listing every ./highfish command."""
    print(
        """HighFish CLI - zebrafish Fish1 connectome -> humanoid biped gait

Usage: ./highfish <command> [options]

Commands:
  run             Interactive drug/stimulus selection, then live 3D humanoid viewer
                  (non-interactive: --no-prompt --drug <name> --dose F --duration F
                  --timelapse F [--food --predator --headless --no-harness --out FILE])
  human           Same as 'run' (live humanoid viewer)
  human-metrics   Headless run; prints locomotion metrics JSON (no window)
  human-intent    Headless run; prints the hindbrain->intent telemetry (forward
                  drive, cadence, coordination, gait mode, motor tone)
  list            Print the full pharmacology catalog: chemical/brand name,
                  PubChem CID, and verified zebrafish receptor systems (--brand)
  timelapse       Long-term PK/PD chronobiology simulation across hours/days
                  (--drug <name> --dose F --hours F --out FILE --fps N --brand)

Help:
  --help, -h, help    Show this message

Examples:
  ./highfish run --no-prompt --drug caffeine --duration 5
  ./highfish run --no-prompt --drug valium --dose 0.8 --predator --duration 10
  ./highfish list --brand
  ./highfish human-metrics --drug ethanol --dose 1.0
  ./highfish timelapse --drug fluoxetine --hours 24 --brand

Notes:
  - On macOS the live viewer (run/human/timelapse) launches via mjpython.
  - Drug names are case-insensitive and accept trade names ('haldol', 'prozac',
    'ritalin', 'coke', 'valium', 'ptz', 'ttx', ...)""")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] in {"--help", "-h", "help"}:
        _print_help()
        return
    if len(sys.argv) < 2 or sys.argv[1] in {"run", ""}:
        cmd_run(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "_view":
        # legacy internal mode: behave like run with explicit flags
        cmd_run(sys.argv[2:])
    elif sys.argv[1] == "list":
        cmd_list(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "human":
        cmd_human(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "human-metrics":
        cmd_human_metrics(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "human-intent":
        cmd_human_intent(sys.argv[2:] if len(sys.argv) > 2 else [])
    elif sys.argv[1] == "timelapse":
        cmd_timelapse(sys.argv[2:] if len(sys.argv) > 2 else [])
    else:
        _print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
