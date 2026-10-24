# Project Guidelines — Zebrafish Connectome → Humanoid Gait Under Pharmacology

Modeling specification for the current implementation (zebrafish Fish1 substrate +
anthropomorphic biped output). This file restates the equations and conventions actually
implemented in `sim/`, so the manuscript (`scripts/build_template_docx.py`) and the code agree.

## 1. Framework

Fully integrated **in silico** neuro-biomechanical pipeline:

```
Connectomic data layer (Fish1 EM reconstruction, E/I polarity, synapse counts)
        ↓
Biophysical & pharmaco-kinetic layer (Hill occupancy Φ → synaptic conductance scaling g_syn → rate-network dynamics)
        ↓
Embodied biomechanical layer (hindbrain readout → HumanIntent → MuJoCo physics: PD servos, BWS harness)
```

Dataset: **Fish1** (Petkova et al. 2025, bioRxiv doi:10.1101/2025.06.10.658982) — serial-section EM
connectome of the larval zebrafish brain + anterior spinal cord. E/I polarity comes from the
`_ei_bayes` layer (vglut2a → type 2 excitatory, gad1b → type 1 inhibitory), CLEM-verified at
IoU > 0.99 (see `data/processed/meta.json`).

## 2. Hypotheses implemented as simulation conditions
- **H1 — cnr1 agonism / GABAergic collapse:** THC-like activity suppresses presynaptic GABA
  release and degrades left-right reciprocal symmetry → non-linear collapse of bipedal
  coordination (ataxic mode) below C_biped ≈ 0.55.
- **H2 — Na_v blockade (Lidocaine, scn1lab/Nav1.1 axis):** use-dependent excitability cut →
  monotonic collapse of motor tone, zero propulsion, knee buckling in the BWS harness.
- **H0 — null:** vehicle control shows baseline steady locomotion with intact symmetry.

## 3. Equations (implement verbatim; PNG renders live in `results/equations/`)
1. E/I rate network (`sim/neural_sim.py`):
   `τ_r · dr_i/dt = −r_i + φ(Σ_E W_ij^E r_j − Σ_I W_ij^I r_j + I_i)`
2. Transfer function & synaptic state: `φ(x) = (√(x²+1) − x)/2`, `ds/dt = −s/τ_s + r`
3. Hill–Langmuir occupancy (non-cooperative, n = 1.0):
   `Φ = [D]^n / ([D]^n + Kd^n)`
4. Drug scaling: agonism `g_syn = g0(1 + Δg_max Φ)`; Na_v blockade `scale_Scn = Kd^n/(Kd^n + [D]^n)`
5. Hindbrain readout (`sim/fish_readout.py`):
   `R_RO = mean(r_i, i ∈ hindbrain pool)`; lateral asymmetry `A_lat = (R_R − R_L)/(R_R + R_L + ε)`
6. Coordination index: `C_biped = (1 − |A_LR|) · (1.0 − 0.35 Φ_GABA)`
7. Forward drive: `D_fwd = clip([0.65(0.70 R_RO_norm + 0.30) + 0.25 S_food + 0.35 S_loom] · scale_Scn · G_stim, 0, 1)`
8. Motor tone: `T_motor = clip(scale_Scn·(0.30 + 0.70 min(1, R_RO_norm)), 0.05, 1.0)`
9. Postural tone: `P_post = clip(scale_Scn · min(1, 0.5+0.5 G_stim) · min(1, |A_LR|+0.3), 0.2, 1.0)`
10. Biped CPG (`sim/human_gait.py`):
    `dφ_L/dt = 2πν + w_c C_biped sin(φ_R − φ_L − π) + η_L(t)` (mirror for φ_R)
11. Cadence & stride: `ν = ν0 + Δν D_fwd`, `L = L0 √D_fwd`
12. Joint targets & PD torque: `θ_k(t) = A_k(D_fwd)·f_k(φ(t)) + θ_k,0`; `τ_k = Kp(θ_t − θ_a) − Kd·θ̇_a`
13. BWS harness: `F_BWS = m g α_support H_posture ẑ`

## 4. Assay parameters
| Parameter | Value |
|---|---|
| Physics engine | MuJoCo 3.9 (humanoid biped body, `sim/humanoid_body.py`) |
| Neural rate network | Fish1 adjacency, τ_r = 20 ms, stepped at 50 Hz |
| Physics integration dt | varies by body model (PHYSICS_DT in `sim/human_pipeline.py`) |
| Harness | BWS overhead carriage; α_support = 1.0 (full support, knee buckling preserved) |
| Seeds | fixed default seed 0 for determinism |

Treatment conditions: vehicle control (Φ = 0); the 30 citation-mapped products in
`data/pharmacology.yaml` (fish: systems → mapping); "Jungle Juice" = concurrent multi-receptor
co-application.

## 5. Phenotyping metrics
1. Forward velocity Vx = Δx_COM / ΔT
2. Straightness Si = ‖Δp_COM‖ / ∫‖v‖dt
3. Step symmetry & biped coordination index (left/right swing-phase statistics)
4. Cadence (Hz), stride length, COM height (P_post), harness load
5. Reaction-time assays: looming escape latency vs. freeze (sim/stimuli.py)

## 6. Validation targets
- Vehicle baseline: Vx ≈ 0.99–1.2 m/s, C_biped ≥ 0.90, stable COM height.
- Lidocaine: T_motor ≤ 0.5, forward drive collapse, fall/suspension in harness.
- THC: C_biped < 0.55 → ataxic mode; CBD: preserved baseline gait.
- Metabolic sanity: harness support ≈ mg at rest during quiet stance.

## 7. Agent-added scope (user requests on top of the original spec)
- 17 products → human mechanisms → verified zebrafish orthologs, all cited
  (PubMed PMIDs, Nature/Science DOIs, PubChem CIDs, citations.md C1–C101). No uncited claims.
- Manuscript template (`scripts/build_template_docx.py`) auto-loaded from the batch test report.
- "Jungle Juice" = all drug effects combined (multi-receptor co-application).
