"""Rebuild final 009 text/runtime, recovering frozen movie assets from public release."""
from pathlib import Path
import argparse,hashlib,importlib.util,io,json,os,shutil,subprocess,sys,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python'))
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-iso',type=Path,required=True)
    parser.add_argument('--font',type=Path,required=True,help='Pinned KyoboHandwriting2019.ttf')
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--release-zip',type=Path,help='Optional previously downloaded final public release')
    args=parser.parse_args();source=args.source_iso.resolve();font=args.font.resolve();output=args.output_dir.resolve()
    if output.exists():raise SystemExit('Use a new output folder; existing outputs are never overwritten.')
    if any(output.is_relative_to(ROOT/p) for p in ['scripts','workspace','docs','inputs','tools']):
        raise SystemExit('Output must be outside source/dependency folders.')
    manifest=json.loads((ROOT/'docs/rebuild/INPUTS.json').read_text(encoding='utf-8'))
    if source.stat().st_size!=manifest['sourceBytes'] or sha(source)!=manifest['sourceSHA256']:
        raise SystemExit('Unsupported original ISO. The final patch requires the pinned USA/PSN source.')
    if sha(font)!=manifest['font']['sha256']:raise SystemExit('Kyobo font hash differs from the final build.')
    for row in manifest['files']:
        p=ROOT/row['path']
        if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise SystemExit('Frozen source input differs: '+row['path'])
    import pycdlib
    spec=importlib.util.find_spec('ziglang')
    if spec is None:raise SystemExit('Install requirements-rebuild.txt into tools/python first.')
    zig=Path(next(iter(spec.submodule_search_locations)))/'zig.exe'
    if not zig.is_file():raise SystemExit('This validated build path requires the Windows Zig 0.13.0 wheel.')
    output.mkdir(parents=True);bootstrap=output/'bootstrap';bootstrap.mkdir()
    archive=args.release_zip.resolve() if args.release_zip else bootstrap/'final_release.zip'
    if not args.release_zip:urllib.request.urlretrieve(manifest['releaseURL'],archive)
    if sha(archive)!=manifest['releaseSHA256']:raise SystemExit('Downloaded release ZIP hash mismatch.')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise SystemExit('Release ZIP CRC error.')
        wanted=['DeathJr_KR_Final_20260926.xdelta','xdelta3.exe']
        for name in wanted:
            matches=[i for i in z.infolist() if Path(i.filename).name==name]
            if len(matches)!=1:raise SystemExit('Release bootstrap member missing or ambiguous: '+name)
            (bootstrap/name).write_bytes(z.read(matches[0]))
    recovered=bootstrap/'public_final.iso'
    with (bootstrap/'xdelta.log').open('w',encoding='utf-8') as log:
        run=subprocess.run([str(bootstrap/'xdelta3.exe'),'-d','-s',str(source),str(bootstrap/'DeathJr_KR_Final_20260926.xdelta'),str(recovered)],stdout=log,stderr=subprocess.STDOUT)
    if run.returncode or sha(recovered)!=manifest['targetSHA256']:raise SystemExit('Public final-release application did not reproduce the expected ISO.')
    project=output/'project';ignore=shutil.ignore_patterns('__pycache__','*.pyc')
    for folder in ['scripts','workspace','docs']:shutil.copytree(ROOT/folder,project/folder,ignore=ignore)
    (project/'original').mkdir();(project/'build').mkdir()
    original_manifest={'source':{'path':str(source),'size_bytes':manifest['sourceBytes'],'sha256':manifest['sourceSHA256']}}
    (project/'original/source_manifest.json').write_text(json.dumps(original_manifest,indent=2),encoding='utf-8')
    iso=pycdlib.PyCdlib();iso.open(str(recovered))
    def get(path):
        buf=io.BytesIO()
        try:iso.get_file_from_iso_fp(buf,iso_path='/'+path)
        except pycdlib.pycdlibexception.PyCdlibInvalidInput:iso.get_file_from_iso_fp(buf,iso_path='/'+path+';1')
        return buf.getvalue()
    saved=json.loads((project/'workspace/video/verified_pmf_007/manifest.json').read_text(encoding='utf-8'))
    for row in saved['pmf']:
        data=get(row['path'])
        if digest(data)!=row['sha256']:raise SystemExit('Recovered frozen PMF differs: '+row['path'])
        (project/'workspace/video/verified_pmf_007'/Path(row['path']).name).write_bytes(data)
    recipe=json.loads((ROOT/'inputs/restore_original_elf.json').read_text(encoding='utf-8'))
    final=get('PSP_GAME/SYSDIR/EBOOT.BIN');iso.close()
    if digest(final)!=recipe['inputFinalELF_SHA256']:raise SystemExit('Bootstrap executable differs.')
    original=bytearray(recipe['originalDecryptedBytes'])
    for row in recipe['copies']:
        a=row['destination'];b=a+row['bytes'];start=row['source'];end=start+row['bytes']
        if min(a,start)<0 or b>len(original) or end>len(final):raise SystemExit('Invalid ELF section relocation recipe.')
        original[a:b]=final[start:end]
    for row in recipe['writes']:
        data=bytes.fromhex(row['restoreHex']);a=row['offset'];b=a+len(data)
        if a<0 or b>len(original) or digest(original[a:b])!=row['beforeSHA256']:raise SystemExit('ELF inverse-write source mismatch.')
        original[a:b]=data
    if digest(original)!=recipe['originalDecryptedSHA256']:raise SystemExit('Recovered original decrypted ELF hash mismatch.')
    analysis=project/'work/analysis';analysis.mkdir(parents=True)
    (analysis/'EBOOT.decrypted.elf').write_bytes(original)
    env=os.environ.copy();env['DEATHJR_FONT']=str(font);env['DEATHJR_ZIG']=str(zig)
    env['PYTHONPATH']=str(ROOT/'tools/python')+os.pathsep+env.get('PYTHONPATH','')
    for name in ['extract_iso.py','build_final_009.py']:
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            run=subprocess.run([sys.executable,'-X','utf8','-B',str(project/'scripts'/name)],cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT)
        if run.returncode:raise SystemExit(name+' failed; see its build log.')
        print('PASS',name,flush=True)
    final_dir=project/'build/009_final_20260926'
    result_iso=final_dir/'DeathJr_KR_Final_20260926.iso'
    if sha(result_iso)!=manifest['targetSHA256']:raise SystemExit('Source rebuild differs from the pinned final release.')
    cpu=json.loads((final_dir/'text_mips_runtime_verification.json').read_text(encoding='utf-8'))
    if not cpu['all_pass'] or cpu['cases']!=1422:raise SystemExit('MIPS CPU cases did not all pass.')
    if sha(source)!=manifest['sourceSHA256']:raise SystemExit('Original ISO changed during build.')
    report=json.loads((final_dir/'build_report.json').read_text(encoding='utf-8'))
    result={'status':'PASS','sourceSHA256':manifest['sourceSHA256'],'finalSHA256':sha(result_iso),'finalBytes':result_iso.stat().st_size,
            'textAndRuntimeBuiltFromSource':True,'translationRows':708,'cpuCases':cpu['cases'],'frozenMoviesRecoveredFromPublicPatch':len(saved['pmf']),
            'logicalFilesVerified':len(report['logical_files']),'originalUnchanged':True,'runtimeSceneOrFullPlaythrough':'not performed'}
    (output/'REBUILD_RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('FINAL PASS',sha(result_iso),'MIPS cases',cpu['cases'],flush=True)

if __name__=='__main__':main()
