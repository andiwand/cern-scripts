"""Reuse the established G4 reference compile/link configuration."""

from pathlib import Path

root = Path(__file__).resolve().parent
script = (
    (root.parent / "fatras-soft-secondaries/build-reference.py")
    .read_text()
    .replace("ionisation-reference", "radiation-reference")
    .replace(
        "Fatras/src/Physics/Ionisation.cpp", "Fatras/src/Physics/Bremsstrahlung.cpp"
    )
    .replace('with_name("radiation-reference.cpp")', 'with_name("reference.cpp")')
)
exec(
    compile(script, str(root / "build-reference.py"), "exec"),
    {"__name__": "__main__", "__file__": str(root / "build-reference.py")},
)
