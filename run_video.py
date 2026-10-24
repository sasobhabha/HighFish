#!/usr/bin/env python3
"""Render the drug-perturbed humanoid biped to a video file (no GUI needed).

Usage:
    .venv3/bin/python run_video.py --drug Caffeine --out out/caffeine.mp4
    .venv3/bin/python run_video.py --drug "Jungle Juice (Everything mixed)"
"""
import argparse
import json
from pathlib import Path

from sim.human_pipeline import HumanPipelineSim
from sim.drug_engine import list_products


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drug", default=None)
    ap.add_argument("--dose", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--out", default="out/humanoid.mp4")
    ap.add_argument("--food", action="store_true")
    ap.add_argument("--predator", action="store_true")
    ap.add_argument("--no-harness", action="store_true")
    args = ap.parse_args()

    if args.drug is not None and args.drug not in list_products():
        raise SystemExit(f"Unknown drug '{args.drug}'. Valid:\n"
                         + "\n".join(f"  - {p}" for p in list_products()))

    from sim.stimuli import StimulusConfig
    cfg = StimulusConfig(food=args.food, predator=args.predator)
    s = HumanPipelineSim(drug_name=args.drug, dose=args.dose,
                         harness=not args.no_harness, stim_cfg=cfg)
    schedule = []
    if args.food:
        schedule.append((0.5, "food"))
    if args.predator:
        schedule.append((1.5, "predator"))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    print(f"rendering {args.duration}s of simulated time to {args.out} ...")
    metrics, _ = s.render_video(out_path=args.out, duration=args.duration,
                                stim_schedule=schedule)
    print(json.dumps(metrics, indent=2)[:800])
    s.close()


if __name__ == "__main__":
    main()
