"""Offline final-document links, source baseline and evidence consistency checks.

This validates technical records, not user participation or individual authorship.
It does not load .env, contact providers or spend AI quota.
"""
import ast
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / 'docs/final'


def read_json(path):
    return json.loads(path.read_text())


def literal_assignment(path, name):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f'Missing literal {name}: {path}')


def main():
    manifest = read_json(FINAL / 'manifest.json')
    checked = 0
    for relative in manifest['documents']:
        path = ROOT / relative
        assert path.is_file(), f'Missing document: {relative}'
        content = path.read_text()
        for match in re.finditer(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', content):
            target = match.group(1).strip().strip('<>')
            if target.startswith('#') or urlsplit(target).scheme:
                continue
            target = unquote(target.split('#', 1)[0])
            resolved = (path.parent / target).resolve()
            assert resolved.is_relative_to(ROOT), f'Outside project: {relative}: {target}'
            assert resolved.exists(), f'Broken link: {relative}: {target}'
            checked += 1
        # Catch private values, not references to environment variable names.
        assert not re.search(r'(?i)(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{20,})', content), f'Possible secret: {relative}'

    for relative, expected in manifest['sourceSha256'].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, f'Runtime source changed; update document baseline: {relative}'

    assert list(literal_assignment(ROOT / 'backend/models.py', 'INTERESTS')) == manifest['interests']
    assert literal_assignment(ROOT / 'backend/config.py', 'POLICY_VERSION') == manifest['policyVersion']
    assert literal_assignment(ROOT / 'backend/config.py', 'CONSENT_VERSION') == manifest['consentVersion']
    assert literal_assignment(ROOT / 'backend/comparison.py', 'VERSION') == manifest['comparisonVersion']
    classification = read_json(ROOT / 'data/recommendation/classification-v2.json')
    assert classification['version'] == manifest['classificationVersion']
    assert len(classification['entries']) == manifest['products']['classifiedProducts']
    assert sum(len(e['matches']) for e in classification['entries'].values()) == manifest['products']['claimLinks']
    knowledge = read_json(ROOT / 'backend/nutrition-knowledge.json')
    assert knowledge['version'] == manifest['knowledgeVersion']
    assert len(knowledge['cards']) == manifest['products']['knowledgeCards']
    assert len(knowledge['sources']) == manifest['products']['knowledgeSources']

    with sqlite3.connect(f'file:{ROOT / "data/products/products.sqlite3"}?mode=ro', uri=True) as db:
        assert db.execute('SELECT count(*) FROM products').fetchone()[0] == manifest['products']['collected']
        public = db.execute("SELECT count(*) FROM label_reviews WHERE data_review_status='verified'").fetchone()[0]
        assert public == manifest['products']['public']
        held = [r[0] for r in db.execute("SELECT product_id FROM label_reviews WHERE data_review_status!='verified' ORDER BY product_id")]
        assert held == manifest['products']['heldIds']
        available = db.execute("SELECT count(*) FROM product_thumbnails WHERE status='available'").fetchone()[0]
        assert available == manifest['products']['thumbnails']
        public_images = db.execute("SELECT count(*) FROM product_thumbnails t JOIN label_reviews r ON r.product_id=t.product_id WHERE t.status='available' AND r.data_review_status='verified'").fetchone()[0]
        assert public_images == manifest['products']['publicThumbnails']

    api = read_json(FINAL / 'evidence/acceptance-api.json')
    assert api['passed'] and len(api['trials']) == 3
    for name in manifest['mustIds'] + ['S01']:
        checks = [c for t in api['trials'] for c in t['checks'] if c['id'] == name]
        count = sum(c['passed'] for c in checks)
        assert len(checks) == 3 and count >= 2, name
        assert api['summary'][name] == {'attempts': 3, 'successes': count}, name
    assert api['summary']['M04']['successes'] == 2, 'Update written failure/success report if evidence changes'
    for key in ('policyVersion', 'consentVersion'):
        assert api['health'][key] == manifest[key]
    assert api['health']['aiProvider'] == manifest['provider']
    assert api['health']['aiModel'] == manifest['model']
    browser = read_json(FINAL / 'evidence/acceptance-browser.json')
    assert browser['passed'] and len(browser['trials']) == 3
    assert all(t['M01'] and t['M02'] for t in browser['trials'])
    release = read_json(FINAL / 'evidence/production-release-2026-10-23.json')
    local = read_json(FINAL / 'evidence/local-checks.json')
    assert release['commit'] == local['baselineCommit'] == manifest['baselineCommit']
    assert release['passed'] and all(c['passed'] for c in local['checks'])
    assert len(manifest['team']) == 5 and len(set(manifest['team'])) == 5
    assert manifest['confirmedAccount'] == {'sayknow': '이승현'}
    assert manifest['submissionReady'] is False and len(manifest['pendingEvidence']) == 3

    # Evidence may contain public field names; raw session credentials must not be saved.
    def inspect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert key.lower() not in {'token', 'api_key', 'apikey', 'authorization', 'x-session-token'}, 'Credential field in evidence'
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    for path in (FINAL / 'evidence').glob('*.json'):
        inspect(read_json(path))
    print(json.dumps({'technicalDocumentationChecksPassed': True,
                      'documents': len(manifest['documents']), 'localLinks': checked,
                      'runtimeSourceHashes': len(manifest['sourceSha256']),
                      'submissionReady': manifest['submissionReady'],
                      'pendingEvidence': manifest['pendingEvidence']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
