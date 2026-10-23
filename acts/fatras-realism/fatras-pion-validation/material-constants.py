import argparse
import json
from pathlib import Path
import acts
import acts.examples
import acts.examples.geant4
import pion_diagnostics

p = argparse.ArgumentParser()
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.write_text(json.dumps(dict(pion_diagnostics.beryllium()), indent=2) + "\n")
