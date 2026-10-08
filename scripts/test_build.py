#!/usr/bin/env python3
"""Small isolated regression checks for deployment safety."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build
import verify


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch_build = patch.object(build, 'ROOT', self.root)
        self.patch_verify = patch.object(verify, 'ROOT', self.root)
        self.patch_build.start()
        self.patch_verify.start()
        (self.root / 'site-config.json').write_text(json.dumps({'preview_origin': 'https://preview.example', 'production_origin': 'https://live.example', 'mode': 'preview'}))
        (self.root / 'index.html').write_text('<!doctype html><html><head><title>VISPO</title></head><body><main id="main"><a href="/web#form">Form</a></main></body></html>')
        (self.root / 'web.html').write_text('<!doctype html><html><head><title>Form</title></head><body><form id="form" action="https://ssl.form-mailer.jp/fm/service/Forms/complete"></form></body></html>')
        (self.root / 'assets').mkdir()
        (self.root / 'assets' / 'secret.env').write_text('NEVER PUBLIC')
        (self.root / 'README.md').write_text('NEVER PUBLIC')
        (self.root / '.env').write_text('NEVER PUBLIC')

    def tearDown(self):
        self.patch_verify.stop()
        self.patch_build.stop()
        self.temp.cleanup()

    def test_preview_default_and_allowlist(self):
        build.build()
        self.assertIn('noindex', (self.root / 'dist/index.html').read_text())
        self.assertIn('X-Robots-Tag: noindex', (self.root / 'dist/_headers').read_text())
        self.assertFalse((self.root / 'dist/site-config.json').exists())
        self.assertFalse((self.root / 'dist/.env').exists())
        self.assertFalse((self.root / 'dist/assets/secret.env').exists())
        self.assertEqual(verify.verify('preview'), 0)

    def test_production_preserves_form_noindex(self):
        build.build('production')
        self.assertNotIn('noindex', (self.root / 'dist/index.html').read_text())
        self.assertIn('noindex', (self.root / 'dist/web.html').read_text())
        self.assertNotIn('/web', (self.root / 'dist/sitemap.xml').read_text())
        self.assertEqual(verify.verify('production'), 0)

    def test_missing_anchor_is_rejected(self):
        build.build()
        path = self.root / 'dist/index.html'
        path.write_text(path.read_text().replace('/web#form', '/web#missing'))
        self.assertEqual(verify.verify('preview'), 1)

    def test_redirect_cycle_is_rejected(self):
        (self.root / '_redirects').write_text('/a /b 301\n/b /a 301\n')
        build.build()
        self.assertEqual(verify.verify('preview'), 1)


    def test_archive_receipt_excluded_and_favicon_preserved(self):
        for stem in ('archive', 'archive-123', 'receipt'):
            (self.root / (stem + '.html')).write_text('<html><head><title>Archive</title><meta name="robots" content="noindex, follow"></head><body></body></html>')
        (self.root / 'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        build.build('production')
        for stem in ('archive', 'archive-123', 'receipt'):
            self.assertIn('noindex, follow', (self.root / ('dist/' + stem + '.html')).read_text())
            self.assertNotIn('/' + stem, (self.root / 'dist/sitemap.xml').read_text())
        self.assertTrue((self.root / 'dist/favicon.svg').is_file())
        self.assertEqual(verify.verify('production'), 0)

    def test_og_origin_follows_build_mode(self):
        path = self.root / 'index.html'
        path.write_text(path.read_text().replace('</head>', '<meta property="og:url" content="https://live.example/"><meta property="og:image" content="https://live.example/assets/photo.jpg"></head>'))
        build.build()
        content = (self.root / 'dist/index.html').read_text()
        self.assertIn('content="https://preview.example/"', content)
        self.assertIn('content="https://preview.example/assets/photo.jpg"', content)
        self.assertIn('href="https://live.example/"', content)
        build.build('production')
        self.assertIn('content="https://live.example/assets/photo.jpg"', (self.root / 'dist/index.html').read_text())

    def test_missing_redirect_target_and_duplicate_are_rejected(self):
        (self.root / '_redirects').write_text('/old /missing 301\n/old /web#missing 301\n')
        build.build()
        self.assertEqual(verify.verify('preview'), 1)
        errors = json.loads((self.root / 'reports/verification.json').read_text())['errors']
        self.assertTrue(any('Duplicate source' in item['message'] for item in errors))
        self.assertTrue(any('Missing local target' in item['message'] for item in errors))
        self.assertTrue(any('Missing anchor' in item['message'] for item in errors))

if __name__ == '__main__':
    unittest.main()
