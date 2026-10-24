#!/usr/bin/env python3
"""Benchmark suite: reflex assays + timing/motion tests for the biped pipeline.

Runs headless (no MuJoCo viewer) via HumanPipelineSim and emits a single JSON
document consumed by scripts/build_benchmarks_docx.py.

Benchmarks
----------
R1  looming-escape reflex latency (predator stimulus at known onset)
R2  escape success rate (did the animal respond at all)
M1  baseline forward velocity (m/s)
M2  straightness index (net displacement / path length)
M3  step symmetry (1 - |DF_L - DF_R| / (DF_L + DF_R))
M4  biped coordination index (single-support fraction)
M5  cadence stability (CV of peak-to-peak stance intervals fallback: duty spread)
M6  fall rate across repeated trials
"""

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.drug_engine import list_products
from sim.human_pipeline import HumanPipelineSim
from sim.stimuli import StimulusConfig

OUT_PATH = ROOT / "results" / "benchmarks" / "benchmark_metrics.json"

# Which drugs to benchmark: the default is every product in the live
# pharmacology catalog (sim.drug_engine.list_products()); pass --drugs to restrict.


def _sess_info() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": SEED,
        "harness": HARNESS_DEFAULT,
        "physics": "MuJoCo full physics (unharnessed 6-DOF freejoint)",
        "n_trials_per_drug": None,  # filled in later by the runner
    }


SEED = 7
# Hybrid benchmarking policy (user-selected):
#   - vehicle/sober control trials run harnessed (body-weight support),
#     which is the regime the walking benchmarks were calibrated in;
#   - drug trials run on an unharnessed 6-DOF freejoint under full MuJoCo
#     physics, so impaired gait truly buckles and falls under gravity.
# Pass --harness/--no-harness-all to disable the hybrid policy.
HARNESS_DEFAULT = False


def _is_vehicle(drug_name):
    return (drug_name is None) or str(drug_name).strip().lower().startswith("vehicle")


def _median(vals):
    vals = [v for v in vals if v is not None]
    return round(float(statistics.median(vals)), 4) if vals else None


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.mean(vals)), 4) if vals else None


def _sd(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.std(vals)), 4) if len(vals) > 1 else None


# ---------------------------------------------------------------------------
# Individual benchmark tests — each returns a dict of raw metrics
# ---------------------------------------------------------------------------
def reflex_looming(pipeline: HumanPipelineSim, duration_s: float = 20.0, onset_s: float = 10.0):
    """R1/R2: schedule a looming predator; capture latency + run."""
    schedule = [(onset_s, "predator")]
    metrics, log = pipeline.run(
        duration=duration_s,
        stim_schedule=schedule,
        terminate_on="none",
    )
    rts = metrics.get("reaction_times") or []
    latencies = [r.get("latency") for r in rts if r.get("latency") is not None]
    modes = [r.get("mode") for r in rts]
    freezes = modes.count("freeze")
    return {
        "reflex_latency_s": _median(latencies),
        "reflex_latency_sd_s": _sd(latencies),
        "responses": len(rts),
        "responded": bool(rts),
        "freeze_responses": freezes,
        "modes": modes,
        "outcome": metrics.get("outcome"),
        "body_metrics": metrics.get("body_metrics", {}),
        "intent_summary": metrics.get("intent_summary", {}),
    }


def motion_baseline(pipeline: HumanPipelineSim, duration_s: float = 10.0):
    """M1-M5: undisturbed forward locomotion for kinematic benchmarking."""
    metrics, log = pipeline.run(
        duration=duration_s,
        stim_schedule=None,
        terminate_on="none",
    )
    bm = metrics.get("body_metrics", {})
    duty_l = bm.get("duty_factor_left")
    duty_r = bm.get("duty_factor_right")
    duty_spread_sd = None
    if duty_l is not None and duty_r is not None:
        duty_spread_sd = round(abs(duty_l - duty_r), 4)
    return {
        "vx_m_s": bm.get("vx_m_s"),
        "straightness_index": bm.get("straightness_index"),
        "step_symmetry": bm.get("step_symmetry"),
        "biped_coordination_index": bm.get("biped_coordination_index"),
        "duty_factor_left": duty_l,
        "duty_factor_right": duty_r,
        "duty_spread_abs": duty_spread_sd,
        "com_height_mean_m": bm.get("com_height_mean"),
        "fall_detected": bm.get("fall_detected"),
        "outcome": metrics.get("outcome"),
        "mean_sync_error": metrics.get("mean_sync_error"),
    }


def stability_repeats(pipeline_factory, n_trials: int = 3, duration_s: float = 10.0):
    """M6: fall-rate/coordination robustness over repeated fresh trials."""
    falls, coords = [], []
    for _ in range(n_trials):
        p = pipeline_factory()
        m, _ = p.run(duration=duration_s, terminate_on="none")
        bm = m.get("body_metrics", {})
        falls.append(1.0 if bm.get("fall_detected") else 0.0)
        coords.append(bm.get("biped_coordination_index"))
    return {
        "fall_rate": round(float(np.mean(falls)), 4) if falls else None,
        "coordination_mean": _mean(coords),
        "coordination_sd": _sd(coords),
    }


def run_suite(drugs=None, trials: int = 3, refl_dur: float = 20.0,
              motion_dur: float = 10.0, onset_s: float = 10.0,
              harness: bool = False, out_path: Path = OUT_PATH) -> dict:
    """Run the whole benchmark family for every requested drug and dump JSON."""
    drugs = drugs if drugs is not None else sorted(list_products())
    info = _sess_info()
    info["n_trials_per_drug"] = trials
    info["reflex_duration_s"] = refl_dur
    info["reflex_onset_s"] = onset_s
    info["motion_duration_s"] = motion_dur
    info["harness"] = harness

    def factory(drug_name, harness):
        return HumanPipelineSim(drug_name=drug_name, dose=1.0,
                                harness=harness, harness_support=1.0)

    def drug_harness(drug_name):
        """Hybrid policy: vehicle walks harnessed, drugs run freejoint."""
        if _is_vehicle(drug_name):
            return True
        return harness  # drug trials: default freejoint; --harness -> legacy all-harnessed

    all_results = {}
    for drug in drugs:
        print(f"  benchmarking: {drug}", flush=True)
        dh = drug_harness(drug)
        f = lambda: factory(drug, dh)  # fresh pipeline per test
        all_results[drug] = {
            "reflex": reflex_looming(f(), refl_dur, onset_s),
            "motion": motion_baseline(f(), motion_dur),
            "stability": stability_repeats(lambda: factory(drug, dh), trials, motion_dur),
        }
        print(f"    reflex={all_results[drug]['reflex'].get('reflex_latency_s')}s "
              f"falls={all_results[drug]['stability'].get('fall_rate')}", flush=True)

    doc = {
        "metadata": {
            "title": "Neuro-mechanical Benchmark Suite: Reflexes, Timing & Motion",
            "suite_version": "1.0",
            "environment": info,
            "tests": {
                "R1": "looming-escape reflex latency (predator stimulus, latency after onset)",
                "R2": "escape success (fraction of looming trials with a detected escape_response)",
                "M1": "baseline forward velocity vx (m/s)",
                "M2": "straightness index = net displacement / path length (0..1)",
                "M3": "step symmetry = 1 - |DF_L - DF_R| / (DF_L + DF_R) (0..1)",
                "M4": "biped coordination index = single-support fraction (0..1)",
                "M5": "duty-spread |DF_L - DF_R| — cadence regularity proxy",
                "M6": "fall rate over repeat trials (drug trials: unharnessed 6-DOF freejoint, full MuJoCo physics, fresh RNG + limb state each trial; vehicle control: harness-walk regime)",
            },
        },
        "drugs": all_results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2))
    print(f"\nresults -> {out_path}")
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drugs", nargs="*", help="subset of products to benchmark")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--reflex-duration", type=float, default=20.0)
    ap.add_argument("--motion-duration", type=float, default=10.0)
    ap.add_argument("--harness", action="store_true",
                    help="run harnessed (body-weight support) instead of full physics")
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    drugs = args.drugs if args.drugs else None
    run_suite(drugs=drugs, trials=args.trials,
              refl_dur=args.reflex_duration, motion_dur=args.motion_duration,
              harness=args.harness,
              out_path=Path(args.out))


if __name__ == "__main__":
    main()
