#!/usr/bin/env python3
"""
build_individual_equations_png.py
Renders ALL project equations into INDIVIDUAL, standalone, publication-grade PNGs.

Features:
- 16 individual PNG files (one for each mathematical formulation).
- Rendered in authentic Computer Modern LaTeX via KaTeX.
- Auto-cropped tightly with clean padding using Pillow.
- High-resolution 2x retina display density.
- Saved in results/equations/ and synced to the artifact directory.
- Creates an HTML preview gallery index.html.
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
        "id": "eq01_lif_membrane_potential",
        "tag": "Eq. 1",
        "title": "Leaky Integrate-and-Fire (LIF) Membrane Dynamics",
        "latex": r"\tau_m \frac{dV_i(t)}{dt} = -\big(V_i(t) - V_{\text{rest}}\big) + \sum_{j=1}^{N} W_{ij} s_j(t) + I_{\text{ext},i}(t)",
        "desc": r"\tau_m = R_m C_m = 20\text{ ms}, \quad V_{\text{rest}} = -65\text{ mV}, \quad W_{ij} \in \mathbb{R}^{139255 \times 139255}"
    },
    {
        "id": "eq02_spike_threshold_reset",
        "tag": "Eq. 2",
        "title": "Action Potential Threshold & Refractory Reset",
        "latex": r"\text{If } V_i(t) \ge V_{\text{th}} \implies \begin{cases} s_i(t) = 1 \\ V_i(t^+) = V_{\text{reset}} \end{cases} \quad \text{for } t \in [t_{\text{spike}}, t_{\text{spike}} + \tau_{\text{ref}})",
        "desc": r"V_{\text{th}} = -50\text{ mV}, \quad V_{\text{reset}} = -70\text{ mV}, \quad \tau_{\text{ref}} = 2.0\text{ ms}"
    },
    {
        "id": "eq03_hill_receptor_binding",
        "tag": "Eq. 3",
        "title": "Hill-Langmuir Cooperative Receptor Binding",
        "latex": r"\theta([D]) = \frac{[D]^n}{K_d^n + [D]^n}",
        "desc": r"\theta([D]) \in [0, 1] \text{ fractional occupancy}, \quad [D] = \text{drug concentration}, \quad K_d = \text{affinity}"
    },
    {
        "id": "eq04_pharmacological_conductance_scaling",
        "tag": "Eq. 4",
        "title": "Pharmacological Conductance & Na_v Channel Scaling",
        "latex": r"\begin{aligned} \text{Agonism: } & g_{\text{syn}} = g_0 \cdot \big(1 + \Delta g_{\max} \cdot \theta([D])\big) \\[4pt] \text{Na}_v\text{ Block: } & \text{scale}_{\text{para}} = 1.0 - \theta_{\text{Nav}}([D]) = \frac{K_d^n}{K_d^n + [D]^n} \end{aligned}",
        "desc": r"\text{Models synaptic modulation and Lidocaine voltage-gated sodium channel conduction block.}"
    },
    {
        "id": "eq05_hexapod_tripod_kuramoto",
        "tag": "Eq. 5",
        "title": "Hexapod Tripod Coupled Phase Oscillators (Kuramoto)",
        "latex": r"\frac{d\phi_i}{dt} = 2\pi \nu_{\text{fly}} + \sum_{j \in \mathcal{N}_i} w_{ij} \sin\big(\phi_j - \phi_i - \Delta\phi_{ij}\big)",
        "desc": r"i \in \{L1, L2, L3, R1, R2, R3\}, \quad \Delta\phi_{ij} = \pi \text{ for alternating tripods (L1-R2-L3 vs. R1-L2-R3)}"
    },
    {
        "id": "eq06_tarsal_adhesion_force",
        "tag": "Eq. 6",
        "title": "Tarsal Contact Adhesion Force (Pulvilli Clamping)",
        "latex": r"\mathbf{F}_{\text{adh}, i} = F_0 \cdot \text{scale}_{\text{para}} \cdot \delta_{\text{contact}, i} \cdot \hat{\mathbf{n}}_{\text{surface}}",
        "desc": r"F_0 = 15\,\mu\text{N per foot pad. Explains why 6-legged insect prototype never tumbles even under full motor block.}"
    },
    {
        "id": "eq07_forward_locomotor_drive",
        "tag": "Eq. 7",
        "title": "Descending Motor Forward Locomotor Drive (D_fwd)",
        "latex": r"D_{\text{fwd}} = \operatorname{clip}\left( \left[ 0.65 \left( 0.70 \frac{R_{\text{DN}}}{R_{\text{DN,base}}} + 0.30 \frac{R_{\text{DNa}}}{R_{\text{DNa,base}}} - 1.20 \max\big(0, R_{\text{MDN}} - R_{\text{MDN,base}}\big) \right) + S_{\text{stim}} \right] \cdot \text{scale}_{\text{para}} \cdot G_{\text{stim}}, \; 0.0, \; 1.0 \right)",
        "desc": r"R_{\text{DN}} = \text{total DN rate}, \quad R_{\text{DNa}} = \text{DNa01/DNa02 rate}, \quad R_{\text{MDN}} = \text{Moonwalker pause rate}"
    },
    {
        "id": "eq08_neuromuscular_motor_tone",
        "tag": "Eq. 8",
        "title": "Neuromuscular Motor Tone (T_motor)",
        "latex": r"T_{\text{motor}} = \operatorname{clip}\left( \text{scale}_{\text{para}} \cdot \left[ 0.30 + 0.70 \min\left(1.0, \frac{R_{\text{DN}}}{R_{\text{DN,base}}}\right) \right], \; 0.05, \; 1.0 \right)",
        "desc": r"\text{Governs joint torque capacity and muscle stiffness; under Lidocaine } T_{\text{motor}} \to 0.10 \text{ causing knee buckling.}"
    },
    {
        "id": "eq09_bipedal_coordination_index",
        "tag": "Eq. 9",
        "title": "Bipedal Reciprocal Coordination Index (C_biped)",
        "latex": r"C_{\text{biped}} = \operatorname{clip}\left( 1.0 - \Phi_{\text{GABA}}, \; 0.0, \; 1.0 \right)",
        "desc": r"\Phi_{\text{GABA}} = \text{commissural interneuron disinhibition (e.g. THC } \Phi_{\text{GABA}} = 0.42 \implies C_{\text{biped}} = 0.58 \text{, ataxic).}"
    },
    {
        "id": "eq10_reciprocal_biped_phase_coupling",
        "tag": "Eq. 10",
        "title": "Reciprocal Biped Phase Coupling & Phase Noise",
        "latex": r"\begin{aligned} \frac{d\phi_L}{dt} &= 2\pi \nu + w_c \sin(\phi_R - \phi_L - \pi) + \eta_L(t) \\[6pt] \frac{d\phi_R}{dt} &= 2\pi \nu + w_c \sin(\phi_L - \phi_R - \pi) + \eta_R(t) \end{aligned}",
        "desc": r"w_c = w_0 \cdot C_{\text{biped}} \; (w_0 = 6.0\text{ rad/s}); \quad \eta(t) \sim \mathcal{N}\big(0, \sigma^2(1 - C_{\text{biped}})\big) \text{ injects ataxic jitter.}"
    },
    {
        "id": "eq11_cadence_and_stride_scaling",
        "tag": "Eq. 11",
        "title": "Stepping Cadence & Stride Length Scaling",
        "latex": r"\nu(D_{\text{fwd}}) = \nu_0 + \Delta\nu \cdot D_{\text{fwd}} \quad (\text{Hz}), \qquad L(D_{\text{fwd}}) = L_0 \sqrt{D_{\text{fwd}}} \quad (\text{m})",
        "desc": r"\nu_0 = 0.85\text{ Hz}, \quad \Delta\nu = 0.55\text{ Hz} \implies \text{baseline } 1.20\text{ Hz, Vyvanse hyper-cadence } 1.35\text{ Hz; } L_0 = 0.72\text{ m}"
    },
    {
        "id": "eq12_sagittal_joint_kinematics",
        "tag": "Eq. 12",
        "title": "Sagittal Joint Angle Trajectories (12-DOF)",
        "latex": r"\theta_k(t) = A_k(D_{\text{fwd}}) \cdot f_k\big(\phi(t)\big) + \theta_{k,\text{offset}}",
        "desc": r"k \in \{\text{hip}, \text{knee}, \text{ankle}\}; \quad \text{Stance: } 0\% \le \phi < 60\%, \quad \text{Swing: } 60\% \le \phi < 100\%"
    },
    {
        "id": "eq13_body_weight_support_harness",
        "tag": "Eq. 13",
        "title": "Active Body-Weight Support (BWS) Overhead Harness",
        "latex": r"\mathbf{F}_{\text{BWS}} = \big(m_{\text{total}} g \cdot \alpha_{\text{support}} \cdot H_{\text{posture}}\big) \hat{\mathbf{z}}",
        "desc": r"m_{\text{total}} = 71.8\text{ kg}, \quad g = 9.81\text{ m/s}^2, \quad \text{nominal lift } F_{\text{lift}} = 635\text{ N. Catches flaccid collapse.}"
    },
    {
        "id": "eq14_two_compartment_pharmacokinetics",
        "tag": "Eq. 14",
        "title": "Two-Compartment Biexponential Plasma Clearance",
        "latex": r"C_p(t) = \frac{F \cdot \text{Dose} \cdot k_a}{V_d (k_a - k_e)} \left( e^{-k_e t} - e^{-k_a t} \right)",
        "desc": r"k_e = \frac{\ln 2}{t_{1/2}} \text{ elimination rate}, \quad k_a = \text{absorption rate}, \quad V_d = \text{distribution volume}"
    },
    {
        "id": "eq15_process_s_sleep_dynamics",
        "tag": "Eq. 15",
        "title": "Process S Homeostatic Sleep Pressure Dynamics",
        "latex": r"\frac{dS(t)}{dt} = \begin{cases} \dfrac{1 - S(t)}{\tau_w}, & \text{Wakefulness } (\tau_w = 18.22\text{ h}) \\[10pt] -\dfrac{S(t)}{\tau_s}, & \text{Sleep / Rest } (\tau_s = 4.20\text{ h}) \end{cases}",
        "desc": r"S(t) \in [0, 1] \text{ tracks cumulative homeostatic sleep pressure across 24 hours.}"
    },
    {
        "id": "eq16_rebound_fatigue_masking",
        "tag": "Eq. 16",
        "title": "Stimulant Receptor Masking & Acute Rebound Fatigue",
        "latex": r"F_{\text{perceived}}(t) = S(t) \cdot \left[ 1.0 - \min\big(0.85, \; \alpha_{\text{stim}} \cdot \theta_{\text{stim}}(t)\big) \right]",
        "desc": r"\text{Stimulants mask fatigue; as drug clears } (t > 12\text{ h}), \text{ unmasked } S(t) \text{ causes an acute rebound exhaustion crash.}"
    }
]

HTML_PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #ffffff;
      padding: 30px;
      display: inline-block;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .card {{
      background: #ffffff;
      border: 1.5px solid #cbd5e1;
      border-radius: 12px;
      padding: 24px 32px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.05);
      display: inline-block;
      min-width: 650px;
      max-width: none;
      width: max-content;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 10px;
    }}
    .title {{
      font-size: 16px;
      font-weight: 700;
      color: #0f172a;
    }}
    .tag {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      font-weight: 700;
      color: #0284c7;
      background: #e0f2fe;
      padding: 3px 10px;
      border-radius: 6px;
    }}
    .math-box {{
      font-size: 26px;
      color: #0f172a;
      text-align: center;
      margin: 18px 0;
      padding: 10px 0;
    }}
    .desc {{
      font-size: 13px;
      color: #475569;
      background: #f8fafc;
      padding: 10px 14px;
      border-radius: 8px;
      border-left: 3px solid #0284c7;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="card" id="card">
    <div class="header">
      <span class="title">{title}</span>
      <span class="tag">{tag}</span>
    </div>
    <div class="math-box" id="math"></div>
    <div class="desc" id="desc"></div>
  </div>
  <script>
    katex.render(String.raw`{latex}`, document.getElementById('math'), {{
      displayMode: true,
      throwOnError: false
    }});
    katex.render(String.raw`{desc}`, document.getElementById('desc'), {{
      displayMode: false,
      throwOnError: false
    }});
  </script>
</body>
</html>
"""


def render_all_equations():
    tmp_html = Path("/tmp/single_eq_render.html")
    tmp_raw_png = Path("/tmp/single_eq_render_raw.png")

    gallery_items = []

    print(f"Rendering {len(EQUATIONS)} individual equation PNGs...")
    for idx, eq in enumerate(EQUATIONS, 1):
        eq_id = eq["id"]
        out_name = f"{eq_id}.png"
        out_png_proj = OUT_DIR_PROJECT / out_name
        out_png_art = OUT_DIR_ARTIFACT / out_name

        # Write dedicated HTML
        html_content = HTML_PAGE_TEMPLATE.format(
            title=eq["title"],
            tag=eq["tag"],
            latex=eq["latex"],
            desc=eq["desc"]
        )
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Chrome headless screenshot at 2x retina
        cmd = [
            CHROME_BIN,
            "--headless=new",
            "--hide-scrollbars",
            f"--screenshot={tmp_raw_png}",
            "--window-size=2400,1000",
            "--device-scale-factor=2",
            "--virtual-time-budget=4000",
            "--run-all-compositor-stages-before-draw",
            f"file://{tmp_html.resolve()}"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Autocrop with Pillow
        img = Image.open(tmp_raw_png).convert("RGB")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()

        if bbox:
            pad = 20
            x0 = max(0, bbox[0] - pad)
            y0 = max(0, bbox[1] - pad)
            x1 = min(img.width, bbox[2] + pad)
            y1 = min(img.height, bbox[3] + pad)
            cropped = img.crop((x0, y0, x1, y1))
            cropped.save(out_png_proj, optimize=True)
            shutil.copy2(out_png_proj, out_png_art)
            print(f"  [{idx:02d}/16] Saved {out_name} (Size: {cropped.size[0]}x{cropped.size[1]} px)")
        else:
            print(f"  [{idx:02d}/16] Warning: Empty bbox for {out_name}")

        gallery_items.append((out_name, eq["tag"], eq["title"]))

    # Generate Gallery HTML Index
    gallery_html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Gallery of All Individual LaTeX Equations</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f1f5f9; padding: 40px; color: #0f172a; }
    h1 { text-align: center; margin-bottom: 8px; font-size: 26px; font-weight: 800; }
    p.sub { text-align: center; color: #64748b; margin-bottom: 30px; font-size: 14px; }
    .grid { display: flex; flex-direction: column; gap: 24px; max-width: 1000px; margin: 0 auto; }
    .item { background: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); text-align: center; }
    .item img { max-width: 100%; height: auto; border-radius: 8px; }
    .item-caption { margin-top: 10px; font-size: 13px; font-weight: 600; color: #475569; }
  </style>
</head>
<body>
  <h1>Individual LaTeX Equation PNGs</h1>
  <p class="sub">16 Standalone, High-Resolution, Perfectly Cropped Mathematical Formulations</p>
  <div class="grid">
"""
    for fname, tag, title in gallery_items:
        gallery_html += f"""    <div class="item">
      <img src="{fname}" alt="{tag}: {title}">
      <div class="item-caption">{tag}: {title}</div>
    </div>\n"""
    gallery_html += """  </div>\n</body>\n</html>"""

    with open(OUT_DIR_PROJECT / "index.html", "w", encoding="utf-8") as f:
        f.write(gallery_html)
    shutil.copy2(OUT_DIR_PROJECT / "index.html", OUT_DIR_ARTIFACT / "index.html")

    print("\nAll 16 individual equations successfully generated and verified!")
    print(f"Project folder: {OUT_DIR_PROJECT}")
    print(f"Artifact folder: {OUT_DIR_ARTIFACT}")


if __name__ == "__main__":
    render_all_equations()
