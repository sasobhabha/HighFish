#!/usr/bin/env python3
"""Builds a complete, professional Draw.io suite:
- Interactive HTML viewer with live tab switching and 1-click 'Open in diagrams.net'
- Direct 1-click web links to app.diagrams.net
- Standalone .drawio files
- Copies to system artifact directory
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import urllib.parse
import zlib
import base64

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"
ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
DRAWIO_DIR = RESULTS_DIR / "diagrams_drawio"
DRAWIO_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def encode_drawio(xml_str: str) -> str:
    """Encodes Draw.io XML into standard diagrams.net URL hash format."""
    quoted = urllib.parse.quote(xml_str, safe='')
    compressor = zlib.compressobj(level=9, wbits=-15)
    deflated = compressor.compress(quoted.encode('utf-8')) + compressor.flush()
    return base64.b64encode(deflated).decode('ascii')


def main():
    diagram_files = [
        ("1_architecture_prototype_to_redesign.drawio", "1. System Architecture (Prototype vs. Redesign)",
         "High-level translation pipeline linking the FlyWire connectome to both the hexapod prototype and humanoid redesign."),
        ("2_neuro_human_translation_homology.drawio", "2. Neuro-Human Homology Matrix",
         "Detailed cross-species mapping from Fly Descending Neurons to Human MLR, Reticulospinal, and spinal CIN circuits."),
        ("3_reciprocal_biped_cpg_control.drawio", "3. 12-DOF Biped CPG & Control Loop",
         "Closed-loop control: HumanIntent -> Kuramoto oscillators -> 12-DOF kinematics -> MuJoCo physics with BWS harness."),
        ("4_pharmacological_evaluation_workflow.drawio", "4. Pharmacological Workflow Across 18 Conditions",
         "Dual-branch evaluation protocol classifying compounds into 6 clinical archetypes with quantitative endpoints."),
    ]

    links_md = []
    html_tabs = []
    html_panels = []

    for idx, (fname, title, desc) in enumerate(diagram_files):
        fpath = DRAWIO_DIR / fname
        with open(fpath, "r", encoding="utf-8") as f:
            xml_content = f.read()

        # Extract diagram XML inner content
        tree = ET.parse(fpath)
        diag_elm = tree.getroot().find("diagram")
        diag_xml = ET.tostring(diag_elm, encoding="unicode") if diag_elm is not None else xml_content

        # Generate draw.io web URL
        encoded_hash = encode_drawio(diag_xml)
        web_url = f"https://app.diagrams.net/#R{encoded_hash}"
        viewer_url = f"https://viewer.diagrams.net/?highlight=0000ff&edit=_blank&layers=1&nav=1&title={urllib.parse.quote(title)}#R{encoded_hash}"

        links_md.append({
            "title": title,
            "filename": fname,
            "file_path": str(fpath),
            "web_url": web_url,
            "viewer_url": viewer_url,
            "desc": desc
        })

        active_class = "active" if idx == 0 else ""
        tab_btn = f'<button class="tab-btn {active_class}" onclick="switchTab({idx})">{title}</button>'
        html_tabs.append(tab_btn)

        panel = f'''
        <div id="panel-{idx}" class="tab-panel {active_class}">
            <div class="panel-header">
                <div>
                    <h2>{title}</h2>
                    <p class="desc">{desc}</p>
                </div>
                <div class="actions">
                    <a href="{web_url}" target="_blank" class="btn btn-primary">Open & Edit in Draw.io (Web) ↗</a>
                    <a href="{fname}" download class="btn btn-secondary">Download .drawio</a>
                </div>
            </div>
            <div class="iframe-container">
                <iframe src="{viewer_url}" frameborder="0"></iframe>
            </div>
        </div>
        '''
        html_panels.append(panel)

    # Build interactive HTML viewer page
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HighFly Pharmacological Models — Draw.io Interactive Suite</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }}
        header {{
            background: #1e293b;
            padding: 14px 24px;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        header h1 {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #38bdf8;
            letter-spacing: -0.01em;
        }}
        header p {{
            font-size: 0.85rem;
            color: #94a3b8;
            margin-top: 2px;
        }}
        .tab-bar {{
            background: #1e293b;
            display: flex;
            gap: 4px;
            padding: 8px 24px 0 24px;
            border-bottom: 1px solid #334155;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            color: #94a3b8;
            padding: 10px 18px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            transition: all 0.15s ease;
        }}
        .tab-btn:hover {{
            background: #334155;
            color: #f8fafc;
        }}
        .tab-btn.active {{
            background: #0f172a;
            color: #38bdf8;
            border-bottom: 2px solid #38bdf8;
        }}
        .content {{
            flex: 1;
            position: relative;
            background: #0f172a;
        }}
        .tab-panel {{
            display: none;
            flex-direction: column;
            width: 100%;
            height: 100%;
            padding: 16px 24px;
        }}
        .tab-panel.active {{
            display: flex;
        }}
        .panel-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .panel-header h2 {{
            font-size: 1.05rem;
            font-weight: 600;
            color: #f1f5f9;
        }}
        .panel-header .desc {{
            font-size: 0.82rem;
            color: #94a3b8;
            margin-top: 3px;
        }}
        .actions {{
            display: flex;
            gap: 10px;
        }}
        .btn {{
            text-decoration: none;
            padding: 7px 14px;
            font-size: 0.82rem;
            font-weight: 600;
            border-radius: 6px;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
        }}
        .btn-primary {{
            background: #0284c7;
            color: #ffffff;
        }}
        .btn-primary:hover {{
            background: #0369a1;
        }}
        .btn-secondary {{
            background: #334155;
            color: #f1f5f9;
        }}
        .btn-secondary:hover {{
            background: #475569;
        }}
        .iframe-container {{
            flex: 1;
            background: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
        }}
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1>HighFly Computational Pharmacology — Draw.io Diagram Suite</h1>
            <p>Vector system architecture, neuro-human homology, and CPG biomechanics diagrams</p>
        </div>
    </header>
    <div class="tab-bar">
        {"".join(html_tabs)}
    </div>
    <div class="content">
        {"".join(html_panels)}
    </div>
    <script>
        function switchTab(idx) {{
            document.querySelectorAll('.tab-btn').forEach((b, i) => {{
                b.classList.toggle('active', i === idx);
            }});
            document.querySelectorAll('.tab-panel').forEach((p, i) => {{
                p.classList.toggle('active', i === idx);
            }});
        }}
    </script>
</body>
</html>'''

    out_html = DRAWIO_DIR / "interactive_diagram_viewer.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved Interactive HTML: {out_html}")

    with open(ARTIFACT_DIR / "interactive_diagram_viewer.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    # Save summary JSON for programmatic access
    with open(RESULTS_DIR / "drawio_manifest.json", "w", encoding="utf-8") as f:
        import json
        json.dump(links_md, f, indent=2)


if __name__ == "__main__":
    main()
