"""Read-only ISO audit for the two 006 movie defects; never runs PPSSPP."""
import io,json,hashlib,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python'))
import pycdlib
from export_movies import demux

def digest(b):return hashlib.sha256(b).hexdigest()
def inspect(b):
    offset=int.from_bytes(b[8:12],'big')
    errors=[];video=bytearray();table=[];stuffed=0
    assert b[:4]==b'PSMF' and offset==2048
    assert int.from_bytes(b[12:16],'big')==len(b)-offset
    assert (len(b)-offset)%2048==0
    for off in range(offset,len(b),2048):
        end=off+2048
        assert b[off:off+4]==b'\0\0\1\xba'
        assert b[off+4]&0xc4==0x44 and b[off+6]&4 and b[off+8]&4 and b[off+9]&1 and b[off+12]&3==3
        stuffing=b[off+13]&7
        assert b[off+14:off+14+stuffing]==b'\xff'*stuffing
        stuffed+=bool(stuffing);p=off+14+stuffing
        while p<end:
            if end-p<6 or b[p:p+3]!=b'\0\0\1':
                errors.append({'kind':'unframed_tail','pack_offset':hex(off),'bytes':end-p});break
            sid=b[p+3];n=int.from_bytes(b[p+4:p+6],'big');q=p+6+n
            assert q<=end
            if sid==0xe0:
                assert b[p+6]&0xc0==0x80
                video.extend(b[p+9+b[p+8]:q])
            elif sid==0xbf:
                data=b[p+6:q];assert data[:2]==b'\x01\xe0'
                tablebytes=int.from_bytes(data[14:16],'big');count=int.from_bytes(data[16:18],'big')
                assert tablebytes==2+4*count and len(data)==18+4*count
                for i in range(count):
                    ent=data[18+4*i:22+4*i]
                    assert ent[:2]==(b'\x04\x00' if i==count-1 else b'\x04\x80')
                    table.append(int.from_bytes(ent[2:],'big'))
            elif sid not in (0xbb,0xbd,0xbe):raise AssertionError(hex(sid))
            p=q
    # Independently use H.264 access-unit delimiters, not muxer's slice splitter.
    positions=[m.start() for m in re.finditer(b'\x00\x00\x00\x01\x09',video)]
    assert positions and positions[0]==0
    sizes=[v-u for u,v in zip(positions,positions[1:]+[len(video)])]
    assert len(sizes)==len(table)
    for i,(actual,declared) in enumerate(zip(sizes,table)):
        if actual>65535 or actual!=declared:
            errors.append({'kind':'frame_length_mismatch','frame':i,'actual':actual,'declared':declared})
    return {'sha256':digest(b),'packs':(len(b)-offset)//2048,'stuffed_packs':stuffed,'frames':len(sizes),'max_frame_bytes':max(sizes),'errors':errors,'result':'FAIL' if errors else 'PASS'}

def main():
    iso=ROOT/'build/007_movie_streamfix_kyobo24/DeathJr_KR_007_MovieStreamFix_Kyobo24.iso'
    before=digest(iso.read_bytes())
    assert before=='7238c1b245782767cf0e36da3208af5f404b605760a695ffece6deb58ee2796b'
    archive=pycdlib.PyCdlib();archive.open(str(iso))
    changed={'GAMEINTRO','GAMEEND','REUNITED','TITLES'};results=[];unchanged=[];samples={}
    for src in sorted((ROOT/'extracted/iso').rglob('*.PMF')):
        name=src.relative_to(ROOT/'extracted/iso').as_posix();buf=io.BytesIO()
        try:archive.get_file_from_iso_fp(buf,iso_path='/'+name)
        except pycdlib.pycdlibexception.PyCdlibInvalidInput:archive.get_file_from_iso_fp(buf,iso_path='/'+name+';1')
        b=buf.getvalue();original=src.read_bytes()
        if src.stem not in changed:
            assert b==original;unchanged.append({'path':name,'sha256':digest(b)});continue
        samples[src.stem]=b
        result=inspect(b);assert result['result']=='PASS',(name,result)
        assert demux(b)==demux(original),'Original ATRAC/first PTS differs'
        assert b[:12]==original[:12] and b[16:2048]==original[16:2048]
        expected=json.loads((ROOT/'workspace/video/manifest.json').read_text())['files']
        assert result['frames']==next(x['frames'] for x in expected if Path(x['mp4']).stem==src.stem)
        result.update(path=name,original_audio_and_pts='PASS',original_header_except_size='PASS',source_frame_count='PASS')
        results.append(result)
    archive.close()
    # Positive controls in memory: reproduce each defect without changing any file.
    # Old 006 artifacts may have been removed after the successful 007 build.
    controls=[]
    sample=samples['GAMEINTRO'];bf=None;padding=None
    for off in range(2048,len(sample),2048):
        p=off+14+(sample[off+13]&7)
        while p<off+2048:
            n=int.from_bytes(sample[p+4:p+6],'big')
            if sample[p+3]==0xbf and bf is None:bf=p
            if sample[p+3]==0xbe and n>=3 and p+6+n==off+2048 and padding is None:padding=p
            p+=6+n
    assert bf is not None and padding is not None
    bad=bytearray(sample);bad[bf+6+18+2:bf+6+18+4]=b'\x00\x00'
    row=inspect(bad);assert any(e['kind']=='frame_length_mismatch' for e in row['errors']);controls.append({'mutation':'zero first BF frame length in memory','errors':row['errors']})
    bad=bytearray(sample);n=int.from_bytes(bad[padding+4:padding+6],'big');bad[padding+4:padding+6]=(n-3).to_bytes(2,'big');bad[padding+6+n-3:padding+6+n]=bytes(3)
    row=inspect(bad);assert any(e['kind']=='unframed_tail' and e['bytes']==3 for e in row['errors']);controls.append({'mutation':'3 unframed zero tail bytes in memory','errors':row['errors']})
    assert digest(iso.read_bytes())==before
    report={'scope':'Static audit of actual ISO PMFs for 006 padding and BF frame-size defects; emulator not launched','iso_sha256':before,'modified_movies':results,'unchanged_original_movies':unchanged,'in_memory_negative_controls':controls,'old_006_artifacts':'Not present; regression uses explicit in-memory defect injection','runtime':'NOT RUN; intro user-confirmed previously; other movie playback not asserted'}
    out=ROOT/'qa/logs/007_movie_packet_audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'movies':[{k:v for k,v in x.items() if k in ['path','frames','max_frame_bytes','result']} for x in results],'unchanged':len(unchanged),'regression_errors':[len(x['errors']) for x in controls]},indent=2))
if __name__=='__main__':main()
