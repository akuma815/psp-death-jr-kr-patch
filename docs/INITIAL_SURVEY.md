# Death Jr. PSP 한글화 초기 검토 — 2026-09-13

## 판단

**조건부 진행 가능.** 번역 대상 문자열, 복호화 가능한 실행 파일, 디코딩 가능한 글꼴 자산을 확보했다. 단순 문자열 치환만으로 전체 한글화가 된다고 판단할 단계는 아니다. 기존 글리프 조회를 추적하고 한글 표시·길이 제한·자산 로딩을 검증하는 PoC가 필요하다.

이번 요청 범위인 폴더 추출과 첫 가능성 검토는 완료했다. 저장 위치부터 화면 출력까지 이어지는 전체 경로가 아직 확인되지 않았으므로, 기술 명세 확정이나 전체 게임 한글 지원 검증 완료를 뜻하지 않는다.

## 입력과 추출

- 원본: `original/Death Jr. (USA) (PSP) (PSN).iso`.
- 크기: 435,159,040 bytes. SHA-256 기준은 `original/source_manifest.json`.
- PARAM.SFO: `TITLE=Death, Jr.`, `DISC_ID=ULUS10027`, `DISC_VERSION=1.01`, `PSP_SYSTEM_VER=1.50`, `CATEGORY=UG`.
- `extracted/iso/`에 86개 파일, 합계 405,650,271 bytes 추출.
- 모든 추출 파일을 원본 ISO의 대응 extent와 크기·SHA-256으로 대조했다. 파일 단위 추출 검증이며, ISO 재구성 검증은 아니다.
- 원본 ISO와 추출 파일을 수정하지 않았다. 복호화 실행 파일은 `work/analysis/EBOOT.decrypted.elf`에 별도 보관한다.
- 파일명에 적힌 PSN 유통 이력은 별도 확인하지 않았다.

## 자산 지도

아래 경로는 `extracted/iso/PSP_GAME/` 기준이다.

| 대상 | 확인 결과 | 한글화 영향 |
|---|---|---|
| `SYSDIR/EBOOT.BIN` | `~PSP` 실행 파일. pspdecrypt 1.0으로 2,434,281-byte ELF 복호화 성공 | 대사·튜토리얼·메뉴 및 코드 분석 가능 |
| `SYSDIR/BOOT.BIN` | 전체 바이트가 0 | 분석 가능한 ELF 대체본이 아님 |
| `USRDIR/STREAMS/` | 23개 STR. 게임 데이터 이름과 일부 평문 발견 | 독자적인 묶음/메모리 구조 추가 분석 필요. 영상 파일로 일괄 취급하지 않음 |
| `STREAMS/UI_BINARY.STR` | `0x830`: Press START Button, `0x84D`: New Game, `0x856`: Load Game | 타이틀 메뉴 표시 시험 후보 |
| `STREAMS/SCHOOL_D2.STR` | `0xAF4250`: So this is the, `0xAF4268`: girls' bathroom | 실행 파일 외에도 대사성 문자열이 존재. 전체 범위 미확정 |
| `LEVELS/GLOBAL/GLOBAL_00.PXD` | 경계가 맞는 0x16→0x15 청크 트리, 텍스처 항목 69개 | RenderWare 계열 텍스처 사전 형태로 해석 가능 |
| `LEVELS/UIENGINE/UIENGINE_99.PXD` | 동일 구조의 텍스처 항목 11개 | UI 그래픽 및 폰트 포함 |
| `USRDIR/FMV/` | PMF 25개. 루트 ICON1.PMF 포함 전체 26개 | 영상 속 대사/자막 유무와 자막 처리 방식은 미확인 |
| `USRDIR/MODULES/LIBFONT.PRX` | 파일 존재 | 존재만으로 게임이 시스템 한글 폰트를 쓴다고 볼 수 없음 |

파일별 크기·해시·LBA: `iso_inventory.json`. PXD 항목: `texture_inventory.json`.

## 글꼴

후속 크기 측정에서 글리프 메트릭과 국소 렌더 경로를 확인했다. **공통 렌더 높이 31px, 208개 메트릭과 이미지 경계 일치**가 추가로 확인됐으며, 현재 크기/매핑 조사 상태는 [FONT_MEASUREMENT.md](FONT_MEASUREMENT.md)를 우선 참고한다. 아래 최초 조사에서 미확인으로 남긴 메트릭 부분을 보완한 결과이며, 실제 화면 검증은 여전히 미수행이다.

두 PXD에 `dj_font`가 있고 256×512, 8비트 인덱스 방식의 기본 이미지를 PNG로 복원했다. 두 자산의 기본 팔레트와 픽셀 해시는 일치한다. 영문·확장 라틴 문자·기호·버튼 아이콘이 보이며 한글은 보이지 않는다.

- [GLOBAL 폰트 PNG](../extracted/assets/fonts/GLOBAL_00_dj_font.png)
- [UIENGINE 폰트 PNG](../extracted/assets/fonts/UIENGINE_99_dj_font.png)
- GLOBAL 청크 시작 `0x2940C`, UIENGINE 청크 시작 `0xEE5FC`.
- 해당 native struct 시작 기준 헤더 172 bytes, 팔레트 1,024 bytes 다음 기본 픽셀.
- 16-byte×8-row 블록 배열을 풀어 복원했다. 역변환한 기본 픽셀은 원본과 바이트 단위 일치했다.

이 검사는 기본 이미지 배열 변환만 입증한다. 하위 mip 전체 재작성, 게임 재삽입, 런타임 사용 여부는 검증하지 않았다. `UI_BINARY.STR`에도 `dj_font` 이름이 있으므로 PXD만 바꿔 실제 화면이 바뀐다고 가정하면 안 된다. 문자 코드→좌표/폭 매핑과 실제 로딩 경로를 먼저 확인해야 한다.

## 문자열과 실제 길이 제한

복호화 ELF의 `0x1C3BE4..0x1C3FF0`, `0x1CAA4C..0x1CC02C` 두 구간에서 NUL로 구분된 문자열 후보 283개를 기록했다. 이 수에는 포맷 문자열과 자산 이름도 포함되므로 번역 문장 수가 아니다. 메뉴 레코드 후보 57개도 별도 기록했다. 모두 조사 자료이며 번역 SSOT로 채택하지 않았다. 전체 번역량은 미확정이다.

- `work/analysis/text_pool_candidates.json`: 원본 바이트와 표시용 Latin-1 표현. Latin-1은 보존용 표시이며 게임 인코딩 확정이 아니다.
- `work/analysis/menu_record_candidates.json`: 0x6C 간격에서 관찰한 문자열 후보. 레코드 의미 전체는 미확정.
- `Press [A4] to jump!`, `Press [7F] to use the Scythe.` 등 고위 바이트가 섞인다. 버튼 아이콘 코드 후보를 일반 문자로 치환하지 않아야 한다. `%d`, `%s` 등 포맷도 보존 대상이다.

**튜토리얼 복사 경로 한 곳에서는 최대 31바이트+NUL 제한을 코드로 확인했다.** ELF 상대 VA `0xD9308..0xD9354`에서 `0x1CAA60` 문자열(파일 오프셋 `0x1CAAE0`)을 바이트 길이로 검사한다. 길이 32 이상이면 31바이트를 복사하고 객체 `+0xBC`에 NUL을 기록하며, 짧으면 NUL 종료 복사를 한다. 목적지는 객체 `+0x9D`이다.

바이트 길이 계산 `0x1AD4C8`, NUL 종료 복사 `0x1AD484`, 제한 복사 `0x1AD5A8`의 동작도 읽었다. 근거: `work/analysis/text_copy_disassembly.txt`. 주소는 적재 후 절대 PSP 주소가 아닌 ELF 상대 VA이며, 이 첫 세그먼트에서 파일 오프셋은 VA+0x80이다. 국소적인 MIPS32 명령 해석이며 전체 Allegrex 디스어셈블 완전성을 주장하지 않는다.

따라서 2바이트 한글을 새로 지원하더라도 이 경로는 공백·기호 없이 최대 15글자만 담는다. UTF-8이라면 일반 한글 음절 기준 최대 10글자다. 이는 바이트 예산 계산이며 어느 인코딩의 사용도 아직 채택하지 않았다. 화면상 폭·줄 수는 별도 확인이 필요하다. 다른 모든 화면이 같은 제한을 쓴다고 일반화하지 않는다.

## 미해결 조건과 다음 증거

| 조건 | 현재 판단 | 다음 확인 |
|---|---|---|
| 문자 해석·글리프 수 | 한글 매핑 미확정, 기존 atlas는 라틴/아이콘 | 한 문자의 읽기→좌표·폭→그리기 함수 추적 |
| 실제 폰트 공급 | PXD와 STR에 관련 자산 공존 | 로더 참조 확인 후 별도 PoC에서 기존 글리프 교체 관찰 |
| 문자열 증가 | 국소 31바이트 제한 확인 | 길이 제한·줄 분할·2바이트 경계 보존 검증; 필요시 버퍼/코드 변경 |
| STR 재삽입 | 전체 컨테이너 사양 미확정 | 헤더·포인터·참조 분석, 무수정 왕복 및 실제 로드 확인 |
| 전체 번역량 | 후보만 확보, 미확정 | 텍스트 소비자/색인으로 대사·메뉴·STR·영상 범위 산정 |
| 동영상 한글화 | PMF 존재만 확인 | 자막 없는 음성 장면인지, 외부 자막 경로인지 판별 |
| 저장·재개·긴 문장 | 미검증 | 대표 PoC 이후 관련 상태별 실행 검사 |

대표 PoC는 **시작 메뉴 한 항목과 튜토리얼 한 줄**을 권장한다. 전자는 STR/폰트 공급, 후자는 ELF 문자열/31바이트 복사 경로를 함께 확인할 수 있다. 그래픽 변경은 먼저 PNG를 검토받고 별도 빌드로 진행한다. 이번 세션에서는 번역·폰트 수정·코드 패치·제품 빌드·에뮬레이터 실행을 하지 않았다.

## 재현

프로젝트 루트에서 실행한다. 도구 출처·버전·해시는 `tools/README.md`에 기록했다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_source.ps1
python .\scripts\extract_iso.py
& .\tools\pspdecrypt-1.0\pspdecrypt.exe -o .\work\analysis\EBOOT.decrypted.elf .\extracted\iso\PSP_GAME\SYSDIR\EBOOT.BIN
python .\work\analysis\survey_assets.py
```

추출 스크립트는 기존 파일이 다르면 덮어쓰지 않고 중단한다. 복호화 명령의 출력은 분석용 파일에만 둔다.

외부 자료는 도구 사용에만 참고했다. 게임별 오프셋과 제한은 이 원본에서 직접 조사했다: [pycdlib API](https://clalancette.github.io/pycdlib/pycdlib-api.html), [pspdecrypt 1.0](https://github.com/John-K/pspdecrypt/releases/tag/1.0).
