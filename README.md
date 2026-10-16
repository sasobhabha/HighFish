# HighFly — Drug-perturbed virtual fruit fly on the FlyWire connectome

An **in silico** neuropharmacology workbench: pick one of 17 drugs/products, and watch a
biomechanically realistic virtual *Drosophila* walk (and react to food/predators) under that
drug's influence. The brain network is the **FlyWire FAA0038 (FAFB) v783 connectome —
139,255 neurons, 2,700,513 connections, 34.15M synapses** — and drug effects act only on
fly receptor systems that are **verified to exist** in *Drosophila* (every claim citation-keyed;
products with no verifiable fly target are modeled as no-ops).

```bash
./highfly run          # interactive: pick drug + stimuli -> live 3D fly
./highfly list         # all 17 products and their fly-level receptor mapping
./highfly metrics --drug "Lidocaine" --predator    # headless metrics JSON

# 3D Humanoid Biped Simulation (Connectome -> Human Translation -> MuJoCo Biped)
./highfly human --drug "Lidocaine"                 # live 3D humanoid viewer
./highfly human-metrics --drug "Caffeine"          # headless humanoid metrics JSON
./highfly human-intent --drug "Vyvanse"            # translation rule table & intent
```

*(In `./highfly run` and `./highfly human`: choose drug, stimuli, dose, duration. A native
window opens with an embodied tracking camera — drag to orbit, scroll to zoom. Locomotion
metrics and reaction times print when the trial ends.)*

---

## Data sources and modeling

| Layer | Status | Provenance |
|---|---|---|
| Brain connectivity | **DATA** | FlyWire codex v783 bulk CSVs (see `data/flywire/DOWNLOAD_LOG.md`); original root IDs preserved |
| Neurotransmitter identity | **DATA** | FlyWire per-neuron NT predictions + per-edge NT labels (codex `neurons.csv.gz`, `connections.csv.gz`) |
| Cell classes (sensory/optic/central/descending/motor…) | **DATA** | FlyWire `classification.csv.gz` super_class labels |
| Compound identities (CIDs) | **DATA** | PubChem PUG REST, API-returned only (`data/pubchem_cids.json`) |
| Human drug→receptor mechanisms | **CITED LITERATURE** | `citations.md` entries C1–C120 (PubMed/PMC/Nature/NCBI) |
| Fly receptor orthologs | **CITED LITERATURE** | `citations.md` C121–C181 (FlyBase/JNeurosci/Nature/eNeuro) |
| Drugs with NO fly target (codeine, melatonin, NSAIDs, famotidine, fexofenadine, pregabalin, THCa, mometasone, Pepto) | **NO-OP** | explicit nulls in `data/pharmacology.yaml`, justification cited (e.g. cannabinoid receptors absent in insects, C153) |
| Descending drive → leg CPG coupling | **MODEL** | PDF spec Eqs. 4–8 (`docs/GUIDELINES.md`); leg CPGs live in the VNC, which is *not* in FAFB |
| Body/physics | **MODEL** | NeuroMechFly v2 (flygym 2.1.0, MuJoCo 3.9): micro-CT fly morphology, dt=1e-4 |
| Occupancy parameters (Φ values) | **MODEL PARAMETERS** | qualitative mechanism + direction are cited; magnitudes are modeling parameters, not measured pharmacology |

**Why a CPG bridge?** FAFB is the *brain* connectome; leg motor neurons are in the VNC
(MANC/MaleCNS, per the PDF). The scientific pipeline is therefore:
`FlyWire brain network → 1,305 descending neurons' population rate → VNC leg CPG (PDF
Eqs. 4–5) → muscle activation (Eqs. 6–7) → PD servos (Eq. 8) → MuJoCo body → metrics
(Eqs. 9–13)`. This mirrors how the fly itself interfaces brain to VNC.

## The 17 products (fly-level outcome)

Stimulant-like: **Caffeine** (D1-like DA ↑, dAdoR-independent — C179/180), **Tobacco/Extract**
(nAChR agonist→desensitization), **Vyvanse** (dDAT block → DA ↑, fumin phenotype),
**Bupropion** (dDAT + nAChR). Sedative-like: **Dormiphen/Gravol/Claritin** (histamine-gated
Cl⁻ channel block — disclosed approximation), **Mirtazapine** (5-HT ↓). Anesthetic:
**Lidocaine/Robax** (para Naᵥ block → bradykinesia). **Weed/CBD/THCa**: CB receptors absent
in insects (C153) — CBD's weak 5-HT1A effect only. **Jungle Juice** = all of the above
additively. No-ops (no fly target, cited): Codeine, Melatonin, Famotidine, Fexofenadine,
Pregabalin, Naproxen, Ibuprofen, Mometasone, Pepto Bismol.

## Reaction-time assays (environment stimuli)

- **Predator** = looming dark disc approaching at constant speed; escape is detected as a
  rise in descending-neuron drive above pre-stimulus baseline (flee) with an absolute
  behavioral floor, else freeze — per looming/escape literature (C182–C185).
- **Food** = odor-source proxy: proximity-gated attraction drive + steering (a simplification:
  the biological attractant circuits are antennal lobe → lateral horn/MB).
- Latencies are measured relative to stimulus onset and are drug-sensitive
  (e.g. baseline flee ≈ 0.9 s; strong Naᵥ block abolishes escape running).

## Project layout

```
highfly                    # CLI: run (interactive viewer) / list / metrics
run_view.py                # quick single-drug viewer
run_video.py               # headless MP4 export (tracking camera)
data/pharmacology.yaml     # 17 products -> mechanisms (citation-keyed)
data/pubchem_cids.json     # API-verified compound CIDs
data/flywire/783/          # raw FlyWire codex v783 files + DOWNLOAD_LOG.md
data/processed/            # adjacency (total + per-NT), neuron table, meta.json
sim/neural_sim.py          # rate network on the FlyWire adjacency (Eq. 2–3)
sim/motor_bridge.py        # leg CPG + muscle model (Eq. 4–7)
sim/body_sim.py            # embodied coupling + metrics (Eq. 8–13)
sim/human_translation.py   # FlyWire DN readout -> HumanIntent translation layer
sim/human_gait.py          # biped reciprocal CPG + 12-DOF kinematics
sim/humanoid_body.py       # MuJoCo 3D humanoid body + PD servos + BWS harness
sim/human_pipeline.py      # coupled connectome -> human locomotion pipeline
sim/stimuli.py             # food/predator assays + reaction-time recorder
sim/drug_engine.py         # YAML -> simulator parameter resolution
citations.md               # MLA-9 source list (C1–C185), the provenance backbone
docs/GUIDELINES.md         # the PDF's spec, restated
docs/HUMAN_TRANSLATION.md  # neurobiological provenance, formulas & biped scaffold
EXECUTION_PLAN.md          # living plan; agent-continuity notes
```

## Verification

```bash
.venv3/bin/python scripts/verify_all.py      # fly data integrity + simulation sanity suite
.venv3/bin/python scripts/verify_human.py    # human translation, joint probe & biped suite
```

## Requirements

macOS (Apple Silicon tested), Python 3.12 venv at `.venv3` (flygym 2.1.0, MuJoCo 3.9,
numpy/scipy/pandas/pyarrow, pyyaml, imageio). Live viewer runs under `mjpython`
(the `highfly` script relaunches itself automatically). Data use follows FlyWire's
terms — see acknowledgment in `data/flywire/DOWNLOAD_LOG.md`.
