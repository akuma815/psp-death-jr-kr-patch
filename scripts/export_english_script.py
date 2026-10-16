"""Extract reviewed source text spans; never overwrite an edited translation CSV.

Offsets are decrypted ELF file offsets, not ISO or encrypted EBOOT offsets.
Run from any directory: python scripts/export_english_script.py
"""
import csv
import hashlib
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'workspace/text'
ELF = ROOT / 'work/analysis/EBOOT.decrypted.elf'
SPAN_GROUPS = [
    (0x1c2578, 0x1c288c, 'combo_and_cheat'),
    (0x1c29bc, 0x1c2ab4, 'weapon_name'),
    (0x1c3378, 0x1c35a0, 'cheat_notification'),
    (0x1c35ac, 0x1c372c, 'level_name'),
    (0x1c37f8, 0x1c38d4, 'options'),
    (0x1c3be4, 0x1c3ff0, 'npc_dialogue'),
    (0x1c5058, 0x1c52a0, 'upgrade_dialogue_tutorial'),
    (0x1c704c, 0x1c70d0, 'level_name'),
    (0x1c83a0, 0x1c8484, 'npc_dialogue'),
    (0x1c849c, 0x1c8748, 'npc_dialogue'),
    (0x1c8748, 0x1c8990, 'upgrade_notification'),
    (0x1caa4c, 0x1cc02c, 'dialogue_tutorial'),
    (0x1cc1b0, 0x1cc1dc, 'result'),
]
EXCLUDE = {b'reunited', b'seepflashback', b'guppyflashback', b'martyflashback',
           b'seepportals', b'guppyportals', b'martyportals'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def display(raw):
    return ''.join(chr(c) if 32 <= c < 127 else '{BYTE_%02X}' % c for c in raw)


def restore(s):
    parts = re.split(r'(\{BYTE_[0-9A-F]{2}\})', s)
    return b''.join(bytes([int(p[6:8], 16)]) if p.startswith('{BYTE_') else p.encode('ascii') for p in parts)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'DeathJr_English_Script.csv'
    if target.exists():
        raise SystemExit('Refusing to overwrite translation SSOT: ' + str(target))
    b = ELF.read_bytes()
    assert digest(b) == 'e521c889dd57db58fe0b081a8c653a750f8c5bf9db6cf184f3714be4d44057f1'
    rows, source_bytes = [], {'EBOOT.decrypted.elf': b}

    def add(source, offset, category, capacity=None, evidence='reviewed_text_pool'):
        data = source_bytes[source]
        end = data.index(0, offset)
        raw = data[offset:end]
        if not raw or raw in EXCLUDE:
            return
        assert len(raw) < 128 and all(c >= 32 for c in raw), (hex(offset), raw)
        row = {'id': ('ELF' if source == 'EBOOT.decrypted.elf' else Path(source).stem) + '_%08X' % offset,
               'translation': '\ubb34\uc2a8 \uc77c\uc774\uc57c?' if offset == 0x1cadbc and source == 'EBOOT.decrypted.elf' else '',
               'original': display(raw), 'category': category,
               'status': 'user_display_confirmed' if offset == 0x1cadbc and source == 'EBOOT.decrypted.elf' else 'untranslated',
               'notes': '', 'source_file': source, 'file_offset_hex': '0x%08X' % offset,
               'original_bytes': len(raw), 'fixed_buffer_bytes': capacity or '',
               'tokens': ' '.join(re.findall(r'\{BYTE_[0-9A-F]{2}\}|%(?:[-+0 #]*\d*(?:\.\d+)?[a-zA-Z])', display(raw))),
               'evidence': evidence, 'raw_hex': raw.hex()}
        assert restore(row['original']) == raw
        rows.append(row)

    for start, end, category in SPAN_GROUPS:
        p = start
        while p < end:
            if b[p] == 0:
                p += 4
                continue
            add('EBOOT.decrypted.elf', p, category)
            p = (b.index(0, p) + 4) & ~3
    for offset, category in [(0x1c3194, 'title'), (0x1c37ab, 'save_description'),
                             (0x1c5800, 'boss_name'), (0x1c5c54, 'boss_name'), (0x1c62d4, 'boss_name')]:
        add('EBOOT.decrypted.elf', offset, category)
    # Two independently identified 0x6c-stride UI template arrays; 32-byte text slots.
    for start, end, category in [(0x1d4381, 0x1d6619, 'menu'), (0x1d8e51, 0x1dbf41, 'upgrade_menu')]:
        for p in range(start, end + 1, 0x6c):
            raw = b[p:b.index(0, p)]
            if not raw or re.fullmatch(rb'Text[1-4]|100/100', raw):
                continue
            add('EBOOT.decrypted.elf', p, category, 32, 'ui_template_stride_0x6c_text_capacity_32')
    for name, offsets in [('UI_BINARY.STR', [0x830, 0x84d, 0x856]), ('SCHOOL_D2.STR', [0xaf4250, 0xaf4268])]:
        source = 'PSP_GAME/USRDIR/STREAMS/' + name
        source_bytes[source] = (ROOT / 'extracted/iso' / source).read_bytes()
        for p in offsets:
            add(source, p, 'title_menu' if name.startswith('UI') else 'level_embedded_dialogue', evidence='serialized_string_usage_not_yet_traced')
    rows.sort(key=lambda r: (r['source_file'] != 'EBOOT.decrypted.elf', r['source_file'], int(r['file_offset_hex'], 16)))
    assert len({r['id'] for r in rows}) == len(rows)
    # Preserve duplicate physical strings; references require independent reinsertion.
    duplicates = Counter(r['original'] for r in rows)
    for r in rows:
        if duplicates[r['original']] > 1:
            r['notes'] = 'duplicate_source_text: ' + str(duplicates[r['original']])
    with target.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with target.open(encoding='utf-8-sig', newline='') as f:
        readback = list(csv.DictReader(f))
    for expected, actual in zip(rows, readback):
        assert all(str(v) == actual[k] for k, v in expected.items())
        assert restore(actual['original']).hex() == actual['raw_hex']
    assert len(rows) == len(readback)
    (OUT / 'english_script_source.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    files = sorted((ROOT / 'extracted/iso').rglob('*'))
    report = {'rows': len(rows), 'unique_originals': len(duplicates), 'categories': dict(Counter(r['category'] for r in rows)),
              'csv_sha256': digest(target.read_bytes()), 'source_sha256': {k: digest(v) for k, v in source_bytes.items()},
              'validation': {'csv_readback': 'PASS', 'original_token_bytes_roundtrip': 'PASS', 'source_ranges': 'PASS', 'unique_ids': 'PASS'},
              'scope': 'Reviewed stored English text pools and two UI template arrays; not a proven complete audiovisual script.',
              'unresolved': ['PMF voiced dialogue and image lettering have not been transcribed.', 'STR scan is heuristic, not a complete serialized-object parser.', 'Dialogue event/line ordering and all runtime consumers are not yet mapped.', 'Full Hangul encoding and reinsertion remain to be implemented.'],
              'file_inventory': [{'path': p.relative_to(ROOT / 'extracted/iso').as_posix(), 'bytes': p.stat().st_size} for p in files if p.is_file()]}
    (ROOT / 'docs/english_script_export_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'file_inventory'}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
