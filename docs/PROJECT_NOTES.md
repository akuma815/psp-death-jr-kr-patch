# Death Jr. PSP 한글화 프로젝트

최종 배포: [한글 번역 + 동영상 자막 통합 xdelta ZIP](dist/DeathJr_KR_Patch_Final_20260926.zip) — 2026-09-26 Final. 기존 게임과 같은 apply.cmd/한국어 안내문/체크섬/도구 포함 형식이다. 원본 ISO는 포함하지 않는다.
현재 빌드: [009 최종 ISO](build/009_final_20260926/DeathJr_KR_Final_20260926.iso). 최신 번역 708행(008 이후 수정 7행)과 자막영상 4개를 반영했다. 정적/ISO 검사, CPU 1,422건 및 한글·공백 경로에서 실제 패치 적용 검증 통과. 게임 실행·화면·전체 플레이 검증은 미수행. [최신 인계](docs/HANDOFF_2026-09-26.md).
기존 008은 보존한다. 과거 005 자막 정상 출력 사용자 확인 기록은 유지한다.
영상 편집 자료: [MP4/WAV 안내](workspace/video/README.md), [26개 영상 목록](workspace/video/CATALOG.md), [미리보기](workspace/video/contact_sheet.jpg). 원본 PMF를 보존하고 소리 포함 편집용 파일 추출을 완료했다.
원본 ISO는 `original/Death Jr. (USA) (PSP) (PSN).iso`에 보존한다. 내부 ID는 `ULUS10027`, 버전은 `1.01`이다.
식별 기준은 `original/source_manifest.json`, 현재 검토 결과는 [INITIAL_SURVEY.md](docs/INITIAL_SURVEY.md), 작업 기록은 [HANDOFF_2026-09-26.md](docs/HANDOFF_2026-09-26.md)를 참고한다.

영상 대사: [번역용 CSV](workspace/video/transcription/DeathJr_Movie_Dialogue_Korean.csv) 59행 한국어 번역 입력 완료. 원문·타임코드·화자 추정과 기존 검수 표시 유지. [사용법과 검수 범위](workspace/video/transcription/README.md).

## 폴더 구성

| 경로 | 용도 |
|---|---|
| `original/` | 원본 ISO, 식별 정보 및 관리 규칙 |
| `extracted/iso/` | ISO에서 추출한 수정하지 않은 파일 트리 |
| `extracted/assets/` | 내부 아카이브에서 추출한 수정하지 않은 자산 |
| `workspace/text/` | 번역 SSOT: 원문·번역·제어 코드·검토 상태 |
| `workspace/fonts/` | 한글 폰트 제작 입력, 문자 매핑 및 라이선스 |
| `workspace/graphics/` | 수정 그래픽의 편집 원본 |
| `workspace/patches/` | 채택한 코드 패치와 적용 명세 |
| `scripts/` | 재현 가능한 추출·삽입·빌드·검증 스크립트 |
| `tools/` | 외부 도구와 버전·출처·사용 방법 기록 |
| `work/analysis/` | 분석 실험 코드, 덤프 및 중간 결과 |
| `work/temp/` | 재생성 가능한 임시 파일 |
| `build/` | 실행용 수정 파일 트리 및 ISO 등 빌드 산출물 |
| `dist/` | 배포용 패치와 적용 안내서 |
| `docs/` | 확인된 기술 명세·진행 상황·인수인계 |
| `qa/screenshots/` | 실행 화면 검증 자료 |
| `qa/logs/` | 정적·빌드·패치 적용·실행 검증 로그 |
| `qa/saves/` | 재현용 세이브 및 대응 빌드 정보 |
| `backups/` | 수정 전 중요 파일 및 이전 검증 결과 |

## 작업 규칙

- 원본 ISO와 추출 원본은 수정하지 않는다. 이전 검증 빌드도 덮어쓰지 않는다.
- 번역 편집 기준은 `workspace/text/`로 통일한다. 데이터 포맷은 텍스트 구조 분석 후 정한다.
- 인코딩·폰트·압축·포인터·재삽입 방법은 이 게임의 증거로 확인한다.
- 그래픽 수정은 PNG 미리보기 확인 후 게임 빌드에 반영한다.
- 정적·빌드·패치 적용·실행·장면 검증을 구분해 기록한다.
- 원본 ISO·게임 데이터·외부 도구 바이너리를 저장소나 배포 패치에 포함하지 않는다.
- 외부 도구 및 폰트를 도입할 때 버전·출처·라이선스와 재현 방법을 기록한다.

## 원본 무결성 재확인

프로젝트 폴더에서 실행한다. 실행 정책 옵션은 이 프로세스에만 적용한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_source.ps1
```

## 다음 작업

009 빌드에서 수정한 대사와 무기 획득 메시지, 긴 자막과 버튼 토큰 표시를 점검하고, 문제가 있으면 장면과 CSV ID를 기록한다.

폰트 크기 측정은 [FONT_MEASUREMENT.md](docs/FONT_MEASUREMENT.md)에 기록했다. 이번 매핑은 확장 문자 6칸을 사용하는 첫 대사 PoC 전용이며 전체 한글 배정이 아니다.

추출 재현은 `python scripts/extract_iso.py`, 정적 조사 재현은 `python work/analysis/survey_assets.py`를 사용한다. 의존성과 복호화 명령은 검토 보고서에 기록했다.


영상 한국어 자막 합성: [4개 MP4와 검증 자료](workspace/video/subtitled_001_kyobo24/README.md). 교보손글씨24px/하단 흰색 자막·검정 음영, 59개 대사. 게임 재삽입 전 편집용 결과.


최신 빌드 상태: [009 검증 범위](build/009_final_20260926/STATUS.md). 재현 명령은 `python -X utf8 scripts/build_final_009.py`, 배포 생성은 `python -X utf8 scripts/make_release_dist.py`이며 기존 출력은 덮어쓰지 않는다.


007 인트로 정상 재생 사용자 확인(2026-09-20)은 과거 증거로 유지한다. 008 영상 바이트는 007과 동일하나 이를 008 실제 실행 확인으로 대신하지 않는다.

007 영상 정적 검증 완료: 자막영상4개 모두 프레임길이 잘림/잘못된패딩 없음, 나머지22개 원본동일. [검증 보고서](qa/logs/007_movie_packet_audit.json). 에뮬레이터실행없이검사.
