"""006 development ISO: 005 game text plus four subtitled PMFs, original audio."""
import hashlib, io, json, struct, subprocess, sys
from pathlib import Path
import imageio_ffmpeg
from export_movies import demux
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python'))
import pycdlib
B=ROOT/'build/006_subtitled_movies_kyobo24'
BASE=ROOT/'build/005_full_csv_rasterfix_kyobo24/DeathJr_KR_005_FullCSV_RasterFix_Kyobo24.iso'
V=ROOT/'workspace/video/subtitled_001_kyobo24'
FF=imageio_ffmpeg.get_ffmpeg_exe()
def sha(b):return hashlib.sha256(b).hexdigest()
def run(cmd,log):
 p=subprocess.run(cmd,capture_output=True)
 (B/'logs'/log).write_bytes(p.stderr+p.stdout)
 assert p.returncode==0,(log,p.stderr[-500:])
 return p.stdout
def main():
 assert not B.exists(),'Existing build is preserved'
 base=BASE.read_bytes();assert sha(base)=='9934e98334cad2c332f902bcde6c49829a118f8df683128c98d5ffc2aaa4d2f2'
 B.mkdir();(B/'logs').mkdir();(B/'pmf').mkdir();(B/'intermediate').mkdir()
 report={'base_iso_sha256':sha(base),'muxer_upstream':'https://github.com/OAleex/pmftools-plus','commit':'26897c95c53fcc4df1c4119ef0f8e297620683fa','pmf':[]}
 video={x['file']:x for x in json.loads((V/'manifest.json').read_text(encoding='utf-8'))['files']}
 modified={}
 for name in ['REUNITED','TITLES','GAMEEND','GAMEINTRO']:
  src=ROOT/f'extracted/iso/PSP_GAME/USRDIR/FMV/{name}.PMF';original=src.read_bytes()
  audio,pts=demux(original);assert list(audio)==[0] and pts=={'video':90000,'0':85820}
  raw=B/'intermediate'/f'{name}.rawatx';raw.write_bytes(audio[0])
  mp4=V/'mp4'/f'{name}.mp4';assert sha(mp4.read_bytes())==video[mp4.name]['output_sha256']
  h264=B/'intermediate'/f'{name}.264';mps=B/'intermediate'/f'{name}.mps'
  run([FF,'-hide_banner','-nostdin','-n','-i',str(mp4),'-an','-c:v','libx264','-preset','slow','-profile:v','main','-level:v','2.1','-b:v','1800k','-maxrate','2400k','-bufsize','2400k','-refs','1','-bf','0','-g','60','-keyint_min','60','-sc_threshold','0','-pix_fmt','yuv420p','-x264-params','weightp=1:weightb=0:8x8dct=0:cabac=1:nal-hrd=vbr:repeat-headers=1:aud=1','-f','h264',str(h264)],name+'_encode.log')
  run(['dotnet',str(ROOT/'tools/pmf_mux_local/bin/Release/net8.0/Mux.dll'),str(h264),str(raw),str(mps)],name+'_mux.log')
  header=bytearray(original[:2048]);assert header[:8]==b'PSMF0012'
  assert header[134:142]==bytes(8),'Original EP table must be empty'
  stream=mps.read_bytes();assert len(stream)%2048==0
  struct.pack_into('>I',header,12,len(stream))
  target=B/'pmf'/f'{name}.PMF';target.write_bytes(header+stream)
  newaudio,newpts=demux(target.read_bytes())
  assert newaudio==audio and newpts==pts,'Audio bytes/AV start timestamps changed'
  # Stream hashes include every decoded picture and prove the mux retained the encoded video.
  framehash=[]
  for label,path in [('h264',h264),('pmf',target)]:
   data=run([FF,'-v','error','-xerror','-i',str(path),'-map','0:v:0','-an','-f','framemd5','-'],name+'_'+label+'_frames.log')
   framehash.append([x.split(b',')[-1].strip() for x in data.splitlines() if x and not x.startswith(b'#')])
  assert framehash[0]==framehash[1] and len(framehash[1])==video[mp4.name]['frames']
  run([FF,'-v','error','-n','-ss',str({'REUNITED':5,'TITLES':18,'GAMEEND':40,'GAMEINTRO':4}[name]),'-i',str(target),'-frames:v','1',str(B/f'{name}_preview.png')],name+'_preview.log')
  logical=f'PSP_GAME/USRDIR/FMV/{name}.PMF';modified[logical]=target.read_bytes()
  report['pmf'].append({'path':logical,'source_sha256':sha(original),'sha256':sha(modified[logical]),'bytes':len(modified[logical]),'frames':len(framehash[1]),'video_decode_mux_roundtrip':'PASS','original_atrac_bytes_preserved':True,'pts':newpts,'header_changes':'stream byte count only at 0x0C'})
  (B/'pmf_report.partial.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(name,'PMF PASS',len(modified[logical]),flush=True)
 # Append replacement files, explicitly update directory extent+length and volume size fields.
 iso=bytearray(base);reader=pycdlib.PyCdlib();reader.open(str(BASE))
 directory=reader.get_record(iso_path='/PSP_GAME/USRDIR/FMV');start=directory.extent_location()*2048;end=start+directory.data_length
 plans=[];done=set();p=start
 while p<end:
  length=base[p]
  if not length:p=((p//2048)+1)*2048;continue
  name=base[p+33:p+33+base[p+32]].split(b';')[0].decode('ascii')
  logical='PSP_GAME/USRDIR/FMV/'+name
  if logical in modified:
   b=modified[logical];lba=len(iso)//2048;assert len(iso)%2048==0
   iso.extend(b+bytes((-len(b))%2048))
   replacement=struct.pack('<I',lba)+struct.pack('>I',lba)+struct.pack('<I',len(b))+struct.pack('>I',len(b))
   plans.append({'offset':p+2,'before':base[p+2:p+18].hex(),'after':replacement.hex(),'owner':logical})
   iso[p+2:p+18]=replacement;done.add(logical)
  p+=length
 assert done==set(modified)
 for s in range(16,64):
  p=s*2048
  assert base[p+1:p+6]==b'CD001'
  if base[p] in (1,2):
   replacement=struct.pack('<I',len(iso)//2048)+struct.pack('>I',len(iso)//2048)
   plans.append({'offset':p+80,'before':base[p+80:p+88].hex(),'after':replacement.hex(),'owner':'volume size'})
   iso[p+80:p+88]=replacement
  if base[p]==255:break
 cursor=0
 for plan in sorted(plans,key=lambda x:x['offset']):
  off=plan['offset'];assert iso[cursor:off]==base[cursor:off]
  assert base[off:off+len(bytes.fromhex(plan['before']))].hex()==plan['before']
  cursor=off+len(bytes.fromhex(plan['after']))
 assert iso[cursor:len(base)]==base[cursor:]
 output=B/'DeathJr_KR_006_SubtitledMovies_Kyobo24.iso';output.write_bytes(iso)
 check=pycdlib.PyCdlib();check.open(str(output));files=[]
 for item in json.loads((ROOT/'docs/iso_inventory.json').read_text())['files']:
  path='/'+item['path'];old=io.BytesIO();new=io.BytesIO()
  for archive,buf in [(reader,old),(check,new)]:
   try:archive.get_file_from_iso_fp(buf,iso_path=path)
   except pycdlib.pycdlibexception.PyCdlibInvalidInput:archive.get_file_from_iso_fp(buf,iso_path=path+';1')
  expected=modified.get(item['path'],old.getvalue());assert new.getvalue()==expected,item['path']
  files.append({'path':item['path'],'sha256':sha(new.getvalue()),'changed':item['path'] in modified})
 reader.close();check.close()
 report.update(iso_sha256=sha(iso),iso_bytes=len(iso),expected_writes=plans,appended_bytes=len(iso)-len(base),logical_files=files,protected_base_bytes='PASS',runtime='NOT RUN',script_sha256=sha(Path(__file__).read_bytes()))
 (B/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('ISO PASS',output,sha(iso),flush=True)
if __name__=='__main__':main()
