"""
JRGS - 재와니의 레트로 게임 보관소
main_window.py - 메인 UI 윈도우
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTabBar, QScrollArea, QLabel, QFrame, QPushButton,
    QStatusBar, QMenuBar, QMenu, QToolBar, QSizePolicy, QButtonGroup,
    QGridLayout, QStackedWidget, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction, QColor, QPalette

from database import init_db, get_all_platforms, get_games_by_platform, get_favorite_games, get_setting
from folders import init_folders, scan_rom_folder, auto_register_fusion, auto_register_desmume, auto_register_oswan, auto_register_bluemsx
from game_grid import GameGridWidget
from info_panel import InfoPanel as InfoPanelWidget

class _LogSignalBridge(QObject):
    """백그라운드 스레드에서 메인 스레드 위젯으로 안전하게 메시지를 전달하는 브릿지"""
    message = pyqtSignal(str)


class _LogRedirector:
    """stdout/stderr를 QPlainTextEdit으로 리다이렉트 (스레드 안전)

    직접 위젯 메서드를 호출하지 않고 pyqtSignal(QueuedConnection)을 통해
    항상 메인 스레드에서 위젯을 업데이트하므로 백그라운드 스레드에서도 안전하다.
    """
    def __init__(self, bridge: "_LogSignalBridge"):
        self.bridge = bridge

    def write(self, text):
        if text.strip():
            try:
                self.bridge.message.emit(text.rstrip())
            except Exception:
                pass

    def flush(self):
        pass

class ScanWorker(QThread):
    """백그라운드 ROM 스캔 스레드 (재사용 방식)"""
    progress = pyqtSignal(int, int, str)
    scan_finished = pyqtSignal(int, int, int)  # added, skipped, missing

    def __init__(self):
        super().__init__()
        self.platform_short = None

    def start_scan(self, platform_short=None):
        self.platform_short = platform_short
        self.wait()   # 이전 실행이 완전히 종료될 때까지 대기 (이미 종료된 경우 즉시 반환)
        self.start()

    def run(self):
        def callback(current, total, filename):
            self.progress.emit(current, total, filename)
        try:
            result = scan_rom_folder(
                progress_callback=callback,
                platform_short=self.platform_short
            )
            self.scan_finished.emit(
                result.get("added", 0),
                result.get("skipped", 0),
                result.get("missing", 0)
            )
        except Exception as e:
            import traceback
            print(f"[스캔 오류] {e}")
            traceback.print_exc()
            self.scan_finished.emit(0, 0, 0)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_platform_id = None
        self.current_game_id = None
        self.platforms = []
        self._all_games = []
        # ScanWorker 단일 인스턴스 (시그널 누적 방지)
        self._scan_worker = ScanWorker()
        self._scan_worker.progress.connect(
            lambda c, t, f: self.status_bar.showMessage(f"스캔 중... ({c}/{t}) {f}"),
            Qt.ConnectionType.QueuedConnection
        )
        self._scan_worker.scan_finished.connect(
            self._on_scan_finished,
            Qt.ConnectionType.QueuedConnection
        )

        self._init_ui()
        self._init_menubar()
        self._init_statusbar()
        self._load_platforms()
        self._apply_style()

        # 첫 실행 시 자동 스캔
        if get_setting("auto_scan_on_start", "1") == "1":
            QTimer.singleShot(500, self._scan_roms)

    def _init_ui(self):
        lang = get_setting("language", "ko")
        # CHANGELOG.md에서 최신 버전 읽기
        from pathlib import Path
        ver = ""
        changelog = Path(__file__).parent.parent / "CHANGELOG.md"
        if changelog.exists():
            for line in changelog.read_text(encoding="utf-8").splitlines():
                if line.startswith("## V.") or line.startswith("## v"):
                    ver = " " + line.lstrip("#").strip().split("—")[0].strip()
                    break
        if lang == "en":
            self.setWindowTitle(f"Jaewani Retro Game Storage (JRGS){ver}")
        else:
            self.setWindowTitle(f"재와니의 레트로 게임 보관소 (JRGS){ver}")

        from folders import get_base_path
        icon_path = get_base_path() / "ICON" / "JRGS.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        w = int(get_setting("window_width", "1280"))
        h = int(get_setting("window_height", "800"))
        self.resize(w, h)
        self.setMinimumSize(900, 600)

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 플랫폼 탭 바 ──
        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.setMovable(True)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                background: #2a2a3e;
                color: #aaaacc;
                border: none;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background: #4a4a8a;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background: #3a3a6a;
                color: #ffffff;
            }
        """)
        main_layout.addWidget(self.tab_bar)

        # ── 메인 스플리터 (좌: 그리드, 우: 정보패널) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)
        main_layout.addWidget(splitter)

        # 좌측: 게임 그리드
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # ── 검색/필터 바 ──
        search_bar = QWidget()
        search_bar.setObjectName("search_bar")
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(6, 4, 6, 4)
        search_layout.setSpacing(6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 게임 검색...")
        self.search_edit.setFixedHeight(24)
        self.search_edit.setStyleSheet("font-size: 8pt;")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)

        self.cmb_genre = QComboBox()
        self.cmb_genre.setFixedHeight(24)
        self.cmb_genre.setFixedWidth(100)
        self.cmb_genre.setStyleSheet("font-size: 8pt;")
        self.cmb_genre.addItem("전체 장르")
        self.cmb_genre.currentIndexChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.cmb_genre)

        self.cmb_sort = QComboBox()
        self.cmb_sort.setFixedHeight(24)
        self.cmb_sort.setFixedWidth(120)
        self.cmb_sort.setStyleSheet("font-size: 8pt;")
        self.cmb_sort.addItems(["이름순", "최근 플레이순", "플레이 횟수순"])
        self.cmb_sort.currentIndexChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.cmb_sort)

        left_layout.addWidget(search_bar)

        self.game_grid = GameGridWidget()
        self.game_grid.game_selected.connect(self._on_game_selected)
        self.game_grid.game_launched.connect(self._on_game_launched)
        self.game_grid.request_add_rom.connect(self._open_rom)
        self.game_grid.request_scan.connect(self._scan_roms)
        left_layout.addWidget(self.game_grid)

        # 그리드 뷰 모드 버튼 (하단)
        view_bar = QWidget()
        view_bar.setObjectName("view_bar")
        view_bar.setFixedHeight(36)
        view_layout = QHBoxLayout(view_bar)
        view_layout.setContentsMargins(8, 4, 8, 4)
        view_layout.setSpacing(4)

        self.btn_view_name  = QPushButton("☰ 이름만")
        self.btn_view_small = QPushButton("⊞ 작은 아이콘")
        self.btn_view_large = QPushButton("⊟ 큰 아이콘")

        for btn in [self.btn_view_name, self.btn_view_small, self.btn_view_large]:
            btn.setCheckable(True)
            btn.setFixedHeight(26)

        self.view_group = QButtonGroup()
        self.view_group.addButton(self.btn_view_name, 0)
        self.view_group.addButton(self.btn_view_small, 1)
        self.view_group.addButton(self.btn_view_large, 2)
        self.view_group.idClicked.connect(self._on_view_mode_changed)

        view_layout.addWidget(self.btn_view_name)
        view_layout.addWidget(self.btn_view_small)
        view_layout.addWidget(self.btn_view_large)

        self.btn_scan_current = QPushButton("🔍 F5")
        self.btn_scan_current.setFixedHeight(26)
        self.btn_scan_current.setToolTip("현재 탭 ROM 스캔")
        self.btn_scan_current.clicked.connect(self._scan_current_platform)
        view_layout.addWidget(self.btn_scan_current)

        view_layout.addStretch()

        # 게임 수 표시
        self.lbl_game_count = QLabel("0개")
        self.lbl_game_count.setStyleSheet("color: #888899; font-size: 12px;")
        view_layout.addWidget(self.lbl_game_count)

        left_layout.addWidget(view_bar)
        splitter.addWidget(left_widget)

        # 우측: 정보 패널
        self.info_panel = InfoPanelWidget()
        self.info_panel.setMinimumWidth(300)
        self.info_panel.setMinimumHeight(0)
        splitter.addWidget(self.info_panel)

        # 스플리터 비율 설정 (70:30)
        splitter.setSizes([900, 380])
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        # 기본 뷰 모드
        self.btn_view_small.setChecked(True)

        # ── 하단 로그 패널 ──
        self.log_panel = QWidget()
        self.log_panel.setObjectName("log_panel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)

        # 로그 헤더 (토글 버튼)
        log_header = QWidget()
        log_header.setObjectName("log_header")
        log_header.setFixedHeight(24)
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(8, 0, 8, 0)
        lbl_log = QLabel("로그")
        lbl_log.setStyleSheet("font-size: 11px; font-family: 'SUIT-Medium';")
        self.btn_log_toggle = QPushButton("로그 표시 ▼")
        self.btn_log_toggle.setFixedHeight(24)
        self.btn_log_toggle.setFlat(True)
        self.btn_log_toggle.clicked.connect(self._toggle_log_panel)
        btn_log_clear = QPushButton("지우기")
        btn_log_clear.setFixedHeight(24)
        btn_log_clear.setFlat(True)
        btn_log_clear.setStyleSheet("font-size: 8pt;")
        def _clear_log():
            self.log_text.clear()
            # _log_bridge는 이미 log_text에 연결되어 있으므로 재설정 불필요
        btn_log_clear.clicked.connect(_clear_log)
        log_header_layout.addWidget(self.btn_log_toggle)
        log_header_layout.addWidget(lbl_log)
        log_header_layout.addStretch()
        log_header_layout.addWidget(btn_log_clear)
        log_layout.addWidget(log_header)

        # 로그 텍스트 영역
        from PyQt6.QtWidgets import QPlainTextEdit
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(120)
        self.log_text.setObjectName("log_text")
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(self.log_panel)
        self.log_visible = False
        self.log_text.setVisible(False)
        self.log_panel.setFixedHeight(24)

        # 스레드 안전 stdout 리다이렉트
        # _LogSignalBridge.message 시그널을 QueuedConnection으로 연결해
        # 백그라운드 스레드의 print()도 항상 메인 스레드에서 위젯에 반영됨
        import sys
        self._log_bridge = _LogSignalBridge()
        self._log_bridge.message.connect(
            self._append_log,
            Qt.ConnectionType.QueuedConnection
        )
        _redirector = _LogRedirector(self._log_bridge)
        sys.stdout = _redirector
        sys.stderr = _redirector

    def _make_action(self, text, callback=None, shortcut=None):
        """PyQt6 호환 QAction 생성 헬퍼"""
        action = QAction(text, self)
        if callback:
            action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        return action

    def _init_menubar(self):
        menubar = self.menuBar()
        # 메뉴바는 시스템 기본 색상 사용 (스타일시트 미적용)
        menubar.setStyleSheet("")

        # ── 메뉴 ──
        menu_main = menubar.addMenu("메뉴")
        menu_main.addAction(self._make_action("환경설정", self._open_settings, "Ctrl+,"))
        menu_main.addAction(self._make_action("테마/스킨", self._open_theme_dialog))
        menu_main.addAction(self._make_action("전체화면 토글", self._toggle_fullscreen, "Alt+Enter"))
        menu_main.addSeparator()
        menu_main.addAction(self._make_action("종료", self.close, "Alt+F4"))

        # ── 에뮬레이터 ──
        menu_emu = menubar.addMenu("에뮬레이터")
        menu_emu.addAction(self._make_action("에뮬레이터 등록/편집 ", self._open_emulator_dialog))
        menu_emu.addAction(self._make_action("에뮬레이터만 실행 ", self._run_emulator_only))

        # ── 도구 ──
        menu_tools = menubar.addMenu("도구")
        menu_tools.addAction(self._make_action("현재 탭 ROM 스캔    ", self._scan_current_platform, "F5"))
        menu_tools.addAction(self._make_action("ROM 전체 스캔    ", self._scan_roms, "Shift+F5"))
        menu_tools.addAction(self._make_action("ROM 불러오기", self._open_rom, "Ctrl+O"))
        menu_tools.addSeparator()
        menu_tools.addAction(self._make_action("ROM 폴더 설정", lambda: self._open_settings(2)))
        menu_tools.addSeparator()
        menu_tools.addAction(self._make_action("스크린샷 설정", self._open_screenshot_settings))
        menu_tools.addAction(self._make_action("녹화 폴더 열기", self._open_record_folder))
        menu_tools.addSeparator()
        menu_tools.addAction(self._make_action("DB 관리"))
        menu_tools.addAction(self._make_action("메타데이터 일괄 갱신", self._batch_update_metadata))
        menu_tools.addAction(self._make_action("플레이 기록 통계", self._show_stats))

        # ── 도움말 ──
        menu_help = menubar.addMenu("도움말")
        menu_help.addAction(self._make_action("버전 정보", self._show_about))
        menu_help.addAction(self._make_action("사용 방법 안내", self._show_help))
        menu_help.addSeparator()
        menu_help.addAction(self._make_action("재와니 블로그", self._open_blog))
        menu_help.addAction(self._make_action("유튜브 채널", self._open_youtube))
        menu_help.addSeparator()        
        menu_help.addAction(self._make_action("...에 관하여", self._show_emulators_about))


    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        # 스타일은 _apply_style에서 테마 적용
        self.status_bar.setStyleSheet("")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("JRGS 시작됨")

        self.lbl_status_total   = QLabel("전체 0개")
        self.lbl_status_recent  = QLabel("최근 플레이: -")
        self.lbl_status_fav     = QLabel("즐겨찾기: 0개")
        self.lbl_status_rec     = QLabel("")  # 녹화 중 표시

        for lbl in [self.lbl_status_total, self.lbl_status_recent,
                    self.lbl_status_fav, self.lbl_status_rec]:
            lbl.setStyleSheet("color: #888899; padding: 0 10px; font-size: 12px;")
            self.status_bar.addPermanentWidget(lbl)

    def _load_platforms(self):
        """플랫폼 탭 로드"""
        self.platforms = get_all_platforms()
        self.tab_bar.blockSignals(True)

        # 기존 탭 전부 제거
        while self.tab_bar.count() > 0:
            self.tab_bar.removeTab(0)

        # 즐겨찾기 탭 (고정)
        self.tab_bar.addTab("★ 즐겨찾기")

        for p in self.platforms:
            if p.get("is_visible", 1):
                self.tab_bar.addTab(p.get("display_name") or p["short_name"])

        self.tab_bar.blockSignals(False)
        self.tab_bar.setCurrentIndex(0)
        self._on_tab_changed(0)

    def _on_tab_changed(self, index):
        """탭 변경 시 게임 목록 로드"""
        visible_platforms = [p for p in self.platforms if p.get("is_visible", 1)]

        if index == 0:
            games = get_favorite_games()
            self.current_platform_id = None
            self.game_grid.current_platform_id = None
            self.game_grid.current_platform_extensions = []
        else:
            if index - 1 >= len(visible_platforms):
                return
            platform = visible_platforms[index - 1]
            self.current_platform_id = platform["id"]
            self.game_grid.current_platform_id = platform["id"]
            exts = [e.strip().lower() for e in platform["extensions"].split()
                    if e.strip()]
            self.game_grid.current_platform_extensions = [
                e if e.startswith(".") else f".{e}" for e in exts
            ]
            games = get_games_by_platform(platform["id"])

        self._all_games = games
        self._update_genre_filter(games)
        self.search_edit.clear()
        self.game_grid.load_games(games)
        self._update_game_count(len(games))

    def _update_game_count(self, count: int):
        """게임 수 표시 갱신"""
        self.lbl_game_count.setText(f"{count}개")
        self.lbl_status_total.setText(f"전체 {count}개")

    def _update_genre_filter(self, games: list):
        """장르 콤보박스 목록 갱신"""
        self.cmb_genre.blockSignals(True)
        self.cmb_genre.clear()
        self.cmb_genre.addItem("전체 장르")
        genres = sorted({g["genre"] for g in games if g.get("genre")})
        for genre in genres:
            self.cmb_genre.addItem(genre)
        self.cmb_genre.blockSignals(False)

    def _on_search_changed(self):
        """검색어/필터/정렬 변경 시 게임 목록 갱신"""
        keyword = self.search_edit.text().strip().lower()
        genre = self.cmb_genre.currentText()
        sort_idx = self.cmb_sort.currentIndex()

        games = self._all_games

        # 검색 필터
        if keyword:
            games = [g for g in games if
                     keyword in (g.get("title_kr") or "").lower() or
                     keyword in (g.get("title_en") or "").lower()]

        # 장르 필터
        if genre and genre != "전체 장르":
            games = [g for g in games if g.get("genre") == genre]

        # 정렬
        if sort_idx == 0:
            games = sorted(games, key=lambda g: (g.get("title_kr") or g.get("title_en") or "").lower())
        elif sort_idx == 1:
            games = sorted(games, key=lambda g: g.get("last_played") or "", reverse=True)
        elif sort_idx == 2:
            games = sorted(games, key=lambda g: g.get("play_count") or 0, reverse=True)

        self.game_grid.load_games(games)

    def _on_game_selected(self, game_id):
        """게임 선택 시 정보 패널 업데이트"""
        self.current_game_id = game_id
        self.info_panel.load_game(game_id)

    def _on_game_launched(self, game_id):
        """게임 실행"""
        self.info_panel.launch_game(game_id)

    def _on_view_mode_changed(self, mode_id):
        """뷰 모드 변경"""
        modes = ["name", "small", "large"]
        self.game_grid.set_view_mode(modes[mode_id])

    def _scan_roms(self, platform_short: str = None):
        """ROM 스캔 실행 (실행 중이면 차단)"""
        if self._scan_worker.isRunning():
            self.status_bar.showMessage("스캔 중입니다. 잠시 기다려주세요.", 2000)
            return
        self.status_bar.showMessage("ROM 스캔 중...")
        self._scan_worker.start_scan(platform_short=platform_short)

    def _unblock_scan(self):
        self._scan_blocked = False

    def _scan_current_platform(self):
        """현재 탭 플랫폼만 스캔"""
        idx = self.tab_bar.currentIndex()
        if idx == 0:
            self._scan_roms()
            return
        visible_platforms = [p for p in self.platforms if p.get("is_visible", 1)]
        if idx - 1 < len(visible_platforms):
            short = visible_platforms[idx - 1]["short_name"]
            self._scan_roms(platform_short=short)

    def _on_scan_finished(self, added: int, skipped: int, missing: int):
        msg = f"스캔 완료 - 추가: {added}개, 누락: {missing}개"
        self.status_bar.showMessage(msg, 5000)
        print(f"[스캔] {msg}")

    def _open_rom(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "ROM 파일 선택")
        if path:
            from folders import get_platform_extensions
            ext = Path(path).suffix.lower()
            ext_map = get_platform_extensions()
            platform_id = ext_map.get(ext)
            if platform_id:
                from database import add_game
                add_game(platform_id, path, title_en=Path(path).stem)
                self._on_tab_changed(self.tab_bar.currentIndex())
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "알 수 없는 형식", f"지원하지 않는 확장자입니다: {ext}")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _open_settings(self, tab_index: int = 0):
        from settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.tabs.setCurrentIndex(tab_index)
        if dlg.exec():
            # 창 크기 즉시 반영
            from database import get_setting
            w = int(get_setting("window_width", "1280"))
            h = int(get_setting("window_height", "800"))
            self.resize(w, h)

    def _open_screenshot_settings(self):
        from screenshot_dialog import ScreenshotSettingsDialog
        dlg = ScreenshotSettingsDialog(self)
        dlg.exec()

    def _open_record_folder(self):
        import subprocess
        from folders import get_record_folder
        subprocess.Popen(f'explorer "{get_record_folder()}"')

    def _open_emulator_dialog(self):
        from emulator_dialog import EmulatorDialog
        dlg = EmulatorDialog(self)
        dlg.exec()

    def _run_emulator_only(self):
        from emulator_dialog import RunEmulatorDialog
        dlg = RunEmulatorDialog(self)
        dlg.exec()

    def _show_stats(self):
        from stats_dialog import StatsDialog
        dlg = StatsDialog(self)
        dlg.exec()

    def _batch_update_metadata(self):
        from batch_meta_dialog import BatchMetaDialog
        current_tab = self.tab_bar.currentIndex()
        platform_id = None
        if current_tab > 0 and current_tab - 1 < len(self.platforms):
            platform_id = self.platforms[current_tab - 1]["id"]
        dlg = BatchMetaDialog(current_platform_id=platform_id, parent=self)
        dlg.exec()

    def _append_log(self, text: str):
        """로그 텍스트 추가 (항상 메인 스레드에서 호출됨)"""
        self.log_text.appendPlainText(text)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def _toggle_log_panel(self):
        self.log_visible = not self.log_visible
        self.log_text.setVisible(self.log_visible)
        self.log_panel.setFixedHeight(24 + (120 if self.log_visible else 0))
        self.btn_log_toggle.setText("로그 숨기기 ▲" if self.log_visible else "로그 표시 ▼")

    def _open_blog(self):
        import webbrowser
        webbrowser.open(get_setting("blog_url", "https://blog.naver.com/akrsodhk"))

    def _show_emulators_about(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
        import webbrowser

        EMULATORS_INFO = [
            {
                "name": "Mesen",
                "version": "v.2.1.1",
                "desc": "FC / SFC / GB / GBA / PCE 에뮬레이터",
                "url": "https://www.mesen.ca/",
            },
            {
                "name": "Fusion",
                "version": "v.3.64",
                "desc": "Mega Drive / SMS / MD CD 에뮬레이터",
                "url": "https://segaretro.org/Gens/GS",
            },
            {
                "name": "DeSmuME",
                "version": "v.0.9.13",
                "desc": "Nintendo DS 에뮬레이터",
                "url": "https://desmume.org/",
            },
            {
                "name": "Oswan",
                "version": "v.1.7.3",
                "desc": "WonderSwan 에뮬레이터",
                "url": "https://www.zophar.net/ws/oswan.html",
            },
            {
                "name": "blueMSX",
                "version": "v.2.8.2",
                "desc": "MSX 에뮬레이터",
                "url": "http://www.bluemsx.com/",
            },
        ]

        MORT_INFO = {
            "name": "MORT 실시간 번역기",
            "github_url": "https://github.com/killkimno/MORT/releases",
            "blog_url": "https://blog.naver.com/killkimno/223907695562",
        }

        dlg = QDialog(self)
        dlg.setWindowTitle("...에 관하여")
        dlg.setFixedWidth(420)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl_title = QLabel("사용 중인 에뮬레이터 및 도구")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(lbl_title)

        # 에뮬레이터 목록
        for info in EMULATORS_INFO:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            row = QHBoxLayout(frame)
            row.setContentsMargins(8, 6, 8, 6)

            left = QVBoxLayout()
            lbl_name = QLabel(info["name"])
            lbl_name.setStyleSheet("font-size: 12px; font-weight: bold;")
            lbl_desc = QLabel(info["desc"])
            lbl_desc.setStyleSheet("font-size: 10px; color: #888899;")
            left.addWidget(lbl_name)
            left.addWidget(lbl_desc)

            btn = QPushButton("🔗 공식 홈페이지")
            btn.setFixedHeight(26)
            btn.setFixedWidth(110)
            btn.clicked.connect(lambda _, u=info["url"]: webbrowser.open(u))

            row.addLayout(left)
            row.addStretch()
            row.addWidget(btn)
            layout.addWidget(frame)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        # MORT 정보
        lbl_mort_title = QLabel("MORT 실시간 번역기")
        lbl_mort_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(lbl_mort_title)

        mort_row = QHBoxLayout()
        btn_mort_git = QPushButton("🔗 GitHub")
        btn_mort_git.setFixedHeight(26)
        btn_mort_git.clicked.connect(lambda: webbrowser.open(MORT_INFO["github_url"]))
        btn_mort_blog = QPushButton("🔗 네이버 블로그")
        btn_mort_blog.setFixedHeight(26)
        btn_mort_blog.clicked.connect(lambda: webbrowser.open(MORT_INFO["blog_url"]))
        mort_row.addWidget(btn_mort_git)
        mort_row.addWidget(btn_mort_blog)
        mort_row.addStretch()
        layout.addLayout(mort_row)

        layout.addStretch()

        btn_close = QPushButton("닫기")
        btn_close.setFixedHeight(30)
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()

    def _open_youtube(self):
        import webbrowser
        webbrowser.open(get_setting("default_youtube_channel", "https://www.youtube.com/@jewani1004"))

    def _show_help(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "사용 방법",
            "1. 에뮬레이터 메뉴에서 에뮬레이터를 등록하세요.\n"
            "2. ROM 파일을 ROM_File 하위 폴더에 넣어주세요.\n"
            "3. F5를 눌러 ROM을 스캔하세요.\n"
            "4. 게임을 선택하고 더블클릭으로 실행하세요.\n\n"
            "자세한 내용은 재와니 블로그를 참고하세요!")

    def _show_about(self):
        from version_dialog import VersionDialog
        dlg = VersionDialog(self)
        dlg.exec()

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        qss = build_stylesheet(t)
        self.setStyleSheet(qss)

        # 탭바 별도 적용
        self.tab_bar.setStyleSheet(f"""
            QTabBar::tab {{
                padding: 8px 16px;
                font-size: 12px;
                font-weight: {t['tab_font']};
                background: {t['bg_panel']};
                color: {t['text_sub']};
                border: none;
                margin-right: 2px;
                border-radius: {t['tab_radius']};
            }}
            QTabBar::tab:selected {{ background: {t['bg_selected']}; color: {t['text_main']}; }}
            QTabBar::tab:hover {{ background: {t['bg_hover']}; color: {t['text_main']}; }}
        """)

        # 그리드/패널 배경 직접 지정
        self.game_grid.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {t['bg_deep']};
                border: none; outline: none;
            }}
            QListWidget::item {{
                color: {t['text_main']};
                border-radius: 6px; padding: 4px;
            }}
            QListWidget::item:selected {{
                background: {t['bg_selected']}; color: {t['text_main']};
            }}
            QListWidget::item:hover {{ background: {t['bg_hover']}; }}
            QToolTip {{
                background: {t['bg_panel']};
                color: {t['text_main']};
                border: 1px solid {t['border_light']};
                padding: 4px;
                font-size: 11px;
            }}
        """)
        self.info_panel._apply_style()
        self.centralWidget().setStyleSheet(f"background: {t['bg_base']};")

        # 하단 뷰 버튼 바
        view_btn_qss = f"""
            QPushButton {{
                background: {t['bg_panel']}; color: {t['text_sub']};
                border: 1px solid {t['border_light']}; border-radius: {t['btn_radius']};
                padding: 0 10px; font-size: 12px;
            }}
            QPushButton:checked {{ background: {t['bg_selected']}; color: {t['text_main']}; }}
            QPushButton:hover {{ background: {t['bg_hover']}; color: {t['text_main']}; }}
        """
        for btn in [self.btn_view_name, self.btn_view_small, self.btn_view_large]:
            btn.setStyleSheet(view_btn_qss)
        self.lbl_game_count.setStyleSheet(f"color: {t['text_dim']}; font-size: 12px;")

        # 뷰바 배경
        self.findChild(QWidget, "view_bar") # view_bar에 objectName 없어서 직접 접근 불가 → centralWidget 통해 처리
        view_bar = self.findChild(QWidget, "view_bar")
        if view_bar:
            view_bar.setStyleSheet(f"background: {t['bg_base']}; border-top: 1px solid {t['border']};")

        self.findChild(QWidget, "log_header").setStyleSheet(
            f"background: {t['bg_panel']}; border-top: 1px solid {t['border']};"
        )
        self.log_text.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {t['bg_deep']};
                color: {t['text_sub']};
                font-family: Consolas, monospace;
                font-size: 11px;
                border: none;
            }}
        """)

        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {t['bg_panel']};
                color: {t['text_dim']};
                border-top: 1px solid {t['border']};
                font-size: 12px;
            }}
        """)
        for lbl in [self.lbl_status_total, self.lbl_status_recent,
                    self.lbl_status_fav, self.lbl_status_rec]:
            lbl.setStyleSheet(f"color: {t['text_dim']}; padding: 0 10px;")
        for lbl in [self.lbl_status_total, self.lbl_status_recent,
                    self.lbl_status_fav, self.lbl_status_rec]:
            lbl.setStyleSheet(f"color: {t['text_dim']}; padding: 0 10px;")

    def _open_theme_dialog(self):
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
            QButtonGroup, QFrame
        )
        from theme import (THEMES, CUSTOM_SLOTS, CUSTOM_SLOT_NAMES,
                           get_current_theme_key, set_theme,
                           build_stylesheet, get_current_theme, CustomThemeDialog)

        dlg = QDialog(self)
        dlg.setWindowTitle("테마/스킨 선택")
        dlg.setMinimumSize(380, 280)
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)

        from PyQt6.QtWidgets import QComboBox
        from PyQt6.QtGui import QFontDatabase
        from database import get_setting, set_setting

        top_row = QHBoxLayout()
        lbl = QLabel("테마를 선택하세요:")
        top_row.addWidget(lbl)
        top_row.addStretch()

        lbl_font = QLabel("폰트:")
        lbl_font.setStyleSheet("font-size: 11px;")
        top_row.addWidget(lbl_font)

        font_combo = QComboBox()
        font_combo.setFixedHeight(24)
        font_combo.setFixedWidth(160)
        font_combo.setStyleSheet("font-size: 11px;")

        bundled = []
        fonts_dir = Path(__file__).resolve().parent.parent / "fonts"
        if fonts_dir.exists():
            for f in fonts_dir.iterdir():
                if f.suffix.lower() in (".ttf", ".otf"):
                    fid = QFontDatabase.addApplicationFont(str(f))
                    fams = QFontDatabase.applicationFontFamilies(fid)
                    if fams:
                        bundled.append(fams[0])
        all_fonts = bundled + [f for f in QFontDatabase.families() if f not in bundled]
        saved_font = get_setting("font", "SUIT-Medium")
        for fam in all_fonts:
            font_combo.addItem(fam)
        idx = font_combo.findText(saved_font)
        if idx >= 0:
            font_combo.setCurrentIndex(idx)

        def _on_font_changed(fam):
            set_setting("font", fam)
            f = QFont(fam)
            f.setPointSize(10)
            QApplication.instance().setFont(f)
            self._apply_style()

        font_combo.currentTextChanged.connect(_on_font_changed)
        top_row.addWidget(font_combo)
        layout.addLayout(top_row)

        current = get_current_theme_key()
        group = QButtonGroup(dlg)

        # 기본 테마 버튼
        btn_layout = QHBoxLayout()
        for key, info in THEMES.items():
            btn = QPushButton(info["name"])
            btn.setCheckable(True)
            btn.setChecked(key == current)
            btn.setFixedHeight(40)
            group.addButton(btn)
            btn.clicked.connect(lambda _, k=key: (
                set_theme(k),
                self._apply_style(),
                dlg.setWindowTitle("테마/스킨 선택  ✔ 적용됨 — 열린 창은 닫고 다시 여세요")
            ))
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        lbl2 = QLabel("커스텀 테마:")
        layout.addWidget(lbl2)

        # 커스텀 슬롯 3개
        from theme import get_custom_theme

        for slot in CUSTOM_SLOTS:
            row = QHBoxLayout()

            theme_data = get_custom_theme(slot)
            slot_label = theme_data.get("name", CUSTOM_SLOT_NAMES[slot])

            btn_select = QPushButton(slot_label)
            btn_select.setCheckable(True)
            btn_select.setChecked(slot == current)
            btn_select.setFixedHeight(36)
            btn_select.setFixedWidth(150)
            group.addButton(btn_select)
            btn_select.clicked.connect(lambda _, s=slot: (
                set_theme(s),
                self._apply_style(),
                dlg.setWindowTitle("테마/스킨 선택  ✔ 적용됨 — 열린 창은 닫고 다시 여세요")
            ))

            btn_edit = QPushButton("✏ 색상 편집")
            btn_edit.setFixedHeight(36)
            def _on_edit(_, s=slot, b=btn_select):
                CustomThemeDialog.open(s, dlg)
                updated = get_custom_theme(s)
                b.setText(updated.get("name", CUSTOM_SLOT_NAMES[s]))
                set_theme(s)
                self._apply_style()
                dlg.setWindowTitle("테마/스킨 선택  ✔ 적용됨 — 열린 창은 닫고 다시 여세요")
            btn_edit.clicked.connect(_on_edit)

            row.addWidget(btn_select)
            row.addWidget(btn_edit)
            row.addStretch()
            layout.addLayout(row)

        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)

        t = get_current_theme()
        dlg.setStyleSheet(build_stylesheet(t))
        dlg.exec()

    def keyPressEvent(self, event):
        """전역 단축키 처리"""
        key = event.key()
        mod = event.modifiers()
        Qt_Key = Qt.Key
        Qt_Mod = Qt.KeyboardModifier

        if key == Qt_Key.Key_F5:
            # 메뉴 액션 단축키와 중복 방지 - keyPressEvent에서는 처리 안 함
            pass
        elif key == Qt_Key.Key_Delete:
            if self.current_game_id:
                from PyQt6.QtWidgets import QMessageBox
                from database import delete_game
                reply = QMessageBox.question(
                    self, "게임 제거",
                    "목록에서 제거합니다. ROM 파일은 삭제되지 않습니다.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    delete_game(self.current_game_id)
                    self.current_game_id = None
                    self.info_panel.clear()
                    self._on_tab_changed(self.tab_bar.currentIndex())
        elif key == Qt_Key.Key_F2:
            if self.current_game_id:
                self.game_grid.rename_selected_game()
        elif key == Qt_Key.Key_F3:
            self.info_panel.load_state()
        elif key == Qt_Key.Key_F9:
            self.info_panel.toggle_ocr_overlay()
        elif key == Qt_Key.Key_F10:
            self.info_panel.screenshot_ocr()
        elif mod == Qt_Mod.ControlModifier and key == Qt_Key.Key_F12:
            self.info_panel.take_screenshot()
        elif mod == Qt_Mod.ControlModifier and key == Qt_Key.Key_R:
            self.info_panel.toggle_record()
        elif mod == Qt_Mod.ControlModifier and key == Qt_Key.Key_P:
            self.info_panel.pause_record()
        elif mod == Qt_Mod.ControlModifier and key == Qt_Key.Key_D:
            if self.current_game_id:
                from database import toggle_favorite
                toggle_favorite(self.current_game_id)
                self.info_panel.load_game(self.current_game_id)
        elif mod == Qt_Mod.ControlModifier and key == Qt_Key.Key_E:
            self.info_panel.enter_edit_mode()
        elif key == Qt_Key.Key_Return or key == Qt_Key.Key_Enter:
            if self.current_game_id:
                self.info_panel.launch_game(self.current_game_id)
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        """Ctrl+Shift+휠로 아이콘 크기 조정"""
        mod = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier
        shift = Qt.KeyboardModifier.ShiftModifier
        if (mod & ctrl) and (mod & shift):
            delta = event.angleDelta().y()
            if delta > 0:
                self.game_grid.increase_icon_size()
            else:
                self.game_grid.decrease_icon_size()
        else:
            super().wheelEvent(event)

    def closeEvent(self, event):
        """종료 시 창 크기 저장"""
        from database import set_setting
        set_setting("window_width", str(self.width()))
        set_setting("window_height", str(self.height()))
        event.accept()


def main():
    from PyQt6.QtCore import Qt
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName("JRGS")
    app.setOrganizationName("Jaewani")

    # 폰트 로드 (fonts/ 폴더 전체)
    from PyQt6.QtGui import QFontDatabase, QFont
    fonts_dir = Path(__file__).resolve().parent.parent / "fonts"
    print(f"[폰트] 폴더 경로: {fonts_dir}")
    print(f"[폰트] 폴더 존재: {fonts_dir.exists()}")
    if fonts_dir.exists():
        for font_file in sorted(fonts_dir.glob("*")):
            print(f"[폰트] 파일 발견: {font_file.name}")
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            fid = QFontDatabase.addApplicationFont(str(font_file))
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                print(f"[폰트] 로드됨: {families[0]}")
        for font_file in fonts_dir.glob("*.otf"):
            fid = QFontDatabase.addApplicationFont(str(font_file))
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                print(f"[폰트] 로드됨: {families[0]}")

    # 앱 기본 폰트 설정
    from database import get_setting
    saved_font = get_setting("font", "SUIT-Medium")
    default_font = QFont(saved_font)
    default_font.setPointSize(10)
    app.setFont(default_font)

    # DB 및 폴더 초기화
    init_db()
    init_folders()
    from folders import auto_register_mesen, auto_register_fusion, auto_register_desmume, auto_register_oswan, auto_register_bluemsx
    auto_register_mesen()
    auto_register_fusion()
    auto_register_desmume()
    auto_register_oswan()
    auto_register_bluemsx()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()