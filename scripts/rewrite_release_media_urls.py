#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
from urllib.parse import quote
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

def warn(message):
    print(f'::warning::{message}')
    print(f'WARNING: {message}', file=sys.stderr)

def fail(message):
    print(f'::error::{message}')
    raise SystemExit(1)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--repository', required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--assets-file', required=True)
    return p.parse_args()

def replace_src(html, old, new):
    pat = re.compile(r'(data-src\s*=\s*)(["\'])' + re.escape(old) + r'\2')
    def repl(m):
        q = m.group(2); return f'{m.group(1)}{q}{new}{q}'
    out, n = pat.subn(repl, html)
    if n == 0:
        fail(f'Cannot update data-src: {old}')
    return out

def remove_span(html, src):
    pat = re.compile(r'[ \t]*<span\b[^>]*\bdata-src\s*=\s*(["\'])' + re.escape(src) + r'\1[^>]*>\s*</span>[ \t]*\r?\n?', re.I)
    out, n = pat.subn('', html, count=1)
    if n == 0:
        warn(f'Could not remove missing data-src entry: {src}')
    return out

def main():
    args = parse_args()
    if not INDEX.exists(): fail('index.html not found')
    ap = Path(args.assets_file)
    available = {x.strip() for x in ap.read_text(encoding='utf-8').splitlines() if x.strip()} if ap.exists() else set()
    html = INDEX.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    rewritten = missing = 0
    for block in soup.select('.video-sources[data-drive-folder][data-target-dir]'):
        target = (block.get('data-target-dir') or '').strip()
        if target not in GROUPS: continue
        group = GROUPS[target]
        for node in block.select('[data-src]'):
            old = (node.get('data-src') or '').strip()
            if not old: continue
            stem = Path(old).stem
            asset = f'{group}__{stem}.mp4'
            if asset not in available:
                warn(f'Release asset missing: {asset}; removing from deploy copy.')
                html = remove_span(html, old); missing += 1; continue
            url = f'https://github.com/{args.repository}/releases/download/{quote(args.tag, safe="")}/{quote(asset, safe="._-")}'
            html = replace_src(html, old, url); rewritten += 1
    INDEX.write_text(html, encoding='utf-8')
    print(f'Rewritten video URLs: {rewritten}')
    print(f'Missing release videos removed from deploy copy: {missing}')

if __name__ == '__main__':
    main()
