"""Preserve source PMF, demux PSP ATRAC3+ and remux lossless H264 to editing MP4."""
import sys,json,hashlib,subprocess,struct,re
from pathlib import Path
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/video'
FF=imageio_ffmpeg.get_ffmpeg_exe()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pts(b):return ((b[0]>>1&7)<<30)|(b[1]<<22)|((b[2]>>1)<<15)|(b[3]<<7)|(b[4]>>1)
def demux(b):
    audio={};first={};p=int.from_bytes(b[8:12],'big')
    while p<len(b)-6:
        p=b.find(b'\0\0\1',p)
        if p<0:break
        sid=b[p+3]
        if sid==0xba:p+=14+(b[p+13]&7);continue
        if sid==0xb9:break
        n=int.from_bytes(b[p+4:p+6],'big');end=p+6+n
        if sid==0xbd or 0xe0<=sid<=0xef:
            assert b[p+6]&0xc0==0x80
            q=p+9+b[p+8];stamp=pts(b[p+9:p+14]) if b[p+7]&0x80 else None
            key='video' if sid!=0xbd else str(b[q])
            if stamp is not None:first.setdefault(key,stamp)
            if sid==0xbd:
                channel=b[q];skip=5 if 0xb0<=channel<=0xbf else 4
                audio.setdefault(channel,bytearray()).extend(b[q+skip:end])
        p=end
    return audio,first
def run(args,log):
    p=subprocess.run([FF,'-hide_banner','-nostdin',*args],capture_output=True)
    log.write_bytes(p.stderr)
    if p.returncode:raise RuntimeError(str(log))
    return p.stderr.decode(errors='replace')
def main():
    for d in ['editable_mp4','audio_wav','audio_atrac','logs']:(OUT/d).mkdir(parents=True,exist_ok=True)
    assert not (OUT/'manifest.json').exists(),'Preserve existing export'
    inv=json.loads((ROOT/'docs/iso_inventory.json').read_text())['files'];original={x['path']:x for x in inv}
    reports=[]
    for src in sorted((ROOT/'extracted/iso').rglob('*.PMF')):
        rel=src.relative_to(ROOT/'extracted/iso').as_posix();assert sha(src)==original[rel]['sha256']
        name=src.stem;out=OUT/'editable_mp4'/f'{name}.mp4';assert not out.exists()
        au,times=demux(src.read_bytes());r={'source':rel,'source_sha256':sha(src),'first_pts_90khz':times,'audio':[]}
        wavs=[]
        for ch,data in au.items():
            pos=0;frames=[];codes=set()
            while pos<len(data):
                assert data[pos:pos+2]==b'\x0f\xd0',(name,pos,data[pos:pos+8].hex())
                c1,c2=data[pos+2:pos+4];size=(((c1&3)<<8)|(c2*8))+16
                assert pos+size<=len(data),(name,'partial frame',pos,len(data))
                codes.add((c1,c2));frames.append(data[pos+8:pos+size]);pos+=size
            assert len(codes)==1; c1,c2=next(iter(codes))
            header=bytearray(96);header[:8]=b'EA3\x01\x00\x60\xff\xff';header[32:36]=bytes([1,0,c1,c2])
            oma=OUT/'audio_atrac'/f'{name}_ch{ch}.oma';oma.write_bytes(header+b''.join(frames))
            wav=OUT/'audio_wav'/f'{name}.wav' if len(au)==1 else OUT/'audio_wav'/f'{name}_ch{ch}.wav'
            delta=(times[str(ch)]-times['video'])/90000
            filt=['-af',f'adelay={round(delta*44100)}S:all=1'] if delta>0 else ['-af',f'atrim=start={-delta},asetpts=PTS-STARTPTS'] if delta<0 else []
            run(['-n','-i',str(oma),*filt,'-c:a','pcm_s16le',str(wav)],OUT/'logs'/f'{name}_audio{ch}.log')
            wavs.append(wav);r['audio'].append({'channel':ch,'frames':len(frames),'offset_seconds':delta,'wav':str(wav.relative_to(OUT)),'oma':str(oma.relative_to(OUT)),'wav_sha256':sha(wav)})
        args=['-n','-i',str(src)]
        for w in wavs:args+=['-i',str(w)]
        args+=['-map','0:v:0']
        for i in range(len(wavs)):args+=['-map',f'{i+1}:a:0']
        args+=['-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
        run(args,OUT/'logs'/f'{name}_mux.log')
        run(['-v','error','-xerror','-i',str(out),'-map','0:v','-map','0:a?','-f','null','-'],OUT/'logs'/f'{name}_decode_check.log')
        # Decoded-frame hashes prove remux did not lose/change image frames.
        hashes=[]
        for label,path in [('source',src),('mp4',out)]:
            dest=OUT/'logs'/f'{name}_{label}.framemd5'
            run(['-n','-v','error','-i',str(path),'-map','0:v:0','-an','-f','framemd5',str(dest)],OUT/'logs'/f'{name}_{label}_frames.log')
            hashes.append([x.split(',')[-1].strip() for x in dest.read_text().splitlines() if not x.startswith('#')])
        assert hashes[0]==hashes[1] and hashes[0]
        probe=subprocess.run([FF,'-hide_banner','-i',str(out)],capture_output=True).stderr.decode(errors='replace')
        r.update(mp4=str(out.relative_to(OUT)),mp4_sha256=sha(out),frames=len(hashes[0]),video_frame_match=True,decode_check='PASS',media_info=probe)
        reports.append(r);(OUT/'manifest.partial.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
        print(name,len(hashes[0]),'frames',len(au),'audio',flush=True)
    (OUT/'manifest.json').write_text(json.dumps({'ffmpeg':FF,'version':subprocess.check_output([FF,'-version']).decode().splitlines()[0],'files':reports},indent=2),encoding='utf-8')
if __name__=='__main__':main()
