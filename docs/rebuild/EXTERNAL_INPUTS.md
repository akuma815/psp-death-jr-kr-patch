# 별도 입력과 도구

`KyoboHandwriting2019.ttf`는 공용 Font 폴더에서 사용해 온 선택 폰트입니다. 전체 폰트 파일을 이 저장소에 추가하지 않습니다. 필수 해시는 INPUTS.json의 font 항목을 참고하세요. 폰트를 변경하면 동결된 최종판과 글리프·ISO 해시가 달라집니다.

Python 도구는 requirements-rebuild.txt의 버전으로 설치합니다. 복제한 실행 파일을 저장소에 넣지 않고 PyPI의 Zig·Unicorn·PyCdlib·Pillow·FontTools·imageio-ffmpeg 배포물을 사용합니다. 공개 최종 릴리즈 ZIP의 xdelta3와 동봉 라이선스도 그대로 보존합니다.

영상 자산을 다시 편집할 때 필요한 PMF mux 프로그램 소스는 기존 tools/pmf_mux_007 등에 있습니다. 동결된 최종 영상 복원에는 이 프로그램을 새로 컴파일하거나 영상을 인코딩할 필요가 없습니다.
