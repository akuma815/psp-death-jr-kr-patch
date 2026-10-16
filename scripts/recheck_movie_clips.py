import json,sys
from pathlib import Path
from dataclasses import asdict
import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
R=Path(__file__).resolve().parents[1]
clips=[('GAMEINTRO',110,116),('GAMEINTRO',115,124),('GAMEINTRO',124,130.5),('GAMEINTRO',130.5,134.5),('GAMEINTRO',66,72),('GAMEEND',37,44),('GAMEEND',44,49),('GAMEEND',24,32),('REUNITED',0,13),('TITLES',16,22)]
for name in ['medium.en','large-v3-turbo']:
 m=WhisperModel(name,device='cpu',compute_type='int8',cpu_threads=10,download_root=str(R/'tools/models/whisper'))
 dest=R/'workspace/video/transcription/raw/clips'/name;dest.mkdir(parents=True,exist_ok=True)
 for video,start,end in clips:
  file=dest/f'{video}_{start}.json'
  if file.exists():continue
  audio=decode_audio(str(R/'workspace/video/audio_wav'/f'{video}.wav'))[int(start*16000):int(end*16000)]
  peak=np.max(np.abs(audio));audio=audio*(0.9/max(peak,1e-4))
  seg,info=m.transcribe(audio,language='en',beam_size=5,temperature=0,word_timestamps=True,condition_on_previous_text=False,vad_filter=False)
  result=[asdict(s) for s in seg];file.write_text(json.dumps({'video':video,'offset':start,'model':name,'segments':result},indent=2))
  print(name,video,start,[(s['start'],s['end'],s['text']) for s in result],flush=True)
