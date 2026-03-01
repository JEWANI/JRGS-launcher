"""
JRGS - 재와니의 레트로 게임 보관소
settings_dialog.py - 환경설정 다이얼로그
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QCheckBox, QComboBox, QPushButton, QLineEdit,
    QFileDialog, QSpinBox, QGroupBox, QFormLayout,
    QDialogButtonBox, QSizePolicy, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QRect

from database import get_setting, set_setting


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("환경설정")
        self.setMinimumSize(660, 500)
        self.setModal(True)
        self._init_ui()
        self._load_settings()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                font-size: 13px;
                padding: 4px 6px;
            }
        """)
        layout.addWidget(self.tabs)

        self._build_tab_general()
        self._build_tab_display()
        self._build_tab_folders()
        self._build_tab_metadata_api()
        self._build_tab_youtube()
        self._build_tab_mort()
        self._build_tab_recorder()
        self._build_tab_platform()
        self._build_tab_backup()

        btn_box = QDialogButtonBox()
        btn_box.addButton("확인", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(self._save_settings)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ── 일반 탭 ──────────────────────────────────────────
    def _build_tab_general(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        group = QGroupBox("시작 옵션")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.chk_auto_scan = self._make_toggle_btn("시작 시 ROM 자동 스캔")
        self.chk_minimize  = self._make_toggle_btn("게임 실행 시 런처 자동 최소화")

        form.addRow(self.chk_auto_scan)
        form.addRow(self.chk_minimize)
        layout.addWidget(group)

        group2 = QGroupBox("언어")
        form2 = QFormLayout(group2)
        form2.setSpacing(10)

        self.cmb_language = QComboBox()
        self.cmb_language.addItem("한국어 (Korean)", "ko")
        self.cmb_language.addItem("English", "en")
        self.cmb_language.setEnabled(True)
        lbl_lang = QLabel("* 언어 변경은 재시작 후 적용됩니다.")
        lbl_lang.setStyleSheet("color: #888899; font-size: 11px;")

        form2.addRow("언어:", self.cmb_language)
        form2.addRow(lbl_lang)
        layout.addWidget(group2)

        layout.addStretch()
        self.tabs.addTab(tab, "일반")

    # ── 화면 탭 ──────────────────────────────────────────
    def _build_tab_display(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        group = QGroupBox("창 크기")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.cmb_window_size = QComboBox()
        self.cmb_window_size.addItems([
            "800 x 600",
            "1024 x 768",
            "1280 x 720",
            "1280 x 800",
            "1600 x 900",
        ])
        self.cmb_window_size.currentIndexChanged.connect(self._on_size_preset_changed)

        form.addRow("창 크기:", self.cmb_window_size)
        layout.addWidget(group)

        group2 = QGroupBox("전체화면")
        form2 = QFormLayout(group2)
        self.chk_fullscreen = self._make_toggle_btn("시작 시 전체화면 모드")
        form2.addRow(self.chk_fullscreen)
        layout.addWidget(group2)

        layout.addStretch()
        self.tabs.addTab(tab, "화면")

    # ── 폴더 설정 탭 ─────────────────────────────────────
    PLATFORM_LABELS = {        
        "FC":   "Famicom (FC)",
        "SFC":  "Super Famicom (SFC)",
        "GB":   "Game Boy (GB)",
        "GBA":  "Game Boy Advance(GBA)",
        "PCE":  "PC Engine (PCE)",
        "SMS":  "Sega Master System(SMS)",
        "MD":   "Mega Drive (MD)",
        "MDCD": "Mega Drive CD(MCD)",
        "WS":   "WonderSwan(WS)",
        "NDS":  "Nintendo DS(NDS)",
        "MSX":  "MSX",
    }

    def _build_tab_folders(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # ── 플랫폼 선택 + 경로 리스트 ──
        group_rom = QGroupBox("플랫폼별 ROM 폴더 (다중 경로 지원)")
        rom_layout = QVBoxLayout(group_rom)
        rom_layout.setSpacing(6)

        # 플랫폼 선택 콤보
        plat_row = QHBoxLayout()
        plat_row.addWidget(QLabel("플랫폼:"))
        self.cmb_platform = QComboBox()
        for short, label in self.PLATFORM_LABELS.items():
            self.cmb_platform.addItem(label, short)
        self.cmb_platform.currentIndexChanged.connect(self._on_platform_changed)
        plat_row.addWidget(self.cmb_platform)
        plat_row.addStretch()
        rom_layout.addLayout(plat_row)

        # 경로 리스트
        from PyQt6.QtWidgets import QListWidget
        self.folder_list = QListWidget()
        self.folder_list.setFixedHeight(130)
        rom_layout.addWidget(self.folder_list)

        # 추가/삭제 버튼
        list_btn_row = QHBoxLayout()
        btn_add_folder = QPushButton("➕ 폴더 추가")
        btn_add_folder.setFixedHeight(28)
        btn_add_folder.clicked.connect(self._add_platform_folder)
        btn_remove_folder = QPushButton("🗑 선택 삭제")
        btn_remove_folder.setFixedHeight(28)
        btn_remove_folder.clicked.connect(self._remove_platform_folder)
        list_btn_row.addWidget(btn_add_folder)
        list_btn_row.addWidget(btn_remove_folder)
        list_btn_row.addStretch()
        rom_layout.addLayout(list_btn_row)

        outer.addWidget(group_rom)

        # ── 커버아트 폴더 (플랫폼별) ──
        group_cover = QGroupBox("플랫폼별 커버아트 폴더 (선택사항)")
        cover_layout = QVBoxLayout(group_cover)
        cover_layout.setSpacing(6)

        lbl_cover_info = QLabel(
            "위에서 선택한 플랫폼의 커버아트 폴더를 지정합니다.\n"
            "ROM 파일명 또는 영문 제목과 동일한 이미지(PNG/JPG/BMP/WEBP)를 자동으로 커버아트로 사용합니다."
        )
        lbl_cover_info.setWordWrap(True)
        lbl_cover_info.setStyleSheet("font-size: 10px; color: #888899;")
        cover_layout.addWidget(lbl_cover_info)

        cover_row = QHBoxLayout()
        self.edit_cover_folder = QLineEdit()
        self.edit_cover_folder.setPlaceholderText("커버아트 폴더 경로 (비워두면 비활성)")
        self.edit_cover_folder.setReadOnly(True)
        btn_cover_browse = QPushButton("찾아보기")
        btn_cover_browse.setFixedWidth(72)
        btn_cover_browse.setFixedHeight(26)
        btn_cover_browse.clicked.connect(self._browse_cover_folder)
        btn_cover_clear = QPushButton("초기화")
        btn_cover_clear.setFixedWidth(60)
        btn_cover_clear.setFixedHeight(26)
        btn_cover_clear.clicked.connect(self._clear_cover_folder)
        cover_row.addWidget(self.edit_cover_folder)
        cover_row.addWidget(btn_cover_browse)
        cover_row.addWidget(btn_cover_clear)
        cover_layout.addLayout(cover_row)

        outer.addWidget(group_cover)

        outer.addStretch()
        self.tabs.addTab(tab, "폴더 설정")

        # 첫 플랫폼 로드
        self._on_platform_changed(0)

    def _on_platform_changed(self, index: int):
        """플랫폼 변경 시 경로 목록 + 커버아트 폴더 갱신"""
        self.folder_list.clear()
        short = self.cmb_platform.itemData(index)
        if not short:
            return
        from database import get_platform_rom_folders
        from folders import get_platform_rom_folder
        # 커버아트 폴더 갱신
        self.edit_cover_folder.setText(get_setting(f"cover_art_folder_{short}", ""))
        # 기본 경로 + 추가 경로
        default = str(get_platform_rom_folder(short))
        extra = get_platform_rom_folders(short)
        all_paths = list(dict.fromkeys([default] + extra))
        for p in all_paths:
            self.folder_list.addItem(p)

    def _add_platform_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "ROM 폴더 선택")
        if not folder:
            return
        short = self.cmb_platform.currentData()
        from database import add_platform_rom_folder
        add_platform_rom_folder(short, folder)
        self._on_platform_changed(self.cmb_platform.currentIndex())

    def _remove_platform_folder(self):
        item = self.folder_list.currentItem()
        if not item:
            return
        short = self.cmb_platform.currentData()
        path = item.text()
        from database import remove_platform_rom_folder
        from folders import get_platform_rom_folder, PLATFORM_FOLDERS
        # 기본 경로는 삭제 불가
        default = str(get_platform_rom_folder(short))
        if path == default:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "삭제 불가", "기본 경로는 삭제할 수 없습니다.")
            return
        remove_platform_rom_folder(short, path)
        self._on_platform_changed(self.cmb_platform.currentIndex())

    def _make_folder_row(self, form: QFormLayout, label: str) -> QLineEdit:
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setPlaceholderText("폴더를 선택하세요...")
        edit.setReadOnly(True)
        btn = QPushButton("찾아보기")
        btn.setFixedWidth(90)
        btn.clicked.connect(lambda _, e=edit: self._browse_folder(e))
        row.addWidget(edit)
        row.addWidget(btn)
        form.addRow(label, row)
        return edit

    def _browse_folder(self, edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택", edit.text() or str(Path.home()))
        if folder:
            edit.setText(folder)

    # ── 설정 불러오기 / 저장 ─────────────────────────────
    def _load_settings(self):
        # 일반
        self.chk_auto_scan.setChecked(get_setting("auto_scan_on_start", "1") == "1")
        self.chk_minimize.setChecked(get_setting("minimize_on_launch", "1") == "1")

        # 언어
        lang = get_setting("language", "ko")
        idx = self.cmb_language.findData(lang)
        if idx >= 0:
            self.cmb_language.setCurrentIndex(idx)

        # 화면
        w = int(get_setting("window_width", "1280"))
        h = int(get_setting("window_height", "800"))
        self._sync_size_preset(w, h)
        self.chk_fullscreen.setChecked(get_setting("start_fullscreen", "0") == "1")

    def _save_settings(self):
        # 일반
        set_setting("auto_scan_on_start", "1" if self.chk_auto_scan.isChecked() else "0")
        set_setting("minimize_on_launch",  "1" if self.chk_minimize.isChecked()  else "0")

        # 언어
        lang = self.cmb_language.currentData()
        if lang:
            set_setting("language", lang)

        # 화면
        idx = self.cmb_window_size.currentIndex()
        if idx < len(self.PRESETS):
            w, h = self.PRESETS[idx]
            set_setting("window_width",  str(w))
            set_setting("window_height", str(h))
        set_setting("start_fullscreen", "1" if self.chk_fullscreen.isChecked() else "0")

        # ScreenScraper 계정
        set_setting("ss_user_id",       self.edit_ss_user_id.text().strip())
        set_setting("ss_user_password", self.edit_ss_user_pw.text().strip())
        # TheGamesDB / MobyGames
        set_setting("tgdb_api_key",      self.edit_tgdb_key.text().strip())
        set_setting("mobygames_api_key", self.edit_mbg_key.text().strip())

        # 유튜브
        set_setting("youtube_api_key",     self.edit_yt_api_key.text().strip())
        set_setting("youtube_channel_url", self.edit_yt_channel.text().strip())

        self.accept()

    # ── 창 크기 프리셋 동기화 ────────────────────────────
    PRESETS = [
        (800,  600),
        (1024, 768),
        (1280, 720),
        (1280, 800),
        (1600, 900),
    ]

    def _sync_size_preset(self, w: int, h: int):
        for i, (pw, ph) in enumerate(self.PRESETS):
            if pw == w and ph == h:
                self.cmb_window_size.setCurrentIndex(i)
                return
        self.cmb_window_size.setCurrentIndex(3)  # 기본값 1280x800

    def _on_size_preset_changed(self, index: int):
        if index < len(self.PRESETS):
            w, h = self.PRESETS[index]
            set_setting("window_width",  str(w))
            set_setting("window_height", str(h))

    # ── 메타데이터 API 탭 ────────────────────────────────
    def _build_tab_metadata_api(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── ScreenScraper ──
        lbl_ss = QLabel(
            "ScreenScraper: 레트로 게임 특화 무료 서비스 (1순위)\n"
            "무료 회원가입 후 아이디/비밀번호를 입력해주세요."
        )
        lbl_ss.setStyleSheet("font-size: 11px; color: #888899;")
        lbl_ss.setWordWrap(True)
        layout.addWidget(lbl_ss)

        btn_ss = QPushButton("🌐  ScreenScraper 회원가입 (무료)")
        btn_ss.setFixedHeight(28)
        btn_ss.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.screenscraper.fr/membreinscription.php"))
        )
        layout.addWidget(btn_ss)

        grp_ss = QGroupBox("ScreenScraper 계정")
        form_ss = QFormLayout(grp_ss)
        form_ss.setSpacing(8)

        self.edit_ss_user_id = QLineEdit()
        self.edit_ss_user_id.setPlaceholderText("ScreenScraper 아이디")
        self.edit_ss_user_id.setText(get_setting("ss_user_id", ""))
        form_ss.addRow("아이디:", self.edit_ss_user_id)

        self.edit_ss_user_pw = QLineEdit()
        self.edit_ss_user_pw.setPlaceholderText("ScreenScraper 비밀번호")
        self.edit_ss_user_pw.setText(get_setting("ss_user_password", ""))
        self.edit_ss_user_pw.setEchoMode(QLineEdit.EchoMode.Password)
        form_ss.addRow("비밀번호:", self.edit_ss_user_pw)

        layout.addWidget(grp_ss)

        # ── TheGamesDB ──
        btn_tgdb = QPushButton("🌐  TheGamesDB API 키 발급 (무료)")
        btn_tgdb.setFixedHeight(28)
        btn_tgdb.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://forums.thegamesdb.net/viewforum.php?f=10"))
        )
        layout.addWidget(btn_tgdb)

        grp_tgdb = QGroupBox("TheGamesDB (2순위 폴백)")
        form_tgdb = QFormLayout(grp_tgdb)
        form_tgdb.setSpacing(8)

        self.edit_tgdb_key = QLineEdit()
        self.edit_tgdb_key.setPlaceholderText("TheGamesDB API 키")
        self.edit_tgdb_key.setText(get_setting("tgdb_api_key", ""))
        form_tgdb.addRow("API 키:", self.edit_tgdb_key)

        layout.addWidget(grp_tgdb)

        # ── MobyGames ──
        btn_mbg = QPushButton("🌐  MobyGames API 키 발급 (무료)")
        btn_mbg.setFixedHeight(28)
        btn_mbg.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.mobygames.com/info/api/"))
        )
        layout.addWidget(btn_mbg)

        grp_mbg = QGroupBox("MobyGames (3순위 폴백)")
        form_mbg = QFormLayout(grp_mbg)
        form_mbg.setSpacing(8)

        self.edit_mbg_key = QLineEdit()
        self.edit_mbg_key.setPlaceholderText("MobyGames API 키")
        self.edit_mbg_key.setText(get_setting("mobygames_api_key", ""))
        form_mbg.addRow("API 키:", self.edit_mbg_key)

        layout.addWidget(grp_mbg)
        layout.addStretch()
        self.tabs.addTab(tab, "메타데이터 API")

    # ── 유튜브 탭 ────────────────────────────────────────
    def _build_tab_youtube(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        from database import get_setting

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # YouTube Data API 키
        group_api = QGroupBox("YouTube Data API")
        v_api = QVBoxLayout(group_api)
        v_api.setSpacing(8)

        lbl_desc = QLabel(
            "유튜브 자동 검색 기능을 사용하려면 YouTube Data API v3 키가 필요합니다.\n"
            "Google Cloud Console에서 무료로 발급받을 수 있습니다."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 11px; color: #888899;")
        v_api.addWidget(lbl_desc)

        btn_console = QPushButton("🌐  Google Cloud Console 열기")
        btn_console.setFixedHeight(28)
        btn_console.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://console.cloud.google.com/apis/credentials")))
        v_api.addWidget(btn_console)

        row_key = QHBoxLayout()
        lbl_key = QLabel("API 키:")
        lbl_key.setFixedWidth(80)
        self.edit_yt_api_key = QLineEdit()
        self.edit_yt_api_key.setFixedHeight(26)
        self.edit_yt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_yt_api_key.setPlaceholderText("AIza...")
        self.edit_yt_api_key.setText(get_setting("youtube_api_key", ""))
        row_key.addWidget(lbl_key)
        row_key.addWidget(self.edit_yt_api_key)
        v_api.addLayout(row_key)
        layout.addWidget(group_api)

        # 재와니 채널 설정
        group_ch = QGroupBox("재와니 채널")
        v_ch = QVBoxLayout(group_ch)
        v_ch.setSpacing(8)

        lbl_ch_desc = QLabel(
            "자동 검색 시 이 채널을 우선 검색합니다.\n"
            "채널에 영상이 없으면 유튜브 일반 검색으로 폴백됩니다."
        )
        lbl_ch_desc.setWordWrap(True)
        lbl_ch_desc.setStyleSheet("font-size: 11px; color: #888899;")
        v_ch.addWidget(lbl_ch_desc)

        row_ch = QHBoxLayout()
        lbl_ch = QLabel("채널 URL:")
        lbl_ch.setFixedWidth(80)
        self.edit_yt_channel = QLineEdit()
        self.edit_yt_channel.setFixedHeight(26)
        self.edit_yt_channel.setPlaceholderText("https://www.youtube.com/@jewani1004")
        self.edit_yt_channel.setText(get_setting(
            "youtube_channel_url", "https://www.youtube.com/@jewani1004"))
        row_ch.addWidget(lbl_ch)
        row_ch.addWidget(self.edit_yt_channel)
        v_ch.addLayout(row_ch)

        btn_ch = QPushButton("🌐  채널 열기")
        btn_ch.setFixedHeight(28)
        btn_ch.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl(self.edit_yt_channel.text().strip() or
                 "https://www.youtube.com/@jewani1004")))
        v_ch.addWidget(btn_ch)
        layout.addWidget(group_ch)

        layout.addStretch()
        self.tabs.addTab(tab, "유튜브")

    # ── 백업/복원 탭 ─────────────────────────────────────
    # ── MORT 연동 탭 ─────────────────────────────────────
    def _build_tab_mort(self):
        from PyQt6.QtWidgets import QLineEdit, QGroupBox
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        group = QGroupBox("MORT 실시간 번역기 연동")
        form_layout = QVBoxLayout(group)
        form_layout.setSpacing(8)

        # MORT 경로
        row_path = QHBoxLayout()
        lbl_path = QLabel("MORT 경로:")
        lbl_path.setFixedWidth(80)
        self.edit_mort_path = QLineEdit(get_setting("mort_exe_path", ""))
        self.edit_mort_path.setPlaceholderText("MORT.exe 경로 선택...")
        self.edit_mort_path.setFixedHeight(26)
        btn_browse = QPushButton("찾아보기")
        btn_browse.setFixedHeight(26)
        btn_browse.setFixedWidth(70)
        btn_browse.clicked.connect(self._browse_mort)
        row_path.addWidget(lbl_path)
        row_path.addWidget(self.edit_mort_path)
        row_path.addWidget(btn_browse)
        form_layout.addLayout(row_path)

        # 옵션 토글 버튼
        self.btn_mort_auto_start = QPushButton(
            "✔  게임 실행 시 MORT 자동 시작" if get_setting("mort_auto_start", "0") == "1"
            else "☐  게임 실행 시 MORT 자동 시작"
        )
        self.btn_mort_auto_start.setCheckable(True)
        self.btn_mort_auto_start.setChecked(get_setting("mort_auto_start", "0") == "1")
        self.btn_mort_auto_start.setFixedHeight(28)
        self.btn_mort_auto_start.toggled.connect(self._on_mort_auto_start_toggled)
        form_layout.addWidget(self.btn_mort_auto_start)

        self.btn_mort_auto_stop = QPushButton(
            "✔  게임 종료 시 MORT 자동 종료" if get_setting("mort_auto_stop", "0") == "1"
            else "☐  게임 종료 시 MORT 자동 종료"
        )
        self.btn_mort_auto_stop.setCheckable(True)
        self.btn_mort_auto_stop.setChecked(get_setting("mort_auto_stop", "0") == "1")
        self.btn_mort_auto_stop.setFixedHeight(28)
        self.btn_mort_auto_stop.toggled.connect(
            lambda c, b=self.btn_mort_auto_stop: (
                b.setText("✔  게임 종료 시 MORT 자동 종료" if c else "☐  게임 종료 시 MORT 자동 종료"),
                self._save_mort_settings(silent=True)
            )
        )
        # 자동 시작 OFF면 자동 종료 비활성화
        if get_setting("mort_auto_start", "0") != "1":
            self.btn_mort_auto_stop.setEnabled(False)
        form_layout.addWidget(self.btn_mort_auto_stop)

        lbl_info = QLabel("※ MORT는 별도 설치가 필요합니다.\nhttps://github.com/killkimno/MORT")
        lbl_info.setStyleSheet("font-size: 10px; color: #888899;")
        form_layout.addWidget(lbl_info)

        btn_link_git = QPushButton("🔗 MORT GitHub")
        btn_link_git.setFixedHeight(26)
        btn_link_git.clicked.connect(lambda: __import__("webbrowser").open("https://github.com/killkimno/MORT/releases"))
        form_layout.addWidget(btn_link_git)

        btn_link_blog = QPushButton("🔗 MORT 네이버 블로그")
        btn_link_blog.setFixedHeight(26)
        btn_link_blog.clicked.connect(lambda: __import__("webbrowser").open("https://blog.naver.com/killkimno/223907695562"))
        form_layout.addWidget(btn_link_blog)

        layout.addWidget(group)
        layout.addStretch()

        # MORT 실행 버튼
        self.btn_run_mort = QPushButton("▶ MORT 실행")
        self.btn_run_mort.setFixedHeight(32)
        self.btn_run_mort.setEnabled(bool(self.edit_mort_path.text().strip()))
        self.btn_run_mort.clicked.connect(self._run_mort)
        self.edit_mort_path.textChanged.connect(
            lambda t: self.btn_run_mort.setEnabled(bool(t.strip()))
        )
        layout.addWidget(self.btn_run_mort)

        # 저장 버튼
        btn_save = QPushButton("💾 저장")
        btn_save.setFixedHeight(32)
        btn_save.clicked.connect(self._save_mort_settings)
        layout.addWidget(btn_save)

        self.tabs.addTab(tab, "MORT 번역기")

    def _build_tab_recorder(self):
        from PyQt6.QtWidgets import QLineEdit, QGroupBox
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        group = QGroupBox("외부 녹화 프로그램 연동")
        form_layout = QVBoxLayout(group)
        form_layout.setSpacing(8)

        lbl_info = QLabel(
            "반디캠, OBS 등 외부 녹화 프로그램을 연동합니다.\n"
            "Ctrl+R 단축키로 게임 실행 시 자동 시작/종료할 수 있습니다."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 10px; color: #888899;")
        form_layout.addWidget(lbl_info)

        # 녹화 프로그램 경로
        row_path = QHBoxLayout()
        lbl_path = QLabel("경로:")
        lbl_path.setFixedWidth(80)
        self.edit_recorder_path = QLineEdit(get_setting("recorder_exe_path", ""))
        self.edit_recorder_path.setPlaceholderText("녹화 프로그램 EXE 경로 선택...")
        self.edit_recorder_path.setFixedHeight(26)
        btn_browse = QPushButton("찾아보기")
        btn_browse.setFixedHeight(26)
        btn_browse.setFixedWidth(70)
        btn_browse.clicked.connect(self._browse_recorder)
        row_path.addWidget(lbl_path)
        row_path.addWidget(self.edit_recorder_path)
        row_path.addWidget(btn_browse)
        form_layout.addLayout(row_path)

        # 실행 인자
        row_args = QHBoxLayout()
        lbl_args = QLabel("실행 인자:")
        lbl_args.setFixedWidth(80)
        self.edit_recorder_args = QLineEdit(get_setting("recorder_args", ""))
        self.edit_recorder_args.setPlaceholderText("예: --startrecord (없으면 비워두세요)")
        self.edit_recorder_args.setFixedHeight(26)
        row_args.addWidget(lbl_args)
        row_args.addWidget(self.edit_recorder_args)
        form_layout.addLayout(row_args)

        # 옵션 토글
        self.btn_rec_auto_start = QPushButton(
            "✔  게임 실행 시 녹화 자동 시작" if get_setting("recorder_auto_start", "0") == "1"
            else "☐  게임 실행 시 녹화 자동 시작"
        )
        self.btn_rec_auto_start.setCheckable(True)
        self.btn_rec_auto_start.setChecked(get_setting("recorder_auto_start", "0") == "1")
        self.btn_rec_auto_start.setFixedHeight(28)
        self.btn_rec_auto_start.toggled.connect(
            lambda c, b=self.btn_rec_auto_start: (
                b.setText("✔  게임 실행 시 녹화 자동 시작" if c else "☐  게임 실행 시 녹화 자동 시작"),
                self._save_recorder_settings(silent=True)
            )
        )
        form_layout.addWidget(self.btn_rec_auto_start)

        self.btn_rec_auto_stop = QPushButton(
            "✔  게임 종료 시 녹화 자동 종료" if get_setting("recorder_auto_stop", "0") == "1"
            else "☐  게임 종료 시 녹화 자동 종료"
        )
        self.btn_rec_auto_stop.setCheckable(True)
        self.btn_rec_auto_stop.setChecked(get_setting("recorder_auto_stop", "0") == "1")
        self.btn_rec_auto_stop.setFixedHeight(28)
        self.btn_rec_auto_stop.toggled.connect(
            lambda c, b=self.btn_rec_auto_stop: (
                b.setText("✔  게임 종료 시 녹화 자동 종료" if c else "☐  게임 종료 시 녹화 자동 종료"),
                self._save_recorder_settings(silent=True)
            )
        )
        form_layout.addWidget(self.btn_rec_auto_stop)

        layout.addWidget(group)
        layout.addStretch()

        # 녹화 프로그램 실행 버튼
        self.btn_run_rec = QPushButton("▶ 녹화 프로그램 실행")
        self.btn_run_rec.setFixedHeight(32)
        self.btn_run_rec.setEnabled(bool(self.edit_recorder_path.text().strip()))
        self.btn_run_rec.clicked.connect(self._run_recorder)
        self.edit_recorder_path.textChanged.connect(
            lambda t: self.btn_run_rec.setEnabled(bool(t.strip()))
        )
        layout.addWidget(self.btn_run_rec)

        btn_save = QPushButton("💾 저장")
        btn_save.setFixedHeight(32)
        btn_save.clicked.connect(self._save_recorder_settings)
        layout.addWidget(btn_save)

        self.tabs.addTab(tab, "녹화 프로그램")

    def _on_mort_auto_start_toggled(self, checked: bool):
        self.btn_mort_auto_start.setText(
            "✔  게임 실행 시 MORT 자동 시작" if checked else "☐  게임 실행 시 MORT 자동 시작"
        )
        if not checked:
            self.btn_mort_auto_stop.setChecked(False)
            self.btn_mort_auto_stop.setText("☐  게임 종료 시 MORT 자동 종료")
            self.btn_mort_auto_stop.setEnabled(False)
        else:
            self.btn_mort_auto_stop.setEnabled(True)
        self._save_mort_settings(silent=True)

    def _run_mort(self):
        import subprocess
        path = self.edit_mort_path.text().strip()
        if not path:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "경고", "MORT 경로가 설정되지 않았습니다.")
            return
        try:
            subprocess.Popen([path])
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "오류", f"MORT 실행 실패:\n{e}")

    def _run_recorder(self):
        import subprocess
        path = self.edit_recorder_path.text().strip()
        args = self.edit_recorder_args.text().strip()
        if not path:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "경고", "녹화 프로그램 경로가 설정되지 않았습니다.")
            return
        try:
            cmd = [path] + args.split() if args else [path]
            subprocess.Popen(cmd)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "오류", f"녹화 프로그램 실행 실패:\n{e}")

    def _browse_recorder(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "녹화 프로그램 선택", "", "실행 파일 (*.exe);;모든 파일 (*)"
        )
        if path:
            self.edit_recorder_path.setText(path)

    def _save_recorder_settings(self, silent=False):
        set_setting("recorder_exe_path", self.edit_recorder_path.text().strip())
        set_setting("recorder_args",     self.edit_recorder_args.text().strip())
        set_setting("recorder_auto_start", "1" if self.btn_rec_auto_start.isChecked() else "0")
        set_setting("recorder_auto_stop",  "1" if self.btn_rec_auto_stop.isChecked() else "0")
        if not silent:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "저장 완료", "녹화 프로그램 설정이 저장되었습니다.")

    def _browse_mort(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "MORT.exe 선택", "", "실행 파일 (*.exe)"
        )
        if path:
            self.edit_mort_path.setText(path)

    def _save_mort_settings(self, silent=False):
        set_setting("mort_exe_path", self.edit_mort_path.text().strip())
        set_setting("mort_auto_start", "1" if self.btn_mort_auto_start.isChecked() else "0")
        set_setting("mort_auto_stop",  "1" if self.btn_mort_auto_stop.isChecked() else "0")
        if not silent:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "저장 완료", "MORT 연동 설정이 저장되었습니다.")

    def _build_tab_platform(self):
        """플랫폼 탭 설정"""
        from database import get_all_platforms
        from PyQt6.QtWidgets import QLineEdit
        from theme import get_current_theme
        t = get_current_theme()

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        lbl = QLabel("탭 표시/숨기기, 순서, 이름을 변경할 수 있습니다.\n★ 즐겨찾기는 항상 고정입니다.")
        lbl.setStyleSheet("font-size: 11px; color: #888899;")
        layout.addWidget(lbl)

        self._platform_rows = []
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(3)
        inner_layout.setContentsMargins(4, 4, 4, 4)

        btn_style = f"""
            QPushButton {{
                background: {t['bg_hover']};
                color: {t['text_main']};
                border: 1px solid {t['border_light']};
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{ background: {t['bg_selected']}; }}
        """

        platforms = get_all_platforms()
        for p in platforms:
            row_widget = QWidget()
            row_widget.setFixedHeight(32)
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(4, 2, 4, 2)
            row.setSpacing(8)

            label = "사용"
            chk = QPushButton(f"✔  {label}" if bool(p.get("is_visible", 1)) else f"☐  {label}")
            chk.setCheckable(True)
            chk.setChecked(bool(p.get("is_visible", 1)))
            chk.setFixedSize(64, 26)
            chk.setStyleSheet("")
            chk.toggled.connect(lambda checked, b=chk, l=label: b.setText(f"✔  {l}" if checked else f"☐  {l}"))
            row.addWidget(chk)

            lbl_short = QLabel(f"[{p['short_name']}]")
            lbl_short.setFixedWidth(58)
            lbl_short.setStyleSheet("font-size: 11px; color: #888899;")
            row.addWidget(lbl_short)

            edit_name = QLineEdit(p.get("display_name") or p["name"])
            edit_name.setFixedHeight(24)
            edit_name.setStyleSheet(f"font-size: 11px; background: {t['bg_panel']}; color: {t['text_main']}; border: 1px solid {t['border']}; border-radius: 3px; padding: 0 4px;")
            row.addWidget(edit_name)

            btn_up = QPushButton("↑")
            btn_up.setFixedSize(26, 26)
            btn_up.setStyleSheet(btn_style)
            btn_down = QPushButton("↓")
            btn_down.setFixedSize(26, 26)
            btn_down.setStyleSheet(btn_style)
            row.addWidget(btn_up)
            row.addWidget(btn_down)

            inner_layout.addWidget(row_widget)
            self._platform_rows.append({
                "short_name": p["short_name"],
                "chk": chk,
                "edit": edit_name,
                "widget": row_widget,
            })

            btn_up.clicked.connect(lambda _, sn=p["short_name"]: self._platform_move(sn, -1))
            btn_down.clicked.connect(lambda _, sn=p["short_name"]: self._platform_move(sn, 1))

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_reset = QPushButton("기본값으로 초기화")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self._platform_reset)
        layout.addWidget(btn_reset)

        btn_save = QPushButton("💾 적용")
        btn_save.setFixedHeight(32)
        btn_save.clicked.connect(self._platform_save)
        layout.addWidget(btn_save)

        self.tabs.addTab(tab, "탭 설정")

    def _platform_move(self, short_name: str, direction: int):
        """순서 이동 (direction: -1=위, 1=아래)"""
        rows = self._platform_rows
        idx = next((i for i, r in enumerate(rows) if r["short_name"] == short_name), None)
        if idx is None:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(rows):
            return
        rows[idx], rows[new_idx] = rows[new_idx], rows[idx]

        # UI 순서 재정렬
        scroll_inner = rows[0]["widget"].parent()
        layout = scroll_inner.layout()
        for r in rows:
            layout.removeWidget(r["widget"])
        for r in rows:
            layout.addWidget(r["widget"])

    def _platform_save(self):
        """플랫폼 탭 설정 저장"""
        from database import update_platform_tab
        for order, r in enumerate(self._platform_rows):
            update_platform_tab(
                r["short_name"],
                1 if r["chk"].isChecked() else 0,
                order,
                r["edit"].text().strip() or r["short_name"]
            )
        # 메인창 탭바 갱신
        if self.parent():
            try:
                self.parent()._load_platforms()
            except Exception:
                pass
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "저장 완료", "플랫폼 탭 설정이 저장되었습니다.")

    def _platform_reset(self):
        """기본 순서/표시 상태로 초기화"""
        from PyQt6.QtWidgets import QMessageBox
        from database import update_platform_tab
        defaults = [
            ('FC',0),('SFC',1),('GB',2),('GBA',3),('PCE',4),
            ('SMS',5),('MD',6),('MDCD',7),('WS',8),('NDS',9),
            ('MSX',10),('PS1',11),('PS2',12),('GP32',13)
        ]
        hidden = {'GP32', 'PS1', 'PS2', 'MSX'}
        for sn, order in defaults:
            conn_row = next((r for r in self._platform_rows if r["short_name"] == sn), None)
            if conn_row:
                original_name = next(
                    (r["edit"].placeholderText() or sn for r in self._platform_rows if r["short_name"] == sn), sn
                )
                update_platform_tab(sn, 0 if sn in hidden else 1, order, original_name)
        # 탭바 갱신 후 다이얼로그 재로드
        if self.parent():
            try:
                self.parent()._load_platforms()
            except Exception:
                pass
        QMessageBox.information(self, "초기화 완료", "기본값으로 초기화되었습니다.\n환경설정을 다시 열어주세요.")
        self.accept()

    def _build_tab_backup(self):
        from PyQt6.QtWidgets import QMessageBox
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 백업 폴더 설정 그룹
        group_folder = QGroupBox("백업 기본 폴더")
        v_folder = QVBoxLayout(group_folder)
        v_folder.setSpacing(6)

        folder_row = QHBoxLayout()
        self.edit_backup_folder = QLineEdit()
        self.edit_backup_folder.setReadOnly(True)
        self.edit_backup_folder.setPlaceholderText("폴더를 지정하면 기본 저장 위치로 사용됩니다")
        saved_folder = get_setting("backup_folder", "")
        self.edit_backup_folder.setText(saved_folder)

        btn_folder = QPushButton("📂 찾아보기")
        btn_folder.setFixedHeight(28)
        btn_folder.setFixedWidth(90)
        btn_folder.clicked.connect(self._pick_backup_folder)

        btn_folder_clear = QPushButton("초기화")
        btn_folder_clear.setFixedHeight(28)
        btn_folder_clear.setFixedWidth(60)
        btn_folder_clear.clicked.connect(self._clear_backup_folder)

        folder_row.addWidget(self.edit_backup_folder)
        folder_row.addWidget(btn_folder)
        folder_row.addWidget(btn_folder_clear)
        v_folder.addLayout(folder_row)
        layout.addWidget(group_folder)

        # 백업 그룹
        group_backup = QGroupBox("백업")
        v_backup = QVBoxLayout(group_backup)
        v_backup.setSpacing(8)

        self.lbl_last_backup = QLabel("마지막 백업: 없음")
        self.lbl_last_backup.setStyleSheet("font-size: 11px; color: #888899;")
        v_backup.addWidget(self.lbl_last_backup)

        btn_backup = QPushButton("💾  지금 백업하기")
        btn_backup.setFixedHeight(34)
        btn_backup.clicked.connect(self._do_backup)
        v_backup.addWidget(btn_backup)
        layout.addWidget(group_backup)

        # 복원 그룹
        group_restore = QGroupBox("복원")
        v_restore = QVBoxLayout(group_restore)
        v_restore.setSpacing(8)

        lbl_warn = QLabel("⚠  복원 시 현재 데이터가 덮어쓰기됩니다.")
        lbl_warn.setStyleSheet("font-size: 11px; color: #ffaa44;")
        v_restore.addWidget(lbl_warn)

        btn_restore = QPushButton("📂  백업 파일로 복원")
        btn_restore.setFixedHeight(34)
        btn_restore.clicked.connect(self._do_restore)
        v_restore.addWidget(btn_restore)
        layout.addWidget(group_restore)

        layout.addStretch()
        self.tabs.addTab(tab, "백업/복원")

        # 마지막 백업 날짜 표시
        self._refresh_last_backup_label()

    def _refresh_last_backup_label(self):
        val = get_setting("last_backup_time", "")
        if val:
            self.lbl_last_backup.setText(f"마지막 백업: {val}")
        else:
            self.lbl_last_backup.setText("마지막 백업: 없음")

    def _pick_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "백업 폴더 선택", self.edit_backup_folder.text() or "")
        if folder:
            self.edit_backup_folder.setText(folder)
            set_setting("backup_folder", folder)

    def _clear_backup_folder(self):
        self.edit_backup_folder.setText("")
        set_setting("backup_folder", "")

    def _do_backup(self):
        import zipfile, datetime
        from PyQt6.QtWidgets import QMessageBox
        from database import get_db_path
        from folders import get_gamedata_root as get_gamedata_folder

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"JRGS_backup_{now_str}.jrgs_backup"

        backup_folder = get_setting("backup_folder", "")
        default_path = str(Path(backup_folder) / default_name) if backup_folder else default_name

        save_path, _ = QFileDialog.getSaveFileName(
            self, "백업 파일 저장", default_path, "JRGS 백업 (*.jrgs_backup)"
        )
        if not save_path:
            return

        try:
            db_path = get_db_path()
            gamedata_path = get_gamedata_folder()

            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # DB 파일
                zf.write(db_path, "jrgs.db")
                # GameData 폴더
                if gamedata_path.exists():
                    for f in gamedata_path.rglob("*"):
                        if f.is_file():
                            zf.write(f, Path("GameData") / f.relative_to(gamedata_path))

            display_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            set_setting("last_backup_time", display_time)
            self._refresh_last_backup_label()
            QMessageBox.information(self, "백업 완료", f"백업이 완료되었습니다.\n{save_path}")
            print(f"[백업] 완료: {save_path}")

        except Exception as e:
            QMessageBox.critical(self, "백업 실패", f"백업 중 오류가 발생했습니다.\n{e}")
            print(f"[백업] 오류: {e}")

    def _do_restore(self):
        import zipfile, shutil, datetime
        from PyQt6.QtWidgets import QMessageBox
        from database import get_db_path
        from folders import get_gamedata_root as get_gamedata_folder

        path, _ = QFileDialog.getOpenFileName(
            self, "백업 파일 선택", "", "JRGS 백업 (*.jrgs_backup)"
        )
        if not path:
            return

        reply = QMessageBox.question(
            self, "복원 확인",
            "현재 데이터가 백업 파일로 덮어쓰기됩니다.\n계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            db_path = get_db_path()
            gamedata_path = get_gamedata_folder()

            # 현재 데이터 임시 백업
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            tmp_dir = db_path.parent / f"_restore_tmp_{now_str}"
            tmp_dir.mkdir(exist_ok=True)
            shutil.copy2(db_path, tmp_dir / "jrgs.db")
            if gamedata_path.exists():
                shutil.copytree(gamedata_path, tmp_dir / "GameData")

            # 복원
            with zipfile.ZipFile(path, "r") as zf:
                for member in zf.namelist():
                    if member == "jrgs.db":
                        zf.extract(member, db_path.parent)
                    elif member.startswith("GameData/") or member.startswith("GameData\\"):
                        zf.extract(member, db_path.parent)

            QMessageBox.information(
                self, "복원 완료",
                "복원이 완료되었습니다.\n앱을 재시작하면 적용됩니다."
            )
            print(f"[복원] 완료: {path}")

        except Exception as e:
            QMessageBox.critical(self, "복원 실패", f"복원 중 오류가 발생했습니다.\n{e}")
            print(f"[복원] 오류: {e}")

    # ── 스타일 ───────────────────────────────────────────
    def _make_toggle_btn(self, label: str) -> QPushButton:
        """✔ 표시 토글 버튼 생성 (QCheckBox 대체)"""
        btn = QPushButton(f"☐  {label}")
        btn.setCheckable(True)
        btn.setFixedHeight(28)
        btn.setStyleSheet("")
        btn.toggled.connect(lambda checked, b=btn, l=label: b.setText(f"✔  {l}" if checked else f"☐  {l}"))
        return btn

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        self.setStyleSheet(build_stylesheet(t) + f"""
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 2px solid {t['border_light']};
                border-radius: 3px;
                background: {t['bg_panel']};
            }}
            QCheckBox::indicator:checked {{
                background: {t['bg_selected']};
                border: 2px solid {t['bg_selected']};
            }}
        """)

    def _browse_cover_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "커버아트 폴더 선택")
        if folder:
            self.edit_cover_folder.setText(folder)
            short = self.cmb_platform.currentData()
            if short:
                set_setting(f"cover_art_folder_{short}", folder)

    def _clear_cover_folder(self):
        self.edit_cover_folder.setText("")
        short = self.cmb_platform.currentData()
        if short:
            set_setting(f"cover_art_folder_{short}", "")