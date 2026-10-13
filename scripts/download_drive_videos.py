#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
VIDEO_ROOT = (ROOT / "assets" / "video").resolve()
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
DOWNLOAD_RETRIES = 3
RETRY_SECONDS = 5


def warn(message: str) -> None:
    print(f"::warning::{message}")
    print(f"WARNING: {message}", file=sys.stderr)


def fail(message: str) -> None:
    print(f"::error::{message}")
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def inside_video_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(VIDEO_ROOT)
        return True
    except ValueError:
        return False


def is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def find_existing(target_dir: Path, expected_src: str) -> Path | None:
    exact = (ROOT / expected_src).resolve()
    if inside_video_root(exact) and is_video(exact):
        return exact

    if not target_dir.exists():
        return None

    wanted = Path(expected_src).stem.casefold()
    matches = [
        p for p in target_dir.iterdir()
        if is_video(p) and p.stem.casefold() == wanted
    ]

    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    mp4s = [p for p in matches if p.suffix.lower() == ".mp4"]
    if len(mp4s) == 1:
        return mp4s[0]

    fail(
        f"Multiple local files have the same stem '{Path(expected_src).stem}': "
        + ", ".join(sorted(p.name for p in matches))
    )


def replace_data_src(html: str, old_src: str, new_src: str) -> str:
    pattern = re.compile(
        r'(data-src\s*=\s*)(["\'])' + re.escape(old_src) + r'\2'
    )

    def repl(match: re.Match[str]) -> str:
        q = match.group(2)
        return f"{match.group(1)}{q}{new_src}{q}"

    updated, count = pattern.subn(repl, html)
    if count == 0:
        fail(f"Cannot update data-src: {old_src}")
    return updated


def remove_data_src_span(html: str, src: str) -> str:
    pattern = re.compile(
        r'[ \t]*<span\b[^>]*\bdata-src\s*=\s*(["\'])'
        + re.escape(src)
        + r'\1[^>]*>\s*</span>[ \t]*\r?\n?',
        flags=re.IGNORECASE,
    )
    updated, count = pattern.subn("", html, count=1)
    if count == 0:
        warn(f"Could not remove missing data-src entry: {src}")
        return html
    return updated


def get_blocks():
    if not INDEX.exists():
        fail("index.html not found")
    html = INDEX.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select(".video-sources[data-drive-folder][data-target-dir]")
    if not blocks:
        fail("No Drive-mapped video blocks found in index.html")
    return html, blocks


def get_block_for_target(target_rel: str):
    _, blocks = get_blocks()
    for block in blocks:
        current = (block.get("data-target-dir") or "").strip()
        if current == target_rel:
            return block
    fail(f"No mapped block found for target: {target_rel}")


def list_drive_folder(folder_url: str):
    import gdown
    try:
        entries = gdown.download_folder(
            url=folder_url,
            output=None,
            quiet=True,
            use_cookies=False,
            skip_download=True,
        )
    except Exception as exc:
        warn(
            f"Cannot list Drive folder {folder_url}: "
            f"{type(exc).__name__}: {exc}"
        )
        return []
    return entries or []


def build_drive_index(entries):
    by_stem = defaultdict(list)
    for entry in entries:
        name = Path(str(entry.path))
        by_stem[name.stem.casefold()].append(entry)
    return by_stem


def download_one(file_id: str, destination: Path) -> bool:
    import gdown
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        print(
            f"    DOWNLOAD {attempt}/{DOWNLOAD_RETRIES}: {destination.name}",
            flush=True,
        )
        try:
            result = gdown.download(
                id=file_id,
                output=str(destination),
                quiet=False,
                use_cookies=False,
            )
            if result and destination.exists() and destination.stat().st_size > 0:
                return True
            last_error = RuntimeError("gdown did not produce a valid file")
        except Exception as exc:
            last_error = exc

        if destination.exists():
            destination.unlink()

        if attempt < DOWNLOAD_RETRIES:
            time.sleep(RETRY_SECONDS)

    warn(
        f"Download failed for {destination.name} (Drive ID {file_id}). "
        f"Will retry on a future workflow run. "
        f"Last error: {type(last_error).__name__}: {last_error}"
    )
    return False


def convert_new_mov(source: Path) -> Path:
    if source.suffix.lower() != ".mov":
        return source

    if shutil.which("ffmpeg") is None:
        warn(f"ffmpeg unavailable; keeping {source.name} as MOV")
        return source

    output = source.with_suffix(".mp4")

    if output.exists() and output.stat().st_size > 0:
        source.unlink(missing_ok=True)
        return output

    print(f"    CONVERT: {source.name} -> {output.name}", flush=True)

    command = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a?",
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
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        output.unlink(missing_ok=True)
        warn(
            f"FFmpeg failed for {source.name} (exit {exc.returncode}). "
            "Keeping the original MOV."
        )
        return source

    if not output.exists() or output.stat().st_size == 0:
        output.unlink(missing_ok=True)
        warn(f"Invalid MP4 output for {source.name}; keeping MOV")
        return source

    source.unlink()
    return output


def process_group(target_rel: str) -> None:
    block = get_block_for_target(target_rel)
    folder_url = (block.get("data-drive-folder") or "").strip()
    target_dir = (ROOT / target_rel).resolve()

    if not folder_url:
        fail(f"Missing Drive URL for {target_rel}")
    if not inside_video_root(target_dir):
        fail(f"Invalid target: {target_rel}")

    target_dir.mkdir(parents=True, exist_ok=True)

    expected = [
        (node.get("data-src") or "").strip()
        for node in block.select("[data-src]")
        if (node.get("data-src") or "").strip()
    ]

    print("=" * 76)
    print(f"PARALLEL WORKER: {target_rel}")
    print(f"Expected videos: {len(expected)}")
    print("=" * 76)

    missing = []

    for src in expected:
        existing = find_existing(target_dir, src)
        if existing is not None:
            print(
                f"SKIP existing: {existing.name} "
                "(no download, no convert)",
                flush=True,
            )
        else:
            print(f"MISSING: {Path(src).stem}", flush=True)
            missing.append(src)

    if not missing:
        print("ALL FILES EXIST -> no Drive access needed.")
        return

    print(f"Need Drive download: {len(missing)}")
    entries = list_drive_folder(folder_url)

    if not entries:
        warn(
            f"No Drive metadata available for {target_rel}. "
            "Keeping existing files only."
        )
        return

    by_stem = build_drive_index(entries)

    for src in missing:
        existing = find_existing(target_dir, src)
        if existing is not None:
            print(f"SKIP appeared meanwhile: {existing.name}")
            continue

        wanted = Path(src).stem.casefold()
        matches = by_stem.get(wanted, [])

        if not matches:
            warn(
                f"Drive file not found by NAME: {Path(src).stem} "
                f"in {folder_url}. Skipping this video."
            )
            continue

        if len(matches) > 1:
            warn(
                f"Multiple Drive files match NAME {Path(src).stem}; "
                "skipping to avoid choosing the wrong file."
            )
            continue

        entry = matches[0]
        drive_name = Path(str(entry.path)).name
        destination = target_dir / drive_name

        print(f"MATCH: {Path(src).name} -> {drive_name}")
        print(f"Drive ID: {entry.id}")

        if not download_one(str(entry.id), destination):
            continue

        final = convert_new_mov(destination)
        size_mb = final.stat().st_size / 1024 / 1024
        print(f"READY: {final.name} ({size_mb:.1f} MB)")

    print(f"WORKER DONE: {target_rel}")


def finalize_index() -> None:
    html, blocks = get_blocks()
    resolved = 0
    removed = 0

    for block in blocks:
        target_rel = (block.get("data-target-dir") or "").strip()
        target_dir = (ROOT / target_rel).resolve()

        for node in block.select("[data-src]"):
            old_src = (node.get("data-src") or "").strip()
            if not old_src:
                continue

            existing = find_existing(target_dir, old_src)

            if existing is None:
                warn(
                    "Final deploy: video unavailable, removing playlist entry: "
                    f"{old_src}"
                )
                html = remove_data_src_span(html, old_src)
                removed += 1
                continue

            real_src = existing.relative_to(ROOT).as_posix()

            if old_src != real_src:
                html = replace_data_src(html, old_src, real_src)

            resolved += 1

    INDEX.write_text(html, encoding="utf-8")

    print("=" * 76)
    print("FINALIZE INDEX")
    print(f"Resolved videos: {resolved}")
    print(f"Missing entries removed from deploy copy: {removed}")
    print("=" * 76)


def parse_args():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--target-dir")
    mode.add_argument("--finalize", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.finalize:
        finalize_index()
    else:
        process_group(args.target_dir)


if __name__ == "__main__":
    main()
