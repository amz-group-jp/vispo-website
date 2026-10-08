#!/usr/bin/env python3
"""Static verification only: never submits forms or publishes data."""
import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from build import ROOT, FORM_PAGES, configuration, excluded_page

class Document(HTMLParser):
    def __init__(self, contents):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs, self.canonicals, self.robots = set(), [], [], []
        self.errors = []
        self.title = self.head = False
        self.feed(contents)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.title |= tag == 'title'
        self.head |= tag == 'head'
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                self.errors.append('duplicate id: ' + attrs['id'])
            self.ids.add(attrs['id'])
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href'))
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.robots.append(attrs.get('content', ''))
        for key in ('href', 'src', 'action'):
            if attrs.get(key):
                self.refs.append((attrs[key], tag, attrs))
        for item in attrs.get('srcset', '').split(','):
            if item.strip():
                self.refs.append((item.strip().split()[0], tag, attrs))


def verify(mode):
    root = ROOT / 'dist'
    config = configuration()
    errors, warnings = [], []
    docs = {path.name: Document(path.read_text()) for path in root.glob('*.html')}
    def error(file, message):
        errors.append({'file': file, 'message': message})
    def check_reference(file, raw, tag='', attrs=None):
        attrs = attrs or {}
        url = urlsplit(raw)
        if url.scheme in {'tel', 'mailto', 'data'}:
            return
        if url.scheme and url.scheme not in {'http', 'https'}:
            error(file, 'Unsupported URL scheme')
            return
        if url.netloc:
            if tag == 'form' and url.hostname != 'ssl.form-mailer.jp':
                error(file, 'Unexpected external form action')
            if url.hostname in {'vispo-fit.com', 'www.vispo-fit.com'} and not (tag == 'link' and attrs.get('rel') == 'canonical'):
                error(file, 'Old-site dependency: ' + url.path)
            return
        relative = unquote(url.path)
        candidate = root / relative.lstrip('/') if relative.startswith('/') else root / Path(file).parent / relative
        if not relative:
            candidate = root / file
        elif relative.endswith('/'):
            candidate /= 'index.html'
        elif not candidate.suffix and not candidate.exists():
            candidate = candidate.with_suffix('.html')
        if not candidate.resolve().is_relative_to(root.resolve()):
            error(file, 'Reference escapes public directory')
        elif not candidate.is_file():
            error(file, 'Missing local target: ' + relative)
        elif url.fragment and candidate.name in docs and unquote(url.fragment) not in docs[candidate.name].ids:
            error(file, 'Missing anchor: ' + unquote(url.fragment))
    for name, doc in sorted(docs.items()):
        for message in doc.errors:
            error(name, message)
        if not doc.head or not doc.title:
            error(name, 'Missing head/title')
        route = '/' if name == 'index.html' else '/' + Path(name).stem
        if doc.canonicals != [config['production_origin'] + route]:
            error(name, 'Canonical mismatch')
        noindex = mode == 'preview' or excluded_page(Path(name).stem) or any(tag == 'form' for _, tag, _ in doc.refs)
        if len(doc.robots) != 1 or ('noindex' in doc.robots[0]) != noindex:
            error(name, 'Robots mode mismatch')
        for raw, tag, attrs in doc.refs:
            check_reference(name, raw, tag, attrs)
    for path in root.rglob('*.css'):
        for value in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)', path.read_text()):
            check_reference(str(path.relative_to(root)), value.strip())
    for path in root.rglob('*.js'):
        result = subprocess.run(['node', '--check', str(path)], capture_output=True, text=True)
        if result.returncode:
            error(path.name, 'JavaScript syntax check failed')
    redirects = root / '_redirects'
    if redirects.exists():
        exact = {}
        sources = set()
        rule_count = 0
        for number, line in enumerate(redirects.read_text().splitlines(), 1):
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            fields = line.split()
            if len(fields) != 3 or not fields[2].isdigit() or int(fields[2]) not in {200, 301, 302, 303, 307, 308}:
                error('_redirects', f'Invalid rule at line {number}')
                continue
            source, target, status = fields
            rule_count += 1
            if source in sources:
                error('_redirects', f'Duplicate source at line {number}: ' + source)
            sources.add(source)
            if not source.startswith('/'):
                error('_redirects', f'Invalid source at line {number}')
            if '*' not in target and not re.search(r':[A-Za-z_]', urlsplit(target).path):
                check_reference('_redirects', target)
            else:
                warnings.append('Dynamic redirect target requires deployed HTTP check')
            if source == target:
                error('_redirects', f'Self redirect at line {number}')
            if '*' not in source and ':' not in source and status != '200':
                exact[source] = target
        if rule_count > 2000:
            error('_redirects', 'More than 2000 redirect rules')
        for source in exact:
            seen, target = {source}, exact[source]
            while target in exact:
                if target in seen:
                    error('_redirects', 'Redirect cycle: ' + source)
                    break
                seen.add(target)
                target = exact[target]
        if any('*' in source or ':' in source for source in sources):
            warnings.append('Wildcard redirects require deployed HTTP checks')
    try:
        tree = ET.parse(root / 'sitemap.xml')
        for loc in tree.findall('.//{*}loc'):
            route = urlsplit(loc.text).path
            if excluded_page(route.strip('/')):
                error('sitemap.xml', 'Excluded form/error page in sitemap')
    except (ET.ParseError, OSError):
        error('sitemap.xml', 'Invalid or missing sitemap')
    forbidden = {'.git', 'tests', 'docs', 'scripts', '.github', '.env', 'site-config.json', 'README.md'}
    for path in root.rglob('*'):
        if any(part in forbidden or part.startswith('.') for part in path.relative_to(root).parts):
            error(str(path.relative_to(root)), 'Nonpublic artifact included')
    if not docs:
        error('dist', 'No HTML pages')
    report = {'ok': not errors, 'mode': mode, 'pages': len(docs), 'errors': errors, 'warnings': warnings,
              'limitations': ['Static HTML parsing is not browser validation', 'No form submissions, email delivery or external HTTP checks performed']}
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    (reports / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('preview', 'production'), default='preview')
    raise SystemExit(verify(parser.parse_args().mode))
