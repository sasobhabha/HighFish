#!/usr/bin/env python3
"""Generates clean, human-designed, neat draw.io format (.drawio XML) diagrams for HighFly.
Produces:
1. architecture_prototype_to_redesign.drawio
2. neuro_human_translation_homology.drawio
3. reciprocal_biped_cpg_control.drawio
4. pharmacological_evaluation_workflow.drawio
5. highfly_master_diagrams.drawio (Multi-page workbook containing all 4 diagrams)
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import html

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
DRAWIO_DIR = ROOT_DIR / "results" / "diagrams_drawio"
DRAWIO_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def create_base_diagram(diagram_id, name):
    diagram = ET.Element("diagram", id=diagram_id, name=name)
    model = ET.SubElement(
        diagram, "mxGraphModel",
        dx="1200", dy="800", grid="1", gridSize="10",
        guides="1", tooltips="1", connect="1", arrows="1",
        fold="1", page="1", pageScale="1", pageWidth="1169", pageHeight="827",
        math="0", shadow="0"
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    return diagram, root


def add_cell(root, cell_id, value, style, x, y, w, h, parent="1", is_vertex=True):
    cell = ET.SubElement(
        root, "mxCell",
        id=str(cell_id),
        value=value,
        style=style,
        parent=str(parent),
        vertex="1" if is_vertex else "0"
    )
    geo = ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), as_="geometry")
    return cell


def add_edge(root, edge_id, value, style, source_id, target_id, parent="1", points=None):
    edge = ET.SubElement(
        root, "mxCell",
        id=str(edge_id),
        value=value,
        style=style,
        parent=str(parent),
        edge="1",
        source=str(source_id),
        target=str(target_id)
    )
    geo = ET.SubElement(edge, "mxGeometry", relative="1", as_="geometry")
    if points:
        pts = ET.SubElement(geo, "Array", as_="points")
        for px, py in points:
            ET.SubElement(pts, "mxPoint", x=str(px), y=str(py))
    return edge


# ----------------------------------------------------------------------
# Diagram 1: Architecture: Prototype to Redesign
# ----------------------------------------------------------------------
def build_diagram_1():
    diagram, root = create_base_diagram("diag-1-arch", "1. System Architecture")
    cid = 100

    # Human-like neat styling constants
    F_HEADER = "rounded=1;arcSize=6;fillColor=#1e293b;strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;"
    F_CONTAINER = "swimlane;startSize=28;rounded=1;arcSize=6;strokeWidth=1.5;fontStyle=1;fontSize=11;align=center;"
    F_BOX_BLUE = "rounded=1;arcSize=6;fillColor=#f0f9ff;strokeColor=#0284c7;strokeWidth=1;fontColor=#0369a1;fontSize=10;align=left;spacingLeft=10;spacingRight=10;whiteSpace=wrap;"
    F_BOX_PURPLE = "rounded=1;arcSize=6;fillColor=#faf5ff;strokeColor=#9333ea;strokeWidth=1;fontColor=#6b21a8;fontSize=10;align=left;spacingLeft=10;spacingRight=10;whiteSpace=wrap;"
    F_BOX_AMBER = "rounded=1;arcSize=6;fillColor=#fffbeb;strokeColor=#d97706;strokeWidth=1;fontColor=#92400e;fontSize=10;align=left;spacingLeft=10;spacingRight=10;whiteSpace=wrap;"
    F_BOX_RED = "rounded=1;arcSize=6;fillColor=#fef2f2;strokeColor=#ef4444;strokeWidth=1;fontColor=#991b1b;fontSize=10;align=left;spacingLeft=10;spacingRight=10;whiteSpace=wrap;"
    F_BOX_GREEN = "rounded=1;arcSize=6;fillColor=#f0fdf4;strokeColor=#16a34a;strokeWidth=1;fontColor=#166534;fontSize=10;align=left;spacingLeft=10;spacingRight=10;whiteSpace=wrap;"
    F_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#475569;strokeWidth=1.5;endArrow=classic;endFill=1;fontSize=9;fontColor=#475569;"

    # 1. Main Header
    add_cell(root, cid, "HIGHFLY COMPUTATIONAL NEURO-PHARMACOLOGY: PROTOTYPE TO REDESIGN", F_HEADER, 40, 20, 1080, 42)
    cid += 1

    # Container 1: Molecular Input (Left)
    c1_id = cid
    add_cell(root, cid, "1. MOLECULAR PHARMACOLOGY", F_CONTAINER + "fillColor=#f8fafc;strokeColor=#94a3b8;fontColor=#334155;", 40, 80, 230, 580)
    cid += 1
    b1_1 = cid
    add_cell(root, cid, "<b>17 Bioactive Compounds</b><br>• Stimulants (Vyvanse, Caffeine)<br>• Sedatives (Dormiphen, Gravol)<br>• Anesthetics (Lidocaine)<br>• Cannabinoids (THC, CBD)<br>• Multi-Tox (Jungle Juice)", F_BOX_BLUE, 55, 120, 200, 110)
    cid += 1
    b1_2 = cid
    add_cell(root, cid, "<b>PubChem Verified Data</b><br>• Standardized PubChem CIDs<br>• Verified 2D/3D SMILES<br>• Primary Molecular Targets", F_BOX_BLUE, 55, 245, 200, 80)
    cid += 1
    b1_3 = cid
    add_cell(root, cid, "<b>Receptor Binding Kinetics</b><br>• Cooperative Hill Equation:<br>&nbsp;&nbsp;θ(D) = Dⁿ / (K_dⁿ + Dⁿ)<br>• Verified Dissociation K_d", F_BOX_BLUE, 55, 340, 200, 95)
    cid += 1
    b1_4 = cid
    add_cell(root, cid, "<b>Pharmacokinetics (PK)</b><br>• Two-compartment absorption<br>• C_max, T_max, elimination t_½<br>• Active hepatic metabolites", F_BOX_BLUE, 55, 450, 200, 85)
    cid += 1

    # Container 2: Connectome (Middle Left)
    c2_id = cid
    add_cell(root, cid, "2. DROSOPHILA CONNECTOME", F_CONTAINER + "fillColor=#f8fafc;strokeColor=#94a3b8;fontColor=#334155;", 295, 80, 245, 580)
    cid += 1
    b2_1 = cid
    add_cell(root, cid, "<b>FlyWire Codex (FAFB v783)</b><br>• 139,255 Reconstructed Neurons<br>• 54.5 Million Synapses<br>• Full Whole-Brain Wiring", F_BOX_PURPLE, 310, 120, 215, 85)
    cid += 1
    b2_2 = cid
    add_cell(root, cid, "<b>Synaptic Sub-Networks</b><br>• Cholinergic (ACH) & Glutamate<br>• GABAergic (Rdl) & Serotonin<br>• Octopaminergic & Dopamine", F_BOX_PURPLE, 310, 220, 215, 85)
    cid += 1
    b2_3 = cid
    add_cell(root, cid, "<b>LIF Membrane Potential</b><br>• τ_m (dV_i/dt) = -(V_i - V_rest)<br>&nbsp;&nbsp;+ Σ W_ij s_j(t) + I_ext<br>• Sparse rate dynamics", F_BOX_PURPLE, 310, 320, 215, 95)
    cid += 1
    b2_4 = cid
    add_cell(root, cid, "<b>1,305 Descending Neurons</b><br>• DNa01, DNa02 (Forward walk)<br>• MDN (Moonwalker halt/reverse)<br>• Cervical connective bundle", F_BOX_PURPLE, 310, 430, 215, 95)
    cid += 1

    # Container 3: Top Right - Original Fly Prototype
    c3_id = cid
    add_cell(root, cid, "3A. INITIAL PROTOTYPE: DROSOPHILA HEXAPOD (NeuroMechFly v2)", F_CONTAINER + "fillColor=#fef2f2;strokeColor=#ef4444;fontColor=#991b1b;", 565, 80, 555, 270)
    cid += 1
    b3_1 = cid
    add_cell(root, cid, "<b>6-Legged Hexapod Physics</b><br>• 18 Actuated joint DOFs<br>• Millimeter scale (1 mg mass)<br>• Realistic exoskeleton body", F_BOX_RED, 580, 120, 250, 75)
    cid += 1
    b3_2 = cid
    add_cell(root, cid, "<b>Hexapod Tripod CPG</b><br>• Alternating Tripod 1 & 2<br>• Phase coupling (LegCPG)<br>• Tarsal claw adhesion (15 µN)", F_BOX_RED, 850, 120, 255, 75)
    cid += 1
    b3_3 = cid
    add_cell(root, cid, "<b>Empirical Endpoints Measured</b><br>• Forward crawling velocity v_x (mm/s)<br>• Tripod Coordination Index (TCI)<br>• Odor / looming predator escape", F_BOX_RED, 580, 205, 250, 80)
    cid += 1
    b3_4 = cid
    add_cell(root, cid, "<b>PROTOTYPE LIMITATIONS:</b><br>• 6-legged tripod provides static stability<br>• Tarsal adhesion masks flaccid hypotonia<br>• Cannot exhibit biped falling or knee buckling", "rounded=1;arcSize=6;fillColor=#fee2e2;strokeColor=#b91c1c;strokeWidth=1.5;fontColor=#7f1d1d;fontSize=9.5;align=left;spacingLeft=8;", 850, 205, 255, 80)
    cid += 1

    # Container 4: Bottom Right - Redesigned Humanoid Biped
    c4_id = cid
    add_cell(root, cid, "3B. REDESIGN: ANTHROPOMORPHIC 3D HUMANOID BIPED (MuJoCo)", F_CONTAINER + "fillColor=#f0fdf4;strokeColor=#16a34a;fontColor=#166534;", 565, 370, 555, 290)
    cid += 1
    b4_1 = cid
    add_cell(root, cid, "<b>DNToHumanTranslator Engine</b><br>• Maps 1,305 DNs to HumanIntent<br>• Forward Drive (D_fwd) & Cadence<br>• Motor Tone (T_motor) & Coord (C_biped)", F_BOX_AMBER, 580, 410, 250, 80)
    cid += 1
    b4_2 = cid
    add_cell(root, cid, "<b>12-DOF Reciprocal Biped CPG</b><br>• 2 coupled Kuramoto phase oscillators<br>• Anti-phase alternation (Δφ = π)<br>• Stance (0-60%) & swing (60-100%)", F_BOX_GREEN, 850, 410, 255, 80)
    cid += 1
    b4_3 = cid
    add_cell(root, cid, "<b>3D Humanoid Physics Body</b><br>• Height 1.75 m | Total Mass 71.8 kg<br>• Realistic inertia, ground contact<br>• Active BWS harness (635 N lift)", F_BOX_GREEN, 580, 505, 250, 85)
    cid += 1
    b4_4 = cid
    add_cell(root, cid, "<b>CLINICAL GAIT UNMASKING:</b><br>• Quantitative speed in m/s & Cadence (Hz)<br>• Unmasks knee buckling & extensor collapse<br>• Clinically actionable ataxia detection", "rounded=1;arcSize=6;fillColor=#dcfce7;strokeColor=#15803d;strokeWidth=1.5;fontColor=#14532d;fontSize=9.5;align=left;spacingLeft=8;", 850, 505, 255, 85)
    cid += 1

    # Connectors
    add_edge(root, cid, "Kd & Occupancy", F_EDGE, b1_3, b2_2)
    cid += 1
    add_edge(root, cid, "DN Drive", F_EDGE, b2_4, b3_1)
    cid += 1
    add_edge(root, cid, "Homologous Intent", F_EDGE, b2_4, b4_1)
    cid += 1
    add_edge(root, cid, "Phase Drive", F_EDGE, b4_1, b4_2)
    cid += 1
    add_edge(root, cid, "Joint Torques", F_EDGE, b4_2, b4_3)
    cid += 1

    return diagram


# ----------------------------------------------------------------------
# Diagram 2: Neuro-Human Translation & Homology
# ----------------------------------------------------------------------
def build_diagram_2():
    diagram, root = create_base_diagram("diag-2-homology", "2. Neuro-Human Homology")
    cid = 200

    F_HEADER = "rounded=1;arcSize=6;fillColor=#1e293b;strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;"
    F_COL_HDR = "rounded=1;arcSize=6;fillColor=#334155;strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=11;align=center;verticalAlign=middle;"
    F_FLY = "rounded=1;arcSize=6;fillColor=#fef2f2;strokeColor=#ef4444;strokeWidth=1;fontColor=#991b1b;fontSize=10;align=left;spacingLeft=10;"
    F_MATH = "rounded=1;arcSize=6;fillColor=#fffbeb;strokeColor=#d97706;strokeWidth=1;fontColor=#92400e;fontSize=9.5;fontFamily=Courier New;align=center;"
    F_HUMAN = "rounded=1;arcSize=6;fillColor=#f0fdf4;strokeColor=#16a34a;strokeWidth=1;fontColor=#166534;fontSize=10;align=left;spacingLeft=10;"
    F_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#64748b;strokeWidth=1.5;endArrow=classic;endFill=1;"

    add_cell(root, cid, "FUNCTIONAL NEURO-ANATOMICAL HOMOLOGY: DROSOPHILA TO HUMANOID", F_HEADER, 40, 20, 1080, 42)
    cid += 1

    # Column Headers
    add_cell(root, cid, "DROSOPHILA CONNECTOME (FlyWire)", F_COL_HDR, 40, 75, 320, 32)
    cid += 1
    add_cell(root, cid, "TRANSLATION ENGINE (DNToHumanTranslator)", F_COL_HDR, 380, 75, 350, 32)
    cid += 1
    add_cell(root, cid, "HUMANOID MOTOR SYSTEM (MuJoCo)", F_COL_HDR, 750, 75, 370, 32)
    cid += 1

    # Row 1: Forward Propulsion
    y = 120
    b_f1 = cid; add_cell(root, cid, "<b>Descending Forward Neurons</b><br>• DNa01 & DNa02 population rate<br>• Direct excitation to walking VNC<br>• Speed modulation via firing rate", F_FLY, 40, y, 320, 85); cid += 1
    b_m1 = cid; add_cell(root, cid, "D_fwd = clip([0.65(0.7 R_DN + 0.3 R_DNa<br>- 1.2 ΔR_MDN) + S_stim] · scale_para, 0, 1)", F_MATH, 380, y+10, 350, 65); cid += 1
    b_h1 = cid; add_cell(root, cid, "<b>MLR & Reticulospinal Tract</b><br>• Mesencephalic Locomotor Region<br>• Reticulospinal drive to lumbar spinal cord<br>• Modulates biped forward velocity (m/s)", F_HUMAN, 750, y, 370, 85); cid += 1
    add_edge(root, cid, "", F_EDGE, b_f1, b_m1); cid += 1
    add_edge(root, cid, "", F_EDGE, b_m1, b_h1); cid += 1

    # Row 2: Motor Arrest
    y += 105
    b_f2 = cid; add_cell(root, cid, "<b>Moonwalker Neurons (MDN)</b><br>• Backward walking command<br>• Immediate forward stepping arrest<br>• Defensive threat response", F_FLY, 40, y, 320, 85); cid += 1
    b_m2 = cid; add_cell(root, cid, "ΔR_MDN = max(0, (R_MDN - R_base)/R_base)<br>D_fwd -> 0.05 | Mode -> 'freeze'", F_MATH, 380, y+10, 350, 65); cid += 1
    b_h2 = cid; add_cell(root, cid, "<b>Brainstem Pause Neurons (PnO/Gi)</b><br>• Pontine / gigantocellular reticular arrest<br>• Halts central pattern generators<br>• Freezing & balance bracing", F_HUMAN, 750, y, 370, 85); cid += 1
    add_edge(root, cid, "", F_EDGE, b_f2, b_m2); cid += 1
    add_edge(root, cid, "", F_EDGE, b_m2, b_h2); cid += 1

    # Row 3: Reciprocal Coordination
    y += 105
    b_f3 = cid; add_cell(root, cid, "<b>VNC GABAergic Interneurons</b><br>• Rdl / GABA_A receptor channels<br>• Enforces alternating tripod stepping<br>• Inter-leg phase coupling w_c", F_FLY, 40, y, 320, 85); cid += 1
    b_m3 = cid; add_cell(root, cid, "C_biped = clip(1.0 - Φ_GABA, 0, 1)<br>w_c = w_0 · C_biped (w_0 = 6.0 rad/s)", F_MATH, 380, y+10, 350, 65); cid += 1
    b_h3 = cid; add_cell(root, cid, "<b>Spinal Commissural Interneurons</b><br>• Lumbar CINs mediating reciprocal Ia inhibition<br>• Enforces anti-phase alternation (Δφ = π)<br>• Blockade -> Stochastic ataxic staggering", F_HUMAN, 750, y, 370, 85); cid += 1
    add_edge(root, cid, "", F_EDGE, b_f3, b_m3); cid += 1
    add_edge(root, cid, "", F_EDGE, b_m3, b_h3); cid += 1

    # Row 4: Axonal Conduction & Muscle Tone
    y += 105
    b_f4 = cid; add_cell(root, cid, "<b>para Voltage-Gated Na+ Channels</b><br>• Axonal action potential propagation<br>• Blocked by local anesthetics (Lidocaine)<br>• Governs intrinsic excitability scale", F_FLY, 40, y, 320, 85); cid += 1
    b_m4 = cid; add_cell(root, cid, "T_motor = clip(scale_para · [0.3 + 0.7<br>· min(1.0, R_DN / R_DN,base)], 0.05, 1.0)", F_MATH, 380, y+10, 350, 65); cid += 1
    b_h4 = cid; add_cell(root, cid, "<b>Axonal Nav1.1 / Nav1.2 / Nav1.6</b><br>• Alpha-motor neuron action potential spike<br>• Extensor motor unit recruitment<br>• Blockade -> Flaccid hypotonia & knee buckling", F_HUMAN, 750, y, 370, 85); cid += 1
    add_edge(root, cid, "", F_EDGE, b_f4, b_m4); cid += 1
    add_edge(root, cid, "", F_EDGE, b_m4, b_h4); cid += 1

    # Row 5: Arousal & Cadence
    y += 105
    b_f5 = cid; add_cell(root, cid, "<b>Dopamine & Nicotinic Arousal</b><br>• D1-like dopamine & dDAT transporters<br>• Nicotinic acetylcholine receptors (nAChR)<br>• Histamine wake pathway (HisCl1/Ort)", F_FLY, 40, y, 320, 85); cid += 1
    b_m5 = cid; add_cell(root, cid, "ν = clip(ν_base · [0.6 + 0.7 D_fwd]<br>· G_stim, 0.4, 2.2) [Hz]", F_MATH, 380, y+10, 350, 65); cid += 1
    b_h5 = cid; add_cell(root, cid, "<b>Basal Ganglia Dopamine & ARAS</b><br>• Striatal D1/D2 locomotor vigor loops<br>• Ascending Reticular Activating System<br>• Sets stepping cadence & stride frequency", F_HUMAN, 750, y, 370, 85); cid += 1
    add_edge(root, cid, "", F_EDGE, b_f5, b_m5); cid += 1
    add_edge(root, cid, "", F_EDGE, b_m5, b_h5); cid += 1

    return diagram


# ----------------------------------------------------------------------
# Diagram 3: Reciprocal Biped CPG & Control Loop
# ----------------------------------------------------------------------
def build_diagram_3():
    diagram, root = create_base_diagram("diag-3-cpg", "3. Biped CPG Control Loop")
    cid = 300

    F_HEADER = "rounded=1;arcSize=6;fillColor=#1e293b;strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;"
    F_CONTAINER = "swimlane;startSize=26;rounded=1;arcSize=6;strokeWidth=1.5;fontStyle=1;fontSize=11;align=center;"
    F_BOX_BLUE = "rounded=1;arcSize=6;fillColor=#f0f9ff;strokeColor=#0284c7;strokeWidth=1;fontColor=#0369a1;fontSize=10;align=center;"
    F_BOX_GREEN = "rounded=1;arcSize=6;fillColor=#f0fdf4;strokeColor=#16a34a;strokeWidth=1;fontColor=#166534;fontSize=10;align=center;"
    F_BOX_AMBER = "rounded=1;arcSize=6;fillColor=#fffbeb;strokeColor=#d97706;strokeWidth=1;fontColor=#92400e;fontSize=10;align=center;"
    F_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#475569;strokeWidth=1.5;endArrow=classic;endFill=1;fontSize=9;fontColor=#334155;"

    add_cell(root, cid, "12-DOF RECIPROCAL BIPED CPG & CLOSED-LOOP MUJOCO BIOMECHANICS", F_HEADER, 40, 20, 1080, 42)
    cid += 1

    # Stage 1: Decoded HumanIntent
    b_intent = cid
    add_cell(root, cid, "<b>HumanIntent Vector</b><br>• D_fwd (Forward Drive: 0-1)<br>• T_motor (Extensor Tone: 0-1)<br>• C_biped (Coordination: 0-1)<br>• ν (Cadence: 0.4-2.2 Hz)<br>• L_stride (Stride Length scale)", F_BOX_AMBER, 40, 120, 200, 110)
    cid += 1

    # Stage 2: Central Pattern Generator
    b_cpg = cid
    add_cell(root, cid, "<b>Reciprocal Kuramoto CPG</b><br>• Left Oscillator: dφ_L/dt = 2πν + w_c sin(φ_R - φ_L - π) + η_L<br>• Right Oscillator: dφ_R/dt = 2πν + w_c sin(φ_L - φ_R - π) + η_R<br>• Coupling: w_c = w_0 · C_biped (w_0 = 6.0 rad/s)<br>• Anti-phase phase lock: Δφ = π", F_BOX_BLUE, 280, 120, 360, 110)
    cid += 1

    # Stage 3: Kinematic Engine
    b_kin = cid
    add_cell(root, cid, "<b>12-DOF Kinematic Engine</b><br>• Hip Pitch (Swing: +A_hip -> Stance: -A_hip)<br>• Knee Flexion (Stance weight -> Swing clearance 0.95 rad)<br>• Ankle Dorsi / Plantarflexion (Late stance push-off)<br>• Arm Swings (Reciprocal contralateral shoulder pitch)", F_BOX_GREEN, 680, 120, 360, 110)
    cid += 1

    # Stage 4: MuJoCo Physics Model
    b_mujoco = cid
    add_cell(root, cid, "<b>MuJoCo 3D Physics Simulation</b><br>• 1.75 m Height | 71.8 kg Mass (Torso, Pelvis, Thighs, Shins, Feet, Arms)<br>• Ground contact dynamics (Normal force, tangential friction, restitution)<br>• Forward velocity v_x (m/s) & Step Symmetry calculation", "rounded=1;arcSize=6;fillColor=#f8fafc;strokeColor=#475569;strokeWidth=1.5;fontColor=#1e293b;fontSize=10;align=center;", 680, 290, 360, 110)
    cid += 1

    # Stage 5: BWS Harness
    b_bws = cid
    add_cell(root, cid, "<b>Active Body-Weight Support (BWS)</b><br>• Overhead low-friction carriage along X-rail<br>• Viscoelastic slide suspension (harness_z, harness_y)<br>• Vertical lift: F_lift = 635 N · support · H_posture<br>• Prevents catastrophic tumbling under hypotonia", "rounded=1;arcSize=6;fillColor=#eff6ff;strokeColor=#3b82f6;strokeWidth=1.5;fontColor=#1e40af;fontSize=10;align=center;", 280, 290, 360, 110)
    cid += 1

    # Stage 6: Sensory Feedback & Ground Contact
    b_sense = cid
    add_cell(root, cid, "<b>Sensory Feedback & Phase Reset</b><br>• Left / Right foot contact detection<br>• Dynamic duty factor computation<br>• Single-support coordination validation", F_BOX_AMBER, 40, 290, 200, 110)
    cid += 1

    # Connections
    add_edge(root, cid, "Drive & Cadence", F_EDGE, b_intent, b_cpg); cid += 1
    add_edge(root, cid, "Phases (φ_L, φ_R)", F_EDGE, b_cpg, b_kin); cid += 1
    add_edge(root, cid, "Joint Angles (θ_j)", F_EDGE, b_kin, b_mujoco); cid += 1
    add_edge(root, cid, "Pelvis State", F_EDGE, b_mujoco, b_bws); cid += 1
    add_edge(root, cid, "Ground Reactions", F_EDGE, b_mujoco, b_sense, points=[(860, 430), (140, 430)]); cid += 1
    add_edge(root, cid, "Phase Reset", F_EDGE, b_sense, b_intent); cid += 1

    return diagram


# ----------------------------------------------------------------------
# Diagram 4: Pharmacological Evaluation Workflow
# ----------------------------------------------------------------------
def build_diagram_4():
    diagram, root = create_base_diagram("diag-4-eval", "4. Pharmacological Workflow")
    cid = 400

    F_HEADER = "rounded=1;arcSize=6;fillColor=#1e293b;strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=13;align=center;verticalAlign=middle;"
    F_CONTAINER = "swimlane;startSize=26;rounded=1;arcSize=6;strokeWidth=1.5;fontStyle=1;fontSize=11;align=center;"
    F_BOX_BLUE = "rounded=1;arcSize=6;fillColor=#f0f9ff;strokeColor=#0284c7;strokeWidth=1;fontColor=#0369a1;fontSize=9.5;align=left;spacingLeft=8;"
    F_BOX_GREEN = "rounded=1;arcSize=6;fillColor=#f0fdf4;strokeColor=#16a34a;strokeWidth=1;fontColor=#166534;fontSize=9.5;align=left;spacingLeft=8;"
    F_BOX_RED = "rounded=1;arcSize=6;fillColor=#fef2f2;strokeColor=#ef4444;strokeWidth=1;fontColor=#991b1b;fontSize=9.5;align=left;spacingLeft=8;"
    F_BOX_PURPLE = "rounded=1;arcSize=6;fillColor=#faf5ff;strokeColor=#9333ea;strokeWidth=1;fontColor=#6b21a8;fontSize=9.5;align=left;spacingLeft=8;"
    F_BOX_ORANGE = "rounded=1;arcSize=6;fillColor=#fff7ed;strokeColor=#ea580c;strokeWidth=1;fontColor=#9a3412;fontSize=9.5;align=left;spacingLeft=8;"
    F_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#475569;strokeWidth=1.5;endArrow=classic;endFill=1;fontSize=9;fontColor=#334155;"

    add_cell(root, cid, "PHARMACOLOGICAL EVALUATION WORKFLOW ACROSS 18 CONDITIONS", F_HEADER, 40, 20, 1080, 42)
    cid += 1

    # Stage 1: The 6 Pharmacological Classes
    add_cell(root, cid, "PHARMACOLOGICAL SUBSTANCE CLASSES", F_CONTAINER + "fillColor=#f8fafc;strokeColor=#94a3b8;fontColor=#334155;", 40, 80, 1080, 140)
    cid += 1
    b_c1 = cid; add_cell(root, cid, "<b>1. Psychostimulants</b><br>• Lisdexamfetamine (Vyvanse)<br>• Caffeine, Bupropion<br>• Nicotine (Leaf & Extract)", F_BOX_BLUE, 55, 115, 160, 90); cid += 1
    b_c2 = cid; add_cell(root, cid, "<b>2. Central Depressants</b><br>• Diphenhydramine (Dormiphen)<br>• Dimenhydrinate (Gravol)<br>• Mirtazapine", F_BOX_PURPLE, 230, 115, 165, 90); cid += 1
    b_c3 = cid; add_cell(root, cid, "<b>3. Local Anesthetics</b><br>• Lidocaine (3676)<br>• High-affinity Na_v block<br>• para / Nav1.2 inhibitor", F_BOX_RED, 410, 115, 155, 90); cid += 1
    b_c4 = cid; add_cell(root, cid, "<b>4. Cannabinoids</b><br>• Delta-9-THC (Weed)<br>• Cannabidiol (CBD)<br>• CB1 / CB2 differential", F_BOX_GREEN, 580, 115, 155, 90); cid += 1
    b_c5 = cid; add_cell(root, cid, "<b>5. Muscle Relaxants</b><br>• Methocarbamol (Robax)<br>• Central spinal depressant<br>• Extensor tone relaxation", F_BOX_ORANGE, 750, 115, 160, 90); cid += 1
    b_c6 = cid; add_cell(root, cid, "<b>6. Polysubstance Mix</b><br>• 'Jungle Juice'<br>• Multi-tox combination<br>• Multi-system collapse", F_BOX_RED, 925, 115, 180, 90); cid += 1

    # Stage 2: Dual Simulation Battery
    b_dual = cid
    add_cell(root, cid, "<b>DUAL EMBODIED BENCHMARK BATTERY (18 Conditions x 2 Models)</b><br>"
                       "<b>Branch A:</b> Drosophila NeuroMechFly v2 Prototype (Hexapod v_x mm/s & Tripod Coordination Index)<br>"
                       "<b>Branch B:</b> Redesigned Anthropomorphic Humanoid (Biped v_x m/s, Cadence Hz, Motor Tone, Gait Mode)",
             "rounded=1;arcSize=6;fillColor=#f1f5f9;strokeColor=#334155;strokeWidth=1.5;fontColor=#0f172a;fontSize=11;align=center;", 140, 250, 880, 70)
    cid += 1

    # Stage 3: Quantitative Findings
    b_res1 = cid
    add_cell(root, cid, "<b>Stimulant Findings</b><br>• Fly: v_x up to 4.75 mm/s (+26%)<br>• Human: 1.40 m/s (+15.7%)<br>• Cadence rises to 1.35 Hz<br>• Hyper-kinetic stepping", F_BOX_BLUE, 60, 350, 230, 95); cid += 1

    b_res2 = cid
    add_cell(root, cid, "<b>Na_v Blockade (Lidocaine)</b><br>• Fly: v_x drops to 0.04 mm/s<br>• Human: Complete arrest (0.00 m/s)<br>• Motor Tone collapses to 0.10<br>• Severe knee buckling caught by BWS", F_BOX_RED, 320, 350, 240, 95); cid += 1

    b_res3 = cid
    add_cell(root, cid, "<b>Cannabinoid Divergence</b><br>• THC: Induces Ataxic gait (1.01 m/s)<br>• C_biped drops to 0.58 (Noise)<br>• CBD: Normal walking (1.15 m/s)<br>• Clean coordination (C_biped=1.0)", F_BOX_GREEN, 590, 350, 240, 95); cid += 1

    b_res4 = cid
    add_cell(root, cid, "<b>Multi-Tox Failure</b><br>• Fly: 0.09 mm/s (-97.5%)<br>• Human: 0.09 m/s (-92.6%)<br>• Severe ataxic flailing<br>• Acute homeostatic breakdown", F_BOX_RED, 860, 350, 240, 95); cid += 1

    # Connectors
    add_edge(root, cid, "", F_EDGE, b_c3, b_dual); cid += 1
    add_edge(root, cid, "", F_EDGE, b_dual, b_res1); cid += 1
    add_edge(root, cid, "", F_EDGE, b_dual, b_res2); cid += 1
    add_edge(root, cid, "", F_EDGE, b_dual, b_res3); cid += 1
    add_edge(root, cid, "", F_EDGE, b_dual, b_res4); cid += 1

    return diagram


def generate_all_drawio():
    # 1. Create individual diagrams
    d1 = build_diagram_1()
    d2 = build_diagram_2()
    d3 = build_diagram_3()
    d4 = build_diagram_4()

    def save_single(diag, filename):
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="HighFly", version="21.0.0", type="device")
        mxfile.append(diag)
        tree = ET.ElementTree(mxfile)
        ET.indent(tree, space="  ", level=0)
        p1 = DRAWIO_DIR / filename
        p2 = ARTIFACT_DIR / filename
        tree.write(p1, encoding="utf-8", xml_declaration=True)
        tree.write(p2, encoding="utf-8", xml_declaration=True)
        print(f"Saved: {p1}")

    save_single(d1, "1_architecture_prototype_to_redesign.drawio")
    save_single(d2, "2_neuro_human_translation_homology.drawio")
    save_single(d3, "3_reciprocal_biped_cpg_control.drawio")
    save_single(d4, "4_pharmacological_evaluation_workflow.drawio")

    # 2. Create Master Multi-Page Workbook
    master_mx = ET.Element("mxfile", host="app.diagrams.net", agent="HighFly", version="21.0.0", type="device")
    master_mx.append(build_diagram_1())
    master_mx.append(build_diagram_2())
    master_mx.append(build_diagram_3())
    master_mx.append(build_diagram_4())
    master_tree = ET.ElementTree(master_mx)
    ET.indent(master_tree, space="  ", level=0)
    m_p1 = DRAWIO_DIR / "highfly_master_diagrams.drawio"
    m_p2 = ARTIFACT_DIR / "highfly_master_diagrams.drawio"
    master_tree.write(m_p1, encoding="utf-8", xml_declaration=True)
    master_tree.write(m_p2, encoding="utf-8", xml_declaration=True)
    print(f"Saved Master Workbook: {m_p1}")


if __name__ == "__main__":
    generate_all_drawio()
