"""Local English ASR with word timestamps; raw results are immutable review inputs."""
import json,os,time,hashlib,sys
from pathlib import Path
from dataclasses import asdict
from faster_whisper import WhisperModel
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/video/transcription'
def main():
    model_name=sys.argv[1] if len(sys.argv)>1 else 'medium.en'
    no_vad='--no-vad' in sys.argv
    dest=OUT/'raw'/(model_name+('_no_vad' if no_vad else ''));dest.mkdir(parents=True,exist_ok=True)
    print('Loading',model_name,flush=True)
    model=WhisperModel(model_name,device='cpu',compute_type='int8',cpu_threads=12,download_root=str(ROOT/'tools/models/whisper'))
    paths=sorted((ROOT/'workspace/video/audio_wav').glob('*.wav'),key=lambda p:(p.stem not in ['GAMEINTRO','GAMEEND','REUNITED'],p.name))
    for p in paths:
        target=dest/(p.stem+'.json')
        if target.exists():continue
        start=time.time()
        seg,info=model.transcribe(str(p),language='en',beam_size=5,word_timestamps=True,vad_filter=not no_vad,vad_parameters={'min_silence_duration_ms':350},condition_on_previous_text=False,temperature=0)
        result=[]
        for s in seg:
            result.append(asdict(s));print(p.stem,round(s.start,2),round(s.end,2),s.text,flush=True)
        target.write_text(json.dumps({'model':model_name,'audio':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration':info.duration,'duration_after_vad':info.duration_after_vad,'elapsed_seconds':time.time()-start,'segments':result},ensure_ascii=False,indent=2),encoding='utf-8')
        print('DONE',p.name,len(result),'segments',round(time.time()-start,1),'sec',flush=True)
if __name__=='__main__':main()
