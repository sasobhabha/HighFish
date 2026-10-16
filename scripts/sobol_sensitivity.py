#!/usr/bin/env python3
"""Global Sobol Sensitivity Analysis for Cross-Species Neuro-Biomechanics.

Implements Saltelli (2002, 2010) Monte Carlo variance decomposition across:
- Translation gains: k_dn, k_dna
- Suspension & posture: harness_support, stiff_rot
- Biped CPG dynamics: w0_cpg, base_cadence, slew_max

Outputs: data/sobol_sensitivity_results.json
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.human_translation import DNToHumanTranslator, HumanIntent
from sim.human_gait import BipedCPG, BipedGaitKinematics
from sim.humanoid_body import HumanoidBodySim

OUTPUT_PATH = ROOT / "data" / "sobol_sensitivity_results.json"

# Parameter space bounds (min, max, nominal)
PARAM_NAMES = [
    "k_dn",             # 1. Forward DN translation gain [0.4, 1.2]
    "k_dna",            # 2. Steering DNa asymmetry gain [0.3, 1.2]
    "harness_support",   # 3. Clinical suspension fraction [0.2, 1.0]
    "stiff_rot",        # 4. Rotational trunk posture stiffness [500, 3500] Nm/rad
    "w0_cpg",           # 5. Intrinsic CPG anti-phase coupling rate [5.0, 30.0] rad/s
    "base_cadence",     # 6. Baseline stepping frequency [0.8, 1.5] Hz
    "slew_max",         # 7. Actuator velocity slew limit [10.0, 35.0] rad/s
]

PARAM_BOUNDS = np.array([
    [0.40, 1.20],      # k_dn
    [0.30, 1.20],      # k_dna
    [0.20, 1.00],      # harness_support
    [500.0, 3500.0],   # stiff_rot
    [5.0, 30.0],       # w0_cpg
    [0.80, 1.50],      # base_cadence
    [10.0, 35.0],      # slew_max
])

OUTPUT_NAMES = [
    "vx_m_s",           # Forward velocity
    "trunk_pitch_abs",  # Absolute trunk pitch angle (deg)
    "com_height",       # Mean COM height (m)
    "step_symmetry",    # Left-right stance symmetry
    "sync_error",       # Mean CPG phase coordination error (rad)
    "harness_load",     # Mean vertical suspension force (N)
]

def evaluate_model(params: np.ndarray, duration: float = 1.2) -> dict[str, float]:
    """Runs a 1.2s simulation trial for a specific parameter vector."""
    k_dn, k_dna, harness_supp, stiff_rot, w0_cpg, base_cad, slew_max = params

    dt = 0.002
    n_steps = int(duration / dt)

    # Initialize CPG and Kinematics with trial parameters
    cpg = BipedCPG()
    cpg.w0 = float(w0_cpg)
    kin = BipedGaitKinematics()
    kin.MAX_TARGET_SPEED = float(slew_max)

    # Create Body simulation with trial harness parameters
    body = HumanoidBodySim(harness=True, harness_support=float(harness_supp), dt=dt)
    # Override rotational stiffness if present in model
    for jn in ("pelvis_roll", "pelvis_pitch", "pelvis_yaw"):
        jid = body.mj_model.joint(jn).id
        if jid >= 0:
            scale = 0.6 if jn == "pelvis_yaw" else 1.0
            body.mj_model.jnt_stiffness[jid] = float(stiff_rot * scale)

    # Synthetic baseline intent scaled by k_dn, k_dna, base_cad
    intent = HumanIntent(
        forward_drive=float(np.clip(0.65 * k_dn, 0.0, 1.2)),
        turn_intent=float(np.clip(0.0 * k_dna, -1.0, 1.0)),
        cadence=float(base_cad),
        stride_length=0.85,
        posture_height=1.0,
        coordination=1.0,
        motor_tone=1.0,
        flee_drive=0.0,
        freeze=False,
        mode="walk",
    )

    trunk_jid = body.mj_model.joint("pelvis_pitch").id
    trunk_qpos = body.mj_model.jnt_qposadr[trunk_jid]

    pitch_list = []
    sync_errors = []

    for s in range(n_steps):
        pl, pr = cpg.step(dt, intent)
        targets = kin.compute_joint_targets(dt, pl, pr, intent)
        body.step(targets)
        pitch_list.append(abs(np.degrees(body.mj_data.qpos[trunk_qpos])))
        sync_errors.append(cpg.phase_sync_error())

    metrics = body.get_metrics()
    body.close()

    return {
        "vx_m_s": float(metrics["vx_m_s"]),
        "trunk_pitch_abs": float(np.mean(pitch_list[-250:])),
        "com_height": float(metrics["com_height_mean"]),
        "step_symmetry": float(metrics["step_symmetry"]),
        "sync_error": float(np.mean(sync_errors[-250:])),
        "harness_load": float(metrics["harness_load_mean_n"]),
    }

def run_sobol_analysis(N: int = 32):
    """Executes Saltelli Monte Carlo sampling and computes Sobol S_i and S_Ti."""
    t0 = time.time()
    print("=" * 65)
    print("  GLOBAL SOBOL SENSITIVITY ANALYSIS (SALTELLI VARIANCE DECOMPOSITION)")
    print("=" * 65)

    D = len(PARAM_NAMES)
    rng = np.random.default_rng(42)

    # Generate base uniform matrices A and B in [0, 1]^D
    A_unit = rng.random((N, D))
    B_unit = rng.random((N, D))

    # Scale to actual parameter domains
    lower = PARAM_BOUNDS[:, 0]
    upper = PARAM_BOUNDS[:, 1]
    A = lower + A_unit * (upper - lower)
    B = lower + B_unit * (upper - lower)

    # Construct cross-matrices A_B^(i)
    AB_list = []
    for i in range(D):
        AB_i = A.copy()
        AB_i[:, i] = B[:, i]
        AB_list.append(AB_i)

    total_evals = N * (D + 2)
    print(f"Generated sample space: N={N}, D={D} parameters.")
    print(f"Total model evaluations to run: {total_evals} (N * (D + 2))...\n")

    # Evaluate A
    print(f"1. Evaluating base matrix A ({N} runs)...")
    eval_A = []
    for j in range(N):
        eval_A.append(evaluate_model(A[j]))
        if (j + 1) % 10 == 0 or j == N - 1:
            print(f"   Completed {j+1}/{N} runs of A")

    # Evaluate B
    print(f"\n2. Evaluating base matrix B ({N} runs)...")
    eval_B = []
    for j in range(N):
        eval_B.append(evaluate_model(B[j]))
        if (j + 1) % 10 == 0 or j == N - 1:
            print(f"   Completed {j+1}/{N} runs of B")

    # Evaluate each cross-matrix A_B^(i)
    eval_AB = []
    for i in range(D):
        print(f"\n3.{i+1} Evaluating cross-matrix A_B for {PARAM_NAMES[i]} ({N} runs)...")
        eval_AB_i = []
        for j in range(N):
            eval_AB_i.append(evaluate_model(AB_list[i][j]))
        eval_AB.append(eval_AB_i)

    print("\nSimulations finished. Computing first-order (Si) and total-order (STi) indices...")

    # Compute Sobol Indices for each output
    sobol_results: dict[str, Any] = {}

    for out_name in OUTPUT_NAMES:
        y_A = np.array([e[out_name] for e in eval_A])
        y_B = np.array([e[out_name] for e in eval_B])
        
        var_y = np.var(np.concatenate([y_A, y_B]), ddof=1)
        if var_y < 1e-9:
            var_y = 1e-9

        s_first = []
        s_total = []

        for i in range(D):
            y_AB_i = np.array([e[out_name] for e in eval_AB[i]])
            
            # First-order index S_i (Saltelli 2010 estimator)
            # S_i = (1/N * sum(y_A * y_AB_i) - mean(y_A)*mean(y_B)) / var_y
            v_i = np.mean(y_B * (y_AB_i - y_A))
            si = float(v_i / var_y)
            si = float(np.clip(si, 0.0, 1.0))
            s_first.append(si)

            # Total-order index S_Ti (Jansen 1999 / Saltelli 2010)
            # S_Ti = 1 / (2N) * sum((y_A - y_AB_i)^2) / var_y
            v_ti = np.mean((y_A - y_AB_i) ** 2) / (2.0 * var_y)
            sti = float(np.clip(v_ti, si, 1.5))
            s_total.append(sti)

        sobol_results[out_name] = {
            "output_variance": round(float(var_y), 6),
            "output_mean": round(float(np.mean(y_A)), 4),
            "first_order_Si": {PARAM_NAMES[i]: round(s_first[i], 4) for i in range(D)},
            "total_order_STi": {PARAM_NAMES[i]: round(s_total[i], 4) for i in range(D)},
            "dominant_driver": PARAM_NAMES[int(np.argmax(s_total))],
        }

    elapsed = time.time() - t0
    print(f"\nSobol analysis completed in {elapsed:.2f}s.")

    # Print summary table
    print("\n--- Sobol Sensitivity Summary (Total-Order STi) ---")
    header = f"{'Output':18s} | " + " | ".join([f"{p[:7]:>7s}" for p in PARAM_NAMES]) + " | Dominant"
    print(header)
    print("-" * len(header))
    for out_name in OUTPUT_NAMES:
        row = f"{out_name:18s} | "
        for p in PARAM_NAMES:
            val = sobol_results[out_name]["total_order_STi"][p]
            row += f"{val:7.3f} | "
        row += f" {sobol_results[out_name]['dominant_driver']}"
        print(row)

    # Save to JSON
    output_dict = {
        "metadata": {
            "method": "Saltelli (2002, 2010) Sobol Variance Decomposition",
            "sample_size_N": N,
            "n_parameters": D,
            "total_evaluations": total_evals,
            "runtime_seconds": round(elapsed, 2),
            "parameters": {
                PARAM_NAMES[i]: {"min": float(lower[i]), "max": float(upper[i])}
                for i in range(D)
            },
        },
        "sobol_indices": sobol_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output_dict, f, indent=2)

    print(f"\nSaved Sobol sensitivity results to:\n  {OUTPUT_PATH}")
    print("=" * 65)

if __name__ == "__main__":
    run_sobol_analysis(N=32)
