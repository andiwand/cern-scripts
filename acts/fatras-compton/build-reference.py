"""Reuse the validated G4 reference compiler configuration."""

from pathlib import Path

root = Path(__file__).resolve().parent
script = (
    (root.parent / "fatras-soft-secondaries/build-reference.py")
    .read_text()
    .replace("ionisation-reference", "compton-reference")
    .replace(
        "Fatras/src/Physics/Ionisation.cpp", "Fatras/src/Physics/ComptonScattering.cpp"
    )
)
# The first replacement also changes the source basename.
script = script.replace(
    'with_name("compton-reference.cpp")', 'with_name("reference.cpp")'
)
exec(
    compile(script, str(root / "build-reference.py"), "exec"),
    {"__name__": "__main__", "__file__": str(root / "build-reference.py")},
)
