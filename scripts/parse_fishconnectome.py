#!/usr/bin/env python3
"""Parse the Fish1 (Petkova et al. 2025) decoded synapse arrays into
simulation-ready artifacts.

Outputs (data/processed/):
- neurons.parquet        one row per agglo cell: cell_id, synapse/degree stats,
                         nt_pred (E/I from outgoing polarity-type majority),
                         ap_norm (anterior->posterior position of the cell's
                         outgoing synapses), roi flags (hindbrain)
- adj_total.npz          sparse csr: summed synapse counts per (pre, post) edge
- adj_E.npz              same, restricted to the layer's E/I `type`==2 edges
                         (verified excitatory: CLEM vglut2a cells emit type 2)
- adj_I.npz              same, restricted to `type`==1 edges (verified
                         inhibitory: CLEM gad1b cells emit type 1)
                         each E/I edge weight is count x mean signed confidence
                         (normalized to (0, 1]; see meta.json)
- meta.json              counts, provenance, E/I semantics

E/I semantics (NOT guessed - verified from the official evaluation ground
truth, data/zebrafish/fish1/polarity_check.json):
  - outgoing synapses of the 244 CLEM-confirmed vglut2a (glutamatergic)
    neurons: 79% type 2, 21% type 1
  - outgoing synapses of the 141 CLEM-confirmed gad1b (GABAergic) neurons:
    82% type 1, 18% type 2
  => type 2 = excitatory bayes class, type 1 = inhibitory bayes class.
  The signed pre_synaptic_confidence gives per-synapse E/I strength.
"""
import json
import os
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path("data/zebrafish/fish1")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# cells with fewer total synapse events are dropped from the graph.
# (Raw agglo space has 13.4M fragment ids; a higher threshold keeps neurons
# that participate meaningfully and keeps the graph dense enough to
# propagate drive. Override with FISH_MIN_SYN env var for experiments.)
MIN_SYN_TOTAL = int(os.environ.get("FISH_MIN_SYN", 100))
E_CODE = 2          # verified excitatory class
I_CODE = 1          # verified inhibitory class


def main() -> None:
    t0 = time.time()
    shards = [np.load(ROOT / "syn_arrays" / f"syn_{s}.npz") for s in range(8)]

    cell_ids = np.unique(np.concatenate(
        [np.concatenate([d["pre_cell"], d["post_cell"]]) for d in shards]))
    n_cells = len(cell_ids)
    print(f"cells: {n_cells:,}")

    # ---- accumulate edges and per-cell stats shard by shard ----
    in_tot = np.zeros(n_cells, np.int32)
    in_E, in_I = np.zeros(n_cells, np.int32), np.zeros(n_cells, np.int32)
    out_tot = np.zeros(n_cells, np.int32)
    out_E, out_I = np.zeros(n_cells, np.int32), np.zeros(n_cells, np.int32)
    out_Econf, out_Iconf = np.zeros(n_cells, np.float64), np.zeros(n_cells, np.float64)
    ap_sum = np.zeros(n_cells, np.float64)      # posterior position accumulator
    lr_sum = np.zeros(n_cells, np.float64)      # lateral position accumulator
    edges = []                                   # (pre_idx, post_idx, count)

    for d in shards:
        pre, post, typ = d["pre_cell"], d["post_cell"], d["type"]
        pc, cc = d["pre_conf"], d["post_conf"]
        sites = d["post_site"]

        pre_i = np.searchsorted(cell_ids, pre).astype(np.int32)
        post_i = np.searchsorted(cell_ids, post).astype(np.int32)
        is_E = (typ == E_CODE)
        is_I = (typ == I_CODE)

        np.add.at(out_tot, pre_i, 1)
        np.add.at(in_tot, post_i, 1)
        np.add.at(out_E, pre_i[is_E], 1); np.add.at(in_E, post_i[is_E], 1)
        np.add.at(out_I, pre_i[is_I], 1); np.add.at(in_I, post_i[is_I], 1)
        np.add.at(out_Econf, pre_i[is_E], pc[is_E].astype(np.float64))
        np.add.at(out_Iconf, pre_i[is_I], pc[is_I].astype(np.float64))
        np.add.at(ap_sum, pre_i, sites[:, 0].astype(np.float64))
        np.add.at(lr_sum, pre_i, sites[:, 1].astype(np.float64))
        np.add.at(lr_sum, pre_i, sites[:, 1].astype(np.float64))

        # coalesced edge counts for this shard
        key = pre_i.astype(np.int64) * n_cells + post_i
        uk, inv = np.unique(key, return_inverse=True)
        counts = np.bincount(inv, minlength=len(uk)).astype(np.int32)
        edges.append((uk // n_cells, uk % n_cells, counts))
    print(f"edges accumulated ({time.time()-t0:.0f}s)")

    rows = np.concatenate([e[0] for e in edges]).astype(np.int32)
    cols = np.concatenate([e[1] for e in edges]).astype(np.int32)
    vals = np.concatenate([e[2] for e in edges])
    del edges
    adj_total = sp.csr_matrix((vals.astype(np.float32), (rows, cols)),
                              shape=(n_cells, n_cells))
    adj_total.sum_duplicates()
    adj_total.data = np.log1p(adj_total.data).astype(np.float32)
    print(f"adj_total: {adj_total.nnz:,} edges (log1p weights)")

    # ---- E/I adjacencies: edges with dominant polarity class ----
    # edge polarity = sum over synapses of signed E-bayes strength:
    #   type==2 contributes +|conf|, type==1 contributes -|conf|
    # (Exactly one class per synapse; confidence sign is the bayes score.)
    # We re-derive edge polarity from the shard accumulators lazily instead.

    # Rebuild E/I edge sums by a second streaming pass over the shards,
    # accumulating per-edge E count and I count in a dict-free way:
    out_frac_E = np.where(out_tot > 0, out_E / np.maximum(out_tot, 1), 0.0)
    nt_pred = np.where(out_tot == 0, "unknown",
                       np.where(out_frac_E >= 0.5, "excitatory", "inhibitory"))
    nt_score = np.abs(np.where(out_tot > 0,
                               (out_Econf - out_Iconf) / np.maximum(out_tot, 1), 0.0))
    ap_norm = np.where(out_tot > 0, ap_sum / np.maximum(out_tot, 1), 0.0)
    ap_norm = ap_norm / max(ap_norm.max(), 1.0)  # 0=anterior, 1=posterior
    lr_raw = np.where(out_tot > 0, lr_sum / np.maximum(out_tot, 1), 0.0)
    lr_mid = float(np.median(lr_raw[out_tot > 0]))
    lr_norm = (lr_raw - lr_mid) / max(np.abs(lr_raw[out_tot > 0] - lr_mid).max(), 1.0)
    # lr_norm: -1 = left, +1 = right (sign of layer y-axis; documented in meta.json)
    lr_raw = np.where(out_tot > 0, lr_sum / np.maximum(out_tot, 1), 0.0)
    lr_mid = y_mid if (y_mid := float(np.median(lr_raw[out_tot > 0]))) else 0.0
    lr_norm = (lr_raw - lr_mid) / max(np.abs(lr_raw[out_tot > 0] - lr_mid).max(), 1.0)
    # lr_norm: -1 = left, +1 = right (sign of layer y-axis; documented in meta.json)

    keep = out_tot + in_tot >= MIN_SYN_TOTAL
    print(f"cells kept (>= {MIN_SYN_TOTAL} synapse events): {keep.sum():,} of {n_cells:,}")

    # remap adjacency onto kept cells
    old2new = -np.ones(n_cells, np.int32)
    old2new[keep] = np.arange(int(keep.sum()), dtype=np.int32)
    keep_rows, keep_cols, keep_vals = [], [], []
    kmask = keep[rows] & keep[cols]
    keep_rows = old2new[rows[kmask]]
    keep_cols = old2new[cols[kmask]]
    keep_vals = vals[kmask]
    nk = int(keep.sum())
    adj_total = sp.csr_matrix((keep_vals.astype(np.float32), (keep_rows, keep_cols)),
                              shape=(nk, nk))
    adj_total.sum_duplicates()

    # ---- polarity-weighted E/I adjacency ----
    # second streaming pass for edge-level E/I counts
    rowsE, colsE, valsE, rowsI, colsI, valsI = [], [], [], [], [], []
    for s_i, d in enumerate(shards):
        pre, post, typ, pc = d["pre_cell"], d["post_cell"], d["type"], d["pre_conf"]
        pre_i = np.searchsorted(cell_ids, pre).astype(np.int32)
        post_i = np.searchsorted(cell_ids, post).astype(np.int32)
        ok = keep[pre_i] & keep[post_i]
        pre_i, post_i, typ, pc = pre_i[ok], post_i[ok], typ[ok], pc[ok]
        mE = typ == E_CODE
        mI = typ == I_CODE
        key = old2new[pre_i].astype(np.int64) * np.int64(nk) + old2new[post_i].astype(np.int64)
        for m, rlist, clist, vlist in ((mE, rowsE, colsE, valsE), (mI, rowsI, colsI, valsI)):
            if not m.any():
                continue
            km = key[m]
            uk, inv = np.unique(km, return_inverse=True)
            cnt = np.bincount(inv, minlength=len(uk)).astype(np.int32)
            w = ((pc[m].astype(np.float32) + 1.0) / 2.0)  # signed bayes -> (0,1]
            # edge weight = count * mean confidence for that class
            wm = np.zeros(len(uk), np.float32)
            ssum = np.zeros(len(uk), np.float32)
            np.add.at(ssum, inv, w)
            wm = cnt * (ssum / cnt)
            rlist.append((uk // nk).astype(np.int32))
            clist.append((uk % nk).astype(np.int32))
            vlist.append(wm)
    rr = np.concatenate(rowsE); cc_ = np.concatenate(colsE); vv = np.concatenate(valsE)
    adj_E = sp.csr_matrix((vv, (rr, cc_)), shape=(nk, nk)); adj_E.sum_duplicates()
    rr = np.concatenate(rowsI); cc_ = np.concatenate(colsI); vv = np.concatenate(valsI)
    adj_I = sp.csr_matrix((vv, (rr, cc_)), shape=(nk, nk)); adj_I.sum_duplicates()
    print(f"adj_E nnz {adj_E.nnz:,} | adj_I nnz {adj_I.nnz:,} ({time.time()-t0:.0f}s)")

    sp.save_npz(OUT / "adj_total.npz", adj_total)
    sp.save_npz(OUT / "adj_E.npz", adj_E)
    sp.save_npz(OUT / "adj_I.npz", adj_I)
    del rows, cols, vals, keep_rows, keep_cols, keep_vals

    # ---- neurons.parquet ----
    new_ids = cell_ids[keep]
    import pandas as pd
    df = pd.DataFrame({
        "cell_id": new_ids,
        "n_syn": out_tot[keep] + in_tot[keep],
        "n_out_syn": out_tot[keep],
        "n_in_syn": in_tot[keep],
        "n_out_E": out_E[keep],
        "n_out_I": out_I[keep],
        "n_in_E": in_E[keep],
        "n_in_I": in_I[keep],
        "nt_pred": nt_pred[keep],
        "nt_score": nt_score[keep].astype(np.float32),
        "frac_out_E": out_frac_E[keep].astype(np.float32),
        "ap_norm": ap_norm[keep].astype(np.float32),
        "lr_norm": lr_norm[keep].astype(np.float32),
        "roi": np.where(ap_norm[keep] >= 0.5, "hindbrain",
                        np.where(ap_norm[keep] <= 0.15, "anterior", "central")),
    })
    df.to_parquet(OUT / "neurons.parquet", index=False)

    pol = json.load(open(ROOT / "polarity_check.json"))
    meta = {
        "dataset": "Fish1 (Petkova et al. 2025) larval zebrafish EM connectome, agglo v2a",
        "annotation_layer": "syn_241003_agg241003_reorient_axde_ei_bayes_idx_pre_250410",
        "n_cells": int(nk),
        "n_cells_raw": int(n_cells),
        "n_synapses": int(sum(len(d["ann_id"]) for d in shards)),
        "n_edges_total": int(adj_total.nnz),
        "n_edges_E": int(adj_E.nnz),
        "n_edges_I": int(adj_I.nnz),
        "min_syn_total_kept": MIN_SYN_TOTAL,
        "ei_semantics": {
            "type2": "excitatory", "type1": "inhibitory",
            "verification": pol,
        },
        "voxel_scale_nm": [8.0, 8.0, 30.0],
        "axis_semantics": {
            "ap_norm": "0 = anterior, 1 = posterior (outgoing-synapse mean x voxels normalized)",
            "lr_norm": "-1 = left, +1 = right (outgoing-synapse median y sign convention)",
            "roi": "anterior (ap<=0.15), central (0.15<ap<0.5), hindbrain (ap>=0.5; posterior half)",
        },
        "predecessor": "scripts/extract_fish1_syns.py -> scripts/parse_fishconnectome.py",
    }
    json.dump(meta, open(OUT / "meta.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k != "ei_semantics"}, indent=1))
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
