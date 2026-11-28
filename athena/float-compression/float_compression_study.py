"""Measure what mantissa truncation and byte shuffling do to the compressed size
of the float32 columns of an ATLAS DAOD_PHYSLITE file.

Usage: python float_compression_study.py <file.root> [max_entries]
"""
import sys
import zlib
import lzma
import collections

import numpy as np
import uproot
import zstandard


def truncate_round(a: np.ndarray, mantissa_bits: int) -> np.ndarray:
    """Replicate CxxUtils::FloatCompressor: round to nearest, then mask."""
    if mantissa_bits >= 23:
        return a
    i = a.view(np.uint32).copy()
    finite = np.isfinite(a)
    drop = 23 - mantissa_bits
    rounding = np.uint32(1 << (drop - 1))
    mask = np.uint32(~((1 << drop) - 1) & 0xFFFFFFFF)
    vmax = np.uint32((0x7F7 << 20) | (0x000FFFFF ^ int(rounding)))
    ok = finite & ((i & np.uint32(0x7FFFFFFF)) < vmax)
    i[ok] += rounding
    i[finite] &= mask
    return i.view(np.float32)


def byte_shuffle(a: np.ndarray) -> bytes:
    """RNTuple split encoding: all first bytes, then all second bytes, ..."""
    b = np.ascontiguousarray(a).view(np.uint8).reshape(-1, a.dtype.itemsize)
    return b.T.tobytes()


def sizes(raw: bytes, comps) -> dict:
    return {name: len(fn(raw)) for name, fn in comps.items()}


def main():
    path = sys.argv[1]
    max_entries = int(sys.argv[2]) if len(sys.argv) > 2 else None

    f = uproot.open(path)
    tree = f["CollectionTree"]
    n = tree.num_entries if max_entries is None else min(max_entries, tree.num_entries)
    print(f"file: {path}")
    print(f"entries: {tree.num_entries}, used: {n}")
    print(f"file compression: {f.file.compression}")

    # 1. Bookkeeping of on-disk size per element type, from the basket metadata.
    bytype = collections.defaultdict(lambda: [0, 0, 0])
    for b in tree.branches:
        for leaf in [b] if not b.branches else b.branches:
            key = str(leaf.interpretation)
            bytype[key][0] += leaf.compressed_bytes
            bytype[key][1] += leaf.uncompressed_bytes
            bytype[key][2] += 1
    tot_c = sum(v[0] for v in bytype.values())
    print("\n== on-disk size per branch interpretation (top 15 by compressed bytes)")
    print(f"{'interpretation':70s} {'n':>5s} {'comp MB':>9s} {'uncomp MB':>10s} {'share':>6s}")
    for key, (c, u, k) in sorted(bytype.items(), key=lambda kv: -kv[1][0])[:15]:
        print(f"{key[:70]:70s} {k:5d} {c/1e6:9.2f} {u/1e6:10.2f} {100*c/tot_c:5.1f}%")

    # Float share.
    float_c = sum(v[0] for k, v in bytype.items() if "float32" in k or ">f4" in k)
    print(f"\nfloat32 branches: {100*float_c/tot_c:.1f}% of compressed CollectionTree bytes")

    # 2. Read every float32 column and test encodings.
    zstd5 = zstandard.ZstdCompressor(level=5)
    zstd9 = zstandard.ZstdCompressor(level=9)
    comps = {
        "zstd5": zstd5.compress,
        "zstd9": zstd9.compress,
        "lzma1": lambda b: lzma.compress(b, preset=1),
        "zlib1": lambda b: zlib.compress(b, 1),
    }
    variants = [("full", 23), ("m15", 15), ("m12", 12), ("m10", 10), ("m7", 7)]

    total = collections.defaultdict(int)
    nvalues = 0
    nbranches = 0
    per_branch = []
    for b in tree.branches:
        leaves = [b] if not b.branches else b.branches
        for leaf in leaves:
            interp = str(leaf.interpretation)
            if "float32" not in interp and ">f4" not in interp:
                continue
            try:
                arr = leaf.array(entry_stop=n, library="np")
            except Exception as e:  # noqa: BLE001
                continue
            if arr.dtype == object:
                try:
                    arr = np.concatenate([np.asarray(x, dtype=np.float32).ravel() for x in arr if len(np.atleast_1d(x))])
                except Exception:  # noqa: BLE001
                    continue
            arr = np.asarray(arr).astype(np.float32, copy=False).ravel()
            if arr.size == 0:
                continue
            nbranches += 1
            nvalues += arr.size
            raw_len = arr.nbytes
            total["raw"] += raw_len
            row = {"name": leaf.name, "n": arr.size}
            for vname, bits in variants:
                t = truncate_round(arr, bits)
                plain = t.tobytes()
                shuf = byte_shuffle(t)
                for cname, fn in comps.items():
                    k1 = f"{vname}/plain/{cname}"
                    k2 = f"{vname}/shuffle/{cname}"
                    s1 = len(fn(plain))
                    s2 = len(fn(shuf))
                    total[k1] += s1
                    total[k2] += s2
                    if vname == "full" and cname == "zstd5":
                        row["plain"] = s1
                        row["shuffle"] = s2
                    if vname == "m7" and cname == "zstd5":
                        row["m7shuffle"] = s2
            per_branch.append(row)

    print(f"\n== float32 columns: {nbranches} branches, {nvalues} values, raw {total['raw']/1e6:.1f} MB")
    print("compressed size relative to raw float32 bytes (lower is better)")
    print(f"{'variant':10s} {'encoding':8s} " + " ".join(f"{c:>8s}" for c in comps))
    for vname, _ in variants:
        for enc in ("plain", "shuffle"):
            vals = [total[f"{vname}/{enc}/{c}"] / total["raw"] for c in comps]
            print(f"{vname:10s} {enc:8s} " + " ".join(f"{v:8.3f}" for v in vals))

    print("\n== largest float branches (zstd5 bytes): plain full, shuffled full, shuffled 7-bit mantissa")
    per_branch.sort(key=lambda r: -r.get("plain", 0))
    for r in per_branch[:20]:
        print(f"{r['name'][:60]:60s} {r['n']:>10d} {r['plain']/1e3:9.1f}k {r['shuffle']/1e3:9.1f}k {r['m7shuffle']/1e3:9.1f}k")


if __name__ == "__main__":
    main()
