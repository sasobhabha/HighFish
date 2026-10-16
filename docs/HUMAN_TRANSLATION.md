# HighFly Human Translation & Embodied Biped Scaffold

This document specifies the scientific provenance, neurobiological mapping, mathematical formalism, biomechanical architecture, and CLI usage of the **Human Translation Layer and Embodied 3D Biped Scaffold** in HighFly.

The system translates whole-brain connectome dynamics from *Drosophila melanogaster* (FlyWire FAFB v783) and verified receptor pharmacology into calibrated **Human Motor Intent** (`HumanIntent`), drives an anti-phase reciprocal **Biped Central Pattern Generator (CPG)**, and simulates an anthropomorphic **3D Humanoid Body** in MuJoCo under body-weight support (BWS).

---

## 1. Scientific Provenance & Cross-Species Homology

In both insects and vertebrates, locomotion is initiated and directed by descending pathways linking cephalic decision centers to thoracic/spinal pattern generators:

| Feature | *Drosophila melanogaster* (FlyWire v783) | Human / Vertebrate Analogue | Provenance & Literature |
|---|---|---|---|
| **Descending Pathways** | ~1,305 descending neurons (DNs) traversing cervical connective to VNC | Reticulospinal, vestibulospinal, and corticospinal tracts descending to lumbar spinal cord | Grillner 2006, Lemon 2008, Bidaye et al. 2014 |
| **Locomotor Initiation & Velocity** | Population activity of forward DNs (e.g. DNa01, DNa02) | Mesencephalic Locomotor Region (MLR) → reticulospinal drive setting speed | Grillner 2008, Lemon 2008, C182 |
| **Steering / Yaw Turning** | Bilateral firing rate asymmetry between left and right DNa01/DNa02 | Asymmetric reticulospinal & vestibulospinal activation modulating lateral limb stroke | Rayshubskiy et al. 2020, Drew & Marigold 2015, C184 |
| **Backward Walking & Motor Arrest** | Moonwalker Descending Neurons (MDN) reversing or halting stepping | Brainstem arrest/pause neurons (PnO/Gi) commanding defensive halt | Bidaye et al. 2014, C183 |
| **Reciprocal Alternation (Coupling)** | GABAergic local interneurons in VNC neuromeres | Spinal commissural interneurons (CINs) mediating reciprocal Ia inhibition | Kiehn 2006, 2016, C121, C122 |
| **Anti-Gravity Tone & Excitability** | Voltage-gated sodium channel (*para* / Naᵥ) axonal conduction | Axonal Naᵥ channels (Nav1.1/1.2/1.6) driving motor unit recruitment & extensor tone | Catterall 2012, C149, C150 |
| **Arousal & Cadence Modulation** | Dopaminergic (D1-like / dDAT) and nicotinic (nAChR) wake signaling | Basal ganglia dopamine loop (D1/D2) modulating locomotor cadence and vigor | Oh et al. 2013, C132, C179 |

---

## 2. Mathematical Formalism: Neuro-Human Translation Layer

The `DNToHumanTranslator` maps instantaneous neural firing rates $\mathbf{r}(t) \in [0, 1]^N$ and pharmacological occupancy parameters $\Phi$ into an 11-field `HumanIntent` tuple:

### 2.1 Forward Propulsion Drive ($D_{fwd}$)
$$\bar{R}_{DN} = \frac{1}{|DN|} \sum_{i \in DN} r_i, \quad \bar{R}_{DNa} = \frac{1}{|DNa|} \sum_{i \in DNa} r_i, \quad \bar{R}_{MDN} = \frac{1}{|MDN|} \sum_{i \in MDN} r_i$$

$$\Delta R_{MDN} = \max\left(0, \frac{\bar{R}_{MDN} - R_{MDN,base}}{R_{MDN,base}}\right)$$

$$D_{raw} = 0.65 \left( 0.7 \frac{\bar{R}_{DN}}{R_{DN,base}} + 0.3 \frac{\bar{R}_{DNa}}{R_{DNa,base}} - 1.2 \Delta R_{MDN} \right) + 0.25 S_{food} + 0.35 S_{pred}$$

$$D_{fwd} = \text{clip}\left( D_{raw} \cdot \text{scale}_{para} \cdot G_{stim}, \; 0.0, \; 1.0 \right)$$

- Calibrated baseline reference: $R_{DN,base} \approx 0.68$, $R_{DNa,base} \approx 0.90$, $R_{MDN,base} \approx 0.90$.
- Under baseline vehicle, $D_{fwd} \approx 0.55 - 0.65$ (steady walking).

### 2.2 Steering / Turn Intent ($\tau_{turn}$)
Unilateral activation of descending steering neurons (DNa01/DNa02) shifts human steering toward the more active side:
$$A_{DNa} = \frac{\bar{R}_{DNa,R} - \bar{R}_{DNa,L}}{\bar{R}_{DNa,R} + \bar{R}_{DNa,L} + \epsilon}, \quad A_{all} = \frac{\bar{R}_{DN,R} - \bar{R}_{DN,L}}{\bar{R}_{DN,R} + \bar{R}_{DN,L} + \epsilon}$$

$$\tau_{turn} = \text{clip}\left( 0.6 A_{DNa} + 0.2 A_{all} + \text{bias}_{turn}, \; -1.0, \; 1.0 \right)$$

### 2.3 Coordination Index ($C_{biped}$)
In vertebrate spinal cord, reciprocal alternating stepping relies on GABAergic and glycinergic commissural interneurons. High GABA_A receptor blockade collapses coordination into an ataxic state:
$$C_{biped} = \text{clip}\left( 1.0 - \Phi_{GABA}, \; 0.0, \; 1.0 \right)$$
- Intact: $C_{biped} = 1.0$ (clean anti-phase gait).
- Ataxia: $C_{biped} < 0.55$ triggers stochastic phase drift and step desynchronization.

### 2.4 Motor Tone & Extensor Force ($T_{motor}$)
Axonal Naᵥ block (e.g. Lidocaine) reduces muscle force capacity, causing flaccid weakness:
$$T_{motor} = \text{clip}\left( \text{scale}_{para} \cdot \left(0.3 + 0.7 \min\left(1.0, \frac{\bar{R}_{DN}}{R_{DN,base}}\right)\right), \; 0.05, \; 1.0 \right)$$

### 2.5 Cadence ($\nu$) and Stride Length ($L_{stride}$)
$$\nu = \text{clip}\left( \nu_{base} \cdot (0.6 + 0.7 D_{fwd}) \cdot G_{stim}, \; 0.4, \; 2.2 \right) \quad [\text{Hz}]$$

$$L_{stride} = \text{clip}\left( L_{base} \cdot D_{fwd} \cdot (0.5 + 0.5 T_{motor}), \; 0.0, \; 1.3 \right) \quad [\text{scale}]$$

### 2.6 Gait Mode Classifier
$$\text{mode} = \begin{cases}
\text{"freeze"}, & \text{if } (\bar{R}_{MDN} > 0.98 \land \bar{R}_{DN} < 0.35) \lor T_{motor} < 0.10 \\
\text{"ataxic"}, & \text{if } C_{biped} < 0.55 \\
\text{"stand"},  & \text{if } D_{fwd} < 0.10 \lor L_{stride} < 0.05 \\
\text{"jog"},    & \text{if } D_{fwd} > 0.85 \\
\text{"walk"},   & \text{otherwise}
\end{cases}$$

---

## 3. Biped CPG & Kinematic Engine

### 3.1 Coupled Phase Oscillator CPG
The biped central pattern generator uses a 2-oscillator reciprocal phase model (Kuramoto analogue, PDF Eqs. 4-5):
$$\frac{d\phi_L}{dt} = 2\pi\nu + w_c \sin(\phi_R - \phi_L - \pi) + \eta_L(t)$$
$$\frac{d\phi_R}{dt} = 2\pi\nu + w_c \sin(\phi_L - \phi_R - \pi) + \eta_R(t)$$
$$w_c = w_0 \cdot C_{biped}, \quad w_0 = 6.0 \text{ rad/s}$$

When $C_{biped} < 0.60$ (ataxic regime under GABA_A blockade), stochastic noise $\eta \sim \mathcal{N}(0, \sigma^2)$ with $\sigma = 4.0(1 - C_{biped})$ is injected, inducing phase desynchronization.

### 3.2 12-DOF Biped Kinematics
For each limb:
- **Stance Phase ($\phi \in [0, \pi)$)**:
  - Hip pitch swings from $+A_{hip}$ (heel strike) to $-A_{hip}$ (toe-off).
  - Knee extends for weight support ($0.04 - 0.10$ rad).
  - Ankle executes late-stance plantarflexion push-off ($\phi \in [0.3\pi, \pi)$), transferring forward thrust to the body.
- **Swing Phase ($\phi \in [\pi, 2\pi)$)**:
  - Knee flexes up to $0.95$ rad for foot ground clearance.
  - Ankle dorsiflexes ($+0.20$ rad) to lift toes clear of the floor.
  - Slew-rate limiting bounds all actuator target accelerations: $\left|\frac{d\theta_j}{dt}\right| \le 25.0 \text{ rad/s}$.

---

## 4. 3D Humanoid Body Scaffold & MuJoCo Mechanics

The humanoid model is compiled dynamically via `get_humanoid_xml()`:
- **Anatomy**: Height 1.75 m, total mass 71.8 kg (head 4.2 kg, torso 24.0 kg, pelvis 14.0 kg, thighs 6.5 kg $\times 2$, shins 3.8 kg $\times 2$, feet 1.5 kg $\times 2$, arms 3.3 kg $\times 2$).
- **Visual Assets**: Textured skybox with natural ambient lighting, checkerboard floor material, distinct torso, leg, and footwear shaders, and a tracking camera (`trackcam`) following the pelvis.
- **Body-Weight Support (BWS)**:
  - An overhead carriage (`harness_carriage`) slides along the forward X-rail with minimal damping (`damping="0.2"`).
  - The pelvis connects to the carriage via viscoelastic slide joints (`harness_z`, `harness_y`) and rotation dampers.
  - An active counterweight actuator (`act_harness_bws`) applies an upward lift force of $635 \text{ N} \cdot \text{support} \cdot H_{posture}$, allowing controlled clinical evaluation of drug-induced hypotonia, knee buckling, and ataxia without unrecoverable catastrophic falling.
  - A forward velocity actuator (`act_rail_vx`) drives the overhead gantry along `rail_x` in synchrony with descending motor intent ($V_x \approx 1.25\text{ m/s} \cdot \text{forward\_drive} \cdot T_{motor}$).

### 4.1 Joint Sign Conventions
All 12 DOFs were probed programmatically via `probe_joint_sign_conventions()` and verified against physiological definitions:
- `hip_pitch`: flexion moves knee/foot anteriorly ($+X$).
- `knee`: flexion moves foot posteriorly ($-X$) and lifts it ($+Z$).
- `ankle`: dorsiflexion lifts toes ($+Z$); plantarflexion pushes down into floor.
- `hip_roll`: abduction moves distal foot laterally.
- `shoulder_pitch`: flexion swings forearm forward ($+X$).
- `elbow`: flexion pulls hand forward and upward.

---

## 5. Locomotion & Clinical Metrics

The pipeline aggregates comprehensive biomechanical and neurological metrics:
- **$V_x$ (Forward Speed)**: $\Delta X / \Delta T$ [m/s].
- **Straightness Index**: Net displacement divided by total 2D path length (1.0 = straight path).
- **Step Symmetry**: Ratio of left and right stride lengths ($[0, 1]$).
- **Biped Coordination Index**: Fraction of time with exactly one foot in contact (alternating single support).
- **Duty Factor (Left / Right)**: Fraction of stride period each foot remains in ground contact.
- **Harness Load**: Mean upward support force exerted by the BWS harness [N].
- **COM Height**: Mean and minimum pelvis vertical position [m].
- **Reaction Time**: Latency from visual looming onset to escape response [s].

---

## 6. CLI Usage Guide

HighFly exposes three primary CLI modes for humanoid simulation via `./highfly`:

### 6.1 Interactive 3D Viewer (`human`)
Opens a native 3D MuJoCo window with tracking camera (`trackcam`) rendering the humanoid body in real time:
```bash
# Vehicle baseline walking
./highfly human

# Lidocaine Na_v conduction block (hypolocomotion & knee buckling)
./highfly human --drug "Lidocaine" --dose 1.0

# Jungle juice cocktail
./highfly human --drug "Jungle Juice (Everything mixed)"

# Caffeine stimulant with looming predator threat assay
./highfly human --drug "Caffeine" --predator --duration 5.0

# Free unharnessed biped
./highfly human --no-harness
```

### 6.2 Headless Metrics Aggregation (`human-metrics`)
Runs headless at full compute speed and outputs a structured JSON report:
```bash
./highfly human-metrics --drug "Lidocaine" --dose 1.0 --duration 3.0
```
Example output:
```json
{
  "drug_name": "Lidocaine",
  "dose": 1.0,
  "duration_s": 3.0,
  "outcome": "completed",
  "body_metrics": {
    "vx_m_s": 0.0321,
    "straightness_index": 0.985,
    "step_symmetry": 0.992,
    "biped_coordination_index": 0.420,
    "com_height_mean": 0.884,
    "fall_detected": false,
    "alive": true
  },
  "intent_summary": {
    "mean_forward_drive": 0.122,
    "mean_motor_tone": 0.255,
    "mean_posture_height": 0.440,
    "mean_cadence": 0.720,
    "final_mode": "walk"
  }
}
```

### 6.3 Instantaneous Intent & Rule Table (`human-intent`)
Displays the complete neurobiological rule table and evaluates the translated `HumanIntent` for a selected drug:
```bash
./highfly human-intent --drug "Vyvanse" --predator
```

### Timelapse Simulation & Video Export
Speed up live rendering or compress long walking trials into concise video summaries:
```bash
# Live interactive viewer running 5x faster than real-time
./highfly human --drug "Vehicle" --duration 20.0 --timelapse 5.0

# Render 30s of walking compressed into a 6s MP4 video
./highfly human --drug "Vehicle" --out out/walk_timelapse.mp4 --duration 30.0 --timelapse 5.0
```

---

## 7. Verification Suite

Run the full verification suite covering translation invariants, joint conventions, CPG dynamics, timelapse execution, and embodied 3D simulation smoke runs:
```bash
.venv3/bin/python scripts/verify_human.py
```
Verification results (57/57 passed):
- **Neuro-Human Translation Invariants & Provenance**: 20/20 PASS
- **MuJoCo Joint Sign Conventions Probe**: 13/13 PASS
- **Biped CPG & Kinematics Invariants**: 4/4 PASS
- **Embodied 3D MuJoCo Simulation Smoke Runs & Timelapse**: 20/20 PASS
