#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import gdown
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

DOWNLOAD_RETRIES = 3
UPLOAD_RETRIES = 3
RETRY_SECONDS = 5


def warn(message: str) -> None:
    print(f"::warning::{message}")
    print(f"WARNING: {message}", file=sys.stderr)


def fail(message: str) -> None:
    print(f"::error::{message}")
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--existing-assets-file", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-tag", required=True)
    return parser.parse_args()


def load_existing_assets(path: Path) -> set[str]:
    if not path.exists():
        return set()

    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def find_block(target_dir: str):
    if not INDEX.exists():
        fail("index.html not found")

    soup = BeautifulSoup(
        INDEX.read_text(encoding="utf-8"),
        "html.parser",
    )

    for block in soup.select(
        ".video-sources[data-drive-folder][data-target-dir]"
    ):
        current = (block.get("data-target-dir") or "").strip()
        if current == target_dir:
            return block

    fail(f"No video block found for target: {target_dir}")


def list_drive_folder(folder_url: str):
    try:
        entries = gdown.download_folder(
            url=folder_url,
            output=None,
            quiet=True,
            use_cookies=False,
            skip_download=True,
        )
    except Exception as exc:
        fail(
            f"Cannot list Drive folder {folder_url}\n"
            f"{type(exc).__name__}: {exc}"
        )

    return entries or []


def build_drive_index(entries):
    by_stem = defaultdict(list)

    for entry in entries:
        p = Path(str(entry.path))
        by_stem[p.stem.casefold()].append(entry)

    return by_stem


def release_asset_name(group: str, html_src: str) -> str:
    """
    Release extension follows HTML exactly.

    HTML .../ABC.MOV  -> group__ABC.MOV
    HTML .../ABC.mov  -> group__ABC.mov
    HTML .../ABC.mp4  -> group__ABC.mp4
    """
    p = Path(html_src)
    return f"{group}__{p.stem}{p.suffix}"


def choose_drive_entry(matches, html_src: str):
    """
    Rule requested by the user:

    1. HTML asks for MP4:
       - prefer an existing Drive MP4 with the same stem -> NO conversion
       - otherwise use exactly one MOV -> convert MOV -> MP4

    2. HTML asks for anything else (MOV in the current project):
       - require the same extension on Drive
       - copy/store it AS-IS -> NO conversion

    This also resolves cases where Drive contains both .MOV and .mp4
    with the same filename stem.
    """
    if not matches:
        return None, "not-found"

    wanted_ext = Path(html_src).suffix.casefold()

    same_ext = [
        entry
        for entry in matches
        if Path(str(entry.path)).suffix.casefold() == wanted_ext
    ]

    if wanted_ext == ".mp4":
        if len(same_ext) == 1:
            return same_ext[0], "copy"

        if len(same_ext) > 1:
            return None, "duplicate-mp4"

        mov_matches = [
            entry
            for entry in matches
            if Path(str(entry.path)).suffix.casefold() == ".mov"
        ]

        if len(mov_matches) == 1:
            return mov_matches[0], "convert-to-mp4"

        if len(mov_matches) > 1:
            return None, "duplicate-mov"

        return None, "no-mp4-or-mov"

    # Non-MP4 HTML entry: do NOT convert.
    if len(same_ext) == 1:
        return same_ext[0], "copy"

    if len(same_ext) > 1:
        return None, "duplicate-same-extension"

    return None, "extension-not-found"


def download_one(file_id: str, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        print(
            f"DOWNLOAD {attempt}/{DOWNLOAD_RETRIES}: {destination.name}",
            flush=True,
        )

        try:
            result = gdown.download(
                id=file_id,
                output=str(destination),
                quiet=False,
                use_cookies=False,
            )

            if (
                result
                and destination.exists()
                and destination.stat().st_size > 0
            ):
                return True

            last_error = RuntimeError(
                "gdown did not produce a valid file"
            )

        except Exception as exc:
            last_error = exc

        destination.unlink(missing_ok=True)

        if attempt < DOWNLOAD_RETRIES:
            time.sleep(RETRY_SECONDS)

    warn(
        f"Download failed: {destination.name}; "
        f"Drive ID={file_id}; "
        f"last={type(last_error).__name__}: {last_error}"
    )
    return False


def convert_mov_to_mp4(source: Path, output: Path) -> bool:
    """
    Conversion runs ONLY when HTML asks for .mp4 and Drive has .MOV.

    Use the first audio stream only. Some iPhone MOV files contain extra
    audio/data streams that caused the previous FFmpeg 'simple filtergraph'
    error when all audio streams were mapped.
    """
    if shutil.which("ffmpeg") is None:
        fail("ffmpeg not found")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(source),

        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-sn",
        "-dn",

        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "128k",

        "-movflags", "+faststart",
        str(output),
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        output.unlink(missing_ok=True)
        warn(
            f"FFmpeg failed for {source.name}: exit {exc.returncode}"
        )
        return False

    return output.exists() and output.stat().st_size > 0


def upload_release_asset(
    file_path: Path,
    repository: str,
    release_tag: str,
) -> bool:
    """
    Upload EACH finished file immediately.

    This is important: after a download/copy/convert succeeds, the file is
    persisted to the GitHub Release before the worker moves to the next video.
    A later failure therefore does not lose all earlier work.
    """
    if shutil.which("gh") is None:
        fail("GitHub CLI 'gh' not found")

    if not os.environ.get("GH_TOKEN"):
        fail("GH_TOKEN is not available")

    last_error = None

    for attempt in range(1, UPLOAD_RETRIES + 1):
        print(
            f"STORE RELEASE {attempt}/{UPLOAD_RETRIES}: {file_path.name}",
            flush=True,
        )

        cmd = [
            "gh",
            "release",
            "upload",
            release_tag,
            str(file_path),
            "--repo",
            repository,
            "--clobber",
        ]

        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as exc:
            last_error = exc

        if attempt < UPLOAD_RETRIES:
            time.sleep(RETRY_SECONDS)

    warn(
        f"Release upload failed for {file_path.name}: "
        f"{last_error}"
    )
    return False


def main():
    args = parse_args()

    if args.target_dir not in GROUPS:
        fail(f"Unknown target dir: {args.target_dir}")

    group = GROUPS[args.target_dir]
    block = find_block(args.target_dir)

    folder_url = (block.get("data-drive-folder") or "").strip()
    if not folder_url:
        fail(f"Missing Drive URL for {args.target_dir}")

    expected = [
        (node.get("data-src") or "").strip()
        for node in block.select("[data-src]")
        if (node.get("data-src") or "").strip()
    ]

    existing = load_existing_assets(
        Path(args.existing_assets_file)
    )

    missing = []

    print("=" * 78)
    print(f"MEDIA GROUP: {group}")
    print(f"HTML entries: {len(expected)}")
    print("=" * 78)

    for html_src in expected:
        asset = release_asset_name(group, html_src)

        if asset in existing:
            print(
                f"SKIP STORED: {asset} "
                "(no Drive download, no conversion)"
            )
            continue

        missing.append(html_src)

        print(
            f"NEED STORE: {asset} | "
            f"HTML wants {Path(html_src).suffix}"
        )

    if not missing:
        print("All HTML-requested assets are already stored.")
        return

    print(
        f"Reading Drive metadata for {len(missing)} missing asset(s)..."
    )

    entries = list_drive_folder(folder_url)
    by_stem = build_drive_index(entries)

    work_dir = Path("_media_work") / group
    work_dir.mkdir(parents=True, exist_ok=True)

    stored = 0
    skipped = 0

    for html_src in missing:
        html_path = Path(html_src)
        stem = html_path.stem
        wanted_ext = html_path.suffix
        asset = release_asset_name(group, html_src)

        matches = by_stem.get(stem.casefold(), [])

        entry, mode = choose_drive_entry(matches, html_src)

        if entry is None:
            detail = ", ".join(
                Path(str(item.path)).name
                for item in matches
            ) or "(none)"

            warn(
                f"Cannot resolve {html_path.name}; "
                f"reason={mode}; Drive candidates={detail}"
            )

            skipped += 1
            continue

        drive_name = Path(str(entry.path)).name
        downloaded = work_dir / drive_name
        output = work_dir / asset

        print()
        print(f"HTML      : {html_path.name}")
        print(f"DRIVE     : {drive_name}")
        print(f"MODE      : {mode}")
        print(f"STORE AS  : {asset}")
        print(f"Drive ID  : {entry.id}")

        if not download_one(str(entry.id), downloaded):
            skipped += 1
            continue

        # --------------------------------------------------
        # User rule:
        # HTML wants .mp4 + Drive is MOV -> convert.
        # Otherwise -> NO conversion.
        # --------------------------------------------------
        if mode == "convert-to-mp4":
            print(
                f"CONVERT because HTML wants MP4: "
                f"{downloaded.name} -> {asset}"
            )

            if not convert_mov_to_mp4(downloaded, output):
                skipped += 1
                continue

        else:
            print(
                f"NO CONVERT: copy bytes as requested by HTML -> {asset}"
            )

            shutil.copy2(downloaded, output)

        if not output.exists() or output.stat().st_size <= 0:
            warn(f"Prepared file invalid: {asset}")
            skipped += 1
            continue

        size_mb = output.stat().st_size / 1024 / 1024
        print(f"PREPARED: {asset} ({size_mb:.1f} MB)")

        # Persist immediately before doing another video.
        if not upload_release_asset(
            output,
            args.repository,
            args.release_tag,
        ):
            skipped += 1
            continue

        print(f"STORED PERMANENTLY: {asset}")
        stored += 1

        # Safe to clean runner temp only after persistent upload succeeded.
        downloaded.unlink(missing_ok=True)
        output.unlink(missing_ok=True)

    print()
    print("=" * 78)
    print(f"STORED THIS RUN : {stored}")
    print(f"SKIPPED/FAILED  : {skipped}")
    print("=" * 78)


if __name__ == "__main__":
    main()
