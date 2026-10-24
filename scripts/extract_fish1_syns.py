#!/usr/bin/env python3
"""Decode the Fish1 (Petkova et al. 2025, fish1-public) synapse annotations.

Layer: gs://fish1-public/syn_241003_agg241003_reorient_axde_ei_bayes_idx_pre_250410.precomputed
(annotation LINE records; official neuroglancer "precomputed" sharded format).

Verified record layout (all records validated; each blob = one gzipped record):
  [0, 24)   geometry: 6 x float32 - two 3D points (pre-site -> post-site), voxels
  [24, 28)  pre_synaptic_confidence: float32 (signed bayes score, [-1, 1])
  [28, 32)  post_synaptic_confidence: float32
  [32, 36)  type: uint32       (polarity class code; {1, 2} observed)
  [36, ...) 4 relationships in info order, each: uint32 count + count x u64 ids
            pre_synaptic_cell, pre_synaptic_site, post_synaptic_cell, post_synaptic_site

Outputs (data/zebrafish/fish1/syn_arrays/):
  syn_{0..7}.npz: ann_id, pre_cell, post_cell, type(u8), pre_conf, post_conf
  polarity_check.json: outgoing-synapse `type` distribution restricted to the
                  CLEM ground-truth vglut2a(+) vs gad1b(+) neurons from the
                  official evaluation neuroglancer state.
"""
from __future__ import annotations

import gzip
import json
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import numpy as np

BASE = Path("data/zebrafish/fish1")
CACHE = BASE / "cache" / "by_id"
OUT = BASE / "syn_arrays"
OUT.mkdir(parents=True, exist_ok=True)

IDX_END = 4096 * 16  # minishard index: shard index = [4096, 2] u64 pairs (start, end)

_SHARD_BUF: dict[int, tuple[bytes, np.ndarray]] = {}


def decode_record(d: bytes):
    """Parse one LINE annotation record by walking the relationship sections
    sequentially (count u32 + count x u64 ids each) until the blob is consumed."""
    geom = np.frombuffer(d, "<f4", count=6, offset=0).reshape(2, 3)
    pre_conf, post_conf = np.frombuffer(d, "<f4", count=2, offset=24)
    (t,) = np.frombuffer(d, "<u4", count=1, offset=32)
    off = 36
    ids_all = []
    for _ in range(4):  # info order: pre_cell, pre_site, post_cell, post_site
        (c,) = np.frombuffer(d, "<u4", count=1, offset=off)
        off += 4
        ids_all.append(np.frombuffer(d, "<u8", count=int(c), offset=off) if c
                       else np.zeros(0, dtype=np.uint64))
        off += 8 * int(c)
    if off != len(d):
        raise ValueError(f"record not fully consumed: off={off} len={len(d)}")
    pre_cell_r, _pre_site_r, post_cell_r, _post_site_r = ids_all
    if len(pre_cell_r) == 0 or len(post_cell_r) == 0:
        return None  # synapse not assigned to both agglo cells: skip
    pre_site = np.rint(geom[0]).astype(np.int32)
    post_site = np.rint(geom[1]).astype(np.int32)
    return int(pre_cell_r[0]), int(post_cell_r[0]), int(t), float(pre_conf), float(post_conf), pre_site, post_site


def worker(task):
    """Decode one (shard, minishard) unit; returns numpy arrays over its records."""
    s, m = task
    if s not in _SHARD_BUF:
        buf = open(CACHE / f"{s}.shard", "rb").read()
        idx = np.frombuffer(buf[:IDX_END], dtype="<u8").reshape((4096, 2))
        _SHARD_BUF[s] = (buf, idx)
    buf, idx = _SHARD_BUF[s]
    a, b = int(idx[m, 0]), int(idx[m, 1])
    if a == b:
        return (np.zeros(0, np.uint64), np.zeros(0, np.uint64), np.zeros(0, np.uint64),
                np.zeros(0, np.uint8), np.zeros(0, np.float32), np.zeros(0, np.float32),
                np.zeros((0, 3), np.int32), np.zeros((0, 3), np.int32))
    rows = np.frombuffer(gzip.decompress(buf[IDX_END + a: IDX_END + b]), "<u8").reshape(3, -1)
    n = rows.shape[1]
    ids = np.cumsum(rows[0], dtype=np.uint64)
    starts = np.cumsum(rows[1], dtype=np.uint64) + np.uint64(IDX_END) + np.concatenate(
        [np.zeros(1, np.uint64), np.cumsum(rows[2][:-1], dtype=np.uint64)])
    sizes = rows[2]
    keep, rec_pre, rec_post, rec_t, rec_pc, rec_cc = [], [], [], [], [], []
    rec_pre_site, rec_post_site = [], []
    for i in range(n):
        d = gzip.decompress(buf[starts[i]: starts[i] + sizes[i]])
        rec = decode_record(d)
        if rec is None:
            continue
        pre, post, t, pc, cc, pre_site, post_site = rec
        keep.append(i); rec_pre.append(pre); rec_post.append(post)
        rec_t.append(t); rec_pc.append(pc); rec_cc.append(cc)
        rec_pre_site.append(pre_site); rec_post_site.append(post_site)
    return (np.array(ids[keep], dtype=np.uint64),
            np.array(rec_pre, dtype=np.uint64),
            np.array(rec_post, dtype=np.uint64),
            np.array(rec_t, dtype=np.uint8),
            np.array(rec_pc, dtype=np.float32),
            np.array(rec_cc, dtype=np.float32),
            np.array(rec_pre_site, dtype=np.int32),
            np.array(rec_post_site, dtype=np.int32))


def main() -> None:
    t0 = time.time()
    # Ground truth ids (official evaluation state) for the polarity spot-check.
    gt = json.load(open(BASE / "ground_truth_segments.json"))
    exc = {int(x) for x in gt["excitatory_cells_predicted_as_excitatory"]}
    inh = {int(x) for x in gt["inhibitory_cells_predicted_as_inhibitory"]}
    tally = {"exc_out": Counter(), "inh_out": Counter(), "exc_n": 0, "inh_n": 0}

    tasks = [(s, m) for s in range(8) for m in range(4096)]
    total = 0
    # ordered imap: results arrive in shard order -> accumulate per shard once
    cur_s = -1
    buf_c = {k: [] for k in ("ann", "pre", "post", "t", "pc", "cc",
                             "pre_site", "post_site")}

    def flush(shard):
        nonlocal total
        if not buf_c["ann"]:
            return
        def _cat(k):
            parts = [a for a in buf_c[k] if a.size]
            return np.concatenate(parts) if parts else np.zeros(0, np.uint8)
        n_recs = len(_cat("ann"))
        np.savez_compressed(
            OUT / f"syn_{shard}.npz",
            ann_id=_cat("ann").astype(np.uint64),
            pre_cell=_cat("pre").astype(np.uint64),
            post_cell=_cat("post").astype(np.uint64),
            type=_cat("t").astype(np.uint8),
            pre_conf=_cat("pc").astype(np.float32),
            post_conf=_cat("cc").astype(np.float32),
            pre_site=_cat("pre_site").astype(np.int32).reshape(-1, 3),
            post_site=_cat("post_site").astype(np.int32).reshape(-1, 3),
        )
        total += n_recs
        print(f"shard {shard}: cumulative {total:,} synapses ({time.time()-t0:.0f}s)", flush=True)

    with Pool(processes=8) as pool:
        for (s, _m), (ann_ids, pre, post, tt, pc, cc, pre_site, post_site) in zip(tasks, pool.imap(worker, tasks, chunksize=16)):
            if s != cur_s:
                flush(cur_s)
                cur_s = s
                buf_c = {k: [] for k in buf_c}
            buf_c["ann"].append(ann_ids); buf_c["pre"].append(pre)
            buf_c["post"].append(post); buf_c["t"].append(tt)
            buf_c["pc"].append(pc); buf_c["cc"].append(cc)
            buf_c["pre_site"].append(pre_site); buf_c["post_site"].append(post_site)
            if len(exc):
                mask = np.isin(pre, np.array(sorted(exc), dtype=np.uint64))
                if mask.any():
                    u, c = np.unique(tt[mask], return_counts=True)
                    for u_, c_ in zip(u.tolist(), c.tolist()):
                        tally["exc_out"][u_] += c_
                    tally["exc_n"] += int(mask.sum())
                mask = np.isin(pre, np.array(sorted(inh), dtype=np.uint64))
                if mask.any():
                    u, c = np.unique(tt[mask], return_counts=True)
                    for u_, c_ in zip(u.tolist(), c.tolist()):
                        tally["inh_out"][u_] += c_
                    tally["inh_n"] += int(mask.sum())
    flush(cur_s)

    checks = {
        "total_synapses": total,
        "exc_gt_cells": len(exc),
        "inh_gt_cells": len(inh),
        "exc_out_type_distribution": {str(k): v for k, v in sorted(tally["exc_out"].items())},
        "inh_out_type_distribution": {str(k): v for k, v in sorted(tally["inh_out"].items())},
        "exc_n": tally["exc_n"], "inh_n": tally["inh_n"],
    }
    json.dump(checks, open(BASE / "polarity_check.json", "w"), indent=1)
    print(json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()
