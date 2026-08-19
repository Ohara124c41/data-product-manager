"""Run the Flyber analysis and artifact-generation pipeline in sequence."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def find_project_root() -> Path:
    candidates = [Path.cwd(), ROOT.parent, *ROOT.parents]
    for candidate in candidates:
        if (candidate / "upload").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not locate the project root. Expected an upload/ directory "
        "containing the three supplied templates."
    )

STEPS = [
    ROOT / "scripts" / "01_analyze_flyber.py",
    ROOT / "scripts" / "02_create_visualizations.py",
    ROOT / "scripts" / "03_build_section3_workbook.py",
    ROOT / "scripts" / "04_populate_proposal.py",
]


def main() -> None:
    project_root = find_project_root()
    for script in STEPS:
        print(f"Running {script.name}")
        subprocess.run(
            [sys.executable, str(script)],
            cwd=project_root,
            check=True,
        )
    print("Flyber pipeline completed successfully.")


if __name__ == "__main__":
    main()
