# 영상 대사 번역용 CSV

`DeathJr_Movie_Dialogue_Korean.csv`: UTF-8 BOM, 59행/14열. `translation` 59행에 한국어 번역 초안을 입력했다(2026-09-20). 이 칸을 검토·수정한다. GAMEINTRO 48행, GAMEEND 3행, REUNITED 7행, TITLES 1행이다.

| 열 | 의미 |
|---|---|
| id | 영상별 고유 대사 ID |
| video_file / audio_file / source_pmf | 대응 MP4, WAV 파일명 및 원본 ISO 내부 PMF 경로 |
| start_time / end_time | 발화 시작/종료, HH:MM:SS.mmm |
| start_ms / end_ms | 영상 0초 기준 밀리초. 이후 자막 생성 기준 |
| speaker | 화자 추정, 쌍둥이 공동 표기, 또는 Unknown |
| original / translation | 영어 전사문 / 한국어 번역 초안 |
| speaker_status | visual_inferred=인접 프레임 기반 추정, group_only=쌍둥이 중 개별 화자 미확정, unknown=미상 |
| review_status | asr_compared=복수 인식 결과 비교·정리, needs_review=우선 청취/경계 확인 필요 |
| notes | 행별 주의점 |

## 정확도와 시간 기준

**전편을 사람이 청취해 검수한 완성 대본이 아니라, 복수 ASR 및 영상 프레임을 비교·정리한 초안**이다. needs_review 13행, asr_compared 46행이며 후자도 오류 없음을 보증하지 않는다. 모든 발화 시각은 ASR 단어 경계 기반 추정이다. 밀리초 자리수는 저장 정밀도이며 프레임 단위 검수 완료를 뜻하지 않는다.

화자는 visual_inferred 32행, Smith / Weston group_only 18행, Unknown 9행이다. 자동 음성 화자 식별 모델을 사용한 결과가 아니다. 쌍둥이 개별 이름과 화면 밖 발화는 확정하지 않았다. 주요 인물 표기는 기존 게임 대본과 호명/장면 맥락을 참고했다.

MP4/WAV의 0초 기준이다. 기존 추출에서 처리한 PMF 오디오 프리롤 약 46.44 ms를 다시 빼지 않는다. 시각 수정 시 ms와 HH:MM:SS.mmm를 함께 바꾸며, 서로 다르면 후속 자막 변환에서 중단해야 한다. ID/파일명은 유지한다. 공간적 자막 위치와 최종 표시 길이/줄바꿈은 아직 정하지 않았다. 짧은 감탄사는 번역 후 읽기 편한 표시 길이 조정이 필요할 수 있다.

## 범위 및 제외 후보

26개 WAV 전체를 medium.en VAD on/off 및 large-v3-turbo VAD off로 처리했다. 경계가 긴 구간·누락 후보는 짧게 잘라 두 모델로 재인식했다. 대소문자/문장부호/고유명사 표기와 발화별 구분을 정리했다.

나머지 22개 영상은 비교 결과 신뢰 가능한 영어 대사가 미검출된 상태이며, 전편 청취로 무대사를 확정한 것은 아니다. 음악에서 모델마다 다르게 생성된 Thank you / I'll see you next time / you / 반복 문장 / 점 하나 등의 후보는 채택하지 않았다. GAMEEND 14–30초대의 0.08초짜리 반복 문장도 제외했다. 비언어적 비명·웃음·신음은 영어 대사 CSV에서 제외했다. 재검토를 위해 모든 raw 후보와 파일별 coverage.json/COVERAGE.md를 보존했다.

## 검증과 재현

입력 WAV 26개 해시가 기존 manifest 및 세 ASR 결과와 일치했다. artifact-tool로 작성 후 CSV 재읽기 840셀 일치, ID 고유/양수 길이/파일별 시각 순서·비중첩/미디어 경로/빈 번역 59칸 검사 통과. csv_preview.png는 표 표시 확인용이며 CSV 자체에는 서식이 없다. 자막 합성·PMF 재인코딩·ISO 삽입·게임 실행은 미수행이다.

프로젝트 전용 tools/transcription_venv/Scripts/python.exe로 scripts/transcribe_movies.py medium.en, medium.en --no-vad, large-v3-turbo --no-vad 및 scripts/recheck_movie_clips.py를 실행했다. scripts/prepare_movie_dialogue.py가 편집 결정을 JSON으로 만들고 tools/artifact_runtime/build_movie_csv.mjs가 CSV를 작성한다. raw 파일은 존재하면 재사용하고 CSV는 존재하면 생성을 거부한다. 번역 시작 후 CSV를 재생성으로 덮어쓰지 않는다. 의존성은 requirements-transcription.txt, 결과 검사는 validation.json을 참고한다.

도구: [faster-whisper](https://github.com/SYSTRAN/faster-whisper). 모델을 로컬로 다운로드했고 음성을 외부 전사 서비스에 업로드하지 않았다. 원본 ISO/PMF/005 빌드/영상 MP4/WAV/기존 게임 대본 CSV는 변경하지 않았다.

현재 번역 상태: 59행 입력 완료. 초기 빈 번역/검증 기록은 과거 상태이며 최신 translation_validation.json을 참고한다. 시간/화자/전사 검수 표시는 유지했다.
