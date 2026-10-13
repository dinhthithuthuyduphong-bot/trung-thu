#!/usr/bin/env python3
"""
Download video folders from Google Drive, prepare browser-compatible files,
and update index.html to point at the real file extension.

Only <div class="video-sources"> blocks that contain BOTH:
    data-drive-folder="..."
    data-target-dir="..."
are processed.

Current index.html maps only 2025 and 2026, so 2024 is untouched.

Matching rule:
    Match by filename stem only, case-insensitive.
    IMG_0346.MOV == IMG_0346.mp4 == img_0346.MP4

Conversion rule:
    Every .MOV/.mov file is transcoded to:
      MP4 container + H.264 video + AAC audio + yuv420p + faststart

The script modifies index.html only in the CI workspace. It does not commit
the generated changes back to GitHub.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import gdown
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / "index.html"
VIDEO_ROOT = (ROOT / "assets" / "video").resolve()

VIDEO_EXTENSIONS = {
    ".mov",
    ".mp4",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
}


def fail(message: str) -> None:
    print(f"\nERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        fail(
            f"Không tìm thấy '{name}'. "
            f"Pipeline phải cài {name} trước khi chạy script."
        )


def is_inside_video_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(VIDEO_ROOT)
        return True
    except ValueError:
        return False


def is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def video_files(folder: Path) -> list[Path]:
    return sorted(
        (p for p in folder.rglob("*") if is_video(p)),
        key=lambda p: p.as_posix().casefold(),
    )


def assert_unique_stems(folder: Path, stage: str) -> None:
    """
    Because HTML matching intentionally ignores extensions, two files with
    the same stem are ambiguous and must fail instead of guessing.
    """
    by_stem: dict[str, list[Path]] = defaultdict(list)

    for path in video_files(folder):
        by_stem[path.stem.casefold()].append(path)

    conflicts = {
        stem: files
        for stem, files in by_stem.items()
        if len(files) > 1
    }

    if not conflicts:
        return

    print(f"\nDuplicate video stems detected ({stage}):", file=sys.stderr)

    for stem, files in sorted(conflicts.items()):
        print(f"  {stem}", file=sys.stderr)
        for file in files:
            print(
                f"    - {file.relative_to(ROOT).as_posix()}",
                file=sys.stderr,
            )

    fail(
        "Có nhiều video cùng tên nhưng khác extension/đường dẫn. "
        "Vì pipeline dò theo NAME בלבד, hãy chỉ giữ một file cho mỗi tên."
    )


def run_ffmpeg(source: Path, output: Path) -> None:
    """
    MOV -> MP4, browser friendly.
    """
    if output.exists():
        fail(
            "Không thể convert vì file đích đã tồn tại: "
            f"{output.relative_to(ROOT).as_posix()}"
        )

    print(f"  CONVERT: {source.name} -> {output.name}")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output),
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        if output.exists():
            output.unlink()
        fail(
            f"FFmpeg convert thất bại cho "
            f"{source.relative_to(ROOT).as_posix()} "
            f"(exit code {exc.returncode})."
        )

    if not output.exists() or output.stat().st_size == 0:
        fail(f"FFmpeg không tạo được file hợp lệ: {output}")

    # Delete the source only after a successful conversion.
    source.unlink()


def convert_all_mov(folder: Path) -> None:
    mov_files = [
        p
        for p in video_files(folder)
        if p.suffix.lower() == ".mov"
    ]

    if not mov_files:
        print("  Không có MOV cần convert.")
        return

    print(f"  Có {len(mov_files)} file MOV cần convert.")

    for source in mov_files:
        output = source.with_suffix(".mp4")
        run_ffmpeg(source, output)


def remove_non_video_files(folder: Path) -> None:
    """
    The supplied Drive folders are video sources. Do not publish unrelated
    files accidentally if somebody later drops a document/image into Drive.
    """
    for path in sorted(folder.rglob("*"), reverse=True):
        if path.is_file() and path.suffix.lower() not in VIDEO_EXTENSIONS:
            print(
                "  REMOVE non-video:",
                path.relative_to(ROOT).as_posix(),
            )
            path.unlink()
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def download_drive_folder(folder_url: str, target_dir: Path) -> None:
    """
    Download the whole public Drive folder, preserving Drive filenames.
    Existing target content is removed in this CI workspace to prevent
    stale committed videos from masking Drive problems.
    """
    if not is_inside_video_root(target_dir):
        fail(
            f"Target phải nằm trong assets/video/: "
            f"{target_dir}"
        )

    if target_dir.exists():
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"  DRIVE : {folder_url}")
    print(f"  TARGET: {target_dir.relative_to(ROOT).as_posix()}")

    try:
        result = gdown.download_folder(
            url=folder_url,
            output=str(target_dir),
            quiet=False,
            use_cookies=False,
        )
    except Exception as exc:
        fail(
            f"Không tải được Google Drive folder:\n"
            f"{folder_url}\n"
            f"{type(exc).__name__}: {exc}"
        )

    if result is None:
        fail(f"gdown không trả về kết quả cho folder: {folder_url}")

    remove_non_video_files(target_dir)

    files = video_files(target_dir)

    if not files:
        fail(
            "Folder Drive tải thành công nhưng không tìm thấy video nào: "
            f"{folder_url}"
        )

    print(f"  Downloaded video files: {len(files)}")


def find_by_stem(folder: Path, expected_src: str) -> Path | None:
    expected_stem = Path(expected_src).stem.casefold()

    matches = [
        file
        for file in video_files(folder)
        if file.stem.casefold() == expected_stem
    ]

    if not matches:
        return None

    if len(matches) > 1:
        names = ", ".join(
            p.relative_to(ROOT).as_posix()
            for p in matches
        )
        fail(
            f"Stem '{Path(expected_src).stem}' match nhiều file: {names}"
        )

    return matches[0]


def replace_data_src(html: str, old_src: str, new_src: str) -> str:
    """
    Replace only the exact data-src attribute value and leave the rest of the
    user's HTML formatting/code untouched.
    """
    pattern = re.compile(
        r'(data-src\s*=\s*)(["\'])'
        + re.escape(old_src)
        + r'\2'
    )

    replacement = lambda match: (
        f"{match.group(1)}{match.group(2)}"
        f"{new_src}{match.group(2)}"
    )

    updated, count = pattern.subn(replacement, html)

    if count == 0:
        fail(f"Không tìm thấy data-src cần update: {old_src}")

    return updated


def remove_unreferenced_videos(
    target_dir: Path,
    referenced_files: set[Path],
) -> None:
    """
    We must download a Drive folder to discover names, but only files listed
    in index.html should be published.
    """
    resolved_refs = {
        p.resolve()
        for p in referenced_files
    }

    for file in video_files(target_dir):
        if file.resolve() not in resolved_refs:
            print(
                "  REMOVE unreferenced:",
                file.relative_to(ROOT).as_posix(),
            )
            file.unlink()

    # Clean empty nested folders.
    for path in sorted(target_dir.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def main() -> None:
    ensure_tool("ffmpeg")

    if not INDEX_FILE.exists():
        fail(f"Không tìm thấy {INDEX_FILE}")

    html = INDEX_FILE.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")

    sources = soup.select(
        ".video-sources[data-drive-folder][data-target-dir]"
    )

    if not sources:
        fail(
            "Không tìm thấy video-sources nào có "
            "data-drive-folder + data-target-dir trong index.html."
        )

    print("=" * 72)
    print("TRUNG THU CHO EM — PREPARE DRIVE VIDEOS")
    print(f"Mapped Drive folders: {len(sources)}")
    print("=" * 72)

    total_expected = 0
    total_matched = 0

    for number, container in enumerate(sources, start=1):
        folder_url = (container.get("data-drive-folder") or "").strip()
        target_rel = (container.get("data-target-dir") or "").strip()

        if not folder_url:
            fail("Có video-sources thiếu data-drive-folder.")

        if not target_rel:
            fail("Có video-sources thiếu data-target-dir.")

        target_dir = (ROOT / target_rel).resolve()

        if not is_inside_video_root(target_dir):
            fail(
                f"data-target-dir không hợp lệ: {target_rel}. "
                "Chỉ cho phép assets/video/..."
            )

        nodes = container.select("[data-src]")

        expected_srcs = [
            (node.get("data-src") or "").strip()
            for node in nodes
            if (node.get("data-src") or "").strip()
        ]

        if not expected_srcs:
            fail(
                f"{target_rel} có Drive mapping nhưng không có data-src."
            )

        print()
        print("-" * 72)
        print(f"[{number}/{len(sources)}] {target_rel}")
        print(f"Expected videos: {len(expected_srcs)}")
        print("-" * 72)

        download_drive_folder(folder_url, target_dir)

        # Since matching ignores extension, ambiguity must be caught before
        # and after MOV conversion.
        assert_unique_stems(target_dir, "before MOV conversion")

        convert_all_mov(target_dir)

        assert_unique_stems(target_dir, "after MOV conversion")

        referenced: set[Path] = set()

        for old_src in expected_srcs:
            total_expected += 1

            actual = find_by_stem(target_dir, old_src)

            if actual is None:
                print("\nAvailable stems:", file=sys.stderr)
                for file in video_files(target_dir):
                    print(
                        f"  - {file.stem} "
                        f"({file.relative_to(ROOT).as_posix()})",
                        file=sys.stderr,
                    )

                fail(
                    "Không tìm thấy video theo NAME:\n"
                    f"  expected: {Path(old_src).stem}\n"
                    f"  folder  : {target_rel}"
                )

            actual_rel = actual.relative_to(ROOT).as_posix()
            referenced.add(actual.resolve())

            print(
                f"  MATCH: {Path(old_src).name}"
                f"  ->  {actual.name}"
            )

            if old_src != actual_rel:
                html = replace_data_src(
                    html,
                    old_src,
                    actual_rel,
                )

            total_matched += 1

        remove_unreferenced_videos(
            target_dir,
            referenced,
        )

        final_files = video_files(target_dir)

        print(f"  Published videos: {len(final_files)}")
        for file in final_files:
            mb = file.stat().st_size / 1024 / 1024
            print(
                f"    {file.relative_to(ROOT).as_posix()} "
                f"({mb:.1f} MB)"
            )

    INDEX_FILE.write_text(
        html,
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("DONE")
    print(f"Expected : {total_expected}")
    print(f"Matched  : {total_matched}")
    print("index.html updated with real deployed extensions.")
    print("=" * 72)


if __name__ == "__main__":
    main()
