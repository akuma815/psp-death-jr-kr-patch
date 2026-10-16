# Death Jr. 영상 편집 자료

- `editable_mp4/`: 편집용 MP4 26개. 원본 H.264 영상 복사 + AAC 192 kbps 오디오. 영상 재압축 없음.
- `audio_wav/`: 대사 전사/자막 타이밍용 WAV 26개. 44,100 Hz, 스테레오, 16-bit PCM. 대사·음악·효과음이 함께 들어 있는 원본 믹스이며 음성 분리/대사 인식은 아직 하지 않았다.
- `audio_atrac/`: PMF에서 분리한 ATRAC3+ 압축 프레임을 담은 OMA 26개. WAV 변환 전의 오디오 보존본.
- `CATALOG.md`: 원본 파일명별 재생 시간 및 MP4/WAV 링크.
- `contact_sheet.jpg`, `previews/`: 각 영상 중간 지점의 미리보기. 대사 존재나 스토리 순서를 의미하지 않는다.
- `manifest.json`: 원본/산출물 해시, PTS, 오디오 프레임 수, 변환 및 검증 기록.
- `logs/`: 변환 로그 및 원본·MP4 디코딩 프레임 MD5 목록.

원본 PMF는 `../../extracted/iso/PSP_GAME/USRDIR/FMV/`에 있으며 PSP 메뉴 영상은 `../../extracted/iso/PSP_GAME/ICON1.PMF`다. 원본 PMF와 ISO를 수정하지 않았다.

## 편집 기준

MP4와 같은 이름의 WAV를 0초에 맞춰 사용한다. 모든 입력의 첫 비디오 PTS는 90,000, 첫 오디오 PTS는 85,820 (90 kHz)이었다. 영상 시작보다 약 46.44 ms 앞선 오디오 프리롤을 WAV 앞에서 잘라 영상 0초에 정렬했다. 자르기 전 오디오는 OMA에 보존했다. 전체 장면을 직접 듣고 확인한 립싱크 검증은 아직 하지 않았다.

원본 해상도/29.97 fps(30000/1001)/영상 길이를 유지하여 작업한다. 실제 해상도는 manifest의 media_info를 참고한다. 대부분의 영상은 480×272이고 ICON1, SAVE_GAME, UMD_MOVIE는 144×80이다. 오디오 끝이 영상보다 조금 길 수 있으며 임의로 짧은 쪽에 맞춰 잘라내지 않았다.

GAMEINTRO, GAMEEND 등의 MP4로 장면을 보면서 같은 이름의 WAV를 전사하면 된다. 번역 자막은 우선 같은 이름의 SRT/ASS로 별도 저장하면 재수정하기 쉽다. 이 MP4는 편집 중간 파일이며 게임에 곧바로 넣을 수 있는 PMF가 아니다. 자막을 입힌 영상의 PSP 호환 인코딩/PMF 재패키징과 ISO 재삽입은 후속 작업이다.

## 재현 및 검증

프로젝트 루트: `python scripts/export_movies.py`. 기존 manifest/MP4가 있으면 중단하여 편집 결과 덮어쓰기를 방지한다. 의존성은 현재 Python의 imageio-ffmpeg, 사용 바이너리는 manifest에 기록된 FFmpeg 7.1이다.

원본 PMF 26개를 ISO inventory 해시와 대조했다. MP4 26개를 비디오/오디오 모두 끝까지 디코딩(-xerror)하여 통과했다. 원본 PMF와 MP4의 모든 디코딩 비디오 프레임 MD5가 동일함을 확인했다. 에뮬레이터 재삽입/재생 검증은 수행하지 않았다.

PSP 오디오 분리 참고: PPSSPP Core/HW/MpegDemux.cpp, OMA 헤더 참고: FFmpeg libavformat/omadec.c (조사 당시 공식 master 소스를 work/analysis에 보존).


## 한국어 자막 합성 결과

[subtitled_001_kyobo24/README.md](subtitled_001_kyobo24/README.md): 번역 CSV 59행을 4개 MP4에 흰색 교보손글씨 24px/하단 검정 음영으로 합성했다. 원본 보존. SRT와 59장 검증 이미지 포함. PSP용 PMF 변환/게임 재삽입은 후속 작업이다.
