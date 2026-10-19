import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli.import_dataset_manifest",
            *sys.argv[1:],
        ],
        cwd=ROOT / "backend",
        check=True,
    )


if __name__ == "__main__":
    main()
