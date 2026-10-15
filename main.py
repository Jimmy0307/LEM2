from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from roughset.app import run_application
from roughset.batch import run_policy_matrix


def load_config(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SystemExit(f"CONFIG NOT FOUND: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"CONFIG JSON ERROR: {path} line {exc.lineno}: {exc.msg}") from exc


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="RoughSet / LEM2 research software")
    parser.add_argument("--config",default="config.json",help="Path to config.json")
    parser.add_argument("--all-policies", action="store_true", help="Run every configured prediction policy into isolated output folders")
    args=parser.parse_args(argv)
    config_path=Path(args.config).resolve()
    print("="*72)
    print("RoughSet Research Software")
    print("="*72)
    print(f"Config: {config_path}")
    try:
        config = load_config(config_path)
        if args.all_policies:
            result = run_policy_matrix(config)
            print("\nCompleted policy matrix:")
            print(result["summary"].to_string(index=False))
            print(f"\nBatch outputs: {Path(result['root_output']).resolve()}")
        else:
            result=run_application(config)
            print("\nCompleted datasets:")
            print(result["summary"].to_string(index=False))
            print(f"\nOutputs: {Path(result['config']['report']['outputs_folder']).resolve()}")
    except Exception as exc:
        print(f"\nERROR: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
