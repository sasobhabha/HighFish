#!/usr/bin/env python3
"""Builds a Google Sheets-ready Excel workbook (.xlsx) and separate CSV files
containing the complete empirical comparison, receptor homology matrix, and report template."""

import json
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
RESULTS_DIR = ROOT_DIR / "results"
CSV_DIR = RESULTS_DIR / "sheets_csv"
CSV_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_HUMAN_JSON = RESULTS_DIR / "all_drugs_test_report.json"
REPORT_FLY_JSON = RESULTS_DIR / "all_drugs_fly_prototype_report.json"

with open(REPORT_HUMAN_JSON) as f:
    human_report = json.load(f)

with open(REPORT_FLY_JSON) as f:
    fly_report = json.load(f)

human_conditions = human_report["conditions"]
fly_conditions_map = {c["canonical_name"]: c for c in fly_report["conditions"]}

# Base vehicle reference values
BASE_FLY_VX = fly_conditions_map.get("Vehicle control", {}).get("fly_vx_mm_s", 3.7655)
BASE_HUMAN_VX = human_conditions[0]["humanoid_locomotion"]["vx_m_s"]


def create_excel_workbook():
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styling palettes
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    fill_sub_fly = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
    fill_sub_human = PatternFill(start_color="16A34A", end_color="16A34A", fill_type="solid")
    fill_sub_pk = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")

    font_data = Font(name="Calibri", size=10)
    font_bold = Font(name="Calibri", size=10, bold=True)
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_red = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    fill_amber = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    fill_blue = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")

    # =========================================================================
    # Sheet 1: 18_Drugs_Empirical_Comparison
    # =========================================================================
    ws1 = wb.create_sheet(title="18_Drugs_Comparison")
    ws1.views.sheetView[0].showGridLines = True

    # Title Banner
    ws1.merge_cells("A1:V1")
    t1 = ws1["A1"]
    t1.value = "HighFly Empirical Pharmacology Matrix: Drosophila Prototype vs. Redesigned Humanoid Biped"
    t1.font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    t1.alignment = Alignment(horizontal="left", vertical="center")
    ws1.row_dimensions[1].height = 28

    headers_row2 = [
        "Index", "Chemical / Generic Name", "Brand Name", "PubChem CID", "Drug Class", "Primary Molecular Target",
        # Fly Prototype
        "Fly Vx (mm/s)", "Fly Delta (%)", "Fly Tripod Coord (TCI)", "Fly DN Rate (Hz)", "Fly Upright (%)",
        # Humanoid Redesign
        "Human Vx (m/s)", "Human Delta (%)", "Cadence (Hz)", "Stride (m)", "Motor Tone", "Coordination", "Gait Mode", "Clinical Gait Status",
        # PK
        "Half-Life t½ (h)", "Peak Conc Cmax (%)", "12h Fatigue Rebound (%)"
    ]
    ws1.append(headers_row2)
    ws1.row_dimensions[2].height = 24

    for col_idx, text in enumerate(headers_row2, 1):
        cell = ws1.cell(row=2, column=col_idx)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border

    # Data rows
    csv_rows_1 = [headers_row2]

    # Drug class and target lookup
    drug_meta = {
        "Vehicle control": ("Baseline Control", "Vehicle (Phosphate Buffer)", "Normal Baseline"),
        "Caffeine": ("Stimulant", "Adenosine A1/A2A antagonist", "Hyper-cadence"),
        "Claritin (Tablet)": ("Antihistamine", "H1 receptor antagonist (systemic)", "Normal / Mild sedation"),
        "Claritin (Gel)": ("Antihistamine", "H1 receptor antagonist (topical)", "Normal / Mild sedation"),
        "Dormiphen (Sleeping Pill)": ("Sedative-Hypnotic", "H1 antagonist + M1 anticholinergic", "Sluggish / Stride slowing"),
        "Acetaminophen": ("Analgesic", "COX-2 / TRPA1 indirect modulator", "Normal gait"),
        "Bupropion (Wellbutrin)": ("Antidepressant / Stimulant", "DAT / NET reuptake inhibitor", "Elevated cadence"),
        "Tobacco": ("Stimulant", "nAChR agonist (whole leaf)", "Hyper-stepping"),
        "Tobacco Extract": ("Stimulant", "nAChR agonist (concentrated extract)", "Hyper-stepping"),
        "Dimenhydrinate (Gravol)": ("Antiemetic / Sedative", "H1 antagonist + muscarinic blocker", "Sluggish stepping"),
        "Lidocaine": ("Local Anesthetic", "para / Nav1.1/1.2 channel blocker", "Complete motor arrest & knee buckling"),
        "Lithium Acetate": ("Mood Stabilizer", "GSK-3β / Inositol monophosphatase", "Normal gait"),
        "Mirtazapine": ("Antidepressant", "5-HT2A/2C, 5-HT3, H1 antagonist", "Sedated shuffling"),
        "Weed": ("Cannabinoid", "CB1 partial agonist (Delta-9-THC)", "Ataxic desynchronization"),
        "CBD nanodrops": ("Cannabinoid", "CB1 negative allosteric / 5-HT1A", "Normal coordinated walk"),
        "Vyvanse": ("Psychostimulant", "TAAR1 / DAT / NET releaser", "Vigorous hyper-cadence (+15.7%)"),
        "Robax": ("Muscle Relaxant", "Spinal polysynaptic reflex inhibitor", "Hypotonic shuffling"),
        "Jungle Juice (Everything mixed)": ("Multi-Tox Cocktail", "Competitive multi-receptor collapse", "Severe ataxic collapse (-92.6%)")
    }

    for row_idx, hc in enumerate(human_conditions, 3):
        canonical = hc["canonical_name"]
        fc = fly_conditions_map.get(canonical, {})
        dclass, dtarget, dstatus = drug_meta.get(canonical, ("Other", "N/A", "Normal"))

        f_vx = fc.get("fly_vx_mm_s", 0.0)
        f_delta = round(((f_vx - BASE_FLY_VX) / BASE_FLY_VX) * 100, 1)
        f_tci = fc.get("fly_tripod_coordination", 0.0)
        f_dn = fc.get("fly_mean_dn_rate", 0.0)
        f_upright = fc.get("fly_upright_pct", 100.0)

        h_vx = hc["humanoid_locomotion"]["vx_m_s"]
        h_delta = round(((h_vx - BASE_HUMAN_VX) / BASE_HUMAN_VX) * 100, 1)
        h_cad = hc["neural_intent"]["cadence_hz"]
        h_stride = hc["neural_intent"]["stride_length_m"]
        h_tone = hc["neural_intent"]["motor_tone"]
        h_coord = hc["neural_intent"]["coordination"]
        h_mode = hc["neural_intent"]["gait_mode"].capitalize()

        pk = hc.get("pharmacokinetics", {})
        pk_thalf = pk.get("t_half_elim_h", "N/A")
        pk_cmax = pk.get("conc_2h_pct", "N/A")
        pk_rebound = pk.get("fatigue_12h_pct", "N/A")

        cid_val = hc["pubchem_cid"] if hc["pubchem_cid"] is not None else "Control"

        vals = [
            hc["index"],
            hc["chemical_name"].replace(" (Baseline)", "").replace(" (1,3,7-Trimethylxanthine)", ""),
            hc["brand_name"].replace(" (Sleeping Pill)", "").replace(" (Wellbutrin)", "").replace(" (Gravol)", "").replace(" (Everything mixed)", ""),
            cid_val,
            dclass,
            dtarget,
            f_vx,
            f"{f_delta:+.1f}%",
            f_tci,
            f_dn,
            f"{f_upright:.1f}%",
            h_vx,
            f"{h_delta:+.1f}%",
            h_cad,
            h_stride,
            h_tone,
            h_coord,
            h_mode,
            dstatus,
            pk_thalf,
            f"{pk_cmax}%" if pk_cmax != "N/A" else "N/A",
            f"{pk_rebound}%" if pk_rebound != "N/A" else "N/A"
        ]
        ws1.append(vals)
        csv_rows_1.append(vals)
        ws1.row_dimensions[row_idx].height = 20

        # Conditional row color
        row_fill = fill_white if row_idx % 2 == 1 else fill_zebra
        if h_tone < 0.25:
            row_fill = fill_red
        elif h_mode == "Ataxic":
            row_fill = fill_amber
        elif h_delta > 10.0:
            row_fill = fill_blue

        for col_i in range(1, len(vals) + 1):
            c = ws1.cell(row=row_idx, column=col_i)
            c.font = font_bold if col_i in (7, 12) else font_data
            c.fill = row_fill
            c.border = thin_border
            c.alignment = align_center if col_i in (1, 4, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 20, 21, 22) else align_left

    # Auto-fit columns
    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 3, 11)
    ws1.column_dimensions["B"].width = 28
    ws1.column_dimensions["F"].width = 36
    ws1.column_dimensions["S"].width = 36

    # =========================================================================
    # Sheet 2: Receptor_Homology_Matrix
    # =========================================================================
    ws2 = wb.create_sheet(title="Receptor_Homology")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:I1")
    t2 = ws2["A1"]
    t2.value = "HighFly Cross-Phylum Functional Homology & Receptor Affinity Matrix"
    t2.font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    t2.alignment = Alignment(horizontal="left", vertical="center")
    ws2.row_dimensions[1].height = 28

    headers_row2_s2 = [
        "Drug Compound", "Brand Name", "PubChem CID", "Drosophila Target", "FlyWire Sub-Graph",
        "Human Ortholog Target", "Human Anatomical Site", "Dissociation Kd / Ki (µM)", "Embodied Behavioral Effect"
    ]
    ws2.append(headers_row2_s2)
    ws2.row_dimensions[2].height = 24

    for col_idx, text in enumerate(headers_row2_s2, 1):
        cell = ws2.cell(row=2, column=col_idx)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border

    homology_data = [
        ("Caffeine", "Caffeine", "2519", "AdoR / DA signaling", "DA / OCT", "Adenosine A1 / A2A", "Striatum / Cortex", "12.0", "Cadence elevation & Process S masking"),
        ("Loratadine", "Claritin", "3957", "HisCl1 / Ort", "HIST", "Histamine H1 (peripheral)", "Periphery / Low CNS", "0.035", "Minimal motor impairment"),
        ("Diphenhydramine", "Dormiphen", "3100", "HisCl1 / Ort / mAChR", "HIST / ACH", "Histamine H1 / M1", "Hypothalamus / Cortex", "0.011", "Sedative sluggishness & swing-phase toe drag"),
        ("Acetaminophen", "Tylenol", "1983", "None (No fly ortholog)", "None", "COX-2 / TRPA1", "Spinal dorsal horn", "150.0", "Unimpaired baseline motor coordination"),
        ("Bupropion", "Wellbutrin", "444", "dDAT / OCT", "DA / OCT", "DAT / NET inhibitor", "VTA / Locus coeruleus", "0.52", "Arousal activation & stride frequency increase"),
        ("Nicotine", "Tobacco", "89594", "nAChR alpha/beta subunits", "ACH", "Neuronal α4β2 nAChR", "Autonomic ganglia / CNS", "0.004", "Massive cholinergic excitation (4.75 mm/s fly)"),
        ("Dimenhydrinate", "Gravol", "10670", "HisCl1 / mAChR", "HIST / ACH", "Histamine H1 / Muscarinic", "Vestibular nuclei / CNS", "0.015", "Vestibular suppression & stepping deceleration"),
        ("Lidocaine", "Lidocaine", "3676", "para (Na+ channel)", "Axonal", "Nav1.1 / Nav1.2 / Nav1.6", "Peripheral & spinal axons", "0.005", "Complete flaccid motor arrest & knee buckling"),
        ("Lithium Acetate", "Lithium", "11953928", "Shaggy (sgg / GSK-3)", "Intracellular", "GSK-3α / GSK-3β", "Cerebellum / Hippocampus", "2000.0", "Preserved locomotion with mild stabilizer lag"),
        ("Mirtazapine", "Remeron", "4254", "5-HT1B / HisCl1", "SER / HIST", "5-HT2A / 5-HT2C / H1", "Raphe / Cortex", "0.0016", "Antihistaminic sedation & reduced motor tone"),
        ("Delta-9-THC", "Weed", "16078", "None (Fly lacks CB1)", "GABA / DA indirect", "Cannabinoid CB1", "Spinal CINs / Basal ganglia", "0.040", "Ataxic desynchronization & lateral limb swaying"),
        ("Cannabidiol", "CBD", "644019", "5-HT1A / TRPA1", "SER / TRP", "CB1 allosteric / 5-HT1A", "Spinal cord / Limbic", "4.5", "Preserved coordination (C_biped = 1.00)"),
        ("Lisdexamfetamine", "Vyvanse", "11597398", "dDAT / D1-like", "DA / OCT", "TAAR1 / DAT / NET", "Prefrontal cortex / Striatum", "0.025", "Vigorous biped acceleration (+15.7% speed)"),
        ("Methocarbamol", "Robax", "4107", "GABA_A modulation", "GABA", "Central internuncial neurons", "Spinal internuncial pool", "85.0", "Hypotonic gait & reduced extensor tone (0.46 m/s)"),
        ("Jungle Juice", "Multi-Tox", "Cocktail", "Multi-system cross-block", "All sub-graphs", "Multi-receptor chaos", "Whole CNS / Spinal cord", "Various", "Profound multi-system motor collapse (-92.6%)")
    ]

    csv_rows_2 = [headers_row2_s2]
    for r_idx, row in enumerate(homology_data, 3):
        ws2.append(row)
        csv_rows_2.append(list(row))
        ws2.row_dimensions[r_idx].height = 20
        r_fill = fill_white if r_idx % 2 == 1 else fill_zebra
        for c_idx in range(1, len(row) + 1):
            c = ws2.cell(row=r_idx, column=c_idx)
            c.font = font_data
            c.fill = r_fill
            c.border = thin_border
            c.alignment = align_center if c_idx in (3, 8) else align_left

    for col in ws2.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws2.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # =========================================================================
    # Sheet 3: Section_By_Section_Template
    # =========================================================================
    ws3 = wb.create_sheet(title="Report_Template")
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells("A1:G1")
    t3 = ws3["A1"]
    t3.value = "Scientific Manuscript Blueprint: Section Outlines, Equations, and Deliverables"
    t3.font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    t3.alignment = Alignment(horizontal="left", vertical="center")
    ws3.row_dimensions[1].height = 28

    headers_row2_s3 = [
        "Section", "Section Title", "Purpose & Core Objective", "Required Topics to Discuss",
        "Key Mathematical Equations", "Figures & Tables Required", "Clinical Diagnostic Endpoint"
    ]
    ws3.append(headers_row2_s3)
    ws3.row_dimensions[2].height = 24

    for col_idx, text in enumerate(headers_row2_s3, 1):
        cell = ws3.cell(row=2, column=col_idx)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = thin_border

    template_data = [
        ("Abstract", "Executive Summary", "Synthesize findings across 18 conditions without fluff",
         "1. Problem statement\n2. FlyWire v783 prototype\n3. Redesign rationale\n4. Humanoid biped\n5. Key findings (Lidocaine, stimulants, Jungle Juice)",
         "None (Executive narrative)", "Summary metrics callout", "Translational safety pharmacology"),
        ("Section 1", "Theoretical Foundations & Drosophila Prototype", "Establish molecular homology and present the insect prototype",
         "1. Biogenic amine conservation\n2. FlyWire v783 connectome (139k neurons, 1.3k DNs)\n3. LIF rate dynamics\n4. Hill occupancy\n5. NeuroMechFly v2 hexapod\n6. Prototype limitations (static stability)",
         "Eq. 1: LIF Membrane Potential\nEq. 2: Hill Receptor Binding\nEq. 3: Tripod CPG Coupling", "Figure 1: Cross-Phylum Architecture", "Insect crawling speed (mm/s) & TCI"),
        ("Section 2", "The Redesign with the Humanoid Biped", "Explain the neuro-computational translation to human biomechanics",
         "1. Functional homology (DNa -> MLR; MDN -> pause neurons; para -> Nav)\n2. DNToHumanTranslator formulation\n3. 12-DOF reciprocal Kuramoto CPG\n4. MuJoCo 3D body (1.75m, 71.8kg)\n5. BWS harness (635 N lift)",
         "Eq. 4: Forward Drive D_fwd\nEq. 5: Motor Tone T_motor\nEq. 6: Biped Coordination C_biped\nEq. 7: Kuramoto CPG Coupling", "Figure 3: CPG & Joint Kinematics", "Bipedal velocity (m/s), Step frequency (Hz), Knee buckling"),
        ("Section 3", "Empirical Results Across 18 Conditions", "Present comprehensive quantitative findings comparing both models",
         "1. Performance table walkthrough\n2. Stimulant acceleration (+15.7% Vyvanse)\n3. Lidocaine flaccid arrest (0.00 m/s)\n4. Antihistamine sedation\n5. Cannabinoid bifurcation\n6. Multi-tox collapse (-92.6%)",
         "Percentage delta: ((Vx - V_base)/V_base) * 100", "Table 1: 18-Condition Performance Matrix\nFigure 2: Empirical Locomotion Comparison", "Side-by-side velocity and coordination"),
        ("Section 4", "Mechanistic Discussion by Drug Class", "Detailed pharmacological interpretation of observed phenotypes",
         "4.1 Psychostimulants (dopaminergic vigor)\n4.2 Local Anesthetics (para/Nav block)\n4.3 Antihistamines (histaminergic wake loss)\n4.4 Cannabinoid divergence (THC vs CBD)\n4.5 Jungle Juice (multi-receptor collapse)",
         "Rebound fatigue: F(t) = F_base + S(t) · (1 - C_p(t))", "Figure 4: 24h PK Curves & Process S\nFigure 5: Photographic Tracking Frames", "Clinical gait phenotypes (ataxia, hypotonia, shuffling)"),
        ("Section 5", "Limitations & Disclosures", "Scientific rigor and translational boundaries",
         "1. PK two-compartment standard clearance (omits CYP polymorphisms)\n2. Proprioception modeled via joint viscoelasticity\n3. Absence of multi-layer mammalian neocortex",
         "None", "Disclosures callout", "Model boundaries & assumptions"),
        ("Section 6", "References", "Formal academic citations", "13 Seminal papers (FlyWire, NeuroMechFly, Grillner, Lemon, Bidaye, Kiehn, Catterall, etc.)", "MLA 9th Edition", "Complete bibliography", "Scientific peer-review standard")
    ]

    csv_rows_3 = [headers_row2_s3]
    for r_idx, row in enumerate(template_data, 3):
        ws3.append(row)
        csv_rows_3.append(list(row))
        ws3.row_dimensions[r_idx].height = 45
        r_fill = fill_white if r_idx % 2 == 1 else fill_zebra
        for c_idx in range(1, len(row) + 1):
            c = ws3.cell(row=r_idx, column=c_idx)
            c.font = font_data
            c.fill = r_fill
            c.border = thin_border
            c.alignment = align_center if c_idx in (1, 5, 7) else align_left

    for col in ws3.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws3.column_dimensions[col_letter].width = max(max_len + 3, 14)
    ws3.column_dimensions["D"].width = 38
    ws3.column_dimensions["E"].width = 28
    ws3.column_dimensions["F"].width = 28

    # Save Excel Workbook
    out_xlsx_proj = RESULTS_DIR / "HighFly_Pharmacology_Google_Sheets_Ready.xlsx"
    out_xlsx_art = ARTIFACT_DIR / "HighFly_Pharmacology_Google_Sheets_Ready.xlsx"
    wb.save(out_xlsx_proj)
    wb.save(out_xlsx_art)
    print(f"Saved Excel Workbook: {out_xlsx_proj}")
    print(f"Saved Artifact Workbook: {out_xlsx_art}")

    # Save CSV files
    import csv
    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Saved CSV: {path}")

    write_csv(CSV_DIR / "18_drugs_empirical_comparison.csv", csv_rows_1)
    write_csv(ARTIFACT_DIR / "18_drugs_empirical_comparison.csv", csv_rows_1)

    write_csv(CSV_DIR / "receptor_homology_matrix.csv", csv_rows_2)
    write_csv(ARTIFACT_DIR / "receptor_homology_matrix.csv", csv_rows_2)

    write_csv(CSV_DIR / "scientific_report_template.csv", csv_rows_3)
    write_csv(ARTIFACT_DIR / "scientific_report_template.csv", csv_rows_3)


if __name__ == "__main__":
    create_excel_workbook()
