#!/usr/bin/env python3
"""Fill only empty bins of the known ODD cylindrical Be pipe, using its physical slab."""
import argparse, hashlib, json
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import uproot
from uproot.writing.identify import to_TH2x

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--input", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--constants", type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
be = json.loads(a.constants.read_text())
assert abs(be["density_g_cm3"] - 1.848) < 1e-9
assert abs(be["A"] - 9.01218) < 1e-6
assert be["Z"] == 4
odd = a.input.parent.parent
xml = odd / "xml/OpenDataDetectorEnvelopes.xml"
constants = {
    e.attrib["name"]: e.attrib["value"] for e in ET.parse(xml).iter("constant")
}


def length(value):
    number, unit = value.split("*")
    return float(number) * {"mm": 1, "m": 1000}[unit.strip()]


assert length(constants["bp_rmin"]) == 23.6
assert length(constants["bp_rmax"]) == 24.4
assert length(constants["bp_length"]) == 4000
prefix = "SurfaceMaterial_vol2_bou0_lay2_app0_sen0/"
f = uproot.open(a.input)
t = f[prefix + "t"].values()
mask = t == 0
assert t.shape == (144, 10)
assert np.all(mask[:, :4]) and np.all(mask[:, 6:]) and not np.any(mask[:, 4:6])
for key in ["x0", "l0", "A", "Z", "rho"]:
    assert np.all(f[prefix + key].values()[mask] == 0)
assert np.allclose(f[prefix + "min"].values(), [-np.pi, -4001])
assert np.allclose(f[prefix + "max"].values(), [np.pi, 4001])
# Physical cylinder: r=23.6..24.4 mm, |z| <=4000 mm, from ODD XML.
z = np.linspace(-4001, 4001, 11)
overlap = np.maximum(0, np.minimum(z[1:], 4000) - np.maximum(z[:-1], -4000)) / np.diff(
    z
)
values = {
    **{k: be[k] for k in ["x0", "l0", "A", "Z", "rho"]},
    "t": np.broadcast_to(0.8 * overlap, t.shape),
}
changed = {}
with uproot.recreate(a.output) as out:
    for path, cls in f.classnames(cycle=False).items():
        if not cls.startswith("TH"):
            continue
        obj = f[path]
        key = path.removeprefix(prefix)
        if path.startswith(prefix) and key in values:
            data = obj.values(flow=True).copy()
            value = np.broadcast_to(values[key], t.shape)
            data[1:-1, 1:-1][mask] = value[mask]
            obj = to_TH2x(
                fName=obj.member("fName"),
                fTitle=obj.member("fTitle"),
                data=data.T.reshape(-1).astype(np.float32),
                fEntries=obj.member("fEntries"),
                fTsumw=float(data.sum()),
                fTsumw2=0,
                fTsumwx=0,
                fTsumwx2=0,
                fTsumwy=0,
                fTsumwy2=0,
                fTsumwxy=0,
                fSumw2=None,
                fXaxis=obj.member("fXaxis"),
                fYaxis=obj.member("fYaxis"),
            )
            changed[key] = int(mask.sum())
        out[path] = obj
new = uproot.open(a.output)
for path, cls in f.classnames(cycle=False).items():
    if not cls.startswith("TH"):
        continue
    old = f[path].values()
    fresh = new[path].values()
    key = path.removeprefix(prefix)
    if path.startswith(prefix) and key in values:
        assert np.array_equal(old[~mask], fresh[~mask])
        assert np.allclose(
            fresh[mask], np.broadcast_to(values[key], t.shape)[mask], rtol=1e-6
        )
    else:
        assert np.array_equal(old, fresh)
    for x, y in zip(f[path].axes, new[path].axes):
        assert np.array_equal(x.edges(), y.edges())
meta = {
    "geometry_xml": str(xml),
    "geometry_xml_sha256": hashlib.sha256(xml.read_bytes()).hexdigest(),
    "input": str(a.input),
    "input_sha256": hashlib.sha256(a.input.read_bytes()).hexdigest(),
    "output_sha256": hashlib.sha256(a.output.read_bytes()).hexdigest(),
    "surface": prefix,
    "changed_bins_per_field": changed,
    "all_other_histogram_bins_and_axes_identical": True,
    "slab": {
        "thickness_mm": 0.8,
        "half_length_mm": 4000,
        "outer_bin_thickness": "weighted by physical z overlap",
        "constants": be,
    },
    "scope": "Only known empty Be-pipe bins; not a general interpolation or replacement of sampled central bins.",
}
a.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps(meta, indent=2))
