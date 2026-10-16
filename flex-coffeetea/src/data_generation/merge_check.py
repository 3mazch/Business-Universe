"""Legacy command retained as a status check; canonical facts stay partitioned."""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "sale_orders"


def run_merge() -> dict:
    manifest_path = OUTPUT_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Sale/Orders manifest not found: {manifest_path}. "
            "Run run_generation.py first."
        )
    with manifest_path.open("r", encoding="utf-8") as source:
        manifest = json.load(source)
    if manifest.get("status") != "complete" or not manifest.get("full_scope_run"):
        raise ValueError(
            "Refusing to report a partial Sale/Orders output as a complete fact set."
        )

    print(
        "No merge performed: store/month CSV partitions are the canonical "
        "Sale/Orders output."
    )
    print(f"Source: {OUTPUT_DIR / 'full'}")
    print(f"Sample: {OUTPUT_DIR / 'sample'}")
    for table, row_count in manifest["row_counts_full"].items():
        print(f"  {table}: {row_count:,} rows")
    return manifest


if __name__ == "__main__":
    run_merge()
