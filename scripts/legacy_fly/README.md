# Legacy fly-era scripts (archived)

These scripts belong to the **superseded Drosophila (FlyWire v783) prototype**
of this project. The study has been reframed around the **larval zebrafish
Fish1 connectome (Petkova et al. 2025, agglo v2a, E/I-resolved)** — still a
gait/locomotion study, with the same humanoid biped output.

They are kept for provenance only; none of them is imported by the active
pipeline (`sim/`, `highfly_main.py`, `scripts/verify_*.py`,
`scripts/run_all_drugs_test.py`, `scripts/build_template_docx.py`).

Active replacements:

| Archived (fly era)                    | Active (zebrafish)                    |
| ------------------------------------- | ------------------------------------- |
| `build_scientific_docx.py`            | `scripts/build_template_docx.py`      |
| `build_data_tables_docx.py`           | `scripts/build_template_docx.py`      |
| `render_latex_equations_png.py`       | `scripts/render_pure_equations_png.py`|
| `build_individual_equations_png.py`   | `scripts/render_pure_equations_png.py`|
| `extract_pharmacological_homology.py` | `data/pharmacology.yaml` + `citations.md` |
| `generate_svg_charts.py`, `generate_drawio_diagrams.py`, `build_drawio_suite.py` | — (diagrams not in active flow) |
| `export_to_sheets.py`                 | — (sheets not in active flow)         |
| `ngsharded.py`, `parse_flywire.py`    | `scripts/extract_fish1_syns.py` + `scripts/parse_fishconnectome.py` |
