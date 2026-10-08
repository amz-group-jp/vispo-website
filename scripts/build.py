#!/usr/bin/env python3
"""Dependency-free, allowlisted Cloudflare Pages build. Preview is the safe default."""
import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
FORM_PAGES = {'web', 'trial', 'inquiry', 'thanks', 'thank-you', 'complete', '404', 'receipt', 'archive'}
ASSET_EXTENSIONS = {'.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.pdf', '.mp4', '.webm'}


def excluded_page(stem):
    return stem in FORM_PAGES or stem.startswith("archive-")


def configuration():
    config = json.loads((ROOT / 'site-config.json').read_text())
    for key in ('preview_origin', 'production_origin'):
        value = config[key]
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError(f'Invalid {key}')
        config[key] = value.rstrip('/')
    return config


def build(mode='preview'):
    config = configuration()
    destination = ROOT / 'dist'
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    for source in sorted(ROOT.iterdir()):
        if source.is_file() and not source.is_symlink() and (source.suffix in {'.html', '.css', '.js'} or source.name in {'_headers', '_redirects', 'favicon.ico', 'favicon.svg', 'apple-touch-icon.png'}):
            shutil.copy2(source, destination / source.name)
    for source in sorted((ROOT / 'assets').rglob('*')):
        relative = source.relative_to(ROOT)
        if source.is_file() and not source.is_symlink() and source.suffix.lower() in ASSET_EXTENSIONS and not any(part.startswith('.') for part in relative.parts):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    locations = []
    noindex_pages = set()
    for page in sorted(destination.glob('*.html')):
        contents = page.read_text()
        excluded = excluded_page(page.stem) or bool(re.search(r'<form\b', contents, re.I))
        if excluded:
            noindex_pages.add(page.stem)
        noindex = mode == 'preview' or excluded
        source_origin = config['preview_origin'] if mode == 'preview' else config['production_origin']
        def social_url(match):
            tag = match.group(0)
            if re.search(r'property=[\"\']og:(?:url|image)[\"\']', tag, re.I):
                for origin_key in ('preview_origin', 'production_origin'):
                    tag = tag.replace(config[origin_key], source_origin)
            return tag
        contents = re.sub(r'<meta\b[^>]*>', social_url, contents, flags=re.I)
        existing_robots = re.search(r'<meta\b[^>]*\bname=[\"\']robots[\"\'][^>]*>', contents, re.I)
        preserve_robots = existing_robots.group(0) if excluded and existing_robots and 'noindex' in existing_robots.group(0).lower() else None
        contents = re.sub(r'<meta\b[^>]*\bname=[\"\']robots[\"\'][^>]*>', '', contents, flags=re.I)
        contents = re.sub(r'<link\b[^>]*\brel=[\"\']canonical[\"\'][^>]*>', '', contents, flags=re.I)
        route = '/' if page.stem == 'index' else '/' + page.stem
        canonical = config['production_origin'] + route
        robots_meta = preserve_robots if mode == 'production' and preserve_robots else f'<meta name="robots" content="{"noindex, nofollow" if noindex else "index, follow"}">'
        metadata = robots_meta + f'<link rel="canonical" href="{canonical}">'
        if '</head>' not in contents:
            raise ValueError(f'Missing head in {page.name}')
        page.write_text(contents.replace('</head>', metadata + '</head>', 1))
        if not excluded:
            locations.append(canonical)
    headers = (destination / '_headers').read_text() if (destination / '_headers').exists() else '/*\n'
    headers = re.sub(r'^\s*X-Robots-Tag:.*\n?', '', headers, flags=re.M | re.I)
    if mode == 'preview':
        headers += '\n/*\n  X-Robots-Tag: noindex, nofollow\n'
    else:
        if any(page == 'archive' or page.startswith('archive-') for page in noindex_pages):
            headers += '\n/archive*\n  X-Robots-Tag: noindex, nofollow\n'
        for page in sorted(noindex_pages):
            if page == 'archive' or page.startswith('archive-'):
                continue
            for route in ('/' + page, '/' + page + '.html'):
                headers += f'\n{route}\n  X-Robots-Tag: noindex, nofollow\n'
    (destination / '_headers').write_text(headers)
    # Allow crawling in preview so crawlers can see the noindex header/meta.
    (destination / 'robots.txt').write_text('User-agent: *\nAllow: /\n' + (f"Sitemap: {config['production_origin']}/sitemap.xml\n" if mode == 'production' else ''))
    (destination / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{escape(url)}</loc></url>\n' for url in locations) + '</urlset>\n')
    return {'mode': mode, 'pages': len(list(destination.glob('*.html'))), 'sitemap_urls': len(locations)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('preview', 'production'), default='preview')
    args = parser.parse_args()
    print(json.dumps(build(args.mode)))
