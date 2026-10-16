"""Extract the identified source ISO; verify every file against its ISO extent.

Run: python scripts/extract_iso.py
Dependency: python -m pip install --target tools/python pycdlib==1.14.0
Existing files must match; mismatches are never overwritten.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/python'))
import pycdlib


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((ROOT / 'original/source_manifest.json').read_text('utf-8-sig'))
    source = ROOT / manifest['source']['path']
    assert source.stat().st_size == manifest['source']['size_bytes']
    assert digest(source) == manifest['source']['sha256']
    dest = (ROOT / 'extracted/iso').resolve()
    iso = pycdlib.PyCdlib()
    iso.open(str(source))
    inventory = []
    try:
        with source.open('rb') as raw:
            for dirname, dirs, files in iso.walk(iso_path='/'):
                for name in sorted(files):
                    iso_path = dirname.rstrip('/') + '/' + name
                    rel = iso_path.lstrip('/').split(';')[0]
                    target = (dest / rel).resolve()
                    assert target.is_relative_to(dest)
                    record = iso.get_record(iso_path=iso_path)
                    assert not record.file_flags & 0x80, 'Multi-extent file unsupported'
                    size = record.data_length
                    lba = record.extent_location()
                    raw.seek(lba * 2048)
                    expected = hashlib.sha256()
                    remaining = size
                    while remaining:
                        chunk = raw.read(min(8 * 1024 * 1024, remaining))
                        assert chunk, 'Truncated extent'
                        expected.update(chunk)
                        remaining -= len(chunk)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        with target.open('xb') as out:
                            iso.get_file_from_iso_fp(out, iso_path=iso_path)
                    assert target.stat().st_size == size
                    assert digest(target) == expected.hexdigest(), rel
                    inventory.append({'path': rel, 'iso_path': iso_path, 'lba': lba,
                                      'size': size, 'sha256': expected.hexdigest()})
    finally:
        iso.close()
    report = {'source_sha256': manifest['source']['sha256'], 'extractor': 'pycdlib 1.14.0',
              'verification': 'All extracted files match raw ISO extents by size and SHA-256',
              'file_count': len(inventory), 'total_file_bytes': sum(x['size'] for x in inventory),
              'files': sorted(inventory, key=lambda x: x['path'])}
    (ROOT / 'docs/iso_inventory.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()
