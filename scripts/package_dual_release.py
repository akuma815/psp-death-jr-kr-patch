"""Package the unchanged final translation with two verified source deltas."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

SOURCES = {
    'PSN': '625c03e32b6757eb4e1ac382f43592d86778b3c943d4f26b95f1134ceee85ea3',
    'USA': '644a57ff208d17ee4ec22ff06546f6d1e66bb3c88ca5f6ea91abb9e8edc22ff1',
}
TARGET = 'c1ed1625cd3f9dac362655af0d332d49470fdab592c23cb5d81b778f4d52b842'

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psn', type=Path, required=True)
    p.add_argument('--usa', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True)
    p.add_argument('--old-package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    for label, path in [('PSN', a.psn), ('USA', a.usa)]:
        assert path.stat().st_size == 435159040 and sha(path) == SOURCES[label], label
    assert a.target.stat().st_size == 477913088 and sha(a.target) == TARGET
    a.output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(a.old_package / 'tools', a.output / 'tools')
    shutil.copy2(a.old_package / 'apply.cmd', a.output / 'apply.cmd')
    patches = {}
    for label, source in [('PSN', a.psn), ('USA', a.usa)]:
        name = f'DeathJr_KR_Final_20261016_{label}.xdelta'
        dest = a.output / name
        if label == 'PSN':
            shutil.copy2(a.old_package / 'DeathJr_KR_Final_20260926.xdelta', dest)
        else:
            subprocess.run([str((a.output / 'tools/xdelta3.exe').resolve()), '-e', '-9', '-S', 'none', '-A', '-s', str(source.resolve()), str(a.target.resolve()), str(dest.resolve())], check=True)
        patches[label] = {'name': name, 'sha256': sha(dest)}
    helper = (a.old_package / 'apply.ps1').read_text(encoding='utf-8-sig')
    start = helper.index('    if ($sourceItem.Length')
    end = helper.index('    $output =', start)
    choices = '\n'.join(f"        '{value}' {{ $patchName = '{patches[key]['name']}'; $patchHash = '{patches[key]['sha256']}' }}" for key, value in SOURCES.items())
    helper = helper[:start] + """    if ($sourceItem.Length -ne 435159040) { throw '지원하지 않는 원본 크기입니다.' }
    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    switch ($sourceHash) {
""" + choices + "\n        default { throw '지원하지 않는 원본 SHA-256입니다. 안내문의 지원 원본 2종을 확인하세요.' }\n    }\n" + helper[end:]
    helper = helper.replace("'DeathJr_KR_Final_20260926.xdelta'", '$patchName')
    helper = helper.replace(".Hash -ne 'e1c8d672355e6c41a712ba38c07d9502cfcb1c3496f68bcaad7c905b794f0394'", '.Hash -ne $patchHash')
    (a.output / 'apply.ps1').write_text(helper, encoding='utf-8-sig')
    root = Path(__file__).resolve().parents[1]
    shutil.copy2(root / 'docs/PATCH_GUIDE.txt', a.output / 'README_적용방법.txt')
    report = {'release': 'final-20261016', 'source_bytes': 435159040, 'sources': SOURCES, 'patches': patches, 'target_bytes': 477913088, 'target_sha256': TARGET, 'game_content': 'unchanged from final-20260926', 'runtime': 'not newly performed'}
    (a.output / 'release_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files = sorted(x for x in a.output.rglob('*') if x.is_file())
    (a.output / 'SHA256.txt').write_text('\n'.join(f'{sha(x)}  {x.relative_to(a.output).as_posix()}' for x in files) + '\n', encoding='utf-8')
    archive = a.output.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(a.output.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(a.output).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps({'archive': str(archive), 'sha256': sha(archive), 'bytes': archive.stat().st_size, **report}, indent=2))

if __name__ == '__main__':
    main()
