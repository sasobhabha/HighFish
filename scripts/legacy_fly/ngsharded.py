#!/usr/bin/env python3
"""Reader for the neuroglancer "precomputed" sharded uint64 index and
annotation collections.

Implements (from the official neuroglancer documentation):
  src/datasource/precomputed/sharded.md     (shard index + minishard index)
  src/datasource/precomputed/annotations.md (single/multiple annotation encoding)

Format summary (verified against the spec):
- Shard file layout: the first 2**minishard_bits * 16 bytes are the "shard
  index": 2**minishard_bits entries of (uint64le start_offset, uint64le
  end_offset), both RELATIVE TO the end of the shard index. The encoded
  minishard index of minishard m lives in
  [shard_index_end + start, shard_index_end + end).
- Minishard index (decoded, per minishard_index_encoding): 24*n bytes =
  C-order [3, n] uint64le array.
    row0: chunk ids, delta-encoded (cumsum -> absolute id of chunk i)
    row1: data start offsets, delta-encoded relative to end of the previous
          chunk; the first chunk's start is shard_index_end + row1[0]
    row2: size in bytes of chunk i's data
- Annotation shards: the "chunk" key for by_id is the annotation id, and the
  chunk data is the single-annotation encoding:
      LINE type: 6 float32le (two 3-vectors)
      properties in info order (float32, float32, uint32 here)
      padding to multiple of 4
      then, for each relationship: uint32le count + count * uint64le ids
- Related-object index (pre_synaptic_cell / post_synaptic_cell): the chunk key
  is the object (cell) id, and the chunk data is the multiple-annotation
  encoding: uint64le count, then per annotation the geometry+property prefix
  interleaved, then all annotation ids at the end.
"""
from __future__ import annotations

import gzip
import json
import os
import struct
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

U64 = np.dtype("<u8")
U32 = np.dtype("<u4")
F32 = np.dtype("<f4")

REPO_URL = "https://storage.googleapis.com/fish1-public"
REL = "syn_241003_agg241003_reorient_axde_ei_bayes_idx_pre_250410.precomputed"


def http_get_range(url: str, start: int, end: int, retries: int = 3) -> bytes:
    """Byte-range GET with retries (GCS supports Range on public objects)."""
    for attempt in range(retries):
        try:
            import urllib.request

            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end - 1}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001 - retry any transient network failure
            if attempt == retries - 1:
                raise
    return b""


class ShardedIndex:
    """Reads a neuroglancer sharded-layout directory (e.g. by_id/)."""

    def __init__(self, base_url: str, cache_dir: Path, minishard_bits: int,
                 shard_bits: int, index_encoding: str = "gzip"):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.minishard_bits = minishard_bits
        self.shard_bits = shard_bits
        self.index_encoding = index_encoding
        self.n_minishards = 1 << minishard_bits
        self.n_shards = 1 << shard_bits
        self.shard_index_end = self.n_minishards * 16
        pad = max(1, (shard_bits + 3) // 4)
        self.shard_pattern = "{:0%d}.shard" % pad

    def shard_url(self, shard: int) -> str:
        return f"{self.base_url}/{self.shard_pattern.format(shard)}"

    def shard_cache_path(self, shard: int) -> Path:
        return self.cache_dir / self.shard_pattern.format(shard)

    def ensure_shard_cached(self, shard: int, url: str | None = None,
                            expected_size: int | None = None) -> Path:
        """Download the whole shard file once (simplest, robust re-runs)."""
        p = self.shard_cache_path(shard)
        if p.exists() and (expected_size is None or p.stat().st_size == expected_size):
            return p
        url = url or f"{REPO_URL}/{REL}/{self.base_url.rsplit('/', 1)[-1]}/{self.shard_pattern.format(shard)}"
        tmp = p.with_suffix(".part")
        import urllib.request

        urllib.request.urlretrieve(url, tmp)
        tmp.rename(p)
        return p

    # ---------------- generic readers over a local cached shard ---------------
    def read_shard_index(self, buf: bytes) -> np.ndarray:
        arr = np.frombuffer(buf[: self.shard_index_end], dtype="<u8")
        return arr.reshape(self.n_minishards, 2)

    def read_minishard_index(self, buf: bytes, start: int, end: int) -> np.ndarray:
        raw = buf[start:end]
        if self.index_encoding == "gzip":
            raw = gzip.decompress(raw)
        arr = np.frombuffer(raw, dtype="<u8")
        assert arr.size % 3 == 0, "minishard index size must be a multiple of 24 bytes"
        return arr.reshape(-1, 3)  # n rows of (id_delta, start_delta, size)

    def minishard_chunks(self, raw_index_rows: np.ndarray,
                         shard_index_end: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Decode one minishard's rows -> (chunk_ids, start_offsets, sizes)."""
        ids = np.cumsum(raw_index_rows[:, 0], dtype=np.uint64)
        starts = np.cumsum(raw_index_rows[:, 1], dtype=np.uint64)
        starts = starts.astype(np.uint64) + np.uint64(shard_index_end)
        ends = np.zeros_like(starts)
        if len(starts) > 1:
            ends[1:] = starts[:-1]
        sizes = raw_index_rows[:, 2].astype(np.uint64)
        blob_end = starts + sizes
        # start offset of chunk i = shard_index_end + sum(row1[0..i]) + sum(row2[0..i-1])
        starts = starts + ends - ends  # keep dtype stable
        starts = starts + np.concatenate([np.zeros(1, dtype=np.uint64),
                                          np.cumsum(sizes[:-1], dtype=np.uint64)])
        return ids, starts, sizes


def single_annotation_blob(blob: memoryview | bytes, ann_type: str,
                           prop_types: list[tuple[str, str]],
                           relationships: list[str]) -> dict:
    """Decode one single-annotation encoding blob per the annotations spec."""
    off = 0
    geo_dims = {"POINT": 1, "LINE": 2, "AXIS_ALIGNED_BOUNDING_BOX": 2,
                "ELLIPSOID": 2, "POLYLINE": None}[ann_type]
    vals: dict = {}
    if ann_type != "POLYLINE":
        n_floats = geo_dims * 3
        vals["geometry"] = np.frombuffer(blob[: off + 4 * n_floats], dtype=F32).copy().reshape(geo_dims, 3)
        off += 4 * n_floats
    else:
        (npts,) = struct.unpack_from("<I", blob, off)
        off += 4
        vals["geometry"] = np.frombuffer(blob[off: off + 4 * 3 * npts], dtype=F32).copy().reshape(npts, 3)
        off += 4 * 3 * npts
    for pid, ptype in prop_types:
        if ptype in ("rgb", "rgba"):
            k = 3 if ptype == "rgb" else 4
            vals[pid] = np.frombuffer(blob[off: off + k], dtype=np.uint8).copy()
            off += k
        else:
            dt = {"uint8": np.uint8, "int8": np.int8, "uint16": "<u2",
                  "int16": "<i2", "uint32": "<u4", "int32": "<i4",
                  "float32": "<f4"}[ptype]
            dt = np.dtype(dt)
            vals[pid] = np.frombuffer(blob[off: off + dt.itemsize], dtype=dt)[0]
            off += dt.itemsize
    pad = (4 - (off % 4)) % 4
    off += pad
    for rname in relationships:
        # Per the annotations spec, relationship counts are encoded as a
        # 2-byte quantized value (required to be representable in 1 byte,
        # so the high byte is always 0).
        (cnt,) = struct.unpack_from("<H", blob, off)
        off += 2
        vals[rname] = np.frombuffer(blob[off: off + 8 * cnt], dtype=U64).copy()
        off += 8 * cnt
    assert off == len(blob), f"blob decoded {off} bytes but has length {len(blob)}"
    return vals


def multiple_annotation_blob(blob: bytes, ann_type: str,
                             prop_types: list[tuple[str, str]],
                             relationships: list[str]) -> dict:
    """Decode a multiple-annotation encoding blob (related-object index /
    spatial index): count, interleaved geometry+property prefixes, then ids."""
    (count,) = struct.unpack_from("<Q", blob, 0)
    prefix = len(blob) - 8 * count
    geo_dims = {"POINT": 1, "LINE": 2, "AXIS_ALIGNED_BOUNDING_BOX": 2,
                "ELLIPSOID": 2}[ann_type]
    n_floats = geo_dims * 3
    prop_bytes = sum({"uint8": 1, "int8": 1, "uint16": 2, "int16": 2,
                      "uint32": 4, "int32": 4, "float32": 4,
                      "rgb": 3, "rgba": 4}[pt] for _, pt in prop_types)
    # NOTE: prefix grows with per-annotation padding; derive record stride from
    # provided prefix once callers supply consistent layers.
    rec = (4 * n_floats) + prop_bytes + ((4 - ((4 * n_floats + prop_bytes) % 4)) % 4)
    payload = np.frombuffer(blob[8: prefix + (count - 1) * rec], dtype=np.uint8)
    m = payload.reshape(count, rec)
    out = {"count": count,
           "geometry": m[:, : 4 * n_floats].tobytes(),  # caller views as f32
           "props_off": 4 * n_floats, "rec": rec}
    ids = np.frombuffer(blob[prefix: prefix + 8 * count], dtype=U64)
    out["ids"] = ids
    return out


def fetch_single_annotations_shard_index(shard_file: Path,
                                         minishard_bits: int) -> np.ndarray:
    """Read the shard index table from a locally cached single shard file."""
    size = (1 << minishard_bits) * 16
    with open(shard_file, "rb") as f:
        buf = f.read(size)
    return np.frombuffer(buf, dtype="<u8").reshape(1 << minishard_bits, 2)


def iter_minishard_annotations(shard_buf: bytes, shard_index_end: int,
                               start: int, end: int, index_encoding: str):
    """Yield (ids, starts, sizes, data_region_bytes) for one minishard."""
    raw = shard_buf[start:end]
    if index_encoding == "gzip":
        raw = gzip.decompress(raw)
    rows = np.frombuffer(raw, dtype="<u8").reshape(-1, 3)
    n = rows.shape[0]
    if n == 0:
        return
    ids = np.cumsum(rows[:, 0], dtype=np.uint64)
    starts = np.cumsum(rows[:, 1].astype(np.uint64), dtype=np.uint64) + np.uint64(shard_index_end)
    sizes = rows[:, 2].astype(np.uint64)
    back = starts + sizes  # inclusive end of each blob
    data_lo = int(starts[0])
    data_hi = int(back[-1])
    data = shard_buf[data_lo:data_hi]
    rel_starts = starts - np.uint64(data_lo)
    return ids, rel_starts, sizes, data
