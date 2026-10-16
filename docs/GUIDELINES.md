# Project Guidelines (from `Drosophila_on_Drugs.pdf`)

Source: *In Silico Modeling of Drosophila Locomotion Under Pharmacological Receptor Blockade:
A Connectome-Constrained Biomechanical Study* (Research Project Plan, September 2026).
This file restates the PDF's specification so the implementation follows it exactly.

## 1. Framework
Fully integrated **in silico** neuro-biomechanical pipeline:

```
Connectomic data layer (EM dense reconstruction, NT identity, synapse counts)
        ↓
Biophysical & pharmaco-kinetic layer (Hill occupancy Φ → synaptic conductance scaling g_syn → CPG / LIF dynamics)
        ↓
Embodied biomechanical layer (NeuroMechFly v2 / FlyGym → MuJoCo physics: contact, adhesion, PD control)
```

Dataset: **FlyWire** (full adult fly brain, FAFB/FAA0038
family) as the connectome, with agent-added receptor/cell-type annotations backed by the
pharmacology sources. The PDF's MANC/MaleCNS VNC focus is respected by driving the leg CPGs
with FlyWire descending neurons (DNa01, DNa02, MDN-class DNs) that feed the VNC.

## 2. Hypotheses implemented as simulation conditions
- **H1 — GABA_A / Rdl antagonism:** suppresses inter-leg reciprocal inhibition → non-linear
  collapse of tripod synchrony at occupancy Φ > 0.45 (high-frequency uncoordinated flailing).
- **H2 — nAChR antagonism:** suppresses excitatory drive to MNs/CPGs → monotonic linear decay
  of peak joint torques, decreased stance height, bradykinesia, preserved phase-coupling matrix.
- **H0 — null:** no significant deviation vs. wild-type baseline.

## 3. Equations (implement verbatim)
1. Hill–Langmuir occupancy (non-cooperative, n = 1.0):
   `Φ = [D]^n / ([D]^n + Kd^n)`
2. Antagonist conductance scaling: `g_syn(t) = (1 − Φ) · g_max · s(t)`
3. Synaptic gating: `ds/dt = −s/τ_decay + Σ_k δ(t − t_k)`
4. CPG phase dynamics (per leg i, baseline ν_i = 12 Hz):
   `dθ_i/dt = 2πν_i + Σ_{j∈Adj(i)} w_ij(Φ) · sin(θ_j − θ_i − Δφ_ij)`
   with antagonist attenuation `w_ij(Φ) = (1 − Φ_GABA) · w_ij^(0)` under GABAergic blockade.
5. Muscle activation (τ_m = 10 ms first-order filter, sigmoid):
   `τ_m · da_k/dt = −a_k + σ(Σ_j w_jk_eff(Φ) · r_j)`, `w_jk_eff = (1 − Φ_nAChR) · w_jk^(0)`
6. Joint target & PD torque:
   `θ_target,k = θ_rest,k + a_k · Δθ_max,k`;  `τ_k = Kp(θ_target − θ_actual) − Kd·dθ_actual/dt`

## 4. Assay parameters (Table 1)
| Parameter | Value |
|---|---|
| Physics engine | MuJoCo via FlyGym / NeuroMechFly v2 |
| Integration dt | 1e-4 s (10 kHz) |
| Trial duration | 3.0 s (30,000 steps) |
| Logging | 100 Hz (every 100 steps) |
| Arena | Flat rigid plane, μs = 1.0, μd = 0.8 |
| Adhesion | Active tarsal adhesion, F_adh,max = 15 μN |
| Seeds | 30 stochastic seeds per condition |

Treatment conditions: vehicle control (Φ = 0); GABA_A blockade (picrotoxin-site);
nAChR blockade (MLA/imidacloprid-site); dual co-titration, Φ ∈ {0.1…1.0}.

## 5. Phenotyping metrics (Eq. 9–13)
1. Forward velocity Vx = Δx_COM / ΔT
2. Straightness Si = ‖Δp_COM‖ / ∫‖v_COM‖dt
3. Tripod Coordination Index TCI = mean |mean C(Tripod1) − mean C(Tripod2)|,
   Tripod1 = {L1,R2,L3}, Tripod2 = {R1,L2,R3}, Ck ∈ {0,1} ground contact
4. Duty factor DFk = t_stance/(t_stance + t_swing)
5. Normalized GRF = Σ Fz,tarsal / (m·g)
6. Vertical COM displacement ΔZ_COM

## 6. Validation targets
- Baseline: Vx 20–35 mm/s, TCI ≥ 0.80, Si ≥ 0.92 over 3 s.
- Rest GRF ≈ m·g (vertical force sanity check).
- Motor-neuron identity and NT predictions verified against anatomical standards.
- Numerical stability at dt = 1e-4 even at saturation Φ = 1.0.

## 7. Agent-added scope (user requests on top of the PDF)
- 27 user-listed products → receptor mechanisms → fly receptor orthologs, all cited
  (PubMed PMIDs, Nature/Science DOIs, PubChem CIDs, FlyBase IDs). No uncited claims.
- Connectome pulled live from FlyWire (codex API): root IDs, synapses, cell classes,
  NT predictions, hemilineage/cell-type annotations.
- Viewer shows live connectome activity + the NeuroMechFly v2 body simultaneously.
- "Jungle Juice" = all drug effects combined (multi-receptor co-application).
