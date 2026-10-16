#!/usr/bin/env python3
"""
render_latex_equations_png.py
Renders ALL project equations into a neatly rendered, publication-grade LaTeX PNG.

Features:
- Complete compilation of all 16 biophysical, pharmacological, connectomic, and biomechanical equations.
- Uses authentic LaTeX math rendering via KaTeX with Computer Modern fonts.
- Crisp 2x retina resolution, elegant academic layout, clear parameter annotations.
- Outputs PNG directly to results/ and the artifact directory.
"""

import os
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

OUT_HTML = RESULTS_DIR / "equations_gallery.html"
OUT_PNG_PROJECT = RESULTS_DIR / "All_Mathematical_Formulations_LaTeX.png"
OUT_PNG_ARTIFACT = ARTIFACT_DIR / "All_Mathematical_Formulations_LaTeX.png"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Mathematical & Biophysical Formulations | Drosophila Connectome to Humanoid Locomotion</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: #f8fafc;
      color: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 40px;
      width: 1400px;
      margin: 0 auto;
    }

    header {
      text-align: center;
      margin-bottom: 35px;
      padding-bottom: 25px;
      border-bottom: 2px solid #e2e8f0;
    }
    .badge {
      display: inline-block;
      background: #0284c7;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 4px 12px;
      border-radius: 9999px;
      margin-bottom: 12px;
    }
    h1 {
      font-size: 28px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.5px;
      margin-bottom: 8px;
    }
    .subtitle {
      font-size: 15px;
      color: #475569;
      max-width: 900px;
      margin: 0 auto;
      line-height: 1.5;
    }

    .section-title {
      font-size: 18px;
      font-weight: 700;
      color: #1e293b;
      margin: 30px 0 15px 0;
      padding-left: 12px;
      border-left: 4px solid #0284c7;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .section-title .part-num {
      color: #64748b;
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 18px;
      margin-bottom: 10px;
    }
    .grid-1 {
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
      margin-bottom: 10px;
    }

    .eq-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 20px 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .eq-card-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 12px;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 8px;
    }
    .eq-name {
      font-size: 14.5px;
      font-weight: 700;
      color: #0f172a;
    }
    .eq-tag {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      font-weight: 700;
      color: #0369a1;
      background: #e0f2fe;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .math-display {
      margin: 14px 0 16px 0;
      font-size: 19px;
      text-align: center;
      color: #0f172a;
      overflow-x: auto;
    }
    .eq-meta {
      font-size: 12px;
      color: #64748b;
      line-height: 1.5;
      background: #f8fafc;
      padding: 8px 12px;
      border-radius: 6px;
      border-left: 3px solid #cbd5e1;
    }
    .eq-meta strong {
      color: #334155;
    }

    footer {
      margin-top: 35px;
      padding-top: 20px;
      border-top: 1px solid #e2e8f0;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
    }
  </style>
</head>
<body>

  <header>
    <div class="badge">Comprehensive Mathematical Compendium</div>
    <h1>Explaining How Drugs Affect the Muscular Control of Homo Sapiens using the Drosophila Connectome</h1>
    <p class="subtitle">Complete mathematical catalog of biophysical connectomics, molecular Hill-Langmuir receptor kinetics, insect hexapod phase dynamics, cross-species motor translation, and 12-DOF anthropomorphic bipedal locomotion.</p>
  </header>

  <!-- PART 1 -->
  <div class="section-title">
    <span class="part-num">Part I</span>
    <span>Biophysical Connectome & Neuron Dynamics</span>
  </div>
  <div class="grid-2">
    <!-- EQ 1 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Leaky Integrate-and-Fire (LIF) Membrane Dynamics</span>
        <span class="eq-tag">Eq. 1</span>
      </div>
      <div class="math-display">
        $$\tau_m \frac{dV_i(t)}{dt} = -\big(V_i(t) - V_{\text{rest}}\big) + \sum_{j=1}^{N} W_{ij} s_j(t) + I_{\text{ext},i}(t)$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $\tau_m = R_m C_m$ (membrane time constant, 20 ms), $V_{\text{rest}} = -65\text{ mV}$, $W_{ij}$ (FlyWire synaptic weight matrix, 54.5M synapses, $N=139,255$), $s_j(t) = \sum_k \delta(t - t_j^k)$ (presynaptic spike events).
      </div>
    </div>

    <!-- EQ 2 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Spike Threshold & Absolute Refractory Reset</span>
        <span class="eq-tag">Eq. 2</span>
      </div>
      <div class="math-display">
        $$\text{If } V_i(t) \ge V_{\text{th}} \implies \begin{cases} s_i(t) = 1 \\ V_i(t^+) = V_{\text{reset}} \end{cases} \quad \text{for } t \in [t_{\text{spike}}, t_{\text{spike}} + \tau_{\text{ref}})$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $V_{\text{th}} = -50\text{ mV}$ (action potential threshold), $V_{\text{reset}} = -70\text{ mV}$ (hyperpolarization reset), $\tau_{\text{ref}} = 2.0\text{ ms}$ (absolute refractory lockout).
      </div>
    </div>
  </div>

  <!-- PART 2 -->
  <div class="section-title">
    <span class="part-num">Part II</span>
    <span>Molecular Pharmacology & Receptor Kinetics</span>
  </div>
  <div class="grid-2">
    <!-- EQ 3 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Hill-Langmuir Cooperative Receptor Binding</span>
        <span class="eq-tag">Eq. 3</span>
      </div>
      <div class="math-display">
        $$\theta([D]) = \frac{[D]^n}{K_d^n + [D]^n}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $\theta([D]) \in [0, 1]$ (fractional receptor occupancy), $[D]$ (free drug concentration, $\mu\text{M}$), $K_d$ (equilibrium dissociation constant), $n$ (Hill cooperativity coefficient; $n=1$ non-cooperative, $n=2$ dimeric, $n=4$ tetrameric).
      </div>
    </div>

    <!-- EQ 4 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Pharmacological Conductance & Channel Scaling</span>
        <span class="eq-tag">Eq. 4</span>
      </div>
      <div class="math-display">
        $$\begin{aligned}
        \text{Agonism: } & g_{\text{syn}} = g_0 \cdot \big(1 + \Delta g_{\max} \cdot \theta([D])\big) \\
        \text{Na}_v\text{ Block: } & \text{scale}_{\text{para}} = 1.0 - \theta_{\text{Nav}}([D]) = \frac{K_d^n}{K_d^n + [D]^n}
        \end{aligned}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $g_0$ (baseline conductance), $\Delta g_{\max}$ (maximal efficacy), $\text{scale}_{\text{para}}$ (fractional availability of axonal voltage-gated sodium channels under Lidocaine blockade).
      </div>
    </div>
  </div>

  <!-- PART 3 -->
  <div class="section-title">
    <span class="part-num">Part III</span>
    <span>Drosophila Hexapod Prototype Biomechanics</span>
  </div>
  <div class="grid-2">
    <!-- EQ 5 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Hexapod Coupled Tripod Phase Oscillators (Kuramoto)</span>
        <span class="eq-tag">Eq. 5</span>
      </div>
      <div class="math-display">
        $$\frac{d\phi_i}{dt} = 2\pi \nu_{\text{fly}} + \sum_{j \in \mathcal{N}_i} w_{ij} \sin\big(\phi_j - \phi_i - \Delta\phi_{ij}\big)$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> Leg indices $i \in \{L1, L2, L3, R1, R2, R3\}$; phase difference $\Delta\phi_{ij} = \pi$ for alternating tripods: Tripod 1 ($L1\text{-}R2\text{-}L3$) vs. Tripod 2 ($R1\text{-}L2\text{-}R3$).
      </div>
    </div>

    <!-- EQ 6 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Tarsal Adhesion Force (Pulvilli Clamping)</span>
        <span class="eq-tag">Eq. 6</span>
      </div>
      <div class="math-display">
        $$\mathbf{F}_{\text{adh}, i} = F_0 \cdot \text{scale}_{\text{para}} \cdot \delta_{\text{contact}, i} \cdot \hat{\mathbf{n}}_{\text{surface}}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $F_0 = 15\,\mu\text{N}$ per foot pad. Explains why the 6-legged insect prototype never tumbled: static 3-point tripod base plus adhesion masked severe flaccid muscle weakness.
      </div>
    </div>
  </div>

  <!-- PART 4 -->
  <div class="section-title">
    <span class="part-num">Part IV</span>
    <span>Cross-Species Motor Translation (DNToHumanTranslator)</span>
  </div>
  <div class="grid-1">
    <!-- EQ 7 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Descending Motor Forward Locomotor Drive ($D_{\text{fwd}}$)</span>
        <span class="eq-tag">Eq. 7</span>
      </div>
      <div class="math-display">
        $$D_{\text{fwd}} = \operatorname{clip}\left( \left[ 0.65 \left( 0.70 \frac{R_{\text{DN}}}{R_{\text{DN,base}}} + 0.30 \frac{R_{\text{DNa}}}{R_{\text{DNa,base}}} - 1.20 \max\big(0, R_{\text{MDN}} - R_{\text{MDN,base}}\big) \right) + S_{\text{stim}} \right] \cdot \text{scale}_{\text{para}} \cdot G_{\text{stim}}, \; 0.0, \; 1.0 \right)$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $R_{\text{DN}}$ (total descending firing rate, 1,305 DNs), $R_{\text{DNa}}$ (forward-steering DNa01/DNa02 firing), $R_{\text{MDN}}$ (Moonwalker pause neuron rate), $S_{\text{stim}} = 0.12$ (catecholaminergic stimulant boost), $G_{\text{stim}} = 1.08$ (arousal gain factor).
      </div>
    </div>
  </div>

  <div class="grid-2">
    <!-- EQ 8 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Neuromuscular Motor Tone ($T_{\text{motor}}$)</span>
        <span class="eq-tag">Eq. 8</span>
      </div>
      <div class="math-display">
        $$T_{\text{motor}} = \operatorname{clip}\left( \text{scale}_{\text{para}} \cdot \left[ 0.30 + 0.70 \min\left(1.0, \frac{R_{\text{DN}}}{R_{\text{DN,base}}}\right) \right], \; 0.05, \; 1.0 \right)$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> Scales joint actuator torque limits and viscoelastic joint stiffness. Under Lidocaine ($\text{scale}_{\text{para}} \to 0$), $T_{\text{motor}} = 0.10$, precipitating flaccid extensor collapse and knee buckling.
      </div>
    </div>

    <!-- EQ 9 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Bipedal Reciprocal Coordination Index ($C_{\text{biped}}$)</span>
        <span class="eq-tag">Eq. 9</span>
      </div>
      <div class="math-display">
        $$C_{\text{biped}} = \operatorname{clip}\left( 1.0 - \Phi_{\text{GABA}}, \; 0.0, \; 1.0 \right)$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $\Phi_{\text{GABA}}$ reflects spinal commissural interneuron disinhibition (e.g. CB1 partial agonism by $\Delta^9$-THC, where $\Phi_{\text{GABA}} = 0.42 \implies C_{\text{biped}} = 0.58$, producing ataxic stumbling).
      </div>
    </div>
  </div>

  <!-- PART 5 -->
  <div class="section-title">
    <span class="part-num">Part V</span>
    <span>Anthropomorphic Humanoid Bipedal CPG & 3D Physics</span>
  </div>
  <div class="grid-2">
    <!-- EQ 10 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Two-Oscillator Reciprocal Biped Phase Coupling & Noise</span>
        <span class="eq-tag">Eq. 10</span>
      </div>
      <div class="math-display">
        $$\begin{aligned}
        \frac{d\phi_L}{dt} &= 2\pi \nu + w_c \sin(\phi_R - \phi_L - \pi) + \eta_L(t) \\[6pt]
        \frac{d\phi_R}{dt} &= 2\pi \nu + w_c \sin(\phi_L - \phi_R - \pi) + \eta_R(t)
        \end{aligned}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $w_c = w_0 \cdot C_{\text{biped}}$ ($w_0 = 6.0\text{ rad/s}$); $\eta(t) \sim \mathcal{N}\big(0, \sigma^2(1 - C_{\text{biped}})\big)$ injects stochastic phase desynchronization when coordination degrades.
      </div>
    </div>

    <!-- EQ 11 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Stepping Cadence ($\nu$) & Stride Length ($L$) Scaling</span>
        <span class="eq-tag">Eq. 11</span>
      </div>
      <div class="math-display">
        $$\begin{aligned}
        \nu(D_{\text{fwd}}) &= \nu_0 + \Delta\nu \cdot D_{\text{fwd}} \quad (\text{Hz}) \\[6pt]
        L(D_{\text{fwd}}) &= L_0 \sqrt{D_{\text{fwd}}} \quad (\text{m})
        \end{aligned}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $\nu_0 = 0.85\text{ Hz}$, $\Delta\nu = 0.55\text{ Hz}$ (baseline $1.20\text{ Hz}$, hyper-cadence $1.35\text{ Hz}$ under Vyvanse); $L_0 = 0.72\text{ m}$ (stride reaches $0.83\text{ m}$).
      </div>
    </div>
  </div>

  <div class="grid-2">
    <!-- EQ 12 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Sagittal Joint Angle Trajectories (12-DOF Kinematics)</span>
        <span class="eq-tag">Eq. 12</span>
      </div>
      <div class="math-display">
        $$\theta_k(t) = A_k(D_{\text{fwd}}) \cdot f_k\big(\phi(t)\big) + \theta_{k,\text{offset}}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> Hip pitch $\theta_{\text{hip}} \in [-15^\circ, +25^\circ]$, Knee flexion $\theta_{\text{knee}} \in [0^\circ, 65^\circ]$, Ankle dorsiflexion $\theta_{\text{ankle}} \in [-15^\circ, +10^\circ]$. Stance: $0\% \le \phi < 60\%$, Swing: $60\% \le \phi < 100\%$.
      </div>
    </div>

    <!-- EQ 13 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Active Body-Weight Support (BWS) Overhead Harness</span>
        <span class="eq-tag">Eq. 13</span>
      </div>
      <div class="math-display">
        $$\mathbf{F}_{\text{BWS}} = \big(m_{\text{total}} g \cdot \alpha_{\text{support}} \cdot H_{\text{posture}}\big) \hat{\mathbf{z}}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $m_{\text{total}} = 71.8\text{ kg}$, $g = 9.81\text{ m/s}^2$, nominal vertical lift $F_{\text{lift}} = 635\text{ N}$. Unloads body weight to safely capture flaccid knee buckling and prevent fatal tumbling.
      </div>
    </div>
  </div>

  <!-- PART 6 -->
  <div class="section-title">
    <span class="part-num">Part VI</span>
    <span>Two-Compartment Pharmacokinetics & Sleep Regulation</span>
  </div>
  <div class="grid-2">
    <!-- EQ 14 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Two-Compartment Biexponential Plasma Clearance</span>
        <span class="eq-tag">Eq. 14</span>
      </div>
      <div class="math-display">
        $$C_p(t) = \frac{F \cdot \text{Dose} \cdot k_a}{V_d (k_a - k_e)} \left( e^{-k_e t} - e^{-k_a t} \right)$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> $F$ (bioavailability), $k_a$ (absorption rate), $k_e = \frac{\ln 2}{t_{1/2}}$ (elimination rate constant), $V_d$ (volume of distribution). Models drug plasma kinetics over 24 hours.
      </div>
    </div>

    <!-- EQ 15 & 16 -->
    <div class="eq-card">
      <div class="eq-card-header">
        <span class="eq-name">Process S Sleep Debt & Rebound Fatigue Crash</span>
        <span class="eq-tag">Eq. 15–16</span>
      </div>
      <div class="math-display">
        $$\begin{aligned}
        \frac{dS}{dt} &= \frac{1 - S}{\tau_w} \quad (\text{Wake: } \tau_w = 18.22\text{ h}) \\[6pt]
        F_{\text{perceived}}(t) &= S(t) \cdot \Big[ 1.0 - \min\big(0.85, \; \alpha_{\text{stim}} \theta_{\text{stim}}(t)\big) \Big]
        \end{aligned}$$
      </div>
      <div class="eq-meta">
        <strong>Variables:</strong> Process S accumulates homeostatic sleep pressure during 16h wakefulness. Stimulants mask fatigue ($F_{\text{perceived}} \downarrow$); as drug clears ($t > 12\text{h}$), unmasked $S(t)$ causes an acute rebound crash.
      </div>
    </div>
  </div>

  <footer>
    Explaining How Drugs Affect the Muscular Control of Homo Sapiens using the Drosophila Connectome &bull; Academic Year 2026
  </footer>

  <script>
    function renderEquations() {
      renderMathInElement(document.body, {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false}
        ],
        throwOnError: false
      });
    }
    if (document.readyState === 'loading') {
      document.addEventListener("DOMContentLoaded", renderEquations);
    } else {
      renderEquations();
    }
  </script>
</body>
</html>
"""

def generate_equations_png():
    print("Writing HTML equations gallery...")
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_bin):
        raise FileNotFoundError(f"Chrome binary not found at: {chrome_bin}")

    cmd = [
        chrome_bin,
        "--headless=new",
        "--hide-scrollbars",
        "--screenshot=" + str(OUT_PNG_PROJECT),
        "--window-size=1480,3150",
        "--device-scale-factor=2",
        "--virtual-time-budget=6000",
        "--run-all-compositor-stages-before-draw",
        f"file://{OUT_HTML.resolve()}"
    ]

    print("Rendering high-resolution LaTeX PNG using Chrome headless...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: Chrome exited with code {result.returncode}")
        print(result.stderr[:400])

    if OUT_PNG_PROJECT.exists():
        size_kb = OUT_PNG_PROJECT.stat().st_size / 1024
        print(f"Successfully generated: {OUT_PNG_PROJECT} ({size_kb:.1f} KB)")
        
        # Copy to artifacts directory
        if ARTIFACT_DIR.exists():
            import shutil
            shutil.copy2(OUT_PNG_PROJECT, OUT_PNG_ARTIFACT)
            print(f"Artifact copy saved to: {OUT_PNG_ARTIFACT}")
    else:
        raise RuntimeError("Failed to generate equations PNG.")

if __name__ == "__main__":
    generate_equations_png()
