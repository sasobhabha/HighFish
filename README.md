# HighFish — Drug-perturbed zebrafish-brain-driven humanoid biped (gait study)

An **in silico** neuropharmacology + gait-safety workbench: pick one of 30 drugs/products, and watch
a 13-DOF humanoid biped walk in 3D physics under a pharmacologically perturbed zebrafish brain.
The brain network is the **Fish1 larval zebrafish EM connectome (Petkova et al. 2025)** —
876,835 segmented cells, 29.5M synapses, 5.8M excitatory/inhibitory-resolved edges — and drug
effects act only on **verified zebrafish receptor systems** (every claim citation-keyed; products
with no verifiable fish ortholog are modeled as disclosed weak-signal approximations or no-ops).

```bash
./highfish run          # interactive: pick drug + stimuli -> live 3D humanoid biped
./highfish list         # all 30 products and their zebrafish receptor mapping
./highfish reflex       # virtual-hospital reflex lab: knee tap / pupil / startle exams
./highfish human-metrics --drug "Lidocaine" --predator  # headless humanoid metrics JSON
./highfish human-intent --drug "Vyvanse"                # translation rule table & intent
```

*(In `./highfish run`: choose drug, stimuli, dose, duration. A native window opens with an embodied
tracking camera — drag to orbit, scroll to zoom. Locomotion metrics and reaction times print when
the trial ends. Alternatively pass flags directly, e.g. `./highfish run --drug Lidocaine --predator
--out fall.mp4` for a headless MP4/GIF render.)*

---

## The reflex lab (interactive demo mode)

A terminal "virtual hospital" built for public demos — no MuJoCo window needed:

```bash
./highfish reflex       # or: ./highfish --reflex
```

1. Pick a "patient" (drug + dose) — a vehicle baseline is measured each session.
2. Run bedside exams:
   - **Patellar tendon tap** — a fixed passive stretch of the knee; recovery metrics
     (percent returned, half-time) are graded against healthy norms. Under tone-collapse
     drugs the response degrades measurably (hyporeflexia bands: brisk / normal / sluggish / absent).
   - **Pupillary light reflex** — modeled photomotor arc with drug-scaled latency/amplitude
     (the connectome carries no photomotor circuitry — disclosed).
   - **Looming startle** — a prey-style threat on the real Fish1 connectome; flee-vs-freeze
     response and latency are genuinely simulated.
3. Every tap exam renders an animated GIF of the 3-D patient under the tap, opened automatically —
   float the window next to the terminal and you have a mini physiology exhibit.

## Data sources and modeling

| Layer | Status | Provenance |
|---|---|---|
| Brain connectivity | **DATA** | Fish1 EM connectome, agglo v2a (Petkova et al. 2025, bioRxiv; see `data/zebrafish/fish1/` + `data/processed/meta.json`); E/I polarity from the `_ei_bayes` layer, CLEM-verified |
| Neurotransmitter identity | **DATA** | vglut2a (excitatory) vs gad1b (inhibitory) synapse typing, CLEM-validated (IoU > 0.99) |
| Hindbrain readout pool | **DATA + MODEL** | posterior (reticulospinal-like) cells with adequate in/out synapses; population rate = descending drive |
| Compound identities (CIDs) | **DATA** | PubChem PUG REST, API-returned only (`data/pubchem_cids.json`) |
| Human drug→receptor mechanisms | **CITED LITERATURE** | `citations.md` entries C1–C224 (PubMed/PMC/Nature/NCBI) |
| Zebrafish receptor orthologs | **CITED LITERATURE** | `citations.md` C1–C224 (Maximino 2011; Sundvik 2011; Siregar 2021; Reuter 2016; Nery 2014; Wei 2024; Baraban 2005; Wiggin 2014; Irons 2013; ...) |
| Rate network | **MODEL** | E/I-resolved firing-rate dynamics (`docs/GUIDELINES.md` Eqs. 1–2) on the Fish1 adjacency |
| Hindbrain readout → HumanIntent | **MODEL** | `sim/fish_readout.py` rule table; equations C1–E9 in the docstring |
| Biped CPG & 13-DOF kinematics | **MODEL** | reciprocal Kuramoto CPG scaled by C_biped (Eqs. 6, 10–11); Winter-based gait kinematics (Table 2 of the manuscript) |
| Body/physics | **MODEL** | MuJoCo 3.9 humanoid (1.75 m, 71.8 kg), PD servos, BWS harness (Eq. 13) |
| Occupancy parameters (Φ values) | **MODEL PARAMETERS** | qualitative mechanism + direction are cited; magnitudes are modeling parameters, not measured pharmacology |

**Why a hindbrain readout bridge?** The Fish1 volume covers the larval brain; the humanoid biped's
locomotor programs live in its own CPG. The pipeline is therefore:
`Fish1 rate network → hindbrain (reticulospinal-like) readout rate → HumanIntent (drive, tone,
posture, coordination, cadence, stride) → biped CPG → MuJoCo body → gait metrics`.

**Whole-body tone collapse.** Muscle relaxants relax *everything*, not just the legs: CPG arm and
ankle drives, hip abduction holds, and all trunk-tone springs scale down with the drug state, and
the trunk slumps at a dedicated **waist joint** (the torso is no longer welded to the pelvis).
Collapse is triggered by **sustained simultaneous bilateral knee flexion** (> 0.25 rad for >
0.45 s) — a dwell-time criterion that separates a true collapse from a fast toe-off transient.
With the harness straps loosened (wider rotation limits), a fully drug-relaxed body genuinely
topples and settles on the floor; with straps taut it crumples to a harness kneel.

## The 30 products (fish-level mechanism → biped outcome)

31 tested conditions = these 30 products + vehicle control.

- **Stimulant-like:** Caffeine (adora1a/b + adora2a upregulation, Wei 2024; Maximino 2011),
  Tobacco/Tobacco Extract (chrna4/chrnb2, chrna7 agonist→desensitization),
  Vyvanse (slc6a3 DAT substrate → DA ↑), Bupropion (slc6a3 + nAChR),
  Methylphenidate/Ritalin (slc6a3 inhibitor, Lange 2018), Cocaine (slc6a3 inhibitor;
  weak larval locomotor signature — conservatively low gain, Kirla 2016).
- **Sedative-like:** Dormiphen/Gravol/Claritin (tablet & gel; hrh1 axis, Sundvik 2011; disclosed
  weak-signal for second-generation antihistamines), Mirtazapine (monoaminergic/histaminergic
  axes), Melatonin (mtnr1aa/bb sleep axis, Zhdanova 2001), Diazepam (GABA_A positive allosteric
  modulator, Cao 2019), Ethanol (glut_iontropic weak antagonist + trace nAChR gain; biphasic
  time-course not simulated — disclosed).
- **Anesthetics & tone collapse:** Lidocaine (scn1lab/Nav use-dependent block → flaccid arrest),
  Robax (GABAergic + COX), Ketamine (grin NMDA antagonist, Riehl 2011), Tetrodotoxin
  (scn1lab Nav site-1 pore block → the strongest excitability collapse in the catalog), Haloperidol
  (drd2b/drd3 antagonist, Irons 2013).
- **Convulsants (inhibitory block):** Pentylenetetrazol (gabrb2/gabra1 axis; Baraban 2005 larval
  seizure model), Picrotoxin (noncompetitive GABA_A pore blocker, Yang 2017), Strychnine
  (glycine receptor antagonist; Wiggin 2014 fictive-swim coordination collapse).
- **Cholinergic / serotonergic:** Donepezil/Aricept (ache inhibitor → mAChR + nAChR gain,
  Giacomini 2020), Fluoxetine/Prozac (slc6a4a/b SERT inhibitor, ~93% identity to human SLC6A4,
  Nozari 2022).
- **Cannabinoids:** Weed (cnr1 terminal modulation → GABA collapse → ataxia) vs CBD nanodrops
  (cnr1 negative allosteric + TRPV1/htr1a → gait preserved).
- **Weak-signal approximations (disclosed):** Acetaminophen (serotonergic gain only; no COX/AM404
  ortholog), Lithium (gsk3b/impa1, Nery 2014).
- **Jungle Juice** = everything mixed concurrently (catastrophic polypharmacy collapse).

## Reaction-time assays (environment stimuli)

- **Predator** = looming dark disc approaching at constant speed; escape is detected as a rise in
  hindbrain descending drive above pre-stimulus baseline (flee) with an absolute behavioral floor,
  else freeze — per looming/escape literature (zebrafish loom circuits, C182–C185).
- **Food** = prey/odor-source proxy: proximity-gated attraction drive + steering.
- Latencies are measured relative to stimulus onset and are drug-sensitive.

## Project layout

```
highfish                   # CLI: run (interactive humanoid viewer) / list / reflex / human-metrics / human-intent
highfish_main.py           # command dispatch (the `highfish` bash launcher relaunches under mjpython for GUI modes)
run_view.py                # quick single-drug humanoid viewer
run_video.py               # headless humanoid MP4 export (tracking camera)
data/pharmacology.yaml     # 30 products -> zebrafish systems (citation-keyed)
data/pubchem_cids.json     # API-verified compound CIDs
data/zebrafish/fish1/      # raw Fish1 EM connectome files + metadata
data/processed/            # adj_E/adj_I, neuron table (parquet), meta.json
scripts/reflex_lab.py      # interactive reflex lab (tap / pupil / startle + GIF rendering)
scripts/extract_fish1_syns.py  # Fish1 bundler -> syn-level extraction
scripts/parse_fishconnectome.py  # syn-level -> adjacency E/I + geometry
sim/neural_sim.py          # rate network on the Fish1 adjacency (Eqs. 1–2)
sim/fish_readout.py        # hindbrain readout -> HumanIntent translation layer
sim/human_gait.py          # biped reciprocal CPG + 13-DOF kinematics (incl. waist)
sim/humanoid_body.py       # MuJoCo 3D humanoid body + PD servos + BWS harness + trunk springs
sim/human_pipeline.py      # coupled connectome -> human locomotion pipeline
sim/stimuli.py             # food/predator assays + reaction-time recorder
sim/drug_engine.py         # YAML -> simulator parameter resolution (30 products)
citations.md               # MLA-9 source list (C1–C224), the provenance backbone
docs/GUIDELINES.md         # modeling spec, restated
```

## Verification

```bash
python scripts/verify_all.py      # data integrity + simulation sanity suite
python scripts/verify_human.py    # translation + biped gait suite
```

## Requirements

macOS (Apple Silicon tested), a Python 3.12 virtualenv with MuJoCo 3.9,
numpy/scipy/pandas/pyarrow, pyyaml, imageio, python-docx. Live viewer runs under `mjpython`
(the `highfish` script relaunches itself automatically — GUI modes only; `reflex`, `list`, and
metrics modes run plain headless).
Data use follows the Fish1 release terms — see acknowledgment in `data/zebrafish/fish1/`.
