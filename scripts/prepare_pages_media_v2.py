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

VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".webm", ".mkv", ".avi"}
DOWNLOAD_RETRIES = 3
UPLOAD_RETRIES = 3
RETRY_SECONDS = 5


def fail(message: str) -> None:
    print(f"::error::{message}")
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"::warning::{message}")
    print(f"WARNING: {message}", file=sys.stderr)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--target-dir", required=True)
    p.add_argument("--existing-assets-file", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--release-tag", required=True)
    return p.parse_args()


def load_existing(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        x.strip()
        for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    }


def find_block(target_dir: str):
    if not INDEX.exists():
        fail("index.html not found")

    soup = BeautifulSoup(INDEX.read_text(encoding="utf-8"), "html.parser")

    for block in soup.select(".video-sources[data-drive-folder][data-target-dir]"):
        current = (block.get("data-target-dir") or "").strip()
        if current == target_dir:
            return block

    fail(f"No mapped video block found for target: {target_dir}")


def list_drive(folder_url: str):
    try:
        return gdown.download_folder(
            url=folder_url,
            output=None,
            quiet=True,
            use_cookies=False,
            skip_download=True,
        ) or []
    except Exception as exc:
        fail(f"Cannot list Drive folder {folder_url}: {type(exc).__name__}: {exc}")


def drive_index(entries):
    by_stem = defaultdict(list)
    for entry in entries:
        p = Path(str(entry.path))
        if p.suffix.casefold() in VIDEO_EXTS:
            by_stem[p.stem.casefold()].append(entry)
    return by_stem


def choose_source(matches, html_src: str):
    """
    Prefer the same extension requested by HTML.
    If that does not exist, accept exactly one MOV as the source.
    Every chosen source is transcoded again; MP4 is NOT copied through.
    """
    if not matches:
        return None

    wanted_ext = Path(html_src).suffix.casefold()

    same = [
        entry for entry in matches
        if Path(str(entry.path)).suffix.casefold() == wanted_ext
    ]
    if len(same) == 1:
        return same[0]
    if len(same) > 1:
        fail(
            f"Multiple Drive files match {Path(html_src).stem} "
            f"with extension {wanted_ext}"
        )

    movs = [
        entry for entry in matches
        if Path(str(entry.path)).suffix.casefold() == ".mov"
    ]
    if len(movs) == 1:
        return movs[0]
    if len(movs) > 1:
        fail(f"Multiple MOV files share stem {Path(html_src).stem}")

    if len(matches) == 1:
        return matches[0]

    fail(
        f"Multiple Drive candidates share stem {Path(html_src).stem}: "
        + ", ".join(Path(str(x.path)).name for x in matches)
    )


def download_one(file_id: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        print(f"DOWNLOAD {attempt}/{DOWNLOAD_RETRIES}: {destination.name}", flush=True)
        try:
            result = gdown.download(
                id=file_id,
                output=str(destination),
                quiet=False,
                use_cookies=False,
            )
            if result and destination.exists() and destination.stat().st_size > 0:
                return
            last_error = RuntimeError("gdown did not create a valid file")
        except Exception as exc:
            last_error = exc

        destination.unlink(missing_ok=True)
        if attempt < DOWNLOAD_RETRIES:
            time.sleep(RETRY_SECONDS)

    fail(
        f"Download failed for {destination.name}: "
        f"{type(last_error).__name__}: {last_error}"
    )


def transcode_mobile(source: Path, output: Path) -> None:
    if shutil.which("ffmpeg") is None:
        fail("ffmpeg not found")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    # 1280x1280 bounding box preserves portrait/landscape aspect ratio.
    # Every file is re-encoded, including existing MP4s.
    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-sn", "-dn",
        "-map_metadata", "-1",
        "-vf",
        "scale=1280:1280:force_original_aspect_ratio=decrease:"
        "force_divisible_by=2,fps=30,setsar=1",
        "-c:v", "libx264",
        "-profile:v", "main",
        "-level:v", "4.0",
        "-tag:v", "avc1",
        "-preset", "medium",
        "-crf", "27",
        "-pix_fmt", "yuv420p",
        "-maxrate", "4M",
        "-bufsize", "8M",
        "-c:a", "aac",
        "-profile:a", "aac_low",
        "-b:a", "96k",
        "-ar", "48000",
        "-ac", "2",
        "-movflags", "+faststart",
        "-metadata:s:v:0", "rotate=0",
        str(output),
    ]

    print(f"TRANSCODE: {source.name} -> {output.name}", flush=True)
    subprocess.run(cmd, check=True)

    if not output.exists() or output.stat().st_size <= 0:
        fail(f"Invalid FFmpeg output: {output.name}")


def validate_mp4(path: Path) -> None:
    if shutil.which("ffprobe") is None:
        fail("ffprobe not found")

    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_name,codec_tag_string,profile,level,pix_fmt,width,height",
        "-of", "default=noprint_wrappers=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True)

    required = {
        "codec_name=h264",
        "codec_tag_string=avc1",
        "pix_fmt=yuv420p",
    }

    missing = [x for x in required if x not in out]
    if missing:
        fail(f"Mobile validation failed for {path.name}: missing {missing}\n{out}")

    print("FFPROBE:")
    print(out.strip())


def upload_asset(path: Path, repository: str, release_tag: str) -> None:
    if shutil.which("gh") is None:
        fail("gh CLI not found")
    if not os.environ.get("GH_TOKEN"):
        fail("GH_TOKEN is missing")

    last_error = None
    for attempt in range(1, UPLOAD_RETRIES + 1):
        print(f"UPLOAD {attempt}/{UPLOAD_RETRIES}: {path.name}", flush=True)
        try:
            subprocess.run(
                [
                    "gh", "release", "upload",
                    release_tag,
                    str(path),
                    "--repo", repository,
                    "--clobber",
                ],
                check=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc

        if attempt < UPLOAD_RETRIES:
            time.sleep(RETRY_SECONDS)

    fail(f"Release upload failed for {path.name}: {last_error}")


def main():
    args = parse_args()

    if args.target_dir not in GROUPS:
        fail(f"Unknown target dir: {args.target_dir}")

    group = GROUPS[args.target_dir]
    block = find_block(args.target_dir)
    folder_url = (block.get("data-drive-folder") or "").strip()
    if not folder_url:
        fail(f"Drive folder missing for {args.target_dir}")

    expected = [
        (node.get("data-src") or "").strip()
        for node in block.select("[data-src]")
        if (node.get("data-src") or "").strip()
    ]

    existing = load_existing(Path(args.existing_assets_file))
    entries = None
    by_stem = None
    work = Path("_pages_media_work") / group
    work.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print(f"GROUP       : {group}")
    print(f"TARGET      : {args.target_dir}")
    print(f"HTML VIDEOS : {len(expected)}")
    print("=" * 78)

    for html_src in expected:
        stem = Path(html_src).stem
        asset = f"{group}__{stem}.mp4"

        if asset in existing:
            print(f"SKIP V2 STORED: {asset}")
            continue

        if entries is None:
            entries = list_drive(folder_url)
            by_stem = drive_index(entries)

        matches = by_stem.get(stem.casefold(), [])
        chosen = choose_source(matches, html_src)
        if chosen is None:
            fail(f"No Drive source found for {html_src}")

        drive_name = Path(str(chosen.path)).name
        downloaded = work / f"source__{drive_name}"
        output = work / asset

        print()
        print(f"HTML   : {html_src}")
        print(f"DRIVE  : {drive_name}")
        print(f"STORE  : {asset}")

        download_one(str(chosen.id), downloaded)
        transcode_mobile(downloaded, output)
        validate_mp4(output)

        size_mb = output.stat().st_size / 1024 / 1024
        print(f"READY  : {asset} ({size_mb:.1f} MiB)")

        upload_asset(output, args.repository, args.release_tag)
        print(f"STORED : {asset}")

        downloaded.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
