#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil, subprocess, sys, time
from collections import defaultdict
from pathlib import Path
import gdown
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'index.html'
GROUPS = {
    'assets/video/nam2025': '2025',
    'assets/video/nam2026/goiqua': '2026-goiqua',
    'assets/video/nam2026/kick-off': '2026-kickoff',
    'assets/video/nam2026/chua': '2026-chua',
    'assets/video/nam2026/tongket': '2026-tongket',
}
DOWNLOAD_RETRIES = 3
RETRY_SECONDS = 5

def warn(message):
    print(f'::warning::{message}')
    print(f'WARNING: {message}', file=sys.stderr)

def fail(message):
    print(f'::error::{message}')
    print(f'ERROR: {message}', file=sys.stderr)
    raise SystemExit(1)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--target-dir', required=True)
    p.add_argument('--existing-assets-file', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--force', action='store_true')
    return p.parse_args()

def load_existing_assets(path):
    path = Path(path)
    if not path.exists():
        return set()
    return {x.strip() for x in path.read_text(encoding='utf-8').splitlines() if x.strip()}

def find_block(target_dir):
    if not INDEX.exists():
        fail('index.html not found')
    soup = BeautifulSoup(INDEX.read_text(encoding='utf-8'), 'html.parser')
    for block in soup.select('.video-sources[data-drive-folder][data-target-dir]'):
        if (block.get('data-target-dir') or '').strip() == target_dir:
            return block
    fail(f'No video-sources block found for target: {target_dir}')

def list_drive_folder(url):
    try:
        entries = gdown.download_folder(url=url, output=None, quiet=True, use_cookies=False, skip_download=True)
    except Exception as exc:
        fail(f'Cannot list Drive folder {url}\n{type(exc).__name__}: {exc}')
    return entries or []

def build_drive_index(entries):
    by_stem = defaultdict(list)
    for e in entries:
        p = Path(str(e.path))
        by_stem[p.stem.casefold()].append(e)
    return by_stem

def download_one(file_id, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        print(f'DOWNLOAD {attempt}/{DOWNLOAD_RETRIES}: {destination.name}', flush=True)
        try:
            result = gdown.download(id=file_id, output=str(destination), quiet=False, use_cookies=False)
            if result and destination.exists() and destination.stat().st_size > 0:
                return True
            last = RuntimeError('gdown did not produce a valid file')
        except Exception as exc:
            last = exc
        destination.unlink(missing_ok=True)
        if attempt < DOWNLOAD_RETRIES:
            time.sleep(RETRY_SECONDS)
    warn(f'Download failed: {destination.name}; Drive ID={file_id}; last={type(last).__name__}: {last}')
    return False

def transcode_to_mp4(source, output):
    source, output = Path(source), Path(output)
    if shutil.which('ffmpeg') is None:
        fail('ffmpeg not found')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    cmd = ['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-map','0:v:0','-map','0:a?','-c:v','libx264','-preset','medium','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        output.unlink(missing_ok=True)
        warn(f'FFmpeg failed for {source.name}: exit {exc.returncode}')
        return False
    return output.exists() and output.stat().st_size > 0

def main():
    args = parse_args()
    if args.target_dir not in GROUPS:
        fail(f'Unknown target dir: {args.target_dir}')
    group = GROUPS[args.target_dir]
    block = find_block(args.target_dir)
    folder_url = (block.get('data-drive-folder') or '').strip()
    if not folder_url:
        fail(f'Missing data-drive-folder for {args.target_dir}')
    expected = [(n.get('data-src') or '').strip() for n in block.select('[data-src]') if (n.get('data-src') or '').strip()]
    existing = load_existing_assets(args.existing_assets_file)
    outdir = Path(args.output_dir); outdir.mkdir(parents=True, exist_ok=True)
    wanted = []
    print('='*76); print(f'MEDIA GROUP: {group}'); print(f'Expected videos: {len(expected)}'); print('='*76)
    for src in expected:
        stem = Path(src).stem
        asset = f'{group}__{stem}.mp4'
        if asset in existing and not args.force:
            print(f'SKIP RELEASE EXISTS: {asset} (no Drive download, no convert)')
        else:
            wanted.append((stem, asset)); print(f'NEED: {asset}')
    if not wanted:
        print('Nothing to prepare. All required release assets already exist.')
        return
    entries = list_drive_folder(folder_url)
    by_stem = build_drive_index(entries)
    workdir = Path('_media_work') / group; workdir.mkdir(parents=True, exist_ok=True)
    produced = 0
    for stem, asset in wanted:
        matches = by_stem.get(stem.casefold(), [])
        if not matches:
            warn(f'Drive file not found by NAME: {stem}. Skipping {asset}.')
            continue
        if len(matches) > 1:
            warn(f'Multiple Drive files match NAME {stem}; skipping.')
            continue
        e = matches[0]
        drive_name = Path(str(e.path)).name
        downloaded = workdir / drive_name
        print(f'MATCH: {stem} -> {drive_name}'); print(f'Drive ID: {e.id}')
        if not download_one(str(e.id), downloaded):
            continue
        final = outdir / asset
        if downloaded.suffix.lower() == '.mp4':
            print(f'COPY MP4: {downloaded.name} -> {asset}')
            shutil.copy2(downloaded, final)
        else:
            print(f'CONVERT: {downloaded.name} -> {asset}')
            if not transcode_to_mp4(downloaded, final):
                continue
        size_mb = final.stat().st_size / 1024 / 1024
        print(f'READY: {asset} ({size_mb:.1f} MB)')
        produced += 1
        downloaded.unlink(missing_ok=True)
    print(f'Produced new/rebuilt assets: {produced}')

if __name__ == '__main__':
    main()
