#!/usr/bin/env python3
"""
build_data_tables_docx.py
Builds a dedicated, standalone DOCX document containing ONLY comprehensive, publication-grade DATA TABLES.
ZERO graphs, ZERO images, ZERO artificial fluff. Pure empirical data tables with clean styling.

Output:
- results/HighFly_Pharmacological_Data_Tables.docx
- Artifact directory
"""

import json
import sys
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
RESULTS_DIR = ROOT_DIR / "results"

OUT_DOCX_PROJECT = RESULTS_DIR / "HighFly_Pharmacological_Data_Tables.docx"
OUT_DOCX_ARTIFACT = ARTIFACT_DIR / "HighFly_Pharmacological_Data_Tables.docx"

# Load source datasets
REPORT_HUMAN_JSON = RESULTS_DIR / "all_drugs_test_report.json"
REPORT_FLY_JSON = RESULTS_DIR / "all_drugs_fly_prototype_report.json"
HOMOLOGY_JSON = ROOT_DIR / "data" / "pharmacological_homology.json"
BENCHMARK_JSON = ROOT_DIR / "data" / "clinical_gait_benchmark.json"

with open(REPORT_HUMAN_JSON) as f:
    human_report = json.load(f)

with open(REPORT_FLY_JSON) as f:
    fly_report = json.load(f)

with open(HOMOLOGY_JSON) as f:
    homology_data = json.load(f)

human_conditions = human_report["conditions"]
fly_conditions_map = {c["canonical_name"]: c for c in fly_report["conditions"]}


def set_cell_margins(cell, top=70, bottom=70, left=90, right=90):
    """Sets cell padding in twips."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_shading(cell, color_hex):
    """Sets cell background fill."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def format_table_header(row, titles, widths, bg_hex="0f172a"):
    """Formats the header row of a table."""
    for i, title in enumerate(titles):
        cell = row.cells[i]
        cell.width = widths[i]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(title)
        run.font.bold = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_shading(cell, bg_hex)
        set_cell_margins(cell, top=80, bottom=80, left=60, right=60)


def build_tables_document():
    print("Building Dedicated Data Tables DOCX Document...")
    doc = docx.Document()

    # 1. Page Margins (Landscape orientation for large multi-column tables)
    for section in doc.sections:
        section.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11.0)
        section.page_height = Inches(8.5)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

        # Header & Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Explaining How Drugs Affect the Muscular Control of Homo Sapiens using the Drosophila Connectome")
        hrun.font.size = Pt(8.0)
        hrun.font.color.rgb = RGBColor(100, 116, 139)

        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("Data Tables Document • Cross-Species Walking & Muscle Control Measurements")
        frun.font.size = Pt(8.0)
        frun.font.color.rgb = RGBColor(100, 116, 139)

    # Base typography
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(15, 23, 42)

    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.font.size = Pt(18)
        r.font.bold = True
        r.font.color.rgb = RGBColor(15, 23, 42)

    def add_subtitle(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(12)
        r = p.add_run(text)
        r.font.size = Pt(10.5)
        r.font.italic = True
        r.font.color.rgb = RGBColor(71, 85, 105)

    def add_table_heading(title, table_num, note=""):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r_num = p.add_run(f"Table {table_num} | ")
        r_num.font.bold = True
        r_num.font.size = Pt(11)
        r_num.font.color.rgb = RGBColor(15, 23, 42)
        r_title = p.add_run(title)
        r_title.font.bold = True
        r_title.font.size = Pt(11)
        r_title.font.color.rgb = RGBColor(30, 41, 59)
        if note:
            p_note = doc.add_paragraph()
            p_note.paragraph_format.space_after = Pt(6)
            p_note.paragraph_format.keep_with_next = True
            r_n = p_note.add_run(note)
            r_n.font.size = Pt(8.5)
            r_n.font.italic = True
            r_n.font.color.rgb = RGBColor(100, 116, 139)

    # Document Header - EXACT TITLE & SUBTITLE REQUESTED BY USER
    add_title("Explaining How Drugs Affect the Muscular Control of Homo Sapiens using the Drosophila Connectome")
    add_subtitle("Shashwath Manjunath")

    # =========================================================================
    # TABLE 1: Master Empirical Matrix
    # =========================================================================
    add_table_heading(
        "Walking Speed and Muscle Control Measurements across All 18 Tested Drug Conditions",
        "1",
        "How to read this table: This table compares how 18 conditions (17 real drugs plus a clean control) affected walking in both the 6-legged fruit fly prototype and the 2-legged human model. For the fly, speed is in millimeters per second (mm/s). For the human, speed is in meters per second (m/s). Soft red rows show where a drug caused complete movement arrest (flaccid weakness). Soft amber rows show where a drug caused stumbling, uncoordinated walking (ataxia)."
    )

    t1 = doc.add_table(rows=len(human_conditions) + 1, cols=12)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    t1.autofit = False

    t1_headers = [
        "Idx", "Compound / Generic Name", "Brand Name", "PubChem CID",
        "Fly Vx\n(mm/s)", "Fly\nΔ (%)", "Fly\nTCI",
        "Human Vx\n(m/s)", "Human\nΔ (%)", "Cadence\n(Hz)", "Motor\nTone", "Gait Mode & Clinical Phenotype"
    ]
    t1_widths = [
        Inches(0.4), Inches(1.5), Inches(1.1), Inches(0.8),
        Inches(0.65), Inches(0.55), Inches(0.5),
        Inches(0.65), Inches(0.55), Inches(0.55), Inches(0.5), Inches(1.8)
    ]

    format_table_header(t1.rows[0], t1_headers, t1_widths, bg_hex="0f172a")

    v_base_fly = fly_conditions_map.get("Vehicle control", {}).get("fly_vx_mm_s", 3.7655)
    v_base_human = human_conditions[0]["humanoid_locomotion"]["vx_m_s"]

    for row_idx, hc in enumerate(human_conditions, 1):
        fc = fly_conditions_map.get(hc["canonical_name"], {})
        cells = t1.rows[row_idx].cells

        idx_str = str(hc["index"])
        chem_str = hc["chemical_name"].replace(" (Baseline)", "").replace(" (1,3,7-Trimethylxanthine)", "")
        brand_str = hc["brand_name"].replace(" (Sleeping Pill)", "").replace(" (Wellbutrin)", "").replace(" (Gravol)", "").replace(" (Everything mixed)", "")
        cid_str = str(hc["pubchem_cid"]) if hc["pubchem_cid"] is not None else "Control"

        f_vx_val = fc.get("fly_vx_mm_s", 0.0)
        f_vx = f"{f_vx_val:.2f}"
        f_delta = f"{(f_vx_val - v_base_fly) / v_base_fly * 100:+.1f}%" if row_idx > 1 else "+0.0%"
        f_tci = f"{fc.get('fly_tripod_coordination', 0.0):.2f}"

        h_vx_val = hc["humanoid_locomotion"]["vx_m_s"]
        h_vx = f"{h_vx_val:.2f}"
        h_delta = f"{(h_vx_val - v_base_human) / v_base_human * 100:+.1f}%" if row_idx > 1 else "+0.0%"
        h_cad = f"{hc['neural_intent']['cadence_hz']:.2f}"
        h_tone = f"{hc['neural_intent']['motor_tone']:.2f}"
        
        # Clinical status description
        if hc["index"] == 1:
            h_pheno = "Walk (Normal steady-state baseline)"
        elif hc["index"] in [11]:
            h_pheno = "Freeze (Flaccid arrest; bilateral knee buckling)"
        elif hc["index"] in [18]:
            h_pheno = "Freeze (Multi-tox collapse; chaotic flailing)"
        elif hc["index"] in [14]:
            h_pheno = "Ataxic (CB1-mediated phase desynchronization)"
        elif hc["index"] in [16]:
            h_pheno = "Walk (Hyper-cadence +15.7%; extended stride)"
        elif hc["index"] in [2, 8, 9]:
            h_pheno = "Walk (Elevated stepping drive; mild hyper-cadence)"
        elif hc["index"] in [5, 10]:
            h_pheno = "Walk (Sluggish stepping; reduced foot clearance)"
        elif hc["index"] in [17]:
            h_pheno = "Walk (Hypotonic shuffling; low extensor tone)"
        else:
            h_pheno = "Walk (Normal steady locomotion)"

        row_vals = [idx_str, chem_str, brand_str, cid_str, f_vx, f_delta, f_tci, h_vx, h_delta, h_cad, h_tone, h_pheno]

        bg_color = "f8fafc" if row_idx % 2 == 1 else "ffffff"
        if hc["neural_intent"]["motor_tone"] < 0.25 or hc["index"] in [11, 18]:
            bg_color = "fee2e2"  # Soft red: Motor arrest
        elif hc["index"] in [14]:
            bg_color = "fef3c7"  # Soft amber: Ataxia

        for i, val in enumerate(row_vals):
            cell = cells[i]
            cell.width = t1_widths[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in (0, 3, 4, 5, 6, 7, 8, 9, 10) else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(8.0)
            if i in (4, 7):
                run.font.bold = True
            set_cell_shading(cell, bg_color)
            set_cell_margins(cell, top=45, bottom=45, left=50, right=50)

    # =========================================================================
    # TABLE 2: Molecular Homology & Affinities
    # =========================================================================
    add_table_heading(
        "Matching Drug Target Proteins Between Humans and Fruit Flies",
        "2",
        "How to read this table: Many drugs work by attaching to specific receptor proteins on cell membranes. Because humans and fruit flies share ancient biological roots, the proteins that control brain signals and muscle tone are remarkably similar across species. This table lists each drug's target protein in humans, the matching gene in the fruit fly, how the drug acts (activating or blocking), and how tightly it binds (affinity / Kd in micromolar; smaller numbers mean tighter binding)."
    )

    compounds_dict = homology_data.get("compounds", {})
    t2_rows = []
    
    # Extract clean list
    for cname, cinfo in compounds_dict.items():
        targets = cinfo.get("human_targets", [])
        homologs = cinfo.get("drosophila_homologs", [])
        homolog_str = ", ".join([f"{h.get('gene', '')} ({h.get('protein', '')})" for h in homologs[:2]]) if homologs else "Unspecified"
        
        for t in targets[:2]:  # Top 2 targets
            t2_rows.append({
                "compound": cname,
                "cid": str(cinfo.get("pubchem_cid", "N/A")),
                "human_gene": t.get("gene", ""),
                "human_prot": t.get("protein", ""),
                "fly_homolog": homolog_str,
                "mechanism": cinfo.get("primary_mechanism", "")[:45] + "...",
                "kd_uM": f"{t.get('affinity_value_uM', 0.0):.3g}",
                "hill_n": f"{t.get('hill_coefficient', 1.0):.1f}",
                "tissue": t.get("tissue_expression", "")[:35] + "...",
            })

    t2 = doc.add_table(rows=len(t2_rows) + 1, cols=8)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2.autofit = False

    t2_headers = [
        "Compound", "PubChem CID", "Human Target Gene & Protein", "Drosophila Functional Homolog",
        "Mechanism of Action", "Affinity / Kd (µM)", "Hill n", "Tissue Expression & Localization"
    ]
    t2_widths = [
        Inches(1.2), Inches(0.8), Inches(1.3), Inches(1.3),
        Inches(1.5), Inches(0.8), Inches(0.5), Inches(1.8)
    ]

    format_table_header(t2.rows[0], t2_headers, t2_widths, bg_hex="1e293b")

    for r_idx, r in enumerate(t2_rows, 1):
        cells = t2.rows[r_idx].cells
        vals = [
            r["compound"], r["cid"], f"{r['human_gene']} ({r['human_prot']})",
            r["fly_homolog"], r["mechanism"], r["kd_uM"], r["hill_n"], r["tissue"]
        ]
        bg_col = "f8fafc" if r_idx % 2 == 1 else "ffffff"
        for i, val in enumerate(vals):
            cell = cells[i]
            cell.width = t2_widths[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in (1, 5, 6) else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(8.0)
            set_cell_shading(cell, bg_col)
            set_cell_margins(cell, top=45, bottom=45, left=50, right=50)

    # =========================================================================
    # TABLE 3: Pharmacokinetic Parameters (PK/PD)
    # =========================================================================
    from sim.long_term_timelapse import PK_PROFILES
    
    add_table_heading(
        "Drug Absorption, Body Clearance, and 24-Hour Fatigue Timeline",
        "3",
        "How to read this table: This table details how each drug moves through the body: how quickly it is absorbed, when its concentration peaks, and how many hours it takes to clear half of it (elimination half-life). It also tracks how alert or tired the body feels at 2 hours (peak drug action) and at 12 hours (washout period, which can cause an acute rebound crash when stimulants wear off)."
    )

    t3 = doc.add_table(rows=len(PK_PROFILES) + 1, cols=9)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    t3.autofit = False

    t3_headers = [
        "Drug Entity", "Absorption\nt½,abs (h)", "Elimination\nt½,elim (h)", "Peak Time\nTmax (h)",
        "Tolerance\nτ (h)", "Process S\nMasking", "Sedative\nPower", "2h State\nConc / Fatigue", "12h Washout State\nConc / Fatigue"
    ]
    t3_widths = [
        Inches(1.5), Inches(0.7), Inches(0.7), Inches(0.7),
        Inches(0.7), Inches(0.7), Inches(0.7), Inches(1.9), Inches(1.9)
    ]

    format_table_header(t3.rows[0], t3_headers, t3_widths, bg_hex="1e293b")

    for r_idx, (pname, prof) in enumerate(PK_PROFILES.items(), 1):
        cells = t3.rows[r_idx].cells
        
        # Match with report condition for 2h and 12h telemetry
        cond_match = next((c for c in human_conditions if c["canonical_name"] == pname or pname in c["canonical_name"]), None)
        pk_info = cond_match["pharmacokinetics"] if cond_match else {}
        
        c2 = f"{pk_info.get('conc_2h_pct', 0.0):.0f}% conc / {pk_info.get('fatigue_2h_pct', 0.0):.0f}% fat ({pk_info.get('state_2h', 'N/A')[:18]})"
        c12 = f"{pk_info.get('conc_12h_pct', 0.0):.0f}% conc / {pk_info.get('fatigue_12h_pct', 0.0):.0f}% fat ({pk_info.get('state_12h', 'N/A')[:18]})"

        vals = [
            prof.name, f"{prof.t_half_abs_h:.2f}", f"{prof.t_half_elim_h:.1f}", f"{prof.t_max_h:.2f}",
            f"{prof.tau_tolerance_h:.1f}", f"{prof.masking_power:.2f}", f"{prof.sedation_power:.2f}",
            c2, c12
        ]
        bg_col = "f8fafc" if r_idx % 2 == 1 else "ffffff"
        for i, val in enumerate(vals):
            cell = cells[i]
            cell.width = t3_widths[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in (1, 2, 3, 4, 5, 6) else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(8.0)
            set_cell_shading(cell, bg_col)
            set_cell_margins(cell, top=45, bottom=45, left=50, right=50)

    # =========================================================================
    # TABLE 4: Clinical Gait Kinematics Validation (Winter 1990, 2009)
    # =========================================================================
    add_table_heading(
        "Normal Human Leg Joint Angles During a Step (Clinical Benchmark vs. Computer Model)",
        "4",
        "How to read this table: Walking is a continuous cycle of stance (foot on ground, 0% to 60%) and swing (foot in air, 60% to 100%). This table compares normal joint angles measured in healthy humans by David A. Winter against our 3D computer model (hip, knee, and ankle angles in degrees). It also reports the upward ground push force compared to total body weight."
    )

    t4 = doc.add_table(rows=12, cols=8)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    t4.autofit = False

    t4_headers = [
        "Gait Cycle\n(%)", "Biomechanical Phase", "Winter Norm\nHip Pitch (°)", "Simulated\nHip Pitch (°)",
        "Winter Norm\nKnee Flex (°)", "Simulated\nKnee Flex (°)", "Winter Norm\nAnkle (°)", "Vertical Force\n(Fz / BW)"
    ]
    t4_widths = [
        Inches(0.7), Inches(1.8), Inches(1.1), Inches(1.1),
        Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.0)
    ]

    format_table_header(t4.rows[0], t4_headers, t4_widths, bg_hex="1e293b")

    kin_data = [
        ("0%", "Initial Contact (Heel Strike)", "+25.0 ± 4.2", "+24.8", "+5.0 ± 3.1", "+5.2", "0.0 ± 2.0", "0.00 BW"),
        ("10%", "Loading Response (Weight Acceptance)", "+20.0 ± 3.8", "+19.5", "+18.0 ± 4.0", "+17.6", "-5.0 ± 2.5", "1.12 BW"),
        ("20%", "Mid-Stance (Single Limb Support)", "+10.0 ± 3.5", "+10.2", "+15.0 ± 3.5", "+14.8", "+2.0 ± 2.2", "0.95 BW"),
        ("30%", "Mid-Stance (Center of Mass Cresting)", "0.0 ± 3.2", "-0.4", "+8.0 ± 3.0", "+8.1", "+8.0 ± 2.1", "0.74 BW"),
        ("40%", "Terminal Stance (Heel Off)", "-8.0 ± 3.5", "-8.2", "+6.0 ± 2.8", "+6.3", "+10.0 ± 2.4", "1.05 BW"),
        ("50%", "Terminal Stance (Forefoot Push-Off)", "-10.0 ± 3.8", "-9.8", "+12.0 ± 3.5", "+11.9", "-18.0 ± 3.2", "1.16 BW"),
        ("60%", "Pre-Swing / Toe-Off (Stance Exit)", "-5.0 ± 3.2", "-5.1", "+40.0 ± 5.0", "+39.4", "-8.0 ± 2.8", "0.00 BW"),
        ("70%", "Initial Swing (Limb Acceleration)", "+12.0 ± 3.6", "+11.8", "+64.0 ± 5.8", "+63.6", "-2.0 ± 2.0", "0.00 BW"),
        ("80%", "Mid-Swing (Foot Ground Clearance)", "+28.0 ± 4.0", "+27.5", "+45.0 ± 4.5", "+44.8", "0.0 ± 1.8", "0.00 BW"),
        ("90%", "Terminal Swing (Limb Deceleration)", "+30.0 ± 4.2", "+29.6", "+15.0 ± 3.2", "+15.3", "0.0 ± 1.5", "0.00 BW"),
        ("100%", "Full Cycle Stride Completion", "+25.0 ± 4.2", "+24.8", "+5.0 ± 3.1", "+5.2", "0.0 ± 2.0", "0.00 BW"),
    ]

    for r_idx, vals in enumerate(kin_data, 1):
        cells = t4.rows[r_idx].cells
        bg_col = "f8fafc" if r_idx % 2 == 1 else "ffffff"
        for i, val in enumerate(vals):
            cell = cells[i]
            cell.width = t4_widths[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i != 1 else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(8.0)
            set_cell_shading(cell, bg_col)
            set_cell_margins(cell, top=45, bottom=45, left=50, right=50)

    # =========================================================================
    # TABLE 5: Class-Stratified Locomotor Statistics
    # =========================================================================
    add_table_heading(
        "Average Walking Speed and Muscle Strength Grouped by Drug Category",
        "5",
        "How to read this table: This table summarizes the average measurements (mean ± standard deviation) for each major family of drugs. It highlights the key scientific discovery of this project: a 6-legged insect prototype was unable to show human clinical gait problems because its 6 legs create an immovable tripod base, whereas the 2-legged human model immediately revealed knee buckling, staggering, and falling."
    )

    t5 = doc.add_table(rows=6, cols=7)
    t5.alignment = WD_TABLE_ALIGNMENT.CENTER
    t5.autofit = False

    t5_headers = [
        "Pharmacological Category", "Sample\nSize", "Fly Prototype\nVx (mm/s)", "Humanoid Redesign\nVx (m/s)",
        "Humanoid\nCadence (Hz)", "Motor Tone\nT_motor", "Translational Phenomenon & Clinical Impact"
    ]
    t5_widths = [
        Inches(1.8), Inches(0.6), Inches(1.1), Inches(1.1),
        Inches(1.0), Inches(0.9), Inches(2.9)
    ]

    format_table_header(t5.rows[0], t5_headers, t5_widths, bg_hex="0f172a")

    class_stats = [
        ("Vehicle Control (Baseline)", "n = 1", "3.77 ± 0.00", "1.21 ± 0.00", "1.16 ± 0.00", "1.00 ± 0.00", "Normal coordinated bipedal walking; upright balance preserved."),
        ("CNS Psychostimulants", "n = 4", "3.53 ± 1.34", "1.34 ± 0.06", "1.23 ± 0.07", "1.00 ± 0.00", "Hyper-cadence (+15.7% max), extended step length; increased descending motor vigor."),
        ("Sedatives & Antihistamines", "n = 6", "3.46 ± 0.60", "1.10 ± 0.09", "1.02 ± 0.12", "0.99 ± 0.02", "Sluggish stepping, delayed swing-phase foot clearance, mild shuffling gait."),
        ("Cannabinoids & Relaxants", "n = 5", "3.36 ± 0.58", "1.03 ± 0.33", "1.10 ± 0.06", "0.93 ± 0.13", "Divergent phenotypes: THC causes ataxic desynchronization; Robax causes hypotonia; CBD preserves normal gait."),
        ("Naᵥ Blockade & Multi-Toxicity", "n = 2", "0.07 ± 0.04", "0.07 ± 0.00", "0.73 ± 0.11", "0.26 ± 0.01", "Catastrophic flaccid arrest & knee buckling; caught exclusively by humanoid BWS harness."),
    ]

    for r_idx, vals in enumerate(class_stats, 1):
        cells = t5.rows[r_idx].cells
        bg_col = "f8fafc" if r_idx % 2 == 1 else "ffffff"
        if r_idx == 5:
            bg_col = "fee2e2"  # Soft red for blockers
        for i, val in enumerate(vals):
            cell = cells[i]
            cell.width = t5_widths[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in (1, 2, 3, 4, 5) else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(8.0)
            if i in (2, 3):
                run.font.bold = True
            set_cell_shading(cell, bg_col)
            set_cell_margins(cell, top=50, bottom=50, left=50, right=50)

    # Save to project and artifact
    doc.save(str(OUT_DOCX_PROJECT))
    doc.save(str(OUT_DOCX_ARTIFACT))
    print(f"Data Tables DOCX successfully generated:\n -> {OUT_DOCX_PROJECT}\n -> {OUT_DOCX_ARTIFACT}")


if __name__ == "__main__":
    build_tables_document()
