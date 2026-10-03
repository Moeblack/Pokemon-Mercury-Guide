# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Package committed static assets; vendor only externally referenced images."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import argparse
import html
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'assets', 'data', 'items', 'pokemon', 'quests', 'trainers', 'maps'}
SUFFIXES = {'.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.json', '.md'}
IMAGE = re.compile(r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])', re.I)
LINK = re.compile(r'<a\b([^>]*?)href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>', re.I | re.S)


def local_target(page, url):
    parts = urlsplit(html.unescape(url))
    if parts.scheme or parts.netloc or not parts.path:
        return None
    return (page.parent / unquote(parts.path)).resolve()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vendor-assets', action='store_true', help='Copy referenced images from the local research tree into assets/vendor')
    args = parser.parse_args()
    out = ROOT / '_site'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    files = [ROOT / p for p in tracked if p and (Path(p).parts[0] in ALLOWED or p in {'index.html', 'README.html', 'README.md'}) and Path(p).suffix.lower() in SUFFIXES and 'runtime_trace' not in Path(p).parts]
    images = set()
    external_links = 0
    for source in files:
        target = out / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix != '.html':
            shutil.copy2(source, target)
            continue
        text = source.read_text(encoding='utf-8')
        def image(match):
            original = local_target(source, match[2])
            if original is None or original.is_relative_to(ROOT):
                return match[0]
            allowed = ROOT.parent / 'wiki_export' / 'assets'
            if not original.is_relative_to(allowed):
                raise ValueError(f'Unexpected external image: {original}')
            relative = original.relative_to(ROOT.parent)
            vendor = ROOT / 'assets' / 'vendor' / relative
            if args.vendor_assets:
                vendor.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, vendor)
            if not vendor.is_file():
                raise FileNotFoundError(f'Missing vendored image: {vendor}; run with --vendor-assets locally')
            published = out / vendor.relative_to(ROOT)
            published.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vendor, published)
            images.add(vendor.relative_to(ROOT).as_posix())
            url = Path(os.path.relpath(published, target.parent)).as_posix()
            return match[1] + html.escape(url, quote=True) + match[3]
        text = IMAGE.sub(image, text)
        def link(match):
            nonlocal external_links
            original = local_target(source, match[2])
            if original is not None and not original.is_relative_to(ROOT):
                external_links += 1
                return '<span class="source-reference" title="本地研究资料，不包含在网页版中">' + match[4] + '（本地资料）</span>'
            return match[0]
        target.write_text(LINK.sub(link, text), encoding='utf-8')
    (out / '.nojekyll').write_text('', encoding='utf-8')
    print(json.dumps({'static_files': len(files), 'vendored_images': len(images), 'local_evidence_links_as_text': external_links, 'output': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
