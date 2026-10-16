#!/usr/bin/env python3
"""Unbiased Descending Population Decoding & Spectral Variance Analysis.

Performs:
1. Multi-state simulation over the 139,255-neuron FlyWire v783 connectome to sample
   all 1,305 descending neurons (DNs) across diverse behavioral & pharmacological states.
2. Unsupervised Principal Component Analysis (PCA) & Spectral Decomposition on the 1,305-DN matrix.
3. Rigorous quantification of manual rule-table bias in sim/human_translation.py:
   - Correlation between hand-picked neuron signals (DNa01/02, MDN) and principal eigenmodes.
   - Percentage of total descending variance captured by manual rules vs. optimal PCA modes.
4. Derivation of data-driven, unbiased population projection vectors (w_fwd, w_turn, w_arrest)
   distributing weight across all 1,305 descending neurons.

Outputs: data/unbiased_dn_pca.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.neural_sim import FlyWireNeuralSim
from sim.human_translation import DNToHumanTranslator
from sim.drug_engine import drug_modulation

OUTPUT_PATH = ROOT / "data" / "unbiased_dn_pca.json"

def run_unbiased_decoding():
    print("=" * 65)
    print("  FLYWIRE DESCENDING POPULATION UNSUPERVISED SPECTRAL DECODING")
    print("=" * 65)

    translator = DNToHumanTranslator()
    dn_indices = translator.all_dn_idx
    n_dns = len(dn_indices)
    print(f"Loaded {n_dns} descending neurons from FlyWire connectome v783.")

    # 1. Sample neural trajectories across diverse behavioral and pharmacological states
    states = [
        {"name": "baseline_forward_walk", "steps": 50, "stim": {}, "drug": None},
        {"name": "steer_hard_left", "steps": 40, "stim": {"turn_bias": -0.85}, "drug": None},
        {"name": "steer_hard_right", "steps": 40, "stim": {"turn_bias": +0.85}, "drug": None},
        {"name": "predator_escape_flee", "steps": 50, "stim": {"predator_intensity": 0.95}, "drug": None},
        {"name": "food_plume_tracking", "steps": 40, "stim": {"food_gain": 0.90}, "drug": None},
        {"name": "spontaneous_pause_halt", "steps": 30, "stim": {}, "drug": None, "pause": True},
        {"name": "lidocaine_conduction_block", "steps": 40, "stim": {}, "drug": ("Lidocaine", 1.0)},
        {"name": "caffeine_arousal", "steps": 40, "stim": {}, "drug": ("Caffeine", 1.0)},
        {"name": "gaba_block_ataxia", "steps": 40, "stim": {}, "drug_params": {"rdl_phi": 0.85}},
        {"name": "nicotine_stimulation", "steps": 40, "stim": {}, "drug": ("Tobacco", 1.0)},
        {"name": "methamphetamine_surge", "steps": 40, "stim": {}, "drug_params": {"d1_like_gain": 0.40, "da_gain": 0.40}},
    ]

    dn_trajectories: list[np.ndarray] = []
    state_labels: list[str] = []

    for s in states:
        sname = s["name"]
        n_steps = s["steps"]
        print(f"  Sampling state: {sname:30s} ({n_steps} steps)...")
        
        sim = FlyWireNeuralSim()
        # Warmup
        for _ in range(20):
            sim.step()

        # Apply pharmacological perturbation if present
        if s.get("drug"):
            dname, dose = s["drug"]
            mod = drug_modulation(dname, dose)
            sim.apply_drug(mod.get("fly_mapping", {}), mod.get("sim_params", {}))
        elif s.get("drug_params"):
            sim.apply_drug({}, s["drug_params"])

        stim = s.get("stim", {})
        for step_i in range(n_steps):
            if s.get("pause") and step_i > 10:
                # Decelerate external sensory input
                sim.apply_stim(food_gain=0.0, predator_intensity=0.0, turn_bias=0.0)
                sim.stim_rate = 0.2
            else:
                sim.apply_stim(
                    food_gain=stim.get("food_gain", 0.0),
                    predator_intensity=stim.get("predator_intensity", 0.0),
                    turn_bias=stim.get("turn_bias", 0.0),
                )
            sim.step()
            # Extract 1,305 DN firing rates
            dn_rates = sim.r[dn_indices].astype(np.float64)
            dn_trajectories.append(dn_rates)
            state_labels.append(sname)

    X = np.array(dn_trajectories)  # Shape: (T, 1305)
    T, P = X.shape
    print(f"\nConstructed descending state matrix X: {T} timepoints x {P} descending neurons.")

    # 2. Unsupervised Principal Component Analysis (Spectral Decomposition)
    mean_X = np.mean(X, axis=0)
    std_X = np.std(X, axis=0)
    std_X[std_X < 1e-6] = 1.0
    X_centered = X - mean_X

    # Covariance matrix C = X_c^T @ X_c / (T - 1)
    # Use SVD on X_centered / sqrt(T - 1) for superior numerical precision
    U, S, Vt = np.linalg.svd(X_centered / np.sqrt(T - 1), full_matrices=False)
    # Eigenvalues lambda_k = S_k^2
    eigenvalues = S ** 2
    total_var = float(np.sum(eigenvalues))
    var_explained = eigenvalues / total_var
    cum_var_explained = np.cumsum(var_explained)

    # Top 5 Principal Components
    print("\n--- Eigenmode Variance Decomposition (Top 10 PCs) ---")
    for k in range(10):
        print(f"  PC{k+1:02d}: lambda = {eigenvalues[k]:.4f} | "
              f"Var Explained = {var_explained[k]*100:5.2f}% | "
              f"Cumulative = {cum_var_explained[k]*100:5.2f}%")

    pc_projections = X_centered @ Vt[:5].T  # Shape: (T, 5)

    # 3. Quantify Existing Manual Rule Table Signals
    # Signal A: DN_pop_mean (uniform pooling across all DNs)
    w_manual_fwd = np.zeros(P)
    w_manual_fwd[:] = 1.0 / P
    # Add manual boost to DNa01/02
    dna_sub_indices = np.where(np.isin(dn_indices, translator.dna_all_idx))[0]
    w_manual_fwd[dna_sub_indices] += 0.3 / max(1, len(dna_sub_indices))
    w_manual_fwd /= np.linalg.norm(w_manual_fwd)

    # Signal B: Bilateral DNa asymmetry + hemisphere asymmetry
    w_manual_turn = np.zeros(P)
    dna_left_sub = np.where(np.isin(dn_indices, translator.dna_left_idx))[0]
    dna_right_sub = np.where(np.isin(dn_indices, translator.dna_right_idx))[0]
    w_manual_turn[dna_right_sub] = +1.0
    w_manual_turn[dna_left_sub] = -1.0
    # Add hemisphere DN bias
    left_dn_sub = np.where(np.isin(dn_indices, translator.left_dn_idx))[0]
    right_dn_sub = np.where(np.isin(dn_indices, translator.right_dn_idx))[0]
    w_manual_turn[right_dn_sub] += 0.2 / max(1, len(right_dn_sub))
    w_manual_turn[left_dn_sub] -= 0.2 / max(1, len(left_dn_sub))
    w_manual_turn /= np.linalg.norm(w_manual_turn)

    # Signal C: MDN arrest
    w_manual_arrest = np.zeros(P)
    mdn_sub = np.where(np.isin(dn_indices, translator.mdn_idx))[0]
    w_manual_arrest[mdn_sub] = 1.0
    w_manual_arrest /= np.linalg.norm(w_manual_arrest)

    # Compute manual feature time-series
    y_manual_fwd = X_centered @ w_manual_fwd
    y_manual_turn = X_centered @ w_manual_turn
    y_manual_arrest = X_centered @ w_manual_arrest

    # Correlation matrix between manual features and top PCs
    corr_fwd_pcs = [float(np.corrcoef(y_manual_fwd, pc_projections[:, k])[0, 1]) for k in range(5)]
    corr_turn_pcs = [float(np.corrcoef(y_manual_turn, pc_projections[:, k])[0, 1]) for k in range(5)]
    corr_arrest_pcs = [float(np.corrcoef(y_manual_arrest, pc_projections[:, k])[0, 1]) for k in range(5)]

    print("\n--- Manual Rule Table vs. Principal Eigenmode Correlations ---")
    print("  Correlation with PC1 (Global Propulsion / Arousal):")
    print(f"    - Forward Drive rule : r = {corr_fwd_pcs[0]:+.4f} (R^2 = {corr_fwd_pcs[0]**2:.3f})")
    print(f"    - Turn Intent rule   : r = {corr_turn_pcs[0]:+.4f}")
    print(f"    - Arrest / MDN rule  : r = {corr_arrest_pcs[0]:+.4f}")

    print("  Correlation with PC2 (Steering & Bilateral Asymmetry):")
    print(f"    - Forward Drive rule : r = {corr_fwd_pcs[1]:+.4f}")
    print(f"    - Turn Intent rule   : r = {corr_turn_pcs[1]:+.4f} (R^2 = {corr_turn_pcs[1]**2:.3f})")
    print(f"    - Arrest / MDN rule  : r = {corr_arrest_pcs[1]:+.4f}")

    print("  Correlation with PC3 (Escape / Defensive Modulation):")
    print(f"    - Forward Drive rule : r = {corr_fwd_pcs[2]:+.4f}")
    print(f"    - Turn Intent rule   : r = {corr_turn_pcs[2]:+.4f}")
    print(f"    - Arrest / MDN rule  : r = {corr_arrest_pcs[2]:+.4f} (R^2 = {corr_arrest_pcs[2]**2:.3f})")

    # Quantify variance explained by the manual 3D subspace
    # Project X_centered onto manual subspace
    W_manual = np.column_stack([w_manual_fwd, w_manual_turn, w_manual_arrest])
    # Orthonormalize W_manual via QR
    Q_manual, _ = np.linalg.qr(W_manual)
    X_proj_manual = X_centered @ Q_manual @ Q_manual.T
    var_manual = float(np.sum(np.var(X_proj_manual, axis=0)))
    total_data_var = float(np.sum(np.var(X_centered, axis=0)))
    var_ratio_manual = var_manual / total_data_var

    # Top 3 optimal PCA subspace variance
    Q_pca = Vt[:3].T
    X_proj_pca = X_centered @ Q_pca @ Q_pca.T
    var_pca = float(np.sum(np.var(X_proj_pca, axis=0)))
    var_ratio_pca = var_pca / total_data_var

    print("\n--- Subspace Variance Capture & Debiasing Quantification ---")
    print(f"  Total Descending Population Variance : {total_data_var:.4f}")
    print(f"  Manual 3-Rule Subspace Variance      : {var_manual:.4f} ({var_ratio_manual*100:.2f}% of total)")
    print(f"  Optimal Top-3 PCA Subspace Variance  : {var_pca:.4f} ({var_ratio_pca*100:.2f}% of total)")
    print(f"  Subspace Efficiency (Manual / Optimal): {var_manual / var_pca * 100:.2f}%")
    print(f"  Residual Population Variance Ignored : {(1.0 - var_ratio_manual)*100:.2f}%")

    # 4. Derive Unbiased Data-Driven Projection Weights
    # Align PC1 with forward drive (positive projection)
    w_unbiased_fwd = Vt[0].copy()
    if np.corrcoef(X_centered @ w_unbiased_fwd, y_manual_fwd)[0, 1] < 0:
        w_unbiased_fwd = -w_unbiased_fwd

    # Align PC2 with turn intent (positive for right steering)
    w_unbiased_turn = Vt[1].copy()
    if np.corrcoef(X_centered @ w_unbiased_turn, y_manual_turn)[0, 1] < 0:
        w_unbiased_turn = -w_unbiased_turn

    # Align PC3 with escape/arrest
    w_unbiased_arrest = Vt[2].copy()
    if np.corrcoef(X_centered @ w_unbiased_arrest, y_manual_arrest)[0, 1] < 0:
        w_unbiased_arrest = -w_unbiased_arrest

    # Number of actively contributing neurons (participation ratio)
    def participation_ratio(w: np.ndarray) -> float:
        w_norm = w / np.linalg.norm(w)
        return float((np.sum(w_norm ** 2) ** 2) / np.sum(w_norm ** 4))

    pr_manual_fwd = participation_ratio(w_manual_fwd)
    pr_unbiased_fwd = participation_ratio(w_unbiased_fwd)
    pr_manual_turn = participation_ratio(w_manual_turn)
    pr_unbiased_turn = participation_ratio(w_unbiased_turn)

    print("\n--- Neuron Participation Ratio (Effective Number of Active Neurons) ---")
    print(f"  Forward Drive : Manual = {pr_manual_fwd:.1f} neurons vs. Unbiased = {pr_unbiased_fwd:.1f} neurons")
    print(f"  Steering Turn : Manual = {pr_manual_turn:.1f} neurons vs. Unbiased = {pr_unbiased_turn:.1f} neurons")

    # Compile structured analysis JSON
    results = {
        "metadata": {
            "title": "Unbiased Spectral & PCA Decoding of FlyWire Descending Connectome",
            "n_descending_neurons": n_dns,
            "n_simulated_timepoints": T,
            "states_sampled": [s["name"] for s in states],
        },
        "spectral_variance_explained": {
            "pc_variance_explained_pct": [round(float(v) * 100, 3) for v in var_explained[:15]],
            "cumulative_variance_pct": [round(float(v) * 100, 3) for v in cum_var_explained[:15]],
            "top_3_pc_variance_pct": round(float(cum_var_explained[2]) * 100, 2),
            "top_5_pc_variance_pct": round(float(cum_var_explained[4]) * 100, 2),
            "top_10_pc_variance_pct": round(float(cum_var_explained[9]) * 100, 2),
        },
        "manual_rule_table_benchmarking": {
            "pc1_forward_correlation_r": round(corr_fwd_pcs[0], 4),
            "pc1_forward_r2": round(corr_fwd_pcs[0] ** 2, 4),
            "pc2_turn_correlation_r": round(corr_turn_pcs[1], 4),
            "pc2_turn_r2": round(corr_turn_pcs[1] ** 2, 4),
            "pc3_arrest_correlation_r": round(corr_arrest_pcs[2], 4),
            "pc3_arrest_r2": round(corr_arrest_pcs[2] ** 2, 4),
            "manual_subspace_variance_ratio_pct": round(var_ratio_manual * 100, 2),
            "optimal_pca_subspace_variance_ratio_pct": round(var_ratio_pca * 100, 2),
            "subspace_efficiency_pct": round(var_manual / var_pca * 100, 2),
            "residual_unmodeled_variance_pct": round((1.0 - var_ratio_manual) * 100, 2),
        },
        "participation_ratios": {
            "manual_forward_effective_neurons": round(pr_manual_fwd, 1),
            "unbiased_forward_effective_neurons": round(pr_unbiased_fwd, 1),
            "manual_turn_effective_neurons": round(pr_manual_turn, 1),
            "unbiased_turn_effective_neurons": round(pr_unbiased_turn, 1),
        },
        "unbiased_weights_summary": {
            "forward_drive_top_10_weights": [
                {"dn_index": int(idx), "weight": round(float(w_unbiased_fwd[idx]), 6)}
                for idx in np.argsort(np.abs(w_unbiased_fwd))[-10:][::-1]
            ],
            "turn_intent_top_10_weights": [
                {"dn_index": int(idx), "weight": round(float(w_unbiased_turn[idx]), 6)}
                for idx in np.argsort(np.abs(w_unbiased_turn))[-10:][::-1]
            ],
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved unbiased spectral decoding analysis to:\n  {OUTPUT_PATH}")
    print("=" * 65)

if __name__ == "__main__":
    run_unbiased_decoding()
