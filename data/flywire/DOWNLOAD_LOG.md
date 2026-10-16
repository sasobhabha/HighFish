# FlyWire Codex Data — Download Log

- **Date:** 30 September 2026
- **Source:** FlyWire Codex bulk data endpoint, as documented in the codex source
  (`murthylab/codex`, `codex/data/local_data_loader.py`) and cited by
  Matsliah et al. 2024 (*Nature*, s41586-024-07981-1) and Yu et al. 2025 (bioRxiv
  2025.07.11.664377): `https://codex.flywire.ai/api/download?dataset=fafb`
- **Storage template (exact, from codex source):**
  `https://storage.googleapis.com/flywire-data/codex/data/fafb/{version}/{filename}`
- **Data snapshot version:** `783` ("Snapshot 783 - Oct 2023 [latest release]", from
  `codex/data/versions.py`; matches Zenodo record 10676866 "release version 783")

## Files downloaded (data/flywire/783/)

| File | Size | Columns (verified by inspection) |
|---|---|---|
| neurons.csv.gz | 1.68 MB | root_id, group, nt_type, nt_type_score, da_avg, ser_avg, gaba_avg, glut_avg, ach_avg, oct_avg |
| classification.csv.gz | 0.93 MB | root_id, flow, super_class, class, sub_class, hemilineage, side, nerve |
| consolidated_cell_types.csv.gz | 0.90 MB | root_id, primary_type, additional_type(s) |
| connections.csv.gz | 50.3 MB | pre_root_id, post_root_id, neuropil, syn_count, nt_type |
| labels.csv.gz | 4.77 MB | root_id, label, user_id, position, supervoxel_id, label_id, date_created, user_name, user_affiliation |
| coordinates.csv.gz | 5.31 MB | (per-neuron soma coordinates) |
| cell_stats.csv.gz | 2.53 MB | (per-cell statistics) |
| nblast.csv.gz | 5.96 MB | (NBLAST similarity scores) |
| connectivity_tags.csv.gz | 0.64 MB | (connectivity tags) |

- Raw CSV sizes on disk (decompressed): see `meta.json` written by the parser.
- Nothing is invented: all downstream artifacts are derived from these files with
  original FlyWire root IDs preserved so every neuron can be looked up at
  https://flywire.ai/ (paste root_id into the URL: `https://flywire.ai/links/<root_id>`).

## FlyWire data usage acknowledgment (per flywire.ai terms)

The connectome data used here is from FlyWire (Dorkenwald et al. 2023, bioRxiv /
Nature; "A connectome of the adult Drosophila visual system" and "Neuronal parts
list and wiring diagram for a visual system", Matsliah et al. 2024, Nature 632),
served via FlyWire Codex (Princeton Neuroscience Institute).
