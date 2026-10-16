"""Build the first-dialogue Kyobo 24px visibility PoC from the original ISO.

python scripts/build_firstline_poc.py --prepare
python scripts/build_firstline_poc.py --build

No executable instructions, file lengths, ISO directories or LBAs are changed.
Six temporary extended-Latin glyph slots are reused in this scoped PoC.
The full-game safety of these slot assignments is NOT established.
"""
from pathlib import Path
import argparse
import os
import hashlib
import importlib.metadata
import json
import math
import shutil
import struct
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/001_firstline_kyobo24'
FONT = Path(os.environ.get('DEATHJR_FONT', str(ROOT.parents[1] / 'Font/KyoboHandwriting2019.ttf')))
FONT_HASH = '92ed8baae0b00321994560281650f7a6ade89dcef6f8848fa511391720ce9aa5'
ELF_HASH = 'e521c889dd57db58fe0b081a8c653a750f8c5bf9db6cf184f3714be4d44057f1'
# syllable, temporary byte, original glyph index, measured source u/v/width
SLOTS = [('무', 0xD0, 149, 28.5, 342.5, 21.5),
         ('슨', 0x9C, 114, 181.5, 240.5, 20.5),
         ('일', 0x8C, 103, 1.5, 240.5, 23.5),
         ('이', 0xAE, 126, 141.5, 274.5, 22.5),
         ('야', 0xC6, 139, 115.5, 308.5, 24.5),
         ('?', 0x99, 111, 119.5, 240.5, 31.5)]
GLOBAL = 'PSP_GAME/USRDIR/STREAMS/GLOBAL_BINARY.STR'
UI = 'PSP_GAME/USRDIR/STREAMS/UI_BINARY.STR'
PXDS = [('PSP_GAME/USRDIR/LEVELS/GLOBAL/GLOBAL_00.PXD', 169168, 170192),
        ('PSP_GAME/USRDIR/LEVELS/UIENGINE/UIENGINE_99.PXD', 976576, 977600)]
EBOOT = 'PSP_GAME/SYSDIR/EBOOT.BIN'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def unpack_indices(raw, width, height):
    stride = max(16, width)
    assert len(raw) == stride * height
    return bytes(raw[((y // 8) * (stride // 16) + x // 16) * 128 + y % 8 * 16 + x % 16]
                 for y in range(height) for x in range(width))


def pack_indices(indices, width, height, original):
    stride = max(16, width)
    out = bytearray(original)
    for y in range(height):
        for x in range(width):
            dest = ((y // 8) * (stride // 16) + x // 16) * 128 + y % 8 * 16 + x % 16
            out[dest] = indices[y * width + x]
    return bytes(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    assert args.prepare != args.build, 'Choose exactly --prepare or --build'
    BUILD.mkdir(parents=True, exist_ok=True)
    iso_out = BUILD / 'DeathJr_KR_PoC_001_Kyobo24.iso'
    if args.build and iso_out.exists():
        raise RuntimeError('Existing ISO is preserved. Use a new version/output for a corrective build.')
    manifest = json.loads((ROOT / 'original/source_manifest.json').read_text('utf-8-sig'))
    source = ROOT / manifest['source']['path']
    assert digest(source) == manifest['source']['sha256']
    assert digest(FONT) == FONT_HASH
    inventory = json.loads((ROOT / 'docs/iso_inventory.json').read_text('utf-8'))
    by_path = {r['path']: r for r in inventory['files']}
    data = {}
    for name in [GLOBAL, UI, EBOOT] + [p for p, _, _ in PXDS]:
        p = ROOT / 'extracted/iso' / name
        assert digest(p) == by_path[name]['sha256'], name
        data[name] = p.read_bytes()
    elf = (ROOT / 'work/analysis/EBOOT.decrypted.elf').read_bytes()
    assert sha(elf) == ELF_HASH
    entry = json.loads((ROOT / 'workspace/text/firstline.json').read_text('utf-8'))
    assert entry['state'] == 'needs_review' and 'PoC' in entry['build_policy']
    old_text = bytes.fromhex(entry['source_hex'])
    offset = entry['decrypted_file_offset']
    assert offset == 0x1CADBC and elf[offset:offset + len(old_text)] == old_text
    codes = {c: byte for c, byte, *_ in SLOTS}
    encoded = bytearray()
    for c in entry['translation']:
        if c in codes:
            encoded.append(codes[c])
        elif c in ' ?':
            encoded.append(ord(c))
        else:
            raise ValueError(f'Unmapped codepoint U+{ord(c):04X}')
    assert len(encoded) <= len(old_text) - 1 and len(encoded) <= 31
    replacement = bytes(encoded).ljust(len(old_text), b'\0')
    modified_elf = elf[:offset] + replacement + elf[offset + len(old_text):]
    assert modified_elf[:offset] == elf[:offset] and modified_elf[offset + len(old_text):] == elf[offset + len(old_text):]
    # Existing instructions and all non-target ELF content remain unchanged.
    padded_elf = modified_elf.ljust(len(data[EBOOT]), b'\0')
    assert len(padded_elf) == len(data[EBOOT])
    with TTFont(FONT) as tf:
        cmap = tf.getBestCmap()
        assert all(ord(c) in cmap for c in codes)
    font = ImageFont.truetype(str(FONT), 24)
    palette = data[PXDS[0][0]][PXDS[0][1]:PXDS[0][1] + 1024]
    pal = [tuple(palette[i:i + 4]) for i in range(0, 1024, 4)]
    premul = [(r * a / 255, g * a / 255, b * a / 255, a) for r, g, b, a in pal]

    @lru_cache(maxsize=65536)
    def quantize(color):
        r, g, b, a = color
        v = (r * a / 255, g * a / 255, b * a / 255, a)
        return min(range(256), key=lambda i: sum((v[j] - premul[i][j]) ** 2 for j in range(4)))

    def rgba(indices, w, h):
        return Image.frombytes('RGBA', (w, h), bytes(c for i in indices for c in pal[i]))

    block_start = PXDS[0][2]
    original_block = data[PXDS[0][0]][block_start:block_start + 175088]
    assert data[PXDS[1][0]][PXDS[1][2]:PXDS[1][2] + 175088] == original_block
    assert data[UI][0x1109C0:0x1109C0 + 175088] == original_block
    assert data[UI][0x13B5C0:0x13B5C0 + 1024] == palette
    raw_base = original_block[:131072]
    original_indices = unpack_indices(raw_base, 256, 512)
    indices = bytearray(original_indices)
    clear = quantize((0, 0, 0, 0))
    boxes = []
    glyph_info = []
    new_widths = {}
    for c, code, ix, u, v, width in SLOTS:
        got = struct.unpack_from('<H', data[GLOBAL], 0x1D470 + code * 2)[0]
        assert got == ix
        metrics = struct.unpack_from('<3f', data[GLOBAL], 0x1CAA0 + ix * 12)
        assert metrics == (u / 256, v / 512, width / 256)
        left, top = math.floor(u), math.floor(v)
        right, bottom = math.ceil(u + width), math.ceil(v + 31)
        # Clear only the selected glyph's sampled interior; preserve separators.
        box = (left, top, right, bottom)
        boxes.append(box)
        font_bbox = font.getbbox(c, stroke_width=1)
        assert font_bbox[1] >= 0 and font_bbox[3] <= 31
        temp = Image.new('RGBA', (64, 31))
        draw = ImageDraw.Draw(temp)
        draw.text((4, 0), c, font=font, fill='white', stroke_width=1, stroke_fill='black')
        ink = temp.getchannel('A').getbbox()
        assert ink and ink[3] <= 31
        glyph = temp.crop((ink[0], 0, ink[2], 31))
        assert glyph.width + 1 <= right - left, (c, glyph.width, right - left)
        for y in range(top, bottom):
            for x in range(left, right):
                indices[y * 256 + x] = clear
        for y in range(31):
            for x in range(glyph.width):
                indices[(top + y) * 256 + left + 1 + x] = quantize(glyph.getpixel((x, y)))
        new_widths[ix] = min(width, glyph.width + 1)
        glyph_info.append({'char': c, 'byte': code, 'slot': ix, 'old_width': width,
                           'new_width': new_widths[ix], 'outlined_ink_size': [glyph.width, ink[3] - ink[1]],
                           'original_cell_sample_box': box})
    allowed = {y * 256 + x for l, t, r, b in boxes for y in range(t, b) for x in range(l, r)}
    assert all(a == b or i in allowed for i, (a, b) in enumerate(zip(original_indices, indices)))
    base_image = rgba(indices, 256, 512)
    mip_block = bytearray()
    mip_records = []
    pos = 0
    for level in range(10):
        w, h = max(1, 256 >> level), max(1, 512 >> level)
        size = max(16, w) * h
        old = original_block[pos:pos + size]
        old_linear = unpack_indices(old, w, h)
        assert pack_indices(old_linear, w, h, old) == old
        if level == 0:
            changed = bytes(indices)
        else:
            scaled = base_image.resize((w, h), Image.Resampling.LANCZOS)
            changed = bytearray(old_linear)
            factor = 1 << level
            for l, t, r, b in boxes:
                # Lanczos footprint; outside these areas retain original mip bytes.
                for y in range(max(0, t // factor - 3), min(h, math.ceil(b / factor) + 3)):
                    for x in range(max(0, l // factor - 3), min(w, math.ceil(r / factor) + 3)):
                        changed[y * w + x] = quantize(scaled.getpixel((x, y)))
        packed = pack_indices(changed, w, h, old)
        assert unpack_indices(packed, w, h) == bytes(changed)
        mip_block.extend(packed)
        mip_records.append({'level': level, 'width': w, 'height': h, 'stored_bytes': size,
                            'changed_bytes': sum(a != b for a, b in zip(old, packed))})
        pos += size
    assert pos == len(original_block) == 175088
    updated = {EBOOT: padded_elf}
    writers = []
    for name, palette_off, pixels_off in PXDS + [(UI, 0x13B5C0, 0x1109C0)]:
        old = data[name]
        assert old[palette_off:palette_off + 1024] == palette
        assert old[pixels_off:pixels_off + pos] == original_block
        updated[name] = old[:pixels_off] + mip_block + old[pixels_off + pos:]
        writers.append({'file': name, 'offset': pixels_off, 'size': pos, 'purpose': 'Six PoC glyphs and their mip footprints',
                        'expected_sha256': sha(original_block), 'new_sha256': sha(mip_block)})
    global_new = bytearray(data[GLOBAL])
    for ix, width in new_widths.items():
        off = 0x1CAA0 + ix * 12 + 8
        struct.pack_into('<f', global_new, off, width / 256)
        writers.append({'file': GLOBAL, 'offset': off, 'size': 4, 'purpose': 'PoC glyph advance width',
                        'expected_hex': data[GLOBAL][off:off + 4].hex(), 'new_hex': global_new[off:off + 4].hex()})
    updated[GLOBAL] = bytes(global_new)
    writers.append({'file': EBOOT, 'offset': 0, 'size': len(padded_elf),
                    'purpose': 'Decrypted ELF with only the target string changed; pad to original file length',
                    'expected_sha256': by_path[EBOOT]['sha256'], 'new_sha256': sha(padded_elf),
                    'plaintext_change': {'offset': offset, 'expected_hex': old_text.hex(), 'new_hex': replacement.hex()}})
    # Preview actual quantized glyphs from the final texture, not a font mockup.
    line = Image.new('RGBA', (240, 40))
    cursor = 0
    for c in entry['translation']:
        code = codes.get(c, ord(c))
        ix = struct.unpack_from('<H', global_new, 0x1D470 + code * 2)[0]
        u, v, width = struct.unpack_from('<3f', global_new, 0x1CAA0 + ix * 12)
        x, y, width = u * 256, v * 512, width * 256
        crop = base_image.crop((math.ceil(x), math.ceil(y), math.ceil(x + width), math.ceil(y + 31)))
        line.alpha_composite(crop, (cursor, 4))
        cursor += math.ceil(width)
    line = line.crop((0, 0, cursor + 1, 40))
    preview = Image.new('RGB', (760, 270), '#23303a')
    draw = ImageDraw.Draw(preview)
    draw.text((20, 15), 'First dialogue: Kyobo Handwriting 2019 / 24px / source atlas preview', fill='white')
    draw.text((20, 44), 'Original: What happened?', fill='white')
    preview.paste(line, (20, 75), line)
    enlarged = line.resize((line.width * 3, line.height * 3), Image.Resampling.NEAREST)
    preview.paste(enlarged, (20, 125), enlarged)
    draw.text((20, 253), 'Actual quantized glyphs. This is not an in-game screenshot.', fill='#bec9d2')
    preview.save(BUILD / 'firstline_preview.png')
    base_image.save(BUILD / 'font_atlas_poc.png')
    report = {'build_id': '001_firstline_kyobo24', 'scope': 'First-dialogue visibility PoC, not a release',
              'source_iso_sha256': manifest['source']['sha256'], 'font_sha256': FONT_HASH,
              'font_path': '../../Font/KyoboHandwriting2019.ttf', 'font_size': 24,
              'translation_entry': entry, 'encoded_hex': bytes(encoded).hex(), 'glyphs': glyph_info,
              'temporary_mapping_limit': 'Six extended-Latin slots replaced for five Hangul syllables and one question mark. Full-game collision freedom not established.',
              'preservation': 'Base-level pixels outside six glyph rectangles unchanged; ASCII and button slots unchanged; all non-target ELF bytes unchanged after decryption.',
              'mips': mip_records, 'writers': writers,
              'dependencies': {x: importlib.metadata.version(x) for x in ['Pillow', 'fonttools']},
              'runtime': 'Not performed; user will test original gameplay entry, without old savestates.'}
    save_json(BUILD / 'prepare_report.json', report)
    if args.prepare:
        print(json.dumps({'preview': str(BUILD / 'firstline_preview.png'), 'glyphs': glyph_info}, ensure_ascii=True, indent=2))
        return
    ranges = sorted((by_path[n]['lba'] * 2048, by_path[n]['lba'] * 2048 + len(v), n) for n, v in updated.items())
    assert all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:]))
    for n, value in updated.items():
        assert len(value) == by_path[n]['size']
        p = BUILD / 'modified_files' / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value)
    shutil.copyfile(source, iso_out)
    with iso_out.open('r+b') as f:
        for start, end, n in ranges:
            f.seek(start)
            assert sha(f.read(end - start)) == by_path[n]['sha256']
            f.seek(start)
            assert f.write(updated[n]) == end - start
    # Verify every logical file, plus every byte outside registered ISO writers.
    with iso_out.open('rb') as f:
        for item in inventory['files']:
            f.seek(item['lba'] * 2048)
            actual = sha(f.read(item['size']))
            assert actual == (sha(updated[item['path']]) if item['path'] in updated else item['sha256']), item['path']
    with source.open('rb') as a, iso_out.open('rb') as b:
        cursor = 0
        for start, end, _ in ranges + [(source.stat().st_size, source.stat().st_size, '')]:
            a.seek(cursor)
            b.seek(cursor)
            remaining = start - cursor
            while remaining:
                size = min(8 * 1024 * 1024, remaining)
                assert a.read(size) == b.read(size), 'Unexpected ISO modification'
                remaining -= size
            cursor = end
    assert source.stat().st_size == iso_out.stat().st_size
    report.update({'iso_path': str(iso_out.relative_to(ROOT)), 'iso_sha256': digest(iso_out),
                   'iso_size': iso_out.stat().st_size,
                   'verification': {'logical_files_checked': len(inventory['files']), 'modified_files': len(updated),
                                    'all_other_iso_bytes_identical': True, 'all_ten_mip_roundtrips': True,
                                    'elf_instructions_unchanged': True, 'runtime': 'Not performed'},
                   'modified_file_hashes': {n: sha(v) for n, v in updated.items()}})
    save_json(BUILD / 'build_report.json', report)
    print(json.dumps({k: report[k] for k in ['iso_path', 'iso_sha256', 'iso_size', 'verification']}, indent=2))


if __name__ == '__main__':
    main()
