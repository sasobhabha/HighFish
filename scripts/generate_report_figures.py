#!/usr/bin/env python3
"""Generates 5 publication-grade figures for the scientific report in DOCX format."""

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image

import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
OUT_FIG_DIR = ROOT_DIR / "out" / "figures"
OUT_FIG_DIR.mkdir(parents=True, exist_ok=True)

REPORT_JSON = ROOT_DIR / "results" / "all_drugs_test_report.json"
with open(REPORT_JSON) as f:
    data = json.load(f)

conditions = data["conditions"]

# Set professional scientific styling
plt.rcParams.update({
    "font.sans-serif": "Helvetica, Arial, DejaVu Sans",
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "bold",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.titlesize": 14,
    "figure.titleweight": "bold",
    "lines.linewidth": 2,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def generate_figure_1():
    """Figure 1: Biped Locomotion Velocity & Motor Tone Spectrum across 18 Conditions."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 7), sharey=True, gridspec_kw={"width_ratios": [2.5, 1.2]})
    
    names = [c["chemical_name"].replace(" (Baseline)", "").replace(" (1,3,7-Trimethylxanthine)", "") for c in conditions]
    speeds = [c["humanoid_locomotion"]["vx_m_s"] for c in conditions]
    tones = [c["neural_intent"]["motor_tone"] for c in conditions]
    modes = [c["neural_intent"]["gait_mode"] for c in conditions]

    y_pos = np.arange(len(names))

    # Color palette based on speed and tone
    colors = []
    for s, t in zip(speeds, tones):
        if t < 0.35:
            colors.append("#ef4444")  # Red: Motor block
        elif s < 0.60:
            colors.append("#f97316")  # Orange: Severe depression
        elif s < 1.05:
            colors.append("#a855f7")  # Purple: Sedated
        elif s > 1.30:
            colors.append("#0ea5e9")  # Cyan: Stimulant
        else:
            colors.append("#22c55e")  # Green: Baseline / Normal

    # Ax1: Velocity Bar Plot
    bars = ax1.barh(y_pos, speeds, color=colors, height=0.65, edgecolor="none", alpha=0.9)
    ax1.axvline(1.21, color="#64748b", linestyle="--", linewidth=1.5, label="Baseline (1.21 m/s)")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=9.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("Bipedal Forward Velocity $v_x$ (m/s)")
    ax1.set_title("A. Humanoid Locomotion Velocity Spectrum")
    ax1.set_xlim(0, 1.6)
    ax1.legend(loc="lower right", frameon=True)
    ax1.grid(axis="x", linestyle=":", alpha=0.6)

    # Annotate velocity values
    for bar, s in zip(bars, speeds):
        ax1.text(s + 0.02, bar.get_y() + bar.get_height()/2, f"{s:.2f}", va="center", fontsize=8.5, color="#1e293b", fontweight="bold")

    # Ax2: Neuromuscular Motor Tone
    bars2 = ax2.barh(y_pos, tones, color="#6366f1", height=0.65, alpha=0.8)
    ax2.axvline(1.0, color="#64748b", linestyle="--", linewidth=1.5)
    ax2.set_xlabel("Motor Tone Index (0 - 1.0)")
    ax2.set_title("B. Neuromuscular Tone")
    ax2.set_xlim(0, 1.15)
    ax2.grid(axis="x", linestyle=":", alpha=0.6)

    for bar, t in zip(bars2, tones):
        ax2.text(t + 0.02, bar.get_y() + bar.get_height()/2, f"{t:.2f}", va="center", fontsize=8.5, color="#1e293b")

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig1_locomotion_spectrum.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 1: {out_path}")


def generate_figure_2():
    """Figure 2: Clinical Driving Impairment Matrix (SDLP vs Brake Reaction Time)."""
    fig, ax = plt.subplots(figsize=(10, 6.5))

    sdlps = [c["driving_impairment"]["sdlp_m"] for c in conditions]
    brts = [c["driving_impairment"]["brake_reaction_time_ms"] for c in conditions]
    outcomes = [c["driving_impairment"]["outcome"] for c in conditions]
    names = [c["chemical_name"].replace(" (Baseline)", "") for c in conditions]

    # Map outcomes to colors & markers
    color_map = {
        "completed_clean": "#22c55e",       # Green
        "cross_traffic_t_bone": "#ef4444",   # Red Alert
        "completed_partial": "#f59e0b",     # Amber
    }
    marker_map = {
        "completed_clean": "o",
        "cross_traffic_t_bone": "X",
        "completed_partial": "s",
    }

    # Plot points
    for s, b, o, n in zip(sdlps, brts, outcomes, names):
        # Cap BRT at 1200 for clean visualization if timeout 9999
        disp_b = 1050 if b > 2000 else b
        c = color_map.get(o, "#3b82f6")
        m = marker_map.get(o, "o")
        ax.scatter(s, disp_b, color=c, marker=m, s=120, edgecolors="#0f172a", linewidth=1.2, zorder=4)

        # Selective label offsets for clean reading
        dx, dy = 0.012, 18
        if "Diphenhydramine" in n:
            ax.annotate(f"{n}\n(BRT Timeout -> Fatal Crash)", (s, disp_b), xytext=(s - 0.22, disp_b - 60),
                        arrowprops=dict(arrowstyle="->", color="#ef4444", lw=1.2), fontweight="bold", color="#dc2626")
        elif "Dimenhydrinate" in n:
            ax.annotate(f"{n}\n(BRT: 405ms -> Crash)", (s, disp_b), xytext=(s + 0.03, disp_b - 30),
                        arrowprops=dict(arrowstyle="->", color="#ef4444", lw=1.2), fontweight="bold", color="#dc2626")
        elif "Methocarbamol" in n:
            ax.annotate(f"{n}\n(Peak Lane Drift: {s:.3f}m)", (s, disp_b), xytext=(s - 0.25, disp_b + 50),
                        arrowprops=dict(arrowstyle="->", color="#475569", lw=1.2), fontweight="bold")
        elif "Lisdexamfetamine" in n:
            ax.annotate(f"{n}\n(Lowest SDLP: {s:.3f}m)", (s, disp_b), xytext=(s - 0.18, disp_b + 55),
                        arrowprops=dict(arrowstyle="->", color="#0284c7", lw=1.2), fontweight="bold", color="#0369a1")
        elif "Lidocaine" in n:
            ax.annotate(f"{n} (Motor Block / Stall)", (s, disp_b), xytext=(s + 0.03, disp_b + 40),
                        arrowprops=dict(arrowstyle="->", color="#d97706", lw=1.2), fontweight="bold", color="#b45309")
        elif "Caffeine" in n:
            ax.annotate("Caffeine", (s, disp_b), xytext=(s + 0.015, disp_b - 35), fontsize=8.5)

    # Shaded Danger Zone (Cross traffic impact zone)
    ax.axhspan(300, 1150, color="#fee2e2", alpha=0.45, label="High Impact Risk Zone (BRT > 300 ms)")
    ax.axvline(0.60, color="#cbd5e1", linestyle="--", linewidth=1.5, label="NHTSA Clinical Weaving Threshold (0.60 m)")

    ax.set_xlabel("Lateral Lane Weaving Index — SDLP (meters)")
    ax.set_ylabel("Emergency Brake Reaction Time — BRT (ms)")
    ax.set_title("Figure 2: Clinical Driving Impairment Matrix (NHTSA / FDA Standards)")
    ax.set_ylim(-50, 1150)
    ax.set_xlim(0.0, 0.72)
    ax.grid(True, linestyle=":", alpha=0.6)

    # Custom legend elements
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Clean Completion', markerfacecolor='#22c55e', markersize=10),
        Line2D([0], [0], marker='X', color='w', label='Fatal T-Bone Collision', markerfacecolor='#ef4444', markersize=11),
        Line2D([0], [0], marker='s', color='w', label='Throttle Paralysis / Partial', markerfacecolor='#f59e0b', markersize=10),
        patches.Patch(facecolor='#fee2e2', edgecolor='none', label='Hazard Collision Risk Zone'),
    ]
    ax.legend(handles=legend_elements, loc="upper center", frameon=True, ncol=2)

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig2_driving_impairment_scatter.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 2: {out_path}")


def generate_figure_3():
    """Figure 3: Multi-Tiered Neural-to-Kinematic Translation Architecture."""
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # Tier 1 Box: Molecular Pharmacology
    b1 = patches.FancyBboxPatch((0.5, 4.5), 2.5, 2.0, boxstyle="round,pad=0.2", facecolor="#eff6ff", edgecolor="#3b82f6", linewidth=2)
    ax.add_patch(b1)
    ax.text(1.75, 6.1, "TIER 1", ha="center", fontsize=10, fontweight="bold", color="#1d4ed8")
    ax.text(1.75, 5.7, "Molecular Pharmacology", ha="center", fontsize=11, fontweight="bold", color="#1e3a8a")
    ax.text(1.75, 5.0, "17 Bioactive Compounds\nPubChem CID Registry\nHill-Langmuir Occupancy\n(PDF Eq. 1-4)", ha="center", fontsize=8.5, color="#334155")

    # Tier 2 Box: Whole-Brain Connectome
    b2 = patches.FancyBboxPatch((3.8, 4.5), 2.5, 2.0, boxstyle="round,pad=0.2", facecolor="#f5f3ff", edgecolor="#8b5cf6", linewidth=2)
    ax.add_patch(b2)
    ax.text(5.05, 6.1, "TIER 2", ha="center", fontsize=10, fontweight="bold", color="#6d28d9")
    ax.text(5.05, 5.7, "Drosophila Connectome", ha="center", fontsize=11, fontweight="bold", color="#4c1d95")
    ax.text(5.05, 5.0, "FlyWire Codex v783\n139,255 Neurons | 1,305 DNs\nSparse LIF Rate Dynamics\n(PDF Eq. 5-7)", ha="center", fontsize=8.5, color="#334155")

    # Tier 3 Box: Translation & Biped CPG
    b3 = patches.FancyBboxPatch((7.0, 4.5), 2.5, 2.0, boxstyle="round,pad=0.2", facecolor="#ecfdf5", edgecolor="#10b981", linewidth=2)
    ax.add_patch(b3)
    ax.text(8.25, 6.1, "TIER 3", ha="center", fontsize=10, fontweight="bold", color="#047857")
    ax.text(8.25, 5.7, "Human Intent & CPG", ha="center", fontsize=11, fontweight="bold", color="#064e3b")
    ax.text(8.25, 5.0, "DN Population Decoding\nMatsuoka Anti-Phase CPG\nHumanIntent Vectors\n(PDF Eq. 8-11)", ha="center", fontsize=8.5, color="#334155")

    # Tier 4 Box: Embodied Behavioral Assays
    b4 = patches.FancyBboxPatch((2.0, 0.8), 6.0, 2.3, boxstyle="round,pad=0.2", facecolor="#fffbeb", edgecolor="#f59e0b", linewidth=2)
    ax.add_patch(b4)
    ax.text(5.0, 2.7, "TIER 4: EMBODIED 3D BEHAVIORAL ASSAYS", ha="center", fontsize=11, fontweight="bold", color="#b45309")
    ax.text(3.5, 1.8, "Assay A: Humanoid 3D Locomotion\n• 12-DoF MuJoCo Biped Model\n• Step Symmetry & Posture\n• Coordinated Gait vs. Ataxia", ha="center", fontsize=8.5, color="#451a03")
    ax.text(6.8, 1.8, "Assay B: Clinical 3D Driving\n• 100m Track + Slalom Pylons\n• Sudden Lead Brake (BRT)\n• Cross-Traffic Collision Assay", ha="center", fontsize=8.5, color="#451a03")

    # Connecting Arrows
    arrow_style = dict(arrowstyle="->", lw=2, color="#475569")
    ax.annotate("", xy=(3.7, 5.5), xytext=(3.1, 5.5), arrowprops=arrow_style)
    ax.annotate("", xy=(6.9, 5.5), xytext=(6.4, 5.5), arrowprops=arrow_style)
    ax.annotate("", xy=(5.0, 3.2), xytext=(5.0, 4.4), arrowprops=arrow_style)

    ax.set_title("Figure 3: Multi-Tiered Neural-to-Kinematic Translation Architecture", y=1.02)
    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig3_translation_architecture.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 3: {out_path}")


def generate_figure_4():
    """Figure 4: Pharmacokinetic Time-Course & Process S Rebound Dynamics across 24 Hours."""
    from sim.long_term_timelapse import LongTermPKPDEngine

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    t_hours = np.linspace(0.0, 24.0, 240)

    archetypes = [
        ("Caffeine", "#0284c7", "Caffeine (Stimulant / Process S Masking)"),
        ("Dormiphen (Sleeping Pill)", "#7c3aed", "Diphenhydramine (Sedative / Histamine Block)"),
        ("Lidocaine", "#dc2626", "Lidocaine (Sodium Channel Blocker)"),
        ("Robax", "#d97706", "Methocarbamol + Ibuprofen (Muscle Relaxant)"),
    ]

    for drug, col, label in archetypes:
        engine = LongTermPKPDEngine(drug_name=drug, dose=1.0)
        conc = []
        fatigue = []
        for t in t_hours:
            st = engine.compute_state(t)
            conc.append(st.plasma_conc * 100)
            fatigue.append(st.perceived_fatigue * 100)
        
        ax1.plot(t_hours, conc, label=label, color=col, linewidth=2.2)
        ax2.plot(t_hours, fatigue, label=label, color=col, linewidth=2.2)

    # Panel A: Plasma Concentration
    ax1.set_ylabel("Plasma Conc $C(t)$ (% of Peak)")
    ax1.set_title("A. Two-Compartment Pharmacokinetics ($0 - 24$ Hours)")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.set_ylim(-2, 105)
    ax1.legend(loc="upper right", frameon=True, fontsize=8.5)

    # Panel B: Perceived Fatigue & Rebound
    ax2.set_xlabel("Elapsed Time Post-Administration (Hours)")
    ax2.set_ylabel("Perceived Fatigue (% Impairment)")
    ax2.set_title("B. Chronobiological Process S & Receptor Desensitization Rebound")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.set_ylim(-2, 105)
    ax2.set_xlim(0, 24)

    # Annotate Caffeine Rebound Peak
    ax2.annotate("Caffeine Rebound Crash\n(Masking decays, Process S unmasked)",
                 xy=(12.0, 25.0), xytext=(13.5, 45.0),
                 arrowprops=dict(arrowstyle="->", color="#0284c7", lw=1.2),
                 fontweight="bold", color="#0369a1", fontsize=8.5)

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig4_pharmacokinetic_profiles.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 4: {out_path}")


def generate_figure_5():
    """Figure 5: Montage of Captured 3D Locomotion Frames."""
    # Load representative frames from our generated walk GIF animations
    gif_files = [
        ("walk_01_vehicle_control.gif", "A. Vehicle Control (Baseline, 1.24 m/s)"),
        ("walk_16_vyvanse.gif", "B. Lisdexamfetamine (Hyperactive, 1.40 m/s)"),
        ("walk_05_dormiphen.gif", "C. Diphenhydramine (Sedated Sluggish, 0.98 m/s)"),
        ("walk_11_lidocaine.gif", "D. Lidocaine (Motor Blockade, 0.06 m/s)"),
        ("walk_17_robax.gif", "E. Methocarbamol (Hypotonic Shuffling, 0.46 m/s)"),
    ]

    fig, axes = plt.subplots(1, 5, figsize=(15, 3.8))
    fig.suptitle("Figure 5: High-Speed MuJoCo 3D Tracking-Camera Frames Across Pharmacological Classes", y=1.02)

    for ax, (fname, caption) in zip(axes, gif_files):
        fpath = ROOT_DIR / "out" / "videos" / "walking" / fname
        if fpath.exists():
            im = Image.open(fpath)
            im.seek(15)  # Seek to middle walking frame
            ax.imshow(im)
        else:
            ax.text(0.5, 0.5, "Frame\nUnavailable", ha="center", va="center")
        ax.set_title(caption, fontsize=8.5, fontweight="bold")
        ax.axis("off")

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig5_representative_locomotion_frames.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 5: {out_path}")


if __name__ == "__main__":
    generate_figure_1()
    generate_figure_2()
    generate_figure_3()
    generate_figure_4()
    generate_figure_5()
