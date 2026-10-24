# HighFish — Drug-perturbed zebrafish-brain-driven humanoid biped (gait study)

An **in silico** neuropharmacology + gait-safety workbench: pick one of 30 drugs/products, and watch
a 12-DOF humanoid biped walk in 3D physics under a pharmacologically perturbed zebrafish brain.
The brain network is the **Fish1 larval zebrafish EM connectome (Petkova et al. 2025)** —
876,835 segmented cells, 29.5M synapses, 5.8M excitatory/inhibitory-resolved edges — and drug
effects act only on **verified zebrafish receptor systems** (every claim citation-keyed; products
with no verifiable fish ortholog are modeled as disclosed weak-signal approximations or no-ops).

```bash
./highfish run          # interactive: pick drug + stimuli -> live 3D humanoid biped
./highfish list         # all 17 products and their zebrafish receptor mapping
./highfish human-metrics --drug "Lidocaine" --predator  # headless humanoid metrics JSON
./highfish human-intent --drug "Vyvanse"                # translation rule table & intent
```

*(In `./highfish run`: choose drug, stimuli, dose, duration. A native window opens with an embodied
tracking camera — drag to orbit, scroll to zoom. Locomotion metrics and reaction times print when
the trial ends.)*

---

## Data sources and modeling

| Layer | Status | Provenance |
|---|---|---|
| Brain connectivity | **DATA** | Fish1 EM connectome, agglo v2a (Petkova et al. 2025, bioRxiv; see `data/zebrafish/fish1/` + `data/processed/meta.json`); E/I polarity from the `_ei_bayes` layer, CLEM-verified |
| Neurotransmitter identity | **DATA** | vglut2a (excitatory) vs gad1b (inhibitory) synapse typing, CLEM-validated (IoU > 0.99) |
| Hindbrain readout pool | **DATA + MODEL** | posterior (reticulospinal-like) cells with adequate in/out synapses; population rate = descending drive |
| Compound identities (CIDs) | **DATA** | PubChem PUG REST, API-returned only (`data/pubchem_cids.json`) |
| Human drug→receptor mechanisms | **CITED LITERATURE** | `citations.md` entries C1–C101 (PubMed/PMC/Nature/NCBI) |
| Zebrafish receptor orthologs | **CITED LITERATURE** | `citations.md` C1–C101 (Maximino 2011; Sundvik 2011; Siregar 2021; Reuter 2016; Nery 2014; Wei 2024; ...) |
| Rate network | **MODEL** | E/I-resolved firing-rate dynamics (`docs/GUIDELINES.md` Eqs. 1–2) on the Fish1 adjacency |
| Hindbrain readout → HumanIntent | **MODEL** | `sim/fish_readout.py` rule table; equations C1–E9 in the docstring |
| Biped CPG & 12-DOF kinematics | **MODEL** | reciprocal Kuramoto CPG scaled by C_biped (Eqs. 6, 10–11); Winter-based gait kinematics (Table 2 of the manuscript) |
| Body/physics | **MODEL** | MuJoCo 3.9 humanoid (1.75 m, 71.8 kg), PD servos, BWS harness (Eq. 13) |
| Occupancy parameters (Φ values) | **MODEL PARAMETERS** | qualitative mechanism + direction are cited; magnitudes are modeling parameters, not measured pharmacology |

**Why a hindbrain readout bridge?** The Fish1 volume covers the larval brain; the humanoid biped's
locomotor programs live in its own CPG. The pipeline is therefore:
`Fish1 rate network → hindbrain (reticulospinal-like) readout rate → HumanIntent (drive, tone,
posture, coordination, cadence, stride) → biped CPG → MuJoCo body → gait metrics`.

## The 17 products (fish-level mechanism → biped outcome)

Stimulant-like: **Caffeine** (adora1a/b + adora2a upregulation, Wei 2024; Maximino 2011),
**Tobacco/Extract** (chrna4/chrnb2, chrna7 agonist→desensitization), **Vyvanse** (slc6a3 DAT
substrate → DA ↑), **Bupropion** (slc6a3 + nAChR). Sedative-like: **Dormiphen/Gravol/Claritin**
(hrh1 axis, Sundvik 2011; disclosed weak-signal for second-generation antihistamines),
**Mirtazapine** (monoaminergic/histaminergic axes). Anesthetic: **Lidocaine** (scn1lab/Nav use-
dependent block → flaccid arrest), **Robax** (GABAergic + COX). **Weed** (cnr1 terminal
modulation → GABA collapse → ataxia) vs **CBD** (cnr1 negative allosteric + TRPV1/htr1a → gait
preserved). **Jungle Juice** = all of the above concurrently. Weak-signal approximations
(disclosed): Acetaminophen (serotonergic gain only; no COX/AM404 ortholog), Lithium (gsk3b/impa1,
Nery 2014).

## Reaction-time assays (environment stimuli)

- **Predator** = looming dark disc approaching at constant speed; escape is detected as a rise in
  hindbrain descending drive above pre-stimulus baseline (flee) with an absolute behavioral floor,
  else freeze — per looming/escape literature (zebrafish loom circuits, C182–C185).
- **Food** = prey/odor-source proxy: proximity-gated attraction drive + steering.
- Latencies are measured relative to stimulus onset and are drug-sensitive.

## Project layout

```
highfish                   # CLI: run (interactive humanoid viewer) / list / human-metrics / human-intent
run_view.py                # quick single-drug humanoid viewer
run_video.py               # headless humanoid MP4 export (tracking camera)
data/pharmacology.yaml     # 17 products -> zebrafish systems (citation-keyed)
data/pubchem_cids.json     # API-verified compound CIDs
data/zebrafish/fish1/      # raw Fish1 EM connectome files + metadata
data/processed/            # adj_E/adj_I, neuron table (parquet), meta.json
scripts/extract_fish1_syns.py  # Fish1 bundler -> syn-level extraction
scripts/parse_fishconnectome.py  # syn-level -> adjacency E/I + geometry
sim/neural_sim.py          # rate network on the Fish1 adjacency (Eqs. 1–2)
sim/fish_readout.py        # hindbrain readout -> HumanIntent translation layer
sim/human_gait.py          # biped reciprocal CPG + 12-DOF kinematics
sim/humanoid_body.py       # MuJoCo 3D humanoid body + PD servos + BWS harness
sim/human_pipeline.py      # coupled connectome -> human locomotion pipeline
sim/stimuli.py             # food/predator assays + reaction-time recorder
sim/drug_engine.py         # YAML -> simulator parameter resolution
citations.md               # MLA-9 source list (C1–C101), the provenance backbone
docs/GUIDELINES.md         # modeling spec, restated
EXECUTION_PLAN.md          # living plan; agent-continuity notes
results/                   # manuscript template DOCX, equation PNGs, test-battery reports
```

## Verification

```bash
.venv3/bin/python scripts/verify_all.py      # data integrity + simulation sanity suite
.venv3/bin/python scripts/verify_human.py    # translation + biped gait suite
```

## Requirements

macOS (Apple Silicon tested), Python 3.12 venv at `.venv3` (MuJoCo 3.9, numpy/scipy/pandas/pyarrow,
pyyaml, imageio, python-docx). Live viewer runs under `mjpython` (the `highfish` script relaunches
itself automatically). Data use follows the Fish1 release terms — see acknowledgment in
`data/zebrafish/fish1/`.
