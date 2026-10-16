"""Burn CSV translations into preserved editing MP4s; no ISO/PMF modification."""
import argparse, csv, hashlib, io, json, math, subprocess
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'workspace/video'
CSV = VIDEO / 'transcription/DeathJr_Movie_Dialogue_Korean.csv'
FONT = ROOT.parents[1] / 'Font/KyoboHandwriting2019.ttf'
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 480, 272, 30000/1001

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(args):
    p = subprocess.run([FF, '-hide_banner', '-nostdin', *args], capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace'))
    return p.stdout

def wrap(text, font):
    words = text.split()
    lines, line = [], ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if font.getlength(candidate) > 420 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    assert len(lines) <= 2 and all(font.getlength(x) <= 420 for x in lines), text
    return lines

def overlay(lines, font):
    img = Image.new('RGBA', (W,H))
    d = ImageDraw.Draw(img)
    width = math.ceil(max(font.getlength(x) for x in lines)) + 24
    height = 30 * len(lines) + 12
    top = H - 10 - height
    d.rounded_rectangle(((W-width)//2, top, (W+width)//2, H-10), radius=5, fill=(0,0,0,180))
    for i,line in enumerate(lines):
        d.text((W/2, top+6+22+i*30), line, font=font, anchor='ms', fill='white', stroke_width=0)
    return img

def stamp(ms):
    h,r = divmod(ms,3600000); m,r = divmod(r,60000); s,r = divmod(r,1000)
    return f'{h:02}:{m:02}:{s:02},{r:03}'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output', default='workspace/video/subtitled_001_kyobo24')
    args=ap.parse_args()
    out=ROOT/args.output
    assert not out.exists(), 'Use a new output directory; existing results are preserved.'
    rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig', newline='')))
    font=ImageFont.truetype(str(FONT),24)
    cmap=TTFont(FONT).getBestCmap()
    assert all(ord(c) in cmap for r in rows for c in r['translation'] if not c.isspace())
    groups=defaultdict(list)
    for r in rows:
        assert r['translation'].strip() and Path(r['video_file']).name==r['video_file']
        r=dict(r, lines=wrap(r['translation'],font), start=int(r['start_ms']), end=int(r['end_ms']))
        assert r['start']<r['end']
        groups[r['video_file']].append(r)
    source_manifest=json.loads((VIDEO/'manifest.json').read_text(encoding='utf-8'))
    specs={Path(x['mp4']).name:x for x in source_manifest['files']}
    for name,cues in groups.items():
        cues.sort(key=lambda r:r['start'])
        assert all(a['end']<=b['start'] for a,b in zip(cues,cues[1:]))
        assert sha(VIDEO/'editable_mp4'/name)==specs[name]['mp4_sha256']
        assert cues[-1]['end']/1000 <= specs[name]['frames']/FPS
    out.mkdir(parents=True)
    for sub in ('mp4','srt','qa','logs'):
        (out/sub).mkdir()
    report={'csv_sha256':sha(CSV),'font':str(FONT),'font_sha256':sha(FONT),
            'font_family':font.getname(),'font_px':24,'resolution':[W,H],'fps':'30000/1001',
            'style':'white centered text; black alpha 180/255 box; bottom margin 10 px; 30 px line spacing',
            'timing':'CSV exact milliseconds; active on frame PTS >= start and < end; no duration extension',
            'ffmpeg':FF,'pillow':Image.__version__,'files':[]}
    for name,cues in groups.items():
        src=VIDEO/'editable_mp4'/name
        dst=out/'mp4'/name
        (out/'srt'/f'{src.stem}.srt').write_text('\n\n'.join(
            f"{i}\n{stamp(r['start'])} --> {stamp(r['end'])}\n"+'\n'.join(r['lines'])
            for i,r in enumerate(cues,1))+'\n',encoding='utf-8-sig')
        layers={r['id']:overlay(r['lines'],font) for r in cues}
        targets={int(math.ceil(((r['start']+r['end'])/2)*FPS/1000)):r for r in cues}
        enc_args=['-n','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30000/1001',
                  '-i','pipe:0','-i',str(src),'-map','0:v:0','-map','1:a:0','-c:v','libx264',
                  '-preset','medium','-crf','16','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(dst)]
        counts={r['id']:0 for r in cues}
        with (out/'logs'/f'{src.stem}_decode.log').open('wb') as dl, (out/'logs'/f'{src.stem}_encode.log').open('wb') as el:
            dec=subprocess.Popen([FF,'-v','error','-xerror','-i',str(src),'-map','0:v:0','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE,stderr=dl)
            enc=subprocess.Popen([FF,'-hide_banner','-nostdin',*enc_args],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=el)
            n=0; idx=0
            try:
                while True:
                    data=dec.stdout.read(W*H*3)
                    if not data: break
                    assert len(data)==W*H*3
                    ms=n*1001/30
                    while idx<len(cues) and ms>=cues[idx]['end']: idx+=1
                    if idx<len(cues) and cues[idx]['start']<=ms<cues[idx]['end']:
                        r=cues[idx]; counts[r['id']]+=1
                        frame=Image.alpha_composite(Image.frombytes('RGB',(W,H),data).convert('RGBA'),layers[r['id']]).convert('RGB')
                        data=frame.tobytes()
                    enc.stdin.write(data)
                    n+=1
                enc.stdin.close()
                assert enc.wait()==0 and dec.wait()==0
            finally:
                if dec.poll() is None: dec.kill()
                if enc.poll() is None: enc.kill()
        assert n==specs[name]['frames'] and all(counts.values())
        # Full decode with both streams, then independent output frame count and copied audio packet hashes.
        run(['-v','error','-xerror','-i',str(dst),'-map','0:v','-map','0:a','-f','null','-'])
        hashes=run(['-v','error','-i',str(dst),'-map','0:v:0','-an','-f','framemd5','-']).decode()
        assert sum(1 for x in hashes.splitlines() if x and not x.startswith('#'))==n
        audio=[]
        for path in (src,dst):
            audio.append(run(['-v','error','-i',str(path),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip())
        assert audio[0]==audio[1]
        # Extract ALL cue midpoint screenshots from the actual encoded result in one pass.
        select='+'.join(f'eq(n,{k})' for k in targets)
        run(['-n','-v','error','-i',str(dst),'-vf',f'select={select.replace(",",chr(92)+",")}','-fps_mode','vfr',str(out/'qa'/f'{src.stem}_%03d.png')])
        record={'file':name,'source_sha256':sha(src),'output_sha256':sha(dst),'frames':n,
                'cues':len(cues),'decode':'PASS','audio_packet_hash':audio[0],
                'cue_layout':[dict(id=r['id'],lines=r['lines'],start_ms=r['start'],end_ms=r['end'],visible_frames=counts[r['id']],review_status=r['review_status']) for r in cues]}
        report['files'].append(record)
        (out/'manifest.partial.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(name,n,'frames',len(cues),'cues PASS',flush=True)
    assert sha(CSV)==report['csv_sha256'] and sha(FONT)==report['font_sha256']
    report['script_sha256']=sha(Path(__file__))
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    shots=sorted((out/'qa').glob('*.png'))
    for page in range(math.ceil(len(shots)/12)):
        sheet=Image.new('RGB',(960,6*296),(25,25,25)); d=ImageDraw.Draw(sheet)
        for i,p in enumerate(shots[page*12:(page+1)*12]):
            x=(i%2)*480; y=(i//2)*296
            sheet.paste(Image.open(p),(x,y)); d.text((x+5,y+274),p.stem,fill='white')
        sheet.save(out/'qa'/f'contact_{page+1:02}.jpg',quality=92)
    print('DONE',out,flush=True)

if __name__=='__main__': main()
