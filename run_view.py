#!/usr/bin/env python3
"""Watch the drug-perturbed humanoid biped walk LIVE in a MuJoCo window.

The biped's motor intent is driven by the zebrafish Fish1 connectome
(Petkova et al. 2025) rate-network simulation through the hindbrain
readout -> HumanIntent -> CPG pipeline (see EXECUTION_PLAN.md for the
pipeline and citations.md for sources).

Usage:
    .venv3/bin/python run_view.py                          # baseline (no drug)
    .venv3/bin/python run_view.py --drug Caffeine
    .venv3/bin/python run_view.py --drug "Lidocaine" --dose 1.0 --duration 15
    .venv3/bin/python run_view.py --drug "Jungle Juice (Everything mixed)"

A native window opens; drag to orbit, scroll to zoom. Metrics print when the
trial ends (or when you close the window).
"""
import argparse
import json
import time

import mujoco
import mujoco.viewer

from sim.human_pipeline import HumanPipelineSim
from sim.drug_engine import list_products


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drug", default=None,
                    help="product name (quotes for names with spaces); "
                         "omit for vehicle control")
    ap.add_argument("--dose", type=float, default=1.0, help="0..1")
    ap.add_argument("--duration", type=float, default=12.0,
                    help="seconds of simulated time to watch")
    ap.add_argument("--no-harness", action="store_true")
    args = ap.parse_args()

    if args.drug is not None and args.drug not in list_products():
        raise SystemExit(f"Unknown drug '{args.drug}'. Valid:\n"
                         + "\n".join(f"  - {p}" for p in list_products()))

    print(f"building simulation (drug={args.drug!r}, dose={args.dose})...")
    s = HumanPipelineSim(drug_name=args.drug, dose=args.dose,
                         harness=not args.no_harness)
    print("neural net: Fish1 zebrafish connectome |", s.neural.n, "neurons |",
          len(s.neural.readout_idx), "hindbrain readout neurons")
    print("opening viewer window...")
    m, d = s.body.mj_model, s.body.mj_data

    metrics = None
    t0 = time.time()
    try:
        with mujoco.viewer.launch_passive(m, d) as v:
            try:
                metrics, _log = s.run(duration=args.duration, viewer=v)
            except (KeyboardInterrupt, Exception) as e:
                print(f"\nrun interrupted ({type(e).__name__}); finishing anyway")
    finally:
        s.close()
        print(f"wall time: {time.time() - t0:.1f}s")
    print(json.dumps(metrics, indent=2)[:1200])


if __name__ == "__main__":
    main()
