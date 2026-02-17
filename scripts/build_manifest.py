#!/usr/bin/env python3
"""Generate static/dist/manifest.json from esbuild metafile.

Maps source filenames (e.g. "app.js") to their hashed outputs
(e.g. "app.ABC123.min.js") for the asset_url() template helper.

Usage:
    python3 scripts/build_manifest.py static/dist
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    dist_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("static/dist")

    meta_path = dist_dir / "meta.json"
    if not meta_path.exists():
        print(f"[manifest] No meta.json found in {dist_dir}")
        sys.exit(1)

    meta = json.loads(meta_path.read_text())

    manifest = {}
    for output_path, info in meta.get("outputs", {}).items():
        # Skip sourcemap files
        if output_path.endswith(".map"):
            continue

        entry_point = info.get("entryPoint", "")
        if entry_point:
            # Map source name to output: "static/js/app.js" -> "app.ABC123.js"
            source_name = Path(entry_point).name
            output_name = Path(output_path).name
            manifest[source_name] = output_name

    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[manifest] Generated {manifest_path} with {len(manifest)} entries:")
    for src, out in manifest.items():
        print(f"  {src} -> {out}")


if __name__ == "__main__":
    main()
