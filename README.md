# 재와니의 레트로 게임 보관소 (JRGS)
## Jaewani Retro Game Storage

---

## 🚀 설치 및 실행 방법

### 1. 필수 패키지 설치
```
pip install PyQt6 Pillow requests psutil
```

### 2. 실행
```
python main.py
```

---

## 📁 폴더 구조
```
JRGS/
├── main.py              ← 실행 파일
├── requirements.txt
├── jrgs.db              ← 자동 생성
├── src/                 ← 소스코드
│   ├── database.py
│   ├── folders.py
│   ├── main_window.py
│   ├── game_grid.py
│   └── info_panel.py
├── ROM_File/            ← 자동 생성
│   ├── Famicom_ROM/
│   ├── SFC_ROM/
│   └── ...
├── GameData/            ← 자동 생성
├── Screenshots/         ← 자동 생성
└── Records/             ← 자동 생성
```

---

## 🎮 단축키

| 기능 | 단축키 |
|------|--------|
| ROM 전체 스캔 | F5 |
| ROM 개별 추가 | Ctrl+O |
| 상태저장 | F2 |
| 상태 불러오기 | F3 |
| 스크린샷 | F12 |
| 번역 오버레이 ON/OFF | F9 |
| 스크린샷 OCR 번역 | F10 |
| 녹화 시작/중지 | Ctrl+R |
| 녹화 일시정지/재개 | Ctrl+P |
| 즐겨찾기 추가/제거 | Ctrl+D |
| 게임 실행 | Enter |
| 게임 정보 편집 | Ctrl+E |
| 전체화면 토글 | Alt+Enter |
| 아이콘 크기 조정 | Ctrl+Shift+마우스 휠 |

---

## 📝 개발 현황 (1단계 완료)

- [x] SQLite DB 설계 및 초기화
- [x] 폴더 구조 자동 생성
- [x] 기본 UI 프레임 (PyQt6)
- [x] 플랫폼 탭 (즐겨찾기 고정)
- [x] 게임 그리드 (이름/작은아이콘/큰아이콘)
- [x] 정보 패널 (커버아트/동영상 탭)
- [x] 단축키 프레임
- [x] ROM 스캔 기반 코드
- [ ] 에뮬레이터 등록/실행 UI (2단계)
- [ ] 메타데이터 자동검색 (4단계)
- [ ] 유튜브 연동 (7단계)
- [ ] OCR 실시간 번역 (8단계)

---

블로그: https://blog.naver.com/akrsodhk
유튜브: https://www.youtube.com/@jewani1004
