#!/usr/bin/env python3
"""Batch runner for Fly Prototype across all 17 drugs + Vehicle control."""
import json
import time
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sim.drug_engine import list_products, get_chemical_name, get_brand_name
from sim.body_sim import DrugBodySim

def run_fly_battery(duration=1.0):
    products = list_products()
    test_conditions = ["Vehicle control"] + products
    out_file = ROOT_DIR / "results" / "all_drugs_fly_prototype_report.json"
    
    # If already exists and complete, load it
    if out_file.exists():
        try:
            with open(out_file) as f:
                data = json.load(f)
            if len(data.get("conditions", [])) == len(test_conditions):
                print("Fly prototype report already complete.")
                return data
        except Exception:
            pass

    results = []
    print(f"Running Fly Prototype Batch across {len(test_conditions)} conditions (duration={duration}s)...")
    t_start = time.time()

    for idx, drug in enumerate(test_conditions, 1):
        is_control = (drug == "Vehicle control")
        drug_arg = None if is_control else drug
        chem_name = "Vehicle control (Baseline)" if is_control else get_chemical_name(drug)
        brand_name = "Vehicle control" if is_control else get_brand_name(drug)
        print(f"[{idx:2d}/{len(test_conditions):2d}] Fly Sim: {chem_name}...", end="", flush=True)

        t0 = time.time()
        sim = DrugBodySim(drug_name=drug_arg, dose=1.0)
        metrics, _ = sim.run(duration=duration)
        sim.close()
        elapsed = time.time() - t0

        entry = {
            "index": idx,
            "canonical_name": drug,
            "chemical_name": chem_name,
            "brand_name": brand_name,
            "fly_vx_mm_s": round(metrics.get("vx_mm_s", 0.0), 4),
            "fly_straightness": round(metrics.get("straightness_index", 0.0), 4),
            "fly_tripod_coordination": round(metrics.get("tripod_coordination_index", 0.0), 4),
            "fly_mean_dn_rate": round(metrics.get("mean_dn_rate", 0.0), 4),
            "fly_alive": metrics.get("survival", {}).get("alive", True),
            "fly_upright_pct": round(metrics.get("survival", {}).get("upright_fraction", 1.0) * 100, 1),
            "elapsed_s": round(elapsed, 2)
        }
        results.append(entry)
        print(f" done in {elapsed:.1f}s | Vx: {entry['fly_vx_mm_s']} mm/s, Tripod: {entry['fly_tripod_coordination']}")

    total_elapsed = time.time() - t_start
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_per_trial_s": duration,
        "total_elapsed_s": round(total_elapsed, 2),
        "conditions": results
    }
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nAll fly conditions completed in {total_elapsed:.1f}s. Saved to {out_file}")
    return output

if __name__ == "__main__":
    run_fly_battery(duration=1.0)
