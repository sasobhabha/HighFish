#!/usr/bin/env python3
"""Parse the FlyWire Codex v783 CSVs into simulation-ready artifacts.

Outputs (data/processed/):
- neurons.parquet        one row per neuron: root_id, group, nt_type, scores, class info
- adj_total.npz          sparse csr: summed synapse counts per (pre, post) edge
- adj_{ACH,GABA,GLUT,...}.npz  sparse csr per neurotransmitter (edge-level dominant NT)
- meta.json              counts, provenance, column provenance

Everything is derived from the downloaded codex files.
Root IDs preserved exactly as FlyWire root_ids (int64).
"""
import gzip
import csv
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path("data/flywire/783")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

NEURON_COLS = None
N_ROWS_NEURONS = 0
N_ROWS_CONN = 0
N_ROWS_CLASS = 0
N_ROWS_TYPES = 0


def read_gz_csv(name):
    with gzip.open(ROOT / f"{name}.csv.gz", "rt", newline="") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        for row in rdr:
            yield header, row


def main():
    global N_ROWS_NEURONS, N_ROWS_CONN, N_ROWS_CLASS, N_ROWS_TYPES
    t0 = time.time()

    # ---- neurons ----
    neuron_ids = []
    nt_type = []
    nt_score = []
    nt_avgs = {k: [] for k in ("da", "ser", "gaba", "glut", "ach", "oct")}
    group = []
    header = None
    for header, row in read_gz_csv("neurons"):
        N_ROWS_NEURONS += 1
        d = dict(zip(header, row))
        neuron_ids.append(int(d["root_id"]))
        nt_type.append(d["nt_type"])
        nt_score.append(float(d["nt_type_score"]))
        for k in nt_avgs:
            nt_avgs[k].append(float(d[f"{k}_avg"]))
        group.append(d["group"])
    neuron_ids = np.array(neuron_ids, dtype=np.int64)
    idx_of = {rid: i for i, rid in enumerate(neuron_ids.tolist())}
    print(f"neurons: {len(neuron_ids)} rows")

    # ---- classification ----
    flow = {}
    super_class = {}
    klass = {}
    sub_class = {}
    hemilineage = {}
    side = {}
    nerve = {}
    for header, row in read_gz_csv("classification"):
        N_ROWS_CLASS += 1
        d = dict(zip(header, row))
        rid = int(d["root_id"])
        flow[rid] = d["flow"]
        super_class[rid] = d["super_class"]
        klass[rid] = d["class"]
        sub_class[rid] = d["sub_class"]
        hemilineage[rid] = d["hemilineage"]
        side[rid] = d["side"]
        nerve[rid] = d["nerve"]
    print(f"classification: {N_ROWS_CLASS} rows")

    # ---- consolidated cell types ----
    primary_type = {}
    for header, row in read_gz_csv("consolidated_cell_types"):
        N_ROWS_TYPES += 1
        d = dict(zip(header, row))
        primary_type[int(d["root_id"])] = d["primary_type"]
    print(f"cell types: {N_ROWS_TYPES} rows")

    # ---- connections -> sparse adjacency ----
    rows, cols, vals = [], [], []
    nt_counter = Counter()
    conn_nt = {"ACH": [], "GABA": [], "GLUT": [], "DA": [], "SER": [], "OCT": []}
    missing = 0
    for header, row in read_gz_csv("connections"):
        N_ROWS_CONN += 1
        d = dict(zip(header, row))
        pre = int(d["pre_root_id"])
        post = int(d["post_root_id"])
        n = int(d["syn_count"])
        nt = d["nt_type"]
        nt_counter[nt] += 1
        i = idx_of.get(pre)
        j = idx_of.get(post)
        if i is None or j is None:
            missing += 1
            continue
        rows.append(i)
        cols.append(j)
        vals.append(n)
        if nt in conn_nt:
            conn_nt[nt].append((i, j, n))
    print(f"connections: {N_ROWS_CONN} rows (missing endpoints: {missing})")

    adj = sp.csr_matrix(
        (np.array(vals, dtype=np.float32), (np.array(rows), np.array(cols))),
        shape=(len(neuron_ids), len(neuron_ids)),
    )
    adj.sum_duplicates()
    sp.save_npz(OUT / "adj_total.npz", adj)

    for nt, triples in conn_nt.items():
        if not triples:
            continue
        r, c, v = zip(*triples)
        m = sp.csr_matrix(
            (np.array(v, dtype=np.float32), (np.array(r), np.array(c))),
            shape=(len(neuron_ids), len(neuron_ids)),
        )
        m.sum_duplicates()
        sp.save_npz(OUT / f"adj_{nt}.npz", m)

    # ---- neurons table ----
    import pandas as pd

    df = pd.DataFrame(
        {
            "root_id": neuron_ids,
            "group": group,
            "nt_type": nt_type,
            "nt_type_score": nt_score,
            **{f"{k}_avg": np.array(v) for k, v in nt_avgs.items()},
            "flow": [flow.get(r, "") for r in neuron_ids.tolist()],
            "super_class": [super_class.get(r, "") for r in neuron_ids.tolist()],
            "class": [klass.get(r, "") for r in neuron_ids.tolist()],
            "sub_class": [sub_class.get(r, "") for r in neuron_ids.tolist()],
            "hemilineage": [hemilineage.get(r, "") for r in neuron_ids.tolist()],
            "side": [side.get(r, "") for r in neuron_ids.tolist()],
            "nerve": [nerve.get(r, "") for r in neuron_ids.tolist()],
            "primary_type": [primary_type.get(r, "") for r in neuron_ids.tolist()],
        }
    )
    df.to_parquet(OUT / "neurons.parquet", index=False)
    df.to_csv(OUT / "neurons.csv", index=False)

    meta = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "FlyWire Codex bulk data, snapshot 783 (Oct 2023)",
        "source_url": "https://codex.flywire.ai/api/download?dataset=fafb",
        "storage_template": "https://storage.googleapis.com/flywire-data/codex/data/fafb/783/",
        "n_neurons": len(neuron_ids),
        "n_edges_total_synapses": int(adj.sum()),
        "n_edges": int(adj.nnz),
        "edge_nt_distribution": dict(nt_counter),
        "classification_rows": N_ROWS_CLASS,
        "cell_type_rows": N_ROWS_TYPES,
        "missing_edge_endpoints": missing,
        "super_class_counts": df["super_class"].value_counts().to_dict(),
        "nt_type_counts": df["nt_type"].value_counts().to_dict(),
        "cite": [
            "Matsliah et al. 2024 Nature 632, https://www.nature.com/articles/s41586-024-07981-1",
            "Dorkenwald et al. 2023/2024 FlyWire whole-brain connectome",
            "codex.flywire.ai (Princeton Neuroscience Institute)",
        ],
    }
    with open(OUT / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2)[:1500])
    print(f"done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
