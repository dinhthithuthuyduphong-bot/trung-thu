from __future__ import annotations
import re, shutil, subprocess, sys, time
from collections import defaultdict
from pathlib import Path
import gdown
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
VIDEO_ROOT = (ROOT / "assets/video").resolve()

def fail(msg):
    print("\nERROR:", msg, file=sys.stderr)
    raise SystemExit(1)

def inside_video_root(p):
    try:
        p.resolve().relative_to(VIDEO_ROOT)
        return True
    except ValueError:
        return False

def replace_src(html, old, new):
    pat = re.compile(r'(data-src\s*=\s*)(["\'])' + re.escape(old) + r'\2')
    out, n = pat.subn(lambda m: f'{m.group(1)}{m.group(2)}{new}{m.group(2)}', html)
    if n == 0:
        fail(f"Không tìm thấy data-src để update: {old}")
    return out

def list_folder(url):
    try:
        items = gdown.download_folder(
            url=url, output=None, quiet=True,
            use_cookies=False, skip_download=True
        )
    except Exception as e:
        fail(f"Không list được Drive folder {url}\n{type(e).__name__}: {e}")
    if not items:
        fail(f"Drive folder rỗng/không truy cập được: {url}")
    return items

def download_one(file_id, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(1, 4):
        print(f"    download {attempt}/3: {dst.name}")
        try:
            r = gdown.download(
                id=str(file_id), output=str(dst),
                quiet=False, use_cookies=False
            )
            if r and dst.exists() and dst.stat().st_size > 0:
                return
            last = RuntimeError("gdown không tạo file hợp lệ")
        except Exception as e:
            last = e
        if dst.exists():
            dst.unlink()
        if attempt < 3:
            time.sleep(6)
    fail(
        f"Không tải được file: {dst.name}\n"
        f"Drive ID: {file_id}\n"
        f"https://drive.google.com/file/d/{file_id}/view\n"
        "Hãy đặt RIÊNG file này thành 'Anyone with the link -> Viewer'.\n"
        f"Chi tiết: {type(last).__name__}: {last}"
    )

def convert_mov(src):
    if src.suffix.lower() != ".mov":
        return src
    out = src.with_suffix(".mp4")
    if out.exists():
        out.unlink()
    print(f"    convert: {src.name} -> {out.name}")
    cmd = [
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-i",str(src),"-map","0:v:0","-map","0:a?",
        "-c:v","libx264","-preset","medium","-crf","22",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
        "-movflags","+faststart",str(out)
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        if out.exists():
            out.unlink()
        fail(f"FFmpeg lỗi với {src.name}: exit {e.returncode}")
    if not out.exists() or out.stat().st_size == 0:
        fail(f"MP4 tạo ra không hợp lệ: {out}")
    src.unlink()
    return out

def main():
    if shutil.which("ffmpeg") is None:
        fail("Không tìm thấy ffmpeg")
    if not INDEX.exists():
        fail("Không tìm thấy index.html")

    html = INDEX.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select(".video-sources[data-drive-folder][data-target-dir]")
    if not blocks:
        fail("Không có data-drive-folder + data-target-dir trong index.html")

    print("="*72)
    print("SELECTIVE DRIVE VIDEO DOWNLOAD")
    print("Mapped folders:", len(blocks))
    print("="*72)

    expected_total = downloaded_total = 0

    for i, block in enumerate(blocks, 1):
        url = (block.get("data-drive-folder") or "").strip()
        target_rel = (block.get("data-target-dir") or "").strip()
        target = (ROOT / target_rel).resolve()

        if not inside_video_root(target):
            fail(f"Target không hợp lệ: {target_rel}")

        expected = [
            (n.get("data-src") or "").strip()
            for n in block.select("[data-src]")
            if (n.get("data-src") or "").strip()
        ]
        if not expected:
            fail(f"{target_rel}: không có data-src")

        print(f"\n[{i}/{len(blocks)}] {target_rel}")
        print("Expected:", len(expected))
        print("Listing Drive metadata only...")

        items = list_folder(url)
        print("Drive entries:", len(items))

        by_stem = defaultdict(list)
        for item in items:
            by_stem[Path(str(item.path)).stem.casefold()].append(item)

        selected = []
        for old_src in expected:
            expected_total += 1
            stem = Path(old_src).stem.casefold()
            matches = by_stem.get(stem, [])
            if not matches:
                fail(f"Drive không có NAME '{Path(old_src).stem}' trong {url}")
            if len(matches) > 1:
                detail = "\n".join(f"- {x.path} (id={x.id})" for x in matches)
                fail(f"Có nhiều file cùng NAME '{Path(old_src).stem}':\n{detail}")
            selected.append((old_src, matches[0]))

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        for old_src, item in selected:
            drive_name = Path(str(item.path)).name
            dst = target / drive_name
            print(f"  MATCH {Path(old_src).name} -> {drive_name}")
            print(f"    Drive ID: {item.id}")

            download_one(item.id, dst)
            final = convert_mov(dst)
            new_src = final.relative_to(ROOT).as_posix()

            if old_src != new_src:
                html = replace_src(html, old_src, new_src)

            print(f"    READY: {new_src}")
            downloaded_total += 1

    INDEX.write_text(html, encoding="utf-8")
    print(f"\nDONE: {downloaded_total}/{expected_total} videos")

if __name__ == "__main__":
    main()
