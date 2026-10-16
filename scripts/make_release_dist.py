"""Package the final text + subtitled movie ISO; no game images enter the ZIP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'DeathJr_KR_Patch_Final_20260926'
PATCH = 'DeathJr_KR_Final_20260926.xdelta'
BUILD = ROOT / 'build/009_final_20260926'
SOURCE = ROOT / 'original/Death Jr. (USA) (PSP) (PSN).iso'
TARGET = BUILD / 'DeathJr_KR_Final_20260926.iso'
SOURCE_HASH = '625c03e32b6757eb4e1ac382f43592d86778b3c943d4f26b95f1134ceee85ea3'
TARGET_HASH = 'c1ed1625cd3f9dac362655af0d332d49470fdab592c23cb5d81b778f4d52b842'
OUT = ROOT / 'dist' / NAME
ZIP = OUT.with_suffix('.zip')
XDELTA = ROOT.parents[1] / 'Tools/xdelta3-3.2.0-windows-x86_64/xdelta3.exe'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def write(path, value):
    path.write_text(value, encoding='utf-8-sig', newline='\r\n')

def package():
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                assert p.suffix.lower() not in ('.iso', '.pmf', '.mp4', '.ttf')
                item = zipfile.ZipInfo((Path(NAME)/p.relative_to(OUT)).as_posix(), (2026,9,26,0,0,0))
                item.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(item, p.read_bytes())

def main():
    assert not OUT.exists() and not ZIP.exists(), 'Existing distribution is protected'
    assert sha(SOURCE) == SOURCE_HASH and sha(TARGET) == TARGET_HASH
    report = json.loads((BUILD/'build_report.json').read_text(encoding='utf-8'))
    assert sha(ROOT/'workspace/text/DeathJr_English_Script_Korean.csv') == report['csv_sha256'], 'CSV changed since build'
    assert report['iso_sha256'] == TARGET_HASH
    (OUT/'tools').mkdir(parents=True)
    shutil.copy2(XDELTA, OUT/'tools/xdelta3.exe')
    shutil.copy2(XDELTA.with_name('README.md'), OUT/'tools/README_xdelta3.md')
    shutil.copy2(ROOT/'tools/xdelta3-3.2.0/LICENSE', OUT/'tools/LICENSE_xdelta3.txt')
    subprocess.run([str(XDELTA), '-e', '-9', '-S', 'none', '-A', '-s', str(SOURCE), str(TARGET), str(OUT/PATCH)], check=True)
    patch_hash = sha(OUT/PATCH)
    write(OUT/'apply.cmd', '''@echo off
setlocal
chcp 65001 >nul
if "%~1"=="" (
  echo Drag the original Death Jr. USA ISO onto apply.cmd.
  if /I not "%DJ_PATCH_NO_PAUSE%"=="1" pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply.ps1" "%~f1"
set "RESULT=%ERRORLEVEL%"
if /I not "%DJ_PATCH_NO_PAUSE%"=="1" pause
exit /b %RESULT%
''')
    # cmd.exe does not accept a UTF-8 BOM before @echo.
    cmd = OUT/'apply.cmd'
    cmd.write_bytes(cmd.read_bytes().removeprefix(b'\xef\xbb\xbf'))
    write(OUT/'apply.ps1', f'''param([Parameter(Mandatory=$true)][string]$InputIso)
$ErrorActionPreference = 'Stop'
$temporary = $null
try {{
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    $source = (Resolve-Path -LiteralPath $InputIso).Path
    $sourceItem = Get-Item -LiteralPath $source
    if ($sourceItem.Length -ne {SOURCE.stat().st_size} -or (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne '{SOURCE_HASH}') {{
        throw '지원하지 않는 원본입니다. Death Jr. USA ULUS10027 v1.01 원본 ISO와 안내문의 SHA-256을 확인하세요.'
    }}
    $output = Join-Path $sourceItem.DirectoryName ($sourceItem.BaseName + '_KR.iso')
    if (Test-Path -LiteralPath $output) {{ throw '결과 파일이 이미 있습니다. 기존 _KR.iso를 보관하거나 이름을 바꾼 뒤 다시 적용하세요.' }}
    $patch = Join-Path $PSScriptRoot '{PATCH}'
    $xdelta = Join-Path $PSScriptRoot 'tools/xdelta3.exe'
    if ((Get-FileHash -LiteralPath $patch -Algorithm SHA256).Hash -ne '{patch_hash}') {{ throw '패치 파일이 손상되었습니다.' }}
    $temporary = Join-Path $sourceItem.DirectoryName ('deathjr_patch_' + [Guid]::NewGuid().ToString('N') + '.tmp')
    & $xdelta -d -s $source $patch $temporary
    if ($LASTEXITCODE -ne 0) {{ throw "xdelta 오류: $LASTEXITCODE" }}
    if ((Get-Item -LiteralPath $temporary).Length -ne {TARGET.stat().st_size} -or (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash -ne '{TARGET_HASH}') {{ throw '패치 결과 검증 실패' }}
    Move-Item -LiteralPath $temporary -Destination $output
    $temporary = $null
    Write-Host '[완료] 한글 번역 및 동영상 자막 패치 적용 완료' -ForegroundColor Green
    Write-Host "결과: $output"
    exit 0
}} catch {{
    if ($temporary -and (Test-Path -LiteralPath $temporary)) {{ Remove-Item -LiteralPath $temporary -Force }}
    Write-Host "[실패] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}}
''')
    write(OUT/'README_적용방법.txt', f'''========================================================================
 Death Jr. 한국어 패치 Final (2026-09-26)
 PSP / 미국판 ULUS10027 / 내부 버전 1.01
========================================================================

[구성]
{PATCH} : 한글 번역 + 동영상 자막 통합 xdelta 패치
apply.cmd / apply.ps1 : Windows 적용 도구
tools/xdelta3.exe : xdelta 3.2.0 (Windows x64)
SHA256.txt : 배포 파일 체크섬
release_report.json : 적용 검증 기록

원본 ISO 및 패치 완료 ISO는 포함되어 있지 않습니다.

[적용 방법]
1. ZIP을 폴더에 모두 풉니다. tools 폴더도 함께 유지하세요.
2. 아래 SHA-256과 일치하는 미국판 원본 ISO를 준비합니다.
3. 원본 ISO를 apply.cmd 위로 끌어다 놓습니다.
4. 원본과 같은 폴더에 <원본 파일명>_KR.iso가 생성됩니다.
   원본은 변경하지 않으며 기존 결과 파일도 덮어쓰지 않습니다.

명령 프롬프트: apply.cmd "Death Jr. (USA) (PSP) (PSN).iso"
Windows x64 및 기본 Windows PowerShell이 필요합니다.
다른 판본, CSO, 이미 수정한 ISO에는 적용하지 마세요.

지원 원본 크기: {SOURCE.stat().st_size:,} 바이트
지원 원본 SHA-256: {SOURCE_HASH.upper()}
완성 ISO 크기: {TARGET.stat().st_size:,} 바이트
완성 ISO SHA-256: {TARGET_HASH.upper()}

[포함 내용]
- 사용자 최종 수정 게임 텍스트 708행 및 교보손글씨 한글 폰트
- GAMEINTRO, GAMEEND, REUNITED, TITLES 영상의 한국어 자막 59개
- 해당 영상의 원본 ATRAC 음성 보존
- 나머지 원본 영상 유지
텍스트와 영상이 통합된 패치이므로 별도의 영상 패치를 적용하지 않습니다.

[검증 범위]
텍스트/폰트 정적 검사, ISO 논리 파일 86개 읽기, MIPS CPU 1,422건,
자막 영상 프레임 길이/패딩/원본 음성 보존 검사를 통과한 빌드입니다.
원본에 xdelta를 적용한 결과를 완성 ISO와 바이트 단위로 비교하고,
한글과 공백이 포함된 경로에서 실제 apply.cmd 적용을 검사했습니다.
이 최종 빌드의 에뮬레이터 화면 및 처음부터 엔딩까지 전체 플레이 검수는
완료되지 않았습니다. Final은 이번 배포본의 이름이며 전체 플레이 검증을 뜻하지 않습니다.
문제 제보에는 장면, 사용 환경, 화면과 지원 원본 해시를 함께 기록해 주세요.

[도구 및 글꼴]
xdelta3: Copyright Joshua MacDonald, Apache License 2.0.
동봉 tools/LICENSE_xdelta3.txt 및 tools/README_xdelta3.md 참조.
https://github.com/jmacd/xdelta/releases/tag/v3.2.0
사용 글꼴: 교보손글씨 2019. 글꼴 원본 파일은 포함하지 않습니다.
비공식 팬 번역 패치이며 게임 및 관련 상표의 권리는 각 권리자에게 있습니다.
배포물에는 ISO 대신 패치와 적용 도구만 포함합니다.
''')
    release = {'name':NAME, 'source':{'bytes':SOURCE.stat().st_size,'sha256':SOURCE_HASH,'id':'ULUS10027','version':'1.01'},
               'target':{'bytes':TARGET.stat().st_size,'sha256':TARGET_HASH},
               'patch':{'file':PATCH,'bytes':(OUT/PATCH).stat().st_size,'sha256':patch_hash},
               'translation_rows':708, 'movie_subtitles':59, 'subtitled_movies':['GAMEINTRO','GAMEEND','REUNITED','TITLES'],
               'csv_sha256':report['csv_sha256'], 'runtime_full_game':'NOT VERIFIED', 'xdelta_apply':'pending'}
    (OUT/'release_report.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
    package()
    # Exercise the exact distributed entry point from a Unicode/space path.
    qa = ROOT/'work/temp/배포 적용 검증 20260926'
    assert not qa.exists()
    qa.mkdir()
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None
        z.extractall(qa)
    original = qa/'원본 게임.iso'
    shutil.copyfile(SOURCE,original)
    env = os.environ.copy();env['DJ_PATCH_NO_PAUSE']='1'
    entry = qa/NAME/'apply.cmd'
    def apply(input_path, expected):
        command = f'cmd.exe /d /s /c ""{entry}" "{input_path}""'
        result = subprocess.run(command,env=env,capture_output=True)
        assert (result.returncode==0)==expected, result.stdout+result.stderr
        return result.stdout.decode('utf-8',errors='replace')+result.stderr.decode('utf-8',errors='replace')
    log = apply(original,True)
    patched = original.with_name(original.stem+'_KR.iso')
    assert sha(patched)==TARGET_HASH and sha(original)==SOURCE_HASH
    with patched.open('rb') as a,TARGET.open('rb') as b:
        while True:
            x=a.read(1048576);y=b.read(1048576);assert x==y
            if not x:break
    log += '\nEXISTING OUTPUT REJECTION\n'+apply(original,False)
    assert sha(patched)==TARGET_HASH
    wrong = qa/'잘못된 원본.iso';wrong.write_bytes(b'unsupported source')
    log += '\nWRONG SOURCE REJECTION\n'+apply(wrong,False)
    assert not wrong.with_name(wrong.stem+'_KR.iso').exists()
    (ROOT/'qa/logs/release_20260926_apply.txt').write_text(log,encoding='utf-8')
    release.update(xdelta_apply='PASS: byte-for-byte equal', unicode_space_apply_cmd='PASS',
                   source_unchanged='PASS',existing_output_rejection='PASS',wrong_source_rejection='PASS')
    (OUT/'release_report.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
    # No recursive deletion; remove only this invocation's disposable test images.
    for p in (original,patched,wrong):p.unlink()
    hashes=''.join(f'{sha(p).upper()}  {p.relative_to(OUT).as_posix()}\n' for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256.txt')
    (OUT/'SHA256.txt').write_text(hashes,encoding='utf-8')
    package()
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None
        for p in OUT.rglob('*'):
            if p.is_file(): assert z.read((Path(NAME)/p.relative_to(OUT)).as_posix())==p.read_bytes()
    ZIP.with_suffix('.zip.sha256').write_text(f'{sha(ZIP).upper()}  {ZIP.name}\n',encoding='ascii')
    print(json.dumps({'zip':str(ZIP),'zip_bytes':ZIP.stat().st_size,'zip_sha256':sha(ZIP),'patch_sha256':patch_hash,'apply':'PASS'},indent=2))

if __name__=='__main__':main()
