#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import quote

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


def warn(message: str) -> None:
    print(f"::warning::{message}")
    print(f"WARNING: {message}", file=sys.stderr)


def fail(message: str) -> None:
    print(f"::error::{message}")
    raise SystemExit(1)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--assets-file", required=True)
    return parser.parse_args()


def asset_name(group: str, html_src: str) -> str:
    p = Path(html_src)
    return f"{group}__{p.stem}{p.suffix}"


def replace_src(html: str, old: str, new: str) -> str:
    pattern = re.compile(
        r'(data-src\s*=\s*)(["\'])'
        + re.escape(old)
        + r'\2'
    )

    def repl(match):
        q = match.group(2)
        return f"{match.group(1)}{q}{new}{q}"

    out, count = pattern.subn(repl, html)

    if count == 0:
        fail(f"Cannot update data-src: {old}")

    return out


def remove_span(html: str, src: str) -> str:
    pattern = re.compile(
        r'[ \t]*<span\b[^>]*\bdata-src\s*=\s*(["\'])'
        + re.escape(src)
        + r'\1[^>]*>\s*</span>[ \t]*\r?\n?',
        re.IGNORECASE,
    )

    out, count = pattern.subn("", html, count=1)

    if count == 0:
        warn(f"Could not remove missing data-src entry: {src}")

    return out


def main():
    args = parse_args()

    if not INDEX.exists():
        fail("index.html not found")

    assets_path = Path(args.assets_file)

    available = {
        line.strip()
        for line in assets_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    } if assets_path.exists() else set()

    html = INDEX.read_text(encoding="utf-8")

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    rewritten = 0
    missing = 0

    for block in soup.select(
        ".video-sources[data-drive-folder][data-target-dir]"
    ):
        target = (
            block.get("data-target-dir")
            or ""
        ).strip()

        if target not in GROUPS:
            continue

        group = GROUPS[target]

        for node in block.select("[data-src]"):
            old = (
                node.get("data-src")
                or ""
            ).strip()

            if not old:
                continue

            asset = asset_name(group, old)

            if asset not in available:
                warn(
                    f"Release asset missing: {asset}; "
                    "removing only this video from the deploy copy."
                )

                html = remove_span(html, old)
                missing += 1
                continue

            url = (
                f"https://github.com/"
                f"{args.repository}/releases/download/"
                f"{quote(args.tag, safe='')}/"
                f"{quote(asset, safe='._-')}"
            )

            html = replace_src(
                html,
                old,
                url,
            )

            rewritten += 1

    INDEX.write_text(
        html,
        encoding="utf-8",
    )

    print(f"Rewritten video URLs: {rewritten}")
    print(f"Missing release videos removed: {missing}")


if __name__ == "__main__":
    main()
