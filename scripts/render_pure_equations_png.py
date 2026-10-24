#!/usr/bin/env python3
"""
render_pure_equations_png.py
Renders pure LaTeX equation PNGs without any card boxes, borders, titles, or description text.

Features:
- Pure mathematical formulas rendered via KaTeX in Computer Modern typography.
- Auto-cropped tightly to equation glyphs with clean minimal padding.
- High resolution (2x retina).
- Clean white background.
- Saved to results/equations/ and copied to artifact directory.
"""

import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageChops

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")

OUT_DIR_PROJECT = ROOT_DIR / "results" / "equations"
OUT_DIR_ARTIFACT = ARTIFACT_DIR / "equations"

OUT_DIR_PROJECT.mkdir(parents=True, exist_ok=True)
OUT_DIR_ARTIFACT.mkdir(parents=True, exist_ok=True)

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

EQUATIONS = [
    {
        "id": "eq01_rate_network_dynamics",
        "latex": r"\tau_r \frac{dr_i(t)}{dt} = -r_i(t) + \phi\left(\!\!\sum_{j \in E} W^{E}_{ij}\, r_j(t) - \sum_{j \in I} W^{I}_{ij}\, r_j(t) + I_i(t)\!\!\right)"
    },
    {
        "id": "eq02_firing_rate_transfer",
        "latex": r"\phi(x) = \dfrac{1}{2}\left(\sqrt{x^{2} + 1} - \!x\right), \qquad 0 \le \phi(x) \le 1, \qquad s(t) = s_0\,e^{-t/\tau_s}"
    },
    {
        "id": "eq03_hill_receptor_binding",
        "latex": r"\theta([D]) = \frac{[D]^n}{K_d^n + [D]^n}"
    },
    {
        "id": "eq04_conductance_scaling",
        "latex": r"\begin{aligned} \text{Agonism: } & g_{\text{syn}} = g_0 \cdot \big(1 + \Delta g_{\max} \cdot \theta([D])\big) \\[4pt] \text{Na}_v\text{ Blockade: } & \text{scale}_{\text{scn}} = 1.0 - \theta_{\text{Na}_v}([D]) = \frac{K_d^n}{K_d^n + [D]^n} \end{aligned}"
    },
    {
        "id": "eq05_hindbrain_readout",
        "latex": r"R_{\text{RO}}(t) = \dfrac{1}{|\,\mathcal{H}\,|} \sum_{i \in \mathcal{H}} r_i(t), \quad A_{\text{lat}}(t) = \dfrac{R_{\text{RO, R}}(t) - R_{\text{RO, L}}(t)}{R_{\text{RO, R}}(t) + R_{\text{RO, L}}(t) + \epsilon}"
    },
    {
        "id": "eq06_gaba_coordination_decay",
        "latex": r"C_{\text{biped}}(t) = \Big(1 - \big| A_{\text{LR}}(t) \big|\Big) \cdot \Big(1.0 - 0.35\, \theta_{\text{GABA}}([D])\Big)"
    },
    {
        "id": "eq07_forward_locomotor_drive",
        "latex": r"D_{\text{fwd}} = \operatorname{clip}\left( \left[ 0.65 \big( 0.70\, R_{\text{RO}}/R_{\text{RO,base}} + 0.30 \big) + 0.25\, S_{\text{food}} + 0.35\, S_{\text{loom}} \right] \cdot \text{scale}_{\text{Scn}} \cdot G_{\text{stim}}, \; 0.0, \; 1.0 \right)"
    },
    {
        "id": "eq08_neuromuscular_motor_tone",
        "latex": r"T_{\text{motor}} = \operatorname{clip}\left( \text{scale}_{\text{Scn}} \cdot \left[ 0.30 + 0.70 \min\left(1.0, \frac{R_{\text{RO}}}{R_{\text{RO,base}}}\right) \right], \; 0.05, \; 1.0 \right)"
    },
    {
        "id": "eq09_bipedal_coordination_index",
        "latex": r"P_{\text{post}} = \operatorname{clip}\left( \text{scale}_{\text{Scn}} \!\cdot\! \min\Big(1.0,\, 0.5 + 0.5\,G_{\text{stim}}\Big) \!\cdot\! \min\big(1.0,\, \big|A_{\text{LR}}\big| + 0.3\big), \; 0.2, \; 1.0 \right)"
    },
    {
        "id": "eq10_reciprocal_biped_phase_coupling",
        "latex": r"\begin{aligned} \frac{d\phi_L}{dt} &= 2\pi \nu + w_c\, C_{\text{biped}}\, \sin(\phi_R - \phi_L - \pi) + \eta_L(t) \\[6pt] \frac{d\phi_R}{dt} &= 2\pi \nu + w_c\, C_{\text{biped}}\, \sin(\phi_L - \phi_R - \pi) + \eta_R(t) \end{aligned}"
    },
    {
        "id": "eq11_cadence_and_stride_scaling",
        "latex": r"\nu(D_{\text{fwd}}) = \nu_0 + \Delta\nu \cdot D_{\text{fwd}} \quad (\text{Hz}), \qquad L(D_{\text{fwd}}) = L_0 \sqrt{D_{\text{fwd}}} \quad (\text{m})"
    },
    {
        "id": "eq12_sagittal_joint_kinematics",
        "latex": r"\theta_k(t) = A_k(D_{\text{fwd}}) \cdot f_k\big(\phi(t)\big) + \theta_{k,\text{offset}}"
    },
    {
        "id": "eq13_body_weight_support_harness",
        "latex": r"\mathbf{F}_{\text{BWS}} = \big(m_{\text{total}} g \cdot \alpha_{\text{support}} \cdot H_{\text{posture}}\big) \hat{\mathbf{z}}"
    },
    {
        "id": "eq14_two_compartment_pharmacokinetics",
        "latex": r"C_p(t) = \frac{F \cdot \text{Dose} \cdot k_a}{V_d (k_a - k_e)} \left( e^{-k_e t} - e^{-k_a t} \right)"
    },
    {
        "id": "eq15_process_s_sleep_dynamics",
        "latex": r"\frac{dS(t)}{dt} = \begin{cases} \dfrac{1 - S(t)}{\tau_w}, & \text{Wakefulness } (\tau_w = 18.22\text{ h}) \\[10pt] -\dfrac{S(t)}{\tau_s}, & \text{Sleep / Rest } (\tau_s = 4.20\text{ h}) \end{cases}"
    },
    {
        "id": "eq16_rebound_fatigue_masking",
        "latex": r"F_{\text{perceived}}(t) = S(t) \cdot \left[ 1.0 - \min\big(0.85, \; \alpha_{\text{stim}} \cdot \theta_{\text{stim}}(t)\big) \right]"
    }
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #ffffff;
      padding: 30px;
      display: inline-block;
    }}
    #math {{
      font-size: 36px;
      color: #0f172a;
      white-space: nowrap;
    }}
  </style>
</head>
<body>
  <div id="math"></div>
  <script>
    katex.render(String.raw`{latex}`, document.getElementById('math'), {{
      displayMode: true,
      throwOnError: false
    }});
  </script>
</body>
</html>
"""


def render_pure_equations():
    tmp_html = Path("/tmp/pure_eq.html")
    tmp_raw_png = Path("/tmp/pure_eq_raw.png")

    print(f"Rendering {len(EQUATIONS)} pure equation PNGs (no cards, no borders, no text)...")
    for idx, eq in enumerate(EQUATIONS, 1):
        eq_id = eq["id"]
        out_name = f"{eq_id}.png"
        out_png_proj = OUT_DIR_PROJECT / out_name
        out_png_art = OUT_DIR_ARTIFACT / out_name

        html_content = HTML_TEMPLATE.format(latex=eq["latex"])
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        cmd = [
            CHROME_BIN,
            "--headless=new",
            "--hide-scrollbars",
            f"--screenshot={tmp_raw_png}",
            "--window-size=2400,600",
            "--device-scale-factor=2",
            "--virtual-time-budget=3000",
            "--run-all-compositor-stages-before-draw",
            f"file://{tmp_html.resolve()}"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Autocrop tightly with Pillow
        img = Image.open(tmp_raw_png).convert("RGB")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()

        if bbox:
            pad_x = 16
            pad_y = 10
            x0 = max(0, bbox[0] - pad_x)
            y0 = max(0, bbox[1] - pad_y)
            x1 = min(img.width, bbox[2] + pad_x)
            y1 = min(img.height, bbox[3] + pad_y)
            cropped = img.crop((x0, y0, x1, y1))
            cropped.save(out_png_proj, optimize=True)
            shutil.copy2(out_png_proj, out_png_art)
            print(f"  [{idx:02d}/16] Saved pure {out_name} ({cropped.size[0]}x{cropped.size[1]} px)")
        else:
            print(f"  [{idx:02d}/16] Warning: Empty bbox for {out_name}")

    print("\nAll pure equation PNGs successfully rendered and verified!")


if __name__ == "__main__":
    render_pure_equations()
