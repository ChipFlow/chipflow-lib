# SPDX-License-Identifier: BSD-2-Clause
import os

from pathlib import Path

working_dir = Path(os.environ["PDM_RUN_CWD"] if "PDM_RUN_CWD" in os.environ else "./")

def main():
    if (working_dir / "chipflow.toml").exists():
        exit(0)
    else:
        print("chipflow.toml not found, this is not a valid project directory")
        tomls = sorted(working_dir.glob('**/chipflow.toml'))
        if tomls:
            print("Valid projects in this directory:")
            for f in tomls:
                print(f"  {str(f.parent.relative_to(working_dir))}")
        exit(1)

if __name__ == "__main__":
    main()
