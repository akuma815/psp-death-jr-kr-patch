# 전체 번역 삽입 003 — 개발 테스트

입력 SSOT는 사용자 제공 `workspace/text/DeathJr_English_Script_Korean.csv`다. 708행 모두 번역되어 있고 초기 추출본과 ID/원문/위치/토큰이 일치한다. 기존 English CSV와 firstline JSON은 이전 추출/PoC 재현용으로 보존한다. 번역문 자체는 수정하지 않았다.

입력 SHA-256: `b714a5268f826a1d5ce6a325f7aac77ba5e6a78fcc5a2bde8d591a2a08576744`.

## 구조

단순 UTF-8 덮어쓰기는 475행이 원문 길이를 넘고, 20개의 확인된 UI 행이 32바이트 버퍼를 넘는다. 한글을 단순 2바이트로 세어도 원문 길이를 넘는 행은 157개다. 이 수치는 대안 조사용이며 채택 인코딩 길이 판정이 아니다.

원문 위치에 짧은 문장 ID를 저장하고 공통 렌더러 진입점 ELF 상대 VA `0xCD194`에서 전체 번역 문자열로 확장한다. 기존 포인터·UI 32바이트 버퍼·문장 복사 경로를 유지한다. 일반 ID는 `1F high low`, 작은 슬롯의 형식 문자열은 단일 제어 바이트 ID를 사용한다. 숫자/문자열 치환 인자는 기존 sprintf에 맡기고 구분 바이트 `1E`로 보존한 뒤 출력 직전에 확장한다. 동일 원문의 서로 다른 번역은 별도 ID라 충돌하지 않는다.

영문/버튼은 원본 208글리프, 한글은 KyoboHandwriting2019.ttf 24px/검은 1px 외곽선 496글리프다. 704글리프를 512×512 T8 swizzled 페이지 2개에 저장했다. 게임의 기존 FF 상위 바이트 전환 디코더를 활용하고 각 은행에 ASCII/버튼 매핑을 복제한다. 문자 누락/대체 없이 인코딩 왕복을 검사한다. 기본 영문·기호는 원본 글꼴이다.

렌더러 원본 함수 사본에서 아이콘 색상 기준만 새 글리프 순서에 맞춰 변경한다. 페이지마다 동일한 폭/배치를 사용하며 다른 페이지 글리프는 투명 영역을 샘플링한다. 두 번의 그리기에서 각 페이지의 실제 글자가 같은 문장 좌표에 놓인다. 폰트 객체·texture·raster는 전용 버퍼에 복사하고, 모든 픽셀/팔레트는 모듈에 상주시켜 지연 GPU 소비 중 변경하지 않는다. 원본 PXD/폰트 STR는 재작성하지 않는다.

**래스터 확장 정보 전역 주소**는 원본 `0x176D48/0x176D4C` 명령의 재배치 정보 `0x10005/0x10006`을 따른다. 즉 segment 1 기준 `0x1E3E60` + 상대 `0x12FFA4` = 모듈 기준 `0x313E04`다. 002의 잘못된 segment 0 계산은 폐기했고, 해당 빌드와 초기 모의 테스트는 검증 근거에서 제외한다.

ELF segment 1의 기존 BSS는 0으로 물리화하고 기존 메모리 끝 이후 VA `0x314000`에 코드/번역/폰트를 추가했다. 모듈 메모리는 578,316바이트 증가한다. 새 코드 및 렌더러 사본을 위한 PSP 재배치 44개를 추가한다. EBOOT는 ISO 끝의 새 extent에 저장하고 ISO9660 EBOOT 디렉터리 레코드의 양 엔디언 LBA/길이와 볼륨 블록 수를 갱신한다. 다른 ISO 파일의 위치는 유지한다. 논리 변경 파일은 EBOOT.BIN, UI_BINARY.STR, SCHOOL_D2.STR 세 개다.

## 검증과 한계

최종 ISO 86개 논리 파일 재읽기/해시 통과. 708행 텍스트 원문/번역 왕복, 512×512 swizzle 왕복, 슬롯 범위/중복 쓰기 방지 통과. 원본 ISO·추출 파일·CSV·TTF·빌드 001은 수정하지 않았다.

Unicorn 2.1.4에서 실제 삽입 MIPS 코드를 모듈 베이스 `0x08804000`, `0x08814000` 두 곳으로 재배치해 1,422건을 실행했다. 기본 708행과 `%s%d`, `Completed: %s`, `%dx %s`의 번역 ID 중첩 사례 3개씩이다. 스택 및 S0~S7/FP/GP 보존, 숫자/문자열 치환, font/raster 복사, 원본 렌더러 글리프·정점 생성, UV 0..1, 두 페이지 좌표 일치를 검사한다. native raster 확장 전역은 원본 재배치 명령에서 독립적으로 읽어 모의 상태를 설정한다.

**GPU binding/transform/draw 호출은 모의 처리**한다. 따라서 이 검사는 PPSSPP 장면 출력, PSP GPU 호환성 또는 부팅 증거가 아니다. texture/raster 구조와 페이지 렌더링의 실제 소비, 증가한 모듈 메모리가 힙/레벨 로딩에 미치는 영향, 렌더러를 우회하는 저장 설명/기타 문자열 소비, 모든 줄의 화면 배치는 후속 검증 대상이다. 공통 렌더러 외 소비 경로에는 ID 제어 바이트가 표시될 가능성을 아직 배제하지 못했다. 영상 음성/이미지 글자는 이번 CSV 범위에 포함되지 않는다.

Zig 0.13.0의 ABI 플래그 혼합 링크 경고가 남지만 생성 C 코드에 GP 기반 명령은 없고 두 베이스에서 실제 코드/보존 레지스터 검사는 통과했다. 실제 PSP 호출 경로 검증을 대체하지 않는다. 함수 사이 12바이트는 링크 정렬 trap filler이며 실행 코드로 취급하지 않는다.

재현(프로젝트 루트):

```powershell
python scripts/build_korean.py
python scripts/test_korean_runtime.py
python scripts/preview_korean.py
```

빌더는 최종 ISO가 존재하면 덮어쓰기 전에 중단한다. 수정 빌드는 새 ID로 생성한다. Python 의존성: Pillow 12.3.0, fonttools 4.63.0, 프로젝트 tools/python의 pycdlib 1.14.0 / ziglang 0.13.0 / Unicorn 2.1.4. websocket-client 1.8.0은 실행 분석 준비용으로 설치했지만 이번 검증에는 사용하지 않았다.

참고한 공식 자료: [PSPSDK texture image 제한/명령](https://github.com/pspdev/pspsdk/blob/master/src/gu/sceGuTexImage.c), [PPSSPP ELF 재배치 구현](https://github.com/hrydgard/ppsspp/blob/master/Core/ELF/ElfReader.cpp), [PPSSPP WebSocket 디버거](https://github.com/hrydgard/ppsspp/blob/master/docs/WebSocketDebugger.md). 실제 도입 판단은 대상 ELF 명령/재배치와 테스트 결과에 근거한다.

정확한 다음 작업: [003 시험 안내](../build/003_full_csv_kyobo24/TEST_README.md)에 따라 PPSSPP에서 새 게임의 메뉴, 첫 대사와 다음 대사를 확인한다. 자동 실행은 자동 승인 검토가 정책상 차단했으므로 이번 세션에는 수행하지 않았다.
