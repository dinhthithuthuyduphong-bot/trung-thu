#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

GROUPS = {
    "assets/video/nam2025": "2025",
    "assets/video/nam2026/goiqua": "2026-goiqua",
    "assets/video/nam2026/kick-off": "2026-kickoff",
    "assets/video/nam2026/chua": "2026-chua",
    "assets/video/nam2026/tongket": "2026-tongket",
}


def fail(message: str) -> None:
    print(f"::error::{message}")
    raise SystemExit(1)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--release-dir", required=True)
    return p.parse_args()


def main():
    args = parse_args()

    if not INDEX.exists():
        fail("index.html not found")

    release_dir = Path(args.release_dir)
    if not release_dir.exists():
        fail(f"Release directory not found: {release_dir}")

    html = INDEX.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    copied = 0

    for block in soup.select(".video-sources[data-target-dir]"):
        target = (block.get("data-target-dir") or "").strip()
        if target not in GROUPS:
            continue

        group = GROUPS[target]

        for node in block.select("[data-src]"):
            local_src = (node.get("data-src") or "").strip()
            if not local_src:
                continue

            stem = Path(local_src).stem
            asset_name = f"{group}__{stem}.mp4"
            source = release_dir / asset_name

            if not source.exists():
                fail(f"Required normalized asset is missing: {asset_name}")

            destination = ROOT / local_src
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
            print(f"COPY: {asset_name} -> {local_src}")

    print(f"Materialized normalized videos: {copied}")


if __name__ == "__main__":
    main()
