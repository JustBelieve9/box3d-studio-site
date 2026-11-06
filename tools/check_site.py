"""Check generated routes, assets, guide coverage and benchmark provenance."""
from collections import Counter
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Site(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.pages = {}
        self.page = None
        self.links = []
        self.stack = []

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if a.get('id'):
            self.ids.append(a['id'])
        if tag == 'main':
            self.page = (a['data-route'], a['data-lang'])
            assert self.page not in self.pages
            self.pages[self.page] = []
        if tag == 'section':
            assert a.get('data-key') and a.get('data-title'), a
            self.pages[self.page].append(a['data-key'])
        if tag == 'a':
            self.links.append(a.get('href', ''))
        if tag == 'img':
            assert 'alt' in a

    def handle_endtag(self, tag):
        if tag == 'main':
            self.page = None


before = (ROOT / 'index.html').read_bytes()
subprocess.run([sys.executable, str(ROOT / 'build.py')], check=True)
assert before == (ROOT / 'index.html').read_bytes(), 'Generated output differs from source; rebuild before publication'
site = Site()
site.feed(before.decode())
duplicates = [key for key, count in Counter(site.ids).items() if count != 1]
assert not duplicates, duplicates
assert len(site.pages) == 5
assert len(site.pages[('physx/guide', 'ru')]) == 24
for href in site.links:
    if href.startswith('#/'):
        path, _, query = href[2:].partition('?')
        lang = 'en' if path.startswith('en/') else 'ru'
        path = path[3:] if lang == 'en' else path
        assert (path, lang) in site.pages, href
        key = parse_qs(query).get('section', [None])[0]
        assert key is None or key in site.pages[(path, lang)], href
    elif href and not href.startswith(('https://', 'http://', '#', 'data:')):
        assert (ROOT / urlsplit(href).path).is_file(), href
reference = json.loads((ROOT / 'data' / 'physx-reference.json').read_text(encoding='utf-8'))
assert reference['version'] == '0.57.0'
assert len(reference['operators']) == 23
assert len({item['id'] for item in reference['operators']}) == 23
for name in ('benchmark-old', 'benchmark-new', 'benchmark-old-awake', 'benchmark-new-awake'):
    data = json.loads((ROOT / 'data' / (name + '.json')).read_text())
    assert len(data['cases']) == 3
    for case in data['cases']:
        assert (case['bodies'], case['frames'], case['workers'], case['substeps']) == (1152, 150, 12, 8)
        assert len(case['seconds']) == 3
        assert case['median'] == sorted(case['seconds'])[1]
        assert case['sleep_disabled'] == name.endswith('-awake')


def luminance(hexcolor):
    channels = [int(hexcolor[i:i+2], 16) / 255 for i in (0, 2, 4)]
    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in channels]
    return sum(x * weight for x, weight in zip(linear, (.2126, .7152, .0722)))


themes = [(['eef2f5', 'c0cad4', 'a1afbd', '54dec7', 'efb553'], ['12161b', '1a2027', '212a33']),
          (['172322', '354a48', '536763', '086a5a', '86510b'], ['f5f6f5', 'ffffff', 'e9efed'])]
contrasts = []
for foregrounds, backgrounds in themes:
    for foreground in foregrounds:
        for background in backgrounds:
            light, dark = sorted([luminance(foreground), luminance(background)], reverse=True)
            ratio = (light + .05) / (dark + .05)
            assert ratio >= 4.5, (foreground, background, ratio)
            contrasts.append(ratio)
print(f'SITE CHECKS PASSED: 5 routes, 24 guide sections, 23 commands, {len(site.links)} links, unique IDs, benchmark medians, min token contrast {min(contrasts):.2f}:1')
