# 데스 주니어 최종판 재빌드

2026-09-26 최종 009 배포본의 텍스트 708행과 런타임 코드를 소스에서 재빌드합니다. 기존 자막 영상 4개는 인코더 버전에 따라 바뀌지 않도록 **공개 최종 릴리즈 패치를 적용한 임시 ISO에서 복원**합니다. 게임 폴더의 캐시 영상·복호화 ELF·과거 추출본·비공개 백업 ZIP은 필요하지 않습니다.

## 필요한 입력

- 최신 Git 소스
- 지원 원본 `Death Jr. (USA) (PSP) (PSN).iso`: ULUS10027 v1.01, 435,159,040바이트
- 별도 `KyoboHandwriting2019.ttf`: 기존 공용 `Font` 폴더의 파일을 사용 가능
- 공개 최종 릴리즈 ZIP: 명령이 자동 다운로드하거나 `--release-zip`으로 전달
- Windows, Python 3.12 및 고정된 Python 의존성

파일 이름과 크기만 같아도 지원 원본이라는 뜻은 아닙니다. 아래 해시를 확인합니다.

| 구분 | SHA-256 |
| --- | --- |
| 지원 원본 ISO | `625c03e32b6757eb4e1ac382f43592d86778b3c943d4f26b95f1134ceee85ea3` |
| 최종 ISO | `c1ed1625cd3f9dac362655af0d332d49470fdab592c23cb5d81b778f4d52b842` |
| 자막·본문 폰트 | `92ed8baae0b00321994560281650f7a6ade89dcef6f8848fa511391720ce9aa5` |

## 실행

저장소 최상위에서 실행합니다. 의존성은 Git 추적에서 제외한 `tools/python`에 설치합니다. 각 출력 경로는 아직 존재하지 않는 새 폴더여야 합니다.

```powershell
python -m pip install --target tools/python -r requirements-rebuild.txt
python -X utf8 -B scripts/rebuild_final.py --source-iso "지원 원본의 절대 경로.iso" --font "KyoboHandwriting2019.ttf의 절대 경로" --output-dir build/restored_final
```

이미 최종 릴리즈 ZIP을 내려받았다면 `--release-zip "ZIP 절대 경로"`를 추가해 다운로드를 생략합니다. [지원 릴리즈](https://github.com/akuma815/psp-death-jr-kr-patch/releases/tag/final-20260926)와 첨부 ZIP의 해시를 입력 목록에 고정했습니다.

최종 결과는 출력 폴더의 `project/build/009_final_20260926/DeathJr_KR_Final_20260926.iso`이며, 전체 확인 결과는 `REBUILD_RESULT.json`에 기록합니다. 기존 체크아웃과 원본 ISO는 덮어쓰지 않습니다. 출력 폴더에는 원본 추출본과 실행 가능한 게임 이미지도 있으므로 공개 업로드하지 마세요.

## 복원·빌드 경계

1. 원본 ISO·폰트·번역·메타데이터의 해시를 검사합니다.
2. 공개 릴리즈 ZIP의 해시·CRC를 확인하고 기존 xdelta로 임시 최종 ISO를 생성해 해시를 검사합니다.
3. 그 ISO에서 동결된 자막 PMF 4개를 복원합니다. 실행 파일은 원래의 비적재 섹션 위치를 되돌리고 소량의 변경 바이트를 역적용해 원래 복호화 ELF를 복원합니다. 복원 ELF의 전체 해시도 확인합니다. `inputs/restore_original_elf.json`은 섹션 복사 위치와 역수정 데이터이며 전체 실행 파일을 포함하지 않습니다.
4. 원본 ISO를 새 작업 폴더로 추출하고, 현재 번역 CSV와 C/어셈블리 소스에서 폰트·코드·삽입 데이터를 새로 빌드합니다. Zig 0.13.0과 MIPS CPU 검사도 실행합니다.
5. 복원한 PMF의 패킷·프레임 구조, 원본 음성·PTS와 보호 바이트를 검사하고 텍스트 빌드에 결합합니다. 최종 ISO 해시가 공개 최종판과 일치해야 통과합니다.

공개 릴리즈는 동결된 영상 자산 복원의 필수 입력입니다. 이 경로는 영상을 다시 인코딩하는 빌드가 아닙니다. 새 영상 자막을 만들려면 공개된 영상 대사 CSV·SRT와 `export_movies.py`, `burn_movie_subtitles.py`, PMF mux 소스를 사용해 별도 후보를 생성·검증해야 합니다. 단순한 영상 재인코딩이 과거 PMF와 같은 바이트를 보장하지는 않습니다.

최종판 재현 진입점은 입력 변경을 거부합니다. 새 텍스트 번역은 `workspace/text/DeathJr_English_Script_Korean.csv`와 기존 하위 빌더로 새 후보를 만드세요. `build_korean.py`는 `DEATHJR_FONT` 및 `DEATHJR_ZIG`로 외부 폰트·컴파일러 경로를 받을 수 있습니다.

## 검증 범위

[VERIFICATION_2026-10-16.json](VERIFICATION_2026-10-16.json)에 실제 적용·재빌드 결과를 기록합니다. CPU 1,422건은 텍스트·포맷·재배치·글리프·정점 처리 검사이며 PSP GPU나 실제 장면 검증이 아닙니다. 새 에뮬레이터 영상 재생·장면·전체 플레이 검수는 수행하지 않았습니다. 원본 ISO·복호화 ELF·PMF·MP4·원본 폰트 파일은 Git에 포함하지 않습니다.

## 2026-10-16 원본 호환성 업데이트

배포 패치 `final-20261016`은 원본 ISO 2종을 자동 구분하여 동일한 최종 ISO를 생성합니다. 이 문서의 소스 재빌드 절차는 기존 정규 입력인 PSN 원본(`625c03e3…`)만 지원합니다. 동영상 자산 복구에 사용하는 `final-20260926` 릴리즈의 URL과 해시는 변경하지 않았습니다. 패치 적용 지원과 소스 재빌드 입력 범위는 구분합니다.

배포 재생성: `python scripts/package_dual_release.py --psn <PSN원본> --usa <USA원본> --target <검증된최종ISO> --old-package <기존배포폴더> --output <새배포폴더>`
