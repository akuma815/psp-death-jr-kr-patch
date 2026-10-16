"""Editorial cue decisions from saved ASR/word timing and scene sheets; no audio synthesis."""
from pathlib import Path
import json,hashlib,collections
R=Path(__file__).resolve().parents[1];O=R/'workspace/video/transcription'
# These are ASR estimates on the exported MP4/WAV timeline, not frame-accurate human alignment.
DATA='''GAMEINTRO|6.06|9.92|Teacher|File in, class, and give me your reports by the end of the day.
GAMEINTRO|10.00|10.94|Teacher|Move it, Molly.
GAMEINTRO|15.02|16.09|Teacher|Oh, God.
GAMEINTRO|17.40|18.56|Teacher|We'll start in the archives.
GAMEINTRO|18.98|20.24|Teacher|Becky, stop hitting Max.
GAMEINTRO|26.50|27.20|Stigmartha|Hi!
GAMEINTRO|29.02|30.84|Stigmartha|We should stay with the class.
GAMEINTRO|31.84|32.22|Stigmartha|Damn it.
GAMEINTRO|32.76|33.68|Stigmartha|Now I'm all nervous.
GAMEINTRO|34.88|35.28|Stigmartha|See?
GAMEINTRO|36.06|37.08|Stigmartha|Come on, guys.
GAMEINTRO|37.32|39.42|Stigmartha|What am I supposed to write a report about?
GAMEINTRO|39.78|41.12|Stigmartha|What we didn't learn today?
GAMEINTRO|41.66|42.82|Marty|You suck, Stigmartha.
GAMEINTRO|43.16|44.46|Marty|Dead Guppy's not scared.
GAMEINTRO|46.36|47.78|Stigmartha|I do not suck.
GAMEINTRO|48.04|50.00|Stigmartha|We're gonna get arrested again.
GAMEINTRO|50.56|51.62|Smith / Weston|Put a cork in it.
GAMEINTRO|52.10|53.74|Smith / Weston|There is a cork in it.
GAMEINTRO|54.13|54.86|Smith / Weston|Aw, gross!
GAMEINTRO|54.86|55.85|Smith / Weston|Repulsive!
GAMEINTRO|56.47|57.55|Smith / Weston|I tire of this discussion.
GAMEINTRO|57.77|59.87|Smith / Weston|You volunteered to write the report for our group, Marty.
GAMEINTRO|60.07|61.07|Smith / Weston|Complaining is futile.
GAMEINTRO|61.51|63.97|Smith / Weston|Let us find more stimulating amusement.
GAMEINTRO|66.06|67.09|Pandora|Like that!
GAMEINTRO|69.94|70.56|Pandora|Oops!
GAMEINTRO|72.32|75.68|Smith / Weston|An artifact estimated to be thousands of years old.
GAMEINTRO|76.10|77.66|Smith / Weston|Attempts to open it have failed.
GAMEINTRO|78.06|79.96|Smith / Weston|The mysteries may never be known.
GAMEINTRO|80.22|81.12|Pandora|Ooh, wicked.
GAMEINTRO|84.14|85.58|Stigmartha|Stop it, Pandora.
GAMEINTRO|86.04|88.96|Stigmartha|Whomever locked that box obviously didn't want it opened again.
GAMEINTRO|91.96|93.48|Pandora|It won't open!
GAMEINTRO|94.46|96.82|Pandora|That's weird. I can open anything.
GAMEINTRO|97.40|99.40|Marty|This is boring. It's just a stupid box.
GAMEINTRO|99.76|100.48|Unknown|Marty, let's roll!
GAMEINTRO|101.24|102.38|Unknown|Whatever. Let's jam.
GAMEINTRO|104.86|106.82|Stigmartha|We're gonna get grounded for this.
GAMEINTRO|107.14|108.66|Marty|Yeah, whatever. Anybody got a smoke?
GAMEINTRO|111.80|113.78|Pandora|I'll be back for you.
GAMEINTRO|114.14|114.84|Unknown|Giddy up!
GAMEINTRO|115.76|118.06|Unknown|If you want an A, leave me alone.
GAMEINTRO|119.00|120.52|Unknown|Hey, DJ.
GAMEINTRO|126.18|127.42|Unknown|What was that noise?
GAMEINTRO|127.66|128.00|Marty|What?
GAMEINTRO|128.32|129.28|Marty|It wasn't me.
GAMEINTRO|131.48|133.26|Marty|Oops, that one was me.
GAMEEND|39.00|41.00|Unknown|I found the key to defeating Moloch,
GAMEEND|41.20|43.00|Unknown|the most powerful weapon in the world!
GAMEEND|46.32|47.72|Marty|Ah, crap.
REUNITED|0.11|0.82|Smith / Weston|DJ!
REUNITED|1.24|3.68|Smith / Weston|Hey! Uh... wow!
REUNITED|4.40|6.16|Smith / Weston|We were looking all over for you.
REUNITED|6.16|7.54|Smith / Weston|In the bathroom stalls.
REUNITED|8.78|9.58|Smith / Weston|Inside. Locked.
REUNITED|9.72|11.20|Smith / Weston|But we were looking for you nonetheless.
REUNITED|11.94|12.60|Smith / Weston|So good to see you.
TITLES|17.34|19.22|Unknown|DJ, the bus is here.'''
def tc(ms):
 h,rest=divmod(ms,3600000);m,rest=divmod(rest,60000);s,milli=divmod(rest,1000)
 return f'{h:02}:{m:02}:{s:02}.{milli:03}'
def main():
 manifest=json.loads((R/'workspace/video/manifest.json').read_text());by={Path(x['source']).stem:x for x in manifest['files']}
 rows=[];counts=collections.Counter()
 for line in DATA.splitlines():
  video,start,end,speaker,original=line.split('|',4);start_ms=round(float(start)*1000);end_ms=round(float(end)*1000);counts[video]+=1
  assert 0<=start_ms<end_ms<=by[video]['frames']*1001/30
  status='group_only' if speaker=='Smith / Weston' else 'unknown' if speaker=='Unknown' else 'visual_inferred'
  note='시작/종료는 영상 0초 기준 ASR 추정. 번역 전 음성·타이밍 확인 권장.'
  if status=='group_only':note+=' 쌍둥이 중 개별 화자 미확정.'
  elif status=='unknown':note+=' 화면만으로 화자 확정 불가.'
  else:note+=' 화자는 인접 영상 프레임을 근거로 추정.'
  review='asr_compared'
  if video=='GAMEEND':review='needs_review';note+=' 원문은 두 모델의 짧은 구간 재인식 결과 일치; 발화 경계·화자 재확인.'
  if video=='GAMEINTRO' and start_ms in [10000,18980,26500,54300,54130,99760,101240,114140,115760,119000,126180]:
   review='needs_review';note+=' 고유명사/짧은 감탄사 또는 화면 밖 발화 확인 필요.'
  rows.append(dict(id=f'{video}_{counts[video]:03}',video_file=video+'.mp4',start_time=tc(start_ms),end_time=tc(end_ms),speaker=speaker,original=original,translation='',speaker_status=status,review_status=review,notes=note,start_ms=str(start_ms),end_ms=str(end_ms),audio_file=video+'.wav',source_pmf=by[video]['source']))
 rows.sort(key=lambda x:(x['video_file'],int(x['start_ms'])))
 (O/'curated_rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 coverage=[]
 for name,source in by.items():
  raw={}
  for model in ['medium.en','medium.en_no_vad','large-v3-turbo_no_vad']:
   p=O/'raw'/model/(name+'.json');j=json.loads(p.read_text());raw[model]=[s['text'] for s in j['segments']]
  coverage.append({'file':name+'.mp4','dialogue_rows':counts[name],'status':'dialogue_draft' if counts[name] else 'no_reliable_dialogue_detected','note':'ASR 모델 비교에 따른 분류; 전편 청취 확인 아님. 무대사 확정으로 해석하지 말 것.','raw_candidates':raw,'wav_sha256':source['audio'][0]['wav_sha256']})
 (O/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
 print(len(rows),'rows',dict(counts))
if __name__=='__main__':main()
