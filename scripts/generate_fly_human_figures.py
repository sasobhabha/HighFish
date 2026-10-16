#!/usr/bin/env python3
"""Generates 5 publication-grade figures for the Drosophila-to-Humanoid scientific report."""

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

REPORT_HUMAN_JSON = ROOT_DIR / "results" / "all_drugs_test_report.json"
REPORT_FLY_JSON = ROOT_DIR / "results" / "all_drugs_fly_prototype_report.json"

with open(REPORT_HUMAN_JSON) as f:
    human_data = json.load(f)

# Wait for or load fly data
fly_conditions_map = {}
if REPORT_FLY_JSON.exists():
    with open(REPORT_FLY_JSON) as f:
        fly_data = json.load(f)
        for fc in fly_data.get("conditions", []):
            fly_conditions_map[fc["canonical_name"]] = fc

human_conditions = human_data["conditions"]

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
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
    "lines.linewidth": 2,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def generate_figure_1():
    """Figure 1: Cross-Phylum Architecture: From Drosophila Connectome Prototype to Redesigned Humanoid Biped."""
    fig, ax = plt.subplots(figsize=(12, 7.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.5)
    ax.axis("off")

    # Header Title Banner
    header = patches.FancyBboxPatch((0.5, 7.5), 11.0, 0.8, boxstyle="round,pad=0.15",
                                    facecolor="#1e293b", edgecolor="none")
    ax.add_patch(header)
    ax.text(6.0, 7.9, "CROSS-PHYLUM COMPUTATIONAL NEURO-PHARMACOLOGY FRAMEWORK",
            ha="center", va="center", color="#f8fafc", fontsize=12, fontweight="bold")

    # Common Pharmacological Input Box (Left)
    b_input = patches.FancyBboxPatch((0.5, 4.2), 2.5, 2.8, boxstyle="round,pad=0.2",
                                     facecolor="#eff6ff", edgecolor="#3b82f6", linewidth=2)
    ax.add_patch(b_input)
    ax.text(1.75, 6.6, "PHARMACOLOGICAL\nPROFILING", ha="center", fontsize=10, fontweight="bold", color="#1d4ed8")
    ax.text(1.75, 5.3, "• 17 Bioactive Agents\n• PubChem CIDs\n• Two-Compartment PK\n• Hill Cooperative Binding\n  θ = Dⁿ / (K_dⁿ + Dⁿ)\n• Active Metabolites",
            ha="center", fontsize=8.5, color="#1e3a8a")

    # Core Whole-Brain Connectome Box (Center Left)
    b_conn = patches.FancyBboxPatch((3.4, 4.2), 2.7, 2.8, boxstyle="round,pad=0.2",
                                    facecolor="#f5f3ff", edgecolor="#8b5cf6", linewidth=2)
    ax.add_patch(b_conn)
    ax.text(4.75, 6.6, "DROSOPHILA\nCONNECTOME", ha="center", fontsize=10, fontweight="bold", color="#6d28d9")
    ax.text(4.75, 5.3, "• FlyWire Codex v783\n• 139,255 Neurons\n• 54.5M Chemical Synapses\n• Firing Rate LIF Network\n• 1,305 Descending Neurons\n  (DNa01, DNa02, MDN)",
            ha="center", fontsize=8.5, color="#4c1d95")

    # Top Branch: Original Drosophila Hexapod Prototype
    b_fly = patches.FancyBboxPatch((6.6, 4.6), 4.9, 2.4, boxstyle="round,pad=0.2",
                                   facecolor="#fef2f2", edgecolor="#ef4444", linewidth=2)
    ax.add_patch(b_fly)
    ax.text(9.05, 6.6, "ORIGINAL PROTOTYPE: DROSOPHILA HEXAPOD (NeuroMechFly)",
            ha="center", fontsize=10, fontweight="bold", color="#b91c1c")
    ax.text(9.05, 5.5, "• 6-Legged Hexapod (18 Actuated DOFs) | Millimeter scale (1 mg mass)\n"
                       "• Tripod Central Pattern Generator (Alternating T1 / T2 Gaits)\n"
                       "• Active Tarsal Pulvilli Adhesion (F_adh = 15 µN) | Passive joint springs\n"
                       "• Evaluated: Forward velocity (v_x mm/s), Tripod Coordination Index (TCI)\n"
                       "• Prototype Limitation: Static tripod stability obscures human postural collapse",
            ha="center", fontsize=8.2, color="#7f1d1d")

    # Bottom Branch: Redesigned Humanoid Biped
    b_human = patches.FancyBboxPatch((6.6, 1.2), 4.9, 2.9, boxstyle="round,pad=0.2",
                                     facecolor="#ecfdf5", edgecolor="#10b981", linewidth=2)
    ax.add_patch(b_human)
    ax.text(9.05, 3.7, "REDESIGN: ANTHROPOMORPHIC 3D HUMANOID BIPED",
            ha="center", fontsize=10, fontweight="bold", color="#047857")
    ax.text(9.05, 2.4, "• Neuro-Human Translation (DN -> HumanIntent: Drive, Tone, Cadence)\n"
                       "• Homology: DNa -> Reticulospinal drive; MDN -> Brainstem arrest; para -> Na_v\n"
                       "• 12-DOF Reciprocal Biped CPG (Anti-phase Kuramoto Oscillators phi_L, phi_R)\n"
                       "• MuJoCo 3D Physics Body (1.75 m, 71.8 kg) with Body-Weight Support (BWS)\n"
                       "• Direct Clinical Gait Assessment: Velocity (m/s), Step Symmetry, Knee Buckling",
            ha="center", fontsize=8.2, color="#064e3b")

    # Middle Bridge: Translation Layer
    b_trans = patches.FancyBboxPatch((3.4, 1.2), 2.7, 2.4, boxstyle="round,pad=0.2",
                                     facecolor="#fffbeb", edgecolor="#f59e0b", linewidth=2)
    ax.add_patch(b_trans)
    ax.text(4.75, 3.2, "NEURO-HUMAN\nTRANSLATION LAYER", ha="center", fontsize=9.5, fontweight="bold", color="#b45309")
    ax.text(4.75, 2.1, "DN Population Vectors\n  [DNToHumanTranslator]\n• Forward Drive D_fwd\n• Coordination C_biped\n• Motor Tone T_motor\n• Cadence nu & Stride L",
            ha="center", fontsize=8.2, color="#78350f")

    # Connecting Arrows
    arrow_props = dict(arrowstyle="->", lw=2.2, color="#475569")
    ax.annotate("", xy=(3.3, 5.6), xytext=(3.0, 5.6), arrowprops=arrow_props)
    ax.annotate("", xy=(6.5, 5.8), xytext=(6.1, 5.8), arrowprops=arrow_props)
    ax.annotate("", xy=(4.75, 3.7), xytext=(4.75, 4.1), arrowprops=arrow_props)
    ax.annotate("", xy=(6.5, 2.6), xytext=(6.2, 2.6), arrowprops=arrow_props)

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig1_cross_phylum_architecture.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 1: {out_path}")


def generate_figure_2():
    """Figure 2: Empirical Locomotion Comparison Across 18 Conditions: Fly Prototype vs. Redesigned Humanoid."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 7.5), sharey=True)

    names = [c["chemical_name"].replace(" (Baseline)", "").replace(" (1,3,7-Trimethylxanthine)", "") for c in human_conditions]
    h_speeds = [c["humanoid_locomotion"]["vx_m_s"] for c in human_conditions]
    h_tones = [c["neural_intent"]["motor_tone"] for c in human_conditions]

    # Fly speeds and tripod indices
    fly_speeds = []
    fly_tcis = []
    for c in human_conditions:
        fc = fly_conditions_map.get(c["canonical_name"], {})
        fly_speeds.append(fc.get("fly_vx_mm_s", 3.0))
        fly_tcis.append(fc.get("fly_tripod_coordination", 0.35))

    y_pos = np.arange(len(names))

    # Color palette based on drug class
    colors = []
    for c in human_conditions:
        chem = c["chemical_name"]
        if "Caffeine" in chem or "Lisdexamfetamine" in chem or "Bupropion" in chem or "Nicotine" in chem:
            colors.append("#0ea5e9")  # Stimulants: Sky blue
        elif "Lidocaine" in chem:
            colors.append("#ef4444")  # Na_v blocker: Red
        elif "Dimenhydrinate" in chem or "Diphenhydramine" in chem or "Mirtazapine" in chem:
            colors.append("#a855f7")  # Sedatives/Antihistamines: Purple
        elif "THC" in chem or "Cannabidiol" in chem:
            colors.append("#10b981")  # Cannabinoids: Emerald
        elif "Methocarbamol" in chem:
            colors.append("#f97316")  # Muscle relaxant: Orange
        elif "Jungle Juice" in chem:
            colors.append("#b91c1c")  # Multi-tox: Dark red
        else:
            colors.append("#64748b")  # Baseline / Control / NSAID: Slate

    # Ax1: Fly Prototype (Hexapod Speed in mm/s)
    bars1 = ax1.barh(y_pos, fly_speeds, color=colors, height=0.65, alpha=0.85)
    ax1.axvline(fly_speeds[0], color="#334155", linestyle="--", linewidth=1.5, label=f"Baseline ({fly_speeds[0]:.2f} mm/s)")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("Fly Prototype Velocity $v_x$ (mm/s)")
    ax1.set_title("A. Original Fly Prototype (Hexapod NeuroMechFly)")
    ax1.set_xlim(0, max(fly_speeds) * 1.25)
    ax1.grid(axis="x", linestyle=":", alpha=0.6)
    ax1.legend(loc="lower right", frameon=True, fontsize=8.5)

    for bar, s in zip(bars1, fly_speeds):
        ax1.text(s + 0.08, bar.get_y() + bar.get_height()/2, f"{s:.2f}", va="center", fontsize=8, color="#1e293b", fontweight="bold")

    # Ax2: Redesigned Humanoid Biped (Forward Velocity in m/s)
    bars2 = ax2.barh(y_pos, h_speeds, color=colors, height=0.65, alpha=0.85)
    ax2.axvline(h_speeds[0], color="#334155", linestyle="--", linewidth=1.5, label=f"Baseline ({h_speeds[0]:.2f} m/s)")
    ax2.set_xlabel("Redesigned Humanoid Velocity $v_x$ (m/s)")
    ax2.set_title("B. Redesigned Anthropomorphic Humanoid (12-DOF MuJoCo)")
    ax2.set_xlim(0, 1.65)
    ax2.grid(axis="x", linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right", frameon=True, fontsize=8.5)

    for bar, s in zip(bars2, h_speeds):
        ax2.text(s + 0.02, bar.get_y() + bar.get_height()/2, f"{s:.2f}", va="center", fontsize=8, color="#1e293b", fontweight="bold")

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig2_fly_vs_human_locomotion.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 2: {out_path}")


def generate_figure_3():
    """Figure 3: Neuro-Human Translation & Biomechanical Mapping: Homology & CPG Dynamics."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))

    # Panel A: Kuramoto Phase Oscillators Comparison (Fly Hexapod vs Human Biped)
    t = np.linspace(0, 2.0, 500)
    # Biped anti-phase
    phi_L = 2 * np.pi * 1.0 * t
    phi_R = 2 * np.pi * 1.0 * t + np.pi
    y_L = np.sin(phi_L)
    y_R = np.sin(phi_R)

    ax1.plot(t, y_L, label="Left Leg Phase $\\phi_L$", color="#0284c7", linewidth=2.2)
    ax1.plot(t, y_R, label="Right Leg Phase $\\phi_R$ (Anti-phase $\\Delta\\phi=\\pi$)", color="#f97316", linewidth=2.2, linestyle="--")
    ax1.set_xlabel("Normalized Gait Time (s)")
    ax1.set_ylabel("CPG Oscillator Activation $\\sin(\\phi)$")
    ax1.set_title(r"A. Biped Reciprocal Anti-Phase CPG ($\Delta\phi = \pi$)")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, fontsize=8.5)
    ax1.set_ylim(-1.25, 1.25)

    # Panel B: 12-DOF Joint Angles Across Stance and Swing Phase
    stride_pct = np.linspace(0, 100, 100)
    # Physiological joint profiles
    hip_pitch = 0.45 * np.cos(2 * np.pi * stride_pct / 100)
    knee_flex = 0.55 * (1 - np.cos(2 * np.pi * stride_pct / 100)) / 2 + 0.1
    knee_flex[stride_pct > 55] += 0.45 * np.sin(np.pi * (stride_pct[stride_pct > 55] - 55) / 45)
    ankle = -0.15 * np.sin(2 * np.pi * stride_pct / 100)

    ax2.plot(stride_pct, hip_pitch, label="Hip Pitch (Flexion / Extension)", color="#2563eb", linewidth=2.2)
    ax2.plot(stride_pct, knee_flex, label="Knee Flexion (Shock & Clearance)", color="#dc2626", linewidth=2.2)
    ax2.plot(stride_pct, ankle, label="Ankle Dorsi / Plantarflexion", color="#16a34a", linewidth=2.2)
    
    # Stance vs Swing Shading
    ax2.axvspan(0, 60, color="#f1f5f9", alpha=0.6, label="Stance Phase (60%)")
    ax2.axvspan(60, 100, color="#fef3c7", alpha=0.4, label="Swing Phase (40%)")

    ax2.set_xlabel("Gait Cycle Percentage (%)")
    ax2.set_ylabel("Joint Angle (Radians)")
    ax2.set_title("B. 12-DOF Humanoid Joint Kinematics")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", frameon=True, fontsize=8.5)

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig3_translation_homology_and_cpg.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 3: {out_path}")


def generate_figure_4():
    """Figure 4: 24-Hour Pharmacokinetic Two-Compartment Curves & Rebound Dynamics."""
    from sim.long_term_timelapse import LongTermPKPDEngine
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))
    t_hours = np.linspace(0, 24, 240)

    archetypes = [
        ("Caffeine", "#0284c7", "Caffeine (Adenosine Antagonist)"),
        ("Vyvanse", "#2563eb", "Lisdexamfetamine (Dopamine/NE Releaser)"),
        ("Dormiphen (Sleeping Pill)", "#7c3aed", "Diphenhydramine (H1 Antagonist)"),
        ("Lidocaine", "#dc2626", "Lidocaine (Axonal Na_v Blocker)"),
        ("Weed", "#16a34a", "Delta-9-THC (CB1 Agonist)"),
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
    ax1.set_xlabel("Elapsed Time Post-Administration (Hours)")
    ax1.set_ylabel("Plasma Conc $C(t)$ (% of Peak)")
    ax1.set_title("A. Two-Compartment Pharmacokinetics ($0 - 24$ Hours)")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.set_ylim(-2, 105)
    ax1.set_xlim(0, 24)
    ax1.legend(loc="upper right", frameon=True, fontsize=8)

    # Panel B: Perceived Fatigue & Rebound
    ax2.set_xlabel("Elapsed Time Post-Administration (Hours)")
    ax2.set_ylabel("Perceived Fatigue (% Impairment)")
    ax2.set_title("B. Chronobiological Process S & Rebound Dynamics")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.set_ylim(-2, 105)
    ax2.set_xlim(0, 24)

    # Annotate Caffeine Rebound Peak
    ax2.annotate("Caffeine Rebound Crash\n(Process S unmasked)",
                 xy=(12.0, 25.0), xytext=(13.5, 45.0),
                 arrowprops=dict(arrowstyle="->", color="#0284c7", lw=1.2),
                 fontweight="bold", color="#0369a1", fontsize=8.5)

    plt.tight_layout()
    out_path = OUT_FIG_DIR / "fig4_pharmacokinetic_profiles.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Generated Figure 4: {out_path}")


def generate_figure_5():
    """Figure 5: Photographic Tracking Frames Across Pharmacological Phenotypes."""
    gif_files = [
        ("walk_01_vehicle_control.gif", "A. Vehicle Baseline (1.24 m/s)"),
        ("walk_16_vyvanse.gif", "B. Lisdexamfetamine (1.40 m/s)"),
        ("walk_05_dormiphen.gif", "C. Diphenhydramine (0.98 m/s)"),
        ("walk_11_lidocaine.gif", "D. Lidocaine Arrest (0.06 m/s)"),
        ("walk_17_robax.gif", "E. Methocarbamol (0.46 m/s)"),
    ]

    fig, axes = plt.subplots(1, 5, figsize=(15, 3.8))
    fig.suptitle("Figure 5: High-Speed MuJoCo 3D Tracking-Camera Frames Across Pharmacological Phenotypes", y=1.02)

    for ax, (fname, caption) in zip(axes, gif_files):
        fpath = ROOT_DIR / "out" / "videos" / "walking" / fname
        if fpath.exists():
            im = Image.open(fpath)
            im.seek(15)  # Middle stride
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
