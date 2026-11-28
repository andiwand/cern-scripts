"""Early review of completed NN runs against the original physical truth denominator."""

from pathlib import Path
import json
import re
import sys
import numpy as np
from analyze import load, check_same
from nn_analyze import counts

root = Path(sys.argv[1])
result = {}
models = None
for v in ["core4", "core5", "core7"]:
    p = root / "nn-native/training" / v
    assert (p / "exit-code").read_text().strip() == "0"
    d = load(p)
    raw = load(root / "training" / v)
    check_same({"raw": raw, "nn": d})
    text = (p / "log.RAWtoALL").read_text()
    assert "TAIL_SCORE_NN pre charge=0 size=0" in text
    hashes = re.findall(r"TAIL_SCORE_NATIVE_MODEL\s+\S+\s+([a-f0-9]{64})", text)
    assert len(hashes) == 4, (v, hashes)
    if models is None:
        models = hashes
    assert models == hashes
    result[v] = dict(raw=counts(raw, "none", 0), nn=counts(d, "none", 0))
(root / "nn-native/early-review.json").write_text(
    json.dumps(
        dict(
            checks="Same physical truth, score dimensions, all-charge NN before selection, identical model hashes",
            models=models,
            counts=result,
        ),
        indent=2,
    )
    + "\n"
)
print(json.dumps(result, indent=2), flush=True)
