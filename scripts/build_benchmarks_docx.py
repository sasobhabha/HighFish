#!/usr/bin/env python3
"""Build a DOCX report from benchmark test results rendered via LaTeX/KaTeX.

Loads the JSON produced by scripts/run_benchmark_suite.py, renders equations
to PNG images, and inserts data tables and figures into a Word document.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results" / "benchmarks"
EQUATIONS_DIR = ROOT / "results" / "equations"


def load_metrics(path: Path) -> dict:
    """Load the benchmark metrics JSON file produced by run_benchmark_suite.py."""
    data = json.loads(path.read_text())

    if "runs" in data:
        raise ValueError("loading single-metric JSON", "(see run_benchmark_suite.py)")

    return data


# ---------------------------------------------------------------------------
# TABLE BUILDING
# ---------------------------------------------------------------------------

def _add_caption(doc, text: str, before_key: bool = False) -> None:
    """Add an italic gray caption paragraph, kept with the adjacent block."""
    from docx.shared import Pt, RGBColor

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3 if not before_key else 10)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = before_key
    run = p.add_run(text)
    run.font.size = Pt(9.5)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)


def _add_data_table(doc, headers: list[str], rows: list[list], col_widths=None) -> None:
    """Add a plain bordered data table with bold header row."""
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        para = hdr[i].paragraphs[0]
        run = para.add_run(h)
        run.font.bold = True
        run.font.size = Pt(9)
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            para = cells[i].paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.RIGHT
            run = para.add_run("" if v is None else str(v))
            run.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


# ---------------------------------------------------------------------------
# REPORT ASSEMBLY
# ---------------------------------------------------------------------------
EQUATIONS = [
    {"id": "bm01_reaction_latency",
     "latex": r"\mathrm{RT}_{ \mathrm{med}} = \operatorname{median}_{k \in \mathcal{R}} \left( t^{(k)}_{ \mathrm{resp}} - t_{ \mathrm{onset}} \right)"},
    {"id": "bm02_velocity",
     "latex": r"v_x = \dfrac{x(T) - x(0)}{T}"},
    {"id": "bm03_straightness",
     "latex": r"\mathrm{SI} = \dfrac{\lVert x(T)-x(0) \rVert}{\int_0^{T} \lVert \dot{x}(t) \rVert\, dt}"},
    {"id": "bm04_step_symmetry",
     "latex": r"\mathrm{Sym} = 1 - \dfrac{\lvert \mathrm{DF}_L - \mathrm{DF}_R \rvert}{\mathrm{DF}_L + \mathrm{DF}_R}"},
    {"id": "bm05_coordination",
     "latex": r"C_{ \mathrm{biped}} = \dfrac{1}{T} \int_0^T \mathbb{1}\!\left[ \mathrm{stance}_L(t) \oplus \mathrm{stance}_R(t) \right]\, dt"},
    {"id": "bm06_fall_rate",
     "latex": r"P_{ \mathrm{fall}} = \dfrac{1}{N_{ \mathrm{trials}}} \sum_{k=1}^{N_{ \mathrm{trials}}} \mathbb{1}\!\left[ \min_t z^{(k)}(t) < 0.45\,\mathrm{m} \right]"},
]


def build_docx(metrics_path: Path, out_path: Path | None = None) -> Path:
    """Assemble the benchmark report DOCX (equations, tables, captions)."""
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    data = load_metrics(metrics_path)
    meta = data.get("metadata", {})
    drugs = data.get("drugs", {})

    rendered = render_latex_equations(EQUATIONS)

    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(meta.get("title", "Neuro-mechanical Benchmark Suite"))
    run.font.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    env = meta.get("environment", {})
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(
        f"suite v{meta.get('suite_version', '?')}  |  {env.get('timestamp_utc', '')}  |  "
        f"python {env.get('python', '?')}  |  {env.get('platform', '')}"
    )
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    # Methods: rendered equations + captions
    doc.add_heading("1. Methods — Benchmark Definitions", level=1)
    tests = meta.get("tests", {})
    eq_captions = {
        "bm01_reaction_latency": "R1/R2 — reaction latency: median over reflex responses of (response time − stimulus onset); responses detected by DN-drive threshold crossings beyond a pre-stimulus baseline.",
        "bm02_velocity": "M1 — forward velocity from pelvis displacement over the motion-baseline window.",
        "bm03_straightness": "M2 — straightness index = net displacement ÷ total path length (1 = perfectly straight).",
        "bm04_step_symmetry": "M3 — step symmetry from left/right duty factors DF.",
        "bm05_coordination": "M4 — biped coordination index: fraction of time in single support (⊕ = XOR of stance flags).",
        "bm06_fall_rate": "M6 — fall rate: fraction of trials whose minimum pelvis height drops below 0.45 m.",
    }
    for idx, eq in enumerate(EQUATIONS, 1):
        png = rendered.get(eq["id"])
        if png and png.exists():
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_picture(str(png), width=Inches(5.2))
        _add_caption(doc, f"Eq. {idx} — {eq_captions.get(eq['id'], eq['id'])}")

    # Table 1: Reflex benchmarks (R1/R2)
    doc.add_heading("2. Reflex Benchmarks (R1 / R2)", level=1)
    _add_caption(doc,
                 "Table 1 — Looming-escape reflex latency (median, s ± SD over trials) and escape success. "
                 "Onset at t=10 s of a 20 s trial; responses detected by DN-drive threshold crossing.",
                 before_key=True)
    headers = ["condition", "latency (s)", "latency SD (s)", "responded", "outcome"]
    rows = []
    for drug, r in drugs.items():
        rf = r.get("reflex", {})
        rows.append([
            drug,
            rf.get("reflex_latency_s"),
            rf.get("reflex_latency_sd_s"),
            "yes" if rf.get("responded") else "no",
            rf.get("outcome"),
        ])
    _add_data_table(doc, headers, rows)

    # Table 2: Motion benchmarks (M1-M5)
    doc.add_heading("3. Timing & Motion Benchmarks (M1-M5)", level=1)
    _add_caption(doc,
                 "Table 2 — Baseline locomotion kinematics over a 10 s motion window: velocity, straightness, "
                 "step symmetry, single-support coordination, duty-factor spread |DF_L − DF_R|.",
                 before_key=True)
    headers = ["condition", "vx (m/s)", "straightness", "symmetry",
               "coordination", "duty spread"]
    rows = []
    for drug, r in drugs.items():
        mo = r.get("motion", {})
        rows.append([
            drug,
            mo.get("vx_m_s"),
            mo.get("straightness_index"),
            mo.get("step_symmetry"),
            mo.get("biped_coordination_index"),
            mo.get("duty_spread_abs"),
        ])
    _add_data_table(doc, headers, rows)

    # Table 3: Stability / fall-rate (M6)
    doc.add_heading("4. Stability Benchmarks (M6)", level=1)
    _add_caption(doc,
                 "Table 3 — Fall rate across repeated fresh trials under full MuJoCo physics "
                 "(unharnessed 6-DOF freejoint; real gravity, real falls) with coordination robustness "
                 "(mean ± SD of the biped coordination index).",
                 before_key=True)
    env = meta.get("environment", {})
    n_trials = env.get("n_trials_per_drug")
    headers = ["condition", f"fall rate (n={n_trials})", "coordination mean", "coordination SD"]
    rows = []
    for drug, r in drugs.items():
        st = r.get("stability", {})
        rows.append([
            drug,
            st.get("fall_rate"),
            st.get("coordination_mean"),
            st.get("coordination_sd"),
        ])
    _add_data_table(doc, headers, rows)

    if out_path is None:
        out_path = metrics_path.with_name(metrics_path.stem + "_report.docx")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metrics", default=str(RESULTS_DIR / "benchmark_metrics.json"),
                    help="path to benchmark_metrics.json from run_benchmark_suite.py")
    ap.add_argument("--out", default=None,
                    help="output DOCX path (default: <metrics stem>_report.docx)")
    ap.add_argument("--skip-render", action="store_true",
                    help="reuse existing equation PNGs (skip KaTeX rendering)")
    args = ap.parse_args()

    metrics_path = Path(args.metrics)
    if not metrics_path.exists():
        raise SystemExit(
            f"metrics file not found: {metrics_path}\n"
            "run scripts/run_benchmark_suite.py first to generate it"
        )
    if args.skip_render:
        global render_latex_equations
        render_latex_equations = lambda equations, out_dir=None: {
            eq["id"]: (out_dir or EQUATIONS_DIR) / f"{eq['id']}.png" for eq in equations
        }
    out = build_docx(metrics_path, out_path=Path(args.out) if args.out else None)
    print(f"wrote -> {out}")


# ---------------------------------------------------------------------------
# LATEX RENDERING
# ---------------------------------------------------------------------------

def render_latex_equations(equations, out_dir: Path | None = None) -> dict[str, Path]:
    """Render each {'id', 'latex'} entry to a standalone PNG.

    Returns a dict mapping each equation id to the path of its PNG.
    Results are cached on disk; repeated runs with the same LaTeX source are
    not re-rendered.
    """
    out_dir = (out_dir or EQUATIONS_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered: dict[str, Path] = {}
    for eq in equations:
        eq_id = eq["id"]
        latex = eq["latex"]
        out_path = out_dir / f"{eq_id}.png"
        _render_single_equation(latex, out_path)
        rendered[eq_id] = out_path
    return rendered


def _render_single_equation(latex: str, out_path: Path) -> None:
    """Render one LaTeX expression to a PNG at out_path, honoring the disk cache."""
    cache_key = _cache_key(latex)
    cache_path = out_path.with_suffix(".cache.json")
    if _cache_is_fresh(cache_path, latex, cache_key):
        return

    _render_with_katex(latex, out_path)
    _write_cache_entry(cache_path, latex, cache_key)


def _cache_key(latex: str) -> str:
    """Stable short hash used to detect stale cache entries."""
    import hashlib
    return hashlib.sha256(latex.encode("utf-8")).hexdigest()[:16]


def _cache_is_fresh(cache_path: Path, latex: str, cache_key: str) -> bool:
    if not cache_path.exists():
        return False
    try:
        entry = json.loads(cache_path.read_text())
    except json.JSONDecodeError:
        return False
    return entry.get("latex") == latex and entry.get("key") == cache_key


def _write_cache_entry(cache_path: Path, latex: str, cache_key: str) -> None:
    cache_path.write_text(json.dumps({"latex": latex, "key": cache_key}))


def _render_with_katex(latex: str, out_path: Path) -> None:
    """Write an HTML page that typesets `latex` with KaTeX and screenshot it to a PNG."""
    import subprocess
    import tempfile

    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
            <style>
                body {{ background: #ffffff; margin: 20px; }}
                #target {{ display: inline-block; }}
            </style>
        </head>
        <body>
            <div id="target"></div>
            <script>
                katex.render(String.raw`{latex}`, document.getElementById("target"), {{
                    displayMode: true,
                    throwOnError: false
                }});
            </script>
        </body>
        </html>
    """

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        tmp_html_path = f.name

    tmp_raw_png = out_path.with_suffix(".raw.png")
    try:
        chrome = _find_chrome()
        subprocess.run([
            str(chrome),
            "--headless=new",
            "--hide-scrollbars",
            f"--screenshot={tmp_raw_png}",
            "--window-size=2400,600",
            "--device-scale-factor=2",
            "--virtual-time-budget=3000",
            "--run-all-compositor-stages-before-draw",
            f"file://{tmp_html_path}",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _autocrop(tmp_raw_png, out_path)
    finally:
        Path(tmp_html_path).unlink()
        tmp_raw_png.unlink(missing_ok=True)


def _autocrop(raw_png: Path, out_png: Path) -> None:
    """Tightly crop a white-background screenshot to its glyphs with padding."""
    from PIL import Image, ImageChops

    img = Image.open(raw_png).convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bbox = ImageChops.difference(img, bg).getbbox()
    if not bbox:
        return
    pad_x, pad_y = 16, 10
    cropped = img.crop((
        max(0, bbox[0] - pad_x),
        max(0, bbox[1] - pad_y),
        min(img.width, bbox[2] + pad_x),
        min(img.height, bbox[3] + pad_y),
    ))
    cropped.save(out_png, optimize=True)


def _find_chrome() -> Path:
    """Locate a Chrome/Chromium executable across common install locations."""
    import shutil

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return Path(candidate)
    found = shutil.which("chromium") or shutil.which("google-chrome")
    if found:
        return Path(found)
    raise RuntimeError("No Chrome/Chromium executable found for KaTeX rendering.")


if __name__ == "__main__":
    main()

