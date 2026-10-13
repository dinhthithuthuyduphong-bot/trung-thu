from __future__ import annotations

import re
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
VIDEO_ROOT = (ROOT / "assets" / "video").resolve()

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".webm",
    ".mkv",
    ".avi",
}

DOWNLOAD_RETRIES = 3
RETRY_SECONDS = 6


def fail(message: str) -> None:
    print(f"\nERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def is_inside_video_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(VIDEO_ROOT)
        return True
    except ValueError:
        return False


def is_video(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def replace_data_src(
    html: str,
    old_src: str,
    new_src: str,
) -> str:
    pattern = re.compile(
        r'(data-src\s*=\s*)(["\'])'
        + re.escape(old_src)
        + r'\2'
    )

    def repl(match: re.Match[str]) -> str:
        quote = match.group(2)
        return (
            f"{match.group(1)}"
            f"{quote}{new_src}{quote}"
        )

    updated, count = pattern.subn(
        repl,
        html,
    )

    if count == 0:
        fail(
            f"Không tìm thấy data-src để update: "
            f"{old_src}"
        )

    return updated


def find_existing_file(
    target_dir: Path,
    expected_src: str,
) -> Path | None:
    """
    Check local/repo/cache FIRST.

    Rule:
    1. If exact data-src path exists -> use it immediately.
    2. Otherwise match by filename stem only, case-insensitive.
    3. If MP4 exists among multiple same-stem candidates -> prefer MP4.
    4. EXISTING files are NEVER converted.
    """

    exact_path = (ROOT / expected_src).resolve()

    if (
        is_inside_video_root(exact_path)
        and is_video(exact_path)
    ):
        return exact_path

    expected_stem = (
        Path(expected_src)
        .stem
        .casefold()
    )

    if not target_dir.exists():
        return None

    matches = [
        path
        for path in target_dir.iterdir()
        if (
            is_video(path)
            and path.stem.casefold() == expected_stem
        )
    ]

    if not matches:
        return None

    if len(matches) == 1:
        return matches[0]

    mp4_matches = [
        path
        for path in matches
        if path.suffix.lower() == ".mp4"
    ]

    if len(mp4_matches) == 1:
        return mp4_matches[0]

    names = ", ".join(
        sorted(path.name for path in matches)
    )

    fail(
        "Có nhiều file local cùng NAME nên không biết dùng file nào:\n"
        f"  stem : {Path(expected_src).stem}\n"
        f"  files: {names}"
    )


def list_drive_folder(folder_url: str):
    """
    Read Drive metadata only.
    No file is downloaded here.
    """

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
            "Không đọc được danh sách Drive folder:\n"
            f"{folder_url}\n"
            f"{type(exc).__name__}: {exc}"
        )

    if not entries:
        fail(
            f"Drive folder rỗng hoặc không truy cập được: "
            f"{folder_url}"
        )

    return entries


def build_drive_stem_index(entries):
    by_stem = defaultdict(list)

    for entry in entries:
        drive_path = Path(str(entry.path))
        by_stem[
            drive_path.stem.casefold()
        ].append(entry)

    return by_stem


def download_one(
    file_id: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    last_error = None

    for attempt in range(
        1,
        DOWNLOAD_RETRIES + 1,
    ):
        print(
            f"    DOWNLOAD {attempt}/{DOWNLOAD_RETRIES}: "
            f"{destination.name}"
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
                return

            last_error = RuntimeError(
                "gdown không tạo file hợp lệ."
            )

        except Exception as exc:
            last_error = exc

        if destination.exists():
            destination.unlink()

        if attempt < DOWNLOAD_RETRIES:
            print(
                f"    Retry sau {RETRY_SECONDS}s..."
            )
            time.sleep(RETRY_SECONDS)

    fail(
        "Không tải được file Drive sau "
        f"{DOWNLOAD_RETRIES} lần:\n"
        f"  file: {destination.name}\n"
        f"  id  : {file_id}\n"
        f"  url : "
        f"https://drive.google.com/file/d/{file_id}/view\n"
        f"  last: {type(last_error).__name__}: "
        f"{last_error}"
    )


def convert_downloaded_mov_to_mp4(
    source: Path,
) -> Path:
    """
    IMPORTANT:
    Called ONLY for a file downloaded in THIS run.

    Existing local/cache files are never converted.
    """

    if source.suffix.lower() != ".mov":
        return source

    output = source.with_suffix(".mp4")

    # If a corresponding MP4 somehow appeared meanwhile,
    # keep it and remove only this newly downloaded MOV.
    if (
        output.exists()
        and output.stat().st_size > 0
    ):
        print(
            f"    MP4 đã tồn tại sau download, "
            f"không convert: {output.name}"
        )

        source.unlink(
            missing_ok=True
        )

        return output

    print(
        f"    CONVERT newly downloaded: "
        f"{source.name} -> {output.name}"
    )

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
        subprocess.run(
            command,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        if output.exists():
            output.unlink()

        fail(
            f"FFmpeg convert lỗi với "
            f"{source.name}: exit "
            f"{exc.returncode}"
        )

    if (
        not output.exists()
        or output.stat().st_size == 0
    ):
        fail(
            f"MP4 tạo ra không hợp lệ: "
            f"{output}"
        )

    source.unlink()

    return output


def main() -> None:
    if shutil.which("ffmpeg") is None:
        fail("Không tìm thấy ffmpeg.")

    if not INDEX.exists():
        fail("Không tìm thấy index.html.")

    html = INDEX.read_text(
        encoding="utf-8"
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    blocks = soup.select(
        ".video-sources"
        "[data-drive-folder]"
        "[data-target-dir]"
    )

    if not blocks:
        fail(
            "Không tìm thấy Drive mapping "
            "trong index.html."
        )

    print("=" * 76)
    print(
        "TRUNG THU CHO EM — "
        "CHECK EXISTING FIRST"
    )
    print(
        f"Mapped folders: {len(blocks)}"
    )
    print("=" * 76)

    total = 0
    skipped = 0
    downloaded = 0

    for block_number, block in enumerate(
        blocks,
        start=1,
    ):
        folder_url = (
            block.get(
                "data-drive-folder"
            )
            or ""
        ).strip()

        target_rel = (
            block.get(
                "data-target-dir"
            )
            or ""
        ).strip()

        target_dir = (
            ROOT / target_rel
        ).resolve()

        if not is_inside_video_root(
            target_dir
        ):
            fail(
                f"Target không hợp lệ: "
                f"{target_rel}"
            )

        expected_srcs = [
            (
                node.get("data-src")
                or ""
            ).strip()
            for node in block.select(
                "[data-src]"
            )
            if (
                node.get("data-src")
                or ""
            ).strip()
        ]

        if not expected_srcs:
            fail(
                f"{target_rel}: "
                f"không có data-src."
            )

        print()
        print("-" * 76)
        print(
            f"[{block_number}/"
            f"{len(blocks)}] "
            f"{target_rel}"
        )
        print(
            f"Expected: "
            f"{len(expected_srcs)}"
        )
        print("-" * 76)

        # -------------------------------------------------
        # PASS 1:
        # Check all existing repo/cache files FIRST.
        # -------------------------------------------------

        missing = []

        for old_src in expected_srcs:
            total += 1

            existing = find_existing_file(
                target_dir,
                old_src,
            )

            if existing is None:
                missing.append(old_src)
                print(
                    f"  MISSING: "
                    f"{Path(old_src).stem}"
                )
                continue

            real_src = (
                existing
                .relative_to(ROOT)
                .as_posix()
            )

            print(
                f"  SKIP existing: "
                f"{existing.name}"
            )
            print(
                "       no download"
            )
            print(
                "       no convert"
            )

            if old_src != real_src:
                html = replace_data_src(
                    html,
                    old_src,
                    real_src,
                )

            skipped += 1

        # -------------------------------------------------
        # If everything already exists:
        # Don't even call Google Drive.
        # -------------------------------------------------

        if not missing:
            print(
                "  ALL FILES EXIST -> "
                "skip Drive folder entirely."
            )
            continue

        # -------------------------------------------------
        # PASS 2:
        # Only now list Drive metadata for missing files.
        # -------------------------------------------------

        print(
            f"  Need download: "
            f"{len(missing)} file(s)"
        )
        print(
            "  Listing Drive metadata..."
        )

        entries = list_drive_folder(
            folder_url
        )

        by_stem = (
            build_drive_stem_index(
                entries
            )
        )

        # -------------------------------------------------
        # PASS 3:
        # Download only missing files.
        # -------------------------------------------------

        for old_src in missing:
            stem = (
                Path(old_src)
                .stem
                .casefold()
            )

            matches = by_stem.get(
                stem,
                [],
            )

            if not matches:
                fail(
                    "Không tìm thấy file "
                    "trên Drive theo NAME:\n"
                    f"  name  : "
                    f"{Path(old_src).stem}\n"
                    f"  folder: {folder_url}"
                )

            if len(matches) > 1:
                details = "\n".join(
                    f"  - {entry.path} "
                    f"(id={entry.id})"
                    for entry in matches
                )

                fail(
                    "Có nhiều file Drive "
                    "cùng NAME:\n"
                    f"{details}"
                )

            entry = matches[0]

            drive_name = Path(
                str(entry.path)
            ).name

            destination = (
                target_dir
                / drive_name
            )

            # One last check immediately before download.
            existing = find_existing_file(
                target_dir,
                old_src,
            )

            if existing is not None:
                real_src = (
                    existing
                    .relative_to(ROOT)
                    .as_posix()
                )

                print(
                    f"  SKIP appeared meanwhile: "
                    f"{existing.name}"
                )

                if old_src != real_src:
                    html = (
                        replace_data_src(
                            html,
                            old_src,
                            real_src,
                        )
                    )

                skipped += 1
                continue

            print(
                f"  DOWNLOAD needed: "
                f"{Path(old_src).name}"
            )
            print(
                f"       Drive file: "
                f"{drive_name}"
            )
            print(
                f"       Drive ID  : "
                f"{entry.id}"
            )

            download_one(
                str(entry.id),
                destination,
            )

            final_file = (
                convert_downloaded_mov_to_mp4(
                    destination
                )
            )

            real_src = (
                final_file
                .relative_to(ROOT)
                .as_posix()
            )

            if old_src != real_src:
                html = replace_data_src(
                    html,
                    old_src,
                    real_src,
                )

            downloaded += 1

            size_mb = (
                final_file.stat().st_size
                / 1024
                / 1024
            )

            print(
                f"    READY: "
                f"{real_src} "
                f"({size_mb:.1f} MB)"
            )

    INDEX.write_text(
        html,
        encoding="utf-8",
    )

    print()
    print("=" * 76)
    print("DONE")
    print(f"Total      : {total}")
    print(f"Skip exists: {skipped}")
    print(f"Downloaded : {downloaded}")
    print("=" * 76)


if __name__ == "__main__":
    main()
