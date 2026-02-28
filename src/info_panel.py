"""
JRGS - 재와니의 레트로 게임 보관소
info_panel.py - 우측 게임 정보 패널
"""

import subprocess
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTabWidget, QComboBox,
    QLineEdit, QTextEdit, QSizePolicy, QListWidget, QListWidgetItem,
    QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

from database import get_game_detail, update_game, toggle_favorite, update_play_history, get_setting

# ── 언어 상수 (추후 다국어 지원 시 교체) ──────────────────────────
TR = {
    "select_game":      "게임을 선택하세요",
    "no_cover":         "커버아트 없음",
    "tab_game_info":    "🖼 게임 정보",
    "tab_video":        "🎬 동영상",
    "tab_snapshot":     "📷 스냅샷",
    "favorite_add":     "☆ 즐겨찾기",
    "favorite_remove":  "★ 즐겨찾기 해제",
    "btn_edit":         "✏ 편집",
    "btn_set_emu":      "🎮 에뮬 지정",
    "btn_launch":       "▶ 실행",
    "btn_meta_search":  "🔍 메타데이터 검색",
    "btn_img_search":   "🖼 이미지 검색",
    "field_platform":   "플랫폼",
    "field_emulator":   "에뮬레이터",
    "field_genre":      "장르",
    "field_developer":  "제작사",
    "field_publisher":  "퍼블리셔",
    "field_year":       "출시연도",
    "field_region":     "출시국가",
    "field_playcount":  "플레이",
    "field_lastplayed": "마지막",
    "field_playtime":   "총 시간",
    "field_tips":       "게임 팁",
    "snap_select":      "스냅샷을 선택하세요",
    "snap_refresh":     "🔄 새로고침",
    "snap_memo_label":  "메모:",
    "snap_memo_save":   "저장",
    "snap_captured":    "촬영:",
    "video_no_url":     "연결된 유튜브 영상이 없습니다.\n아래에서 링크를 추가해주세요.",
    "video_add_link":   "➕ 링크 추가",
    "video_del_link":   "🗑 선택 삭제",
    "video_desc_label": "영상 설명:",
    "video_desc_edit":  "✏ 편집",
    "video_desc_save":  "💾 저장",
    "video_open_browser": "🌐 브라우저로 열기",
    "no_data":          "-",
}


class LaunchWorker(QThread):
    """에뮬레이터 실행 스레드 (플레이 타임 측정)"""
    finished = pyqtSignal(int)  # playtime_sec

    def __init__(self, exe_path, args, rom_path):
        super().__init__()
        self.exe_path = exe_path
        self.args = args
        self.rom_path = rom_path

    def run(self):
        from database import get_setting
        import os
        start = time.time()
        mort_proc = None
        rec_proc  = None

        # MORT 자동 시작
        mort_exe = get_setting("mort_exe_path", "")
        if mort_exe and get_setting("mort_auto_start", "0") == "1":
            try:
                if os.path.exists(mort_exe):
                    mort_proc = subprocess.Popen([mort_exe])
                    print(f"[MORT] 자동 시작: {mort_exe}")
            except Exception as e:
                print(f"[MORT] 시작 오류: {e}")

        # 녹화 프로그램 자동 시작
        rec_exe  = get_setting("recorder_exe_path", "")
        rec_args = get_setting("recorder_args", "")
        if rec_exe and get_setting("recorder_auto_start", "0") == "1":
            try:
                if os.path.exists(rec_exe):
                    cmd = [rec_exe] + rec_args.split() if rec_args else [rec_exe]
                    rec_proc = subprocess.Popen(cmd)
                    print(f"[녹화] 자동 시작: {rec_exe}")
            except Exception as e:
                print(f"[녹화] 시작 오류: {e}")

        try:
            CREATE_NO_WINDOW = 0x08000000
            proc = subprocess.Popen(
                [self.exe_path] + self.args.split() + [self.rom_path],
                creationflags=CREATE_NO_WINDOW
            )
            proc.wait()
        except Exception as e:
            print(f"[실행] 오류: {e}")

        # MORT 자동 종료
        if mort_proc and get_setting("mort_auto_stop", "0") == "1":
            try:
                mort_proc.terminate()
                print("[MORT] 자동 종료")
            except Exception as e:
                print(f"[MORT] 종료 오류: {e}")

        # 녹화 프로그램 자동 종료
        if rec_proc and get_setting("recorder_auto_stop", "0") == "1":
            try:
                rec_proc.terminate()
                print("[녹화] 자동 종료")
            except Exception as e:
                print(f"[녹화] 종료 오류: {e}")

        elapsed = int(time.time() - start)
        self.finished.emit(max(0, min(elapsed, 2147483647)))


class InfoPanel(QWidget):
    """우측 게임 정보 패널"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_data = None
        self.is_recording = False
        self._main_window = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.setStyleSheet("QScrollBar:horizontal { height: 0px; }")

        # ── 미디어 탭 (게임정보 / 동영상 / 스냅샷) ──
        self.media_tabs = QTabWidget()
        self.media_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.media_tabs.setStyleSheet("QScrollBar:horizontal { height: 0px; }")

        # 탭 1: 게임 정보 (커버아트 + 정보 필드)
        self.media_tabs.addTab(self._build_tab_game_info(), TR["tab_game_info"])

        # 탭 2: 동영상
        self.media_tabs.addTab(self._build_tab_video(), TR["tab_video"])

        # 탭 3: 스냅샷
        self.media_tabs.addTab(self._build_tab_snapshot(), TR["tab_snapshot"])

        layout.addWidget(self.media_tabs)

        # ── 하단 버튼 영역 (2줄) ──
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        # 1줄: 즐겨찾기 / 편집 / 에뮬 지정
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(6)
        self.btn_favorite = QPushButton(TR["favorite_add"])
        self.btn_edit     = QPushButton(TR["btn_edit"])
        self.btn_set_emu  = QPushButton(TR["btn_set_emu"])
        self.btn_set_emu.setEnabled(False)
        for btn in [self.btn_favorite, self.btn_edit, self.btn_set_emu]:
            btn.setFixedHeight(28)
        btn_row1.addWidget(self.btn_favorite)
        btn_row1.addWidget(self.btn_edit)
        btn_row1.addWidget(self.btn_set_emu)

        # 2줄: 실행 버튼 (전체 너비)
        self.btn_launch = QPushButton(TR["btn_launch"])
        self.btn_launch.setObjectName("btn_launch")
        self.btn_launch.setEnabled(False)
        self.btn_launch.setFixedHeight(34)

        self.btn_favorite.clicked.connect(self._toggle_favorite)
        self.btn_edit.clicked.connect(self._open_edit_dialog)
        self.btn_set_emu.clicked.connect(self.enter_edit_mode)
        self.btn_launch.clicked.connect(self._launch_current)

        btn_layout.addLayout(btn_row1)
        btn_layout.addWidget(self.btn_launch)
        layout.addLayout(btn_layout)

        self._apply_style()

    # ── 탭 1: 게임 정보 ──────────────────────────────────────────
    def _build_tab_game_info(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 커버아트
        self.lbl_cover = QLabel()
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cover.setFixedHeight(160)
        self.lbl_cover.setText(TR["no_cover"])
        self.lbl_cover.setStyleSheet("border: 1px solid #444; border-radius: 4px;")
        layout.addWidget(self.lbl_cover)

        # 게임명
        self.lbl_title_kr = QLabel(TR["select_game"])
        self.lbl_title_kr.setFont(QFont("ThecircleM", 12, QFont.Weight.Bold))
        self.lbl_title_kr.setWordWrap(True)
        layout.addWidget(self.lbl_title_kr)

        self.lbl_title_en = QLabel("")
        self.lbl_title_en.setWordWrap(True)
        self.lbl_title_en.setObjectName("field_val")
        layout.addWidget(self.lbl_title_en)

        layout.addWidget(self._make_separator())

        self.fields = {}

        # 1열 필드
        for key, label in [("platform", TR["field_platform"]), ("emulator", TR["field_emulator"])]:
            row = QHBoxLayout()
            lbl_k = QLabel(f"{label}:")
            lbl_k.setFixedWidth(70)
            lbl_k.setObjectName("field_key")
            lbl_v = QLabel(TR["no_data"])
            lbl_v.setObjectName("field_val")
            lbl_v.setWordWrap(True)
            row.addWidget(lbl_k)
            row.addWidget(lbl_v)
            self.fields[key] = lbl_v
            layout.addLayout(row)

        # 2열 필드
        from PyQt6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        double_fields = [
            ("genre",          TR["field_genre"]),
            ("developer",      TR["field_developer"]),
            ("publisher",      TR["field_publisher"]),
            ("release_year",   TR["field_year"]),
            ("release_region", TR["field_region"]),
            ("play_count",     TR["field_playcount"]),
            ("last_played",    TR["field_lastplayed"]),
            ("total_playtime", TR["field_playtime"]),
        ]
        for i, (key, label) in enumerate(double_fields):
            r, c = i // 2, (i % 2) * 2
            lbl_k = QLabel(f"{label}:")
            lbl_k.setObjectName("field_key")
            lbl_k.setFixedWidth(60)
            lbl_v = QLabel(TR["no_data"])
            lbl_v.setObjectName("field_val")
            lbl_v.setWordWrap(True)
            grid.addWidget(lbl_k, r, c)
            grid.addWidget(lbl_v, r, c + 1)
            self.fields[key] = lbl_v
        layout.addLayout(grid)

        # 게임 팁
        layout.addWidget(self._make_separator())
        lbl_tips_title = QLabel(f"{TR['field_tips']}:")
        lbl_tips_title.setObjectName("field_key")
        layout.addWidget(lbl_tips_title)
        self.lbl_tips = QLabel(TR["no_data"])
        self.lbl_tips.setWordWrap(True)
        self.lbl_tips.setObjectName("tips_val")
        layout.addWidget(self.lbl_tips)

        # 더보기 버튼
        refresh_row = QHBoxLayout()
        self.btn_refresh_meta = QPushButton(TR["btn_meta_search"])
        self.btn_refresh_meta.setFixedHeight(25)
        self.btn_refresh_meta.setStyleSheet("font-size: 11px;")
        self.btn_refresh_meta.clicked.connect(self._refresh_metadata)

        self.btn_refresh_image = QPushButton(TR["btn_img_search"])
        self.btn_refresh_image.setFixedHeight(25)
        self.btn_refresh_image.setStyleSheet("font-size: 11px;")
        self.btn_refresh_image.clicked.connect(self._refresh_image)

        refresh_row.addWidget(self.btn_refresh_meta)
        refresh_row.addWidget(self.btn_refresh_image)
        layout.addLayout(refresh_row)
        layout.addStretch()

        return widget

    # ── 탭 2: 동영상 ──────────────────────────────────────────────
    def _build_tab_video(self):
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # WebEngineView 영역
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            self.web_view = QWebEngineView()
            self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.web_view.setHtml(self._youtube_placeholder_html())
            self._web_engine_ok = True
        except Exception:
            self.web_view = QLabel("PyQt6-WebEngine이 설치되지 않았습니다.")
            self.web_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._web_engine_ok = False
        layout.addWidget(self.web_view, stretch=1)

        # 링크 리스트 + 버튼
        link_header = QHBoxLayout()
        lbl_links = QLabel("유튜브 링크:")
        lbl_links.setObjectName("field_key")
        btn_auto = QPushButton("🔍 자동검색")
        btn_auto.setFixedHeight(26)
        btn_auto.setStyleSheet("font-size: 8pt;")
        btn_auto.clicked.connect(self._auto_search_youtube)
        btn_add = QPushButton("➕ 추가")
        btn_add.setFixedHeight(26)
        btn_add.setStyleSheet("font-size: 8pt;")
        btn_add.clicked.connect(self._add_youtube_link)
        btn_del = QPushButton("🗑 삭제")
        btn_del.setFixedHeight(26)
        btn_del.setStyleSheet("font-size: 8pt;")
        btn_del.clicked.connect(self._del_youtube_link)
        link_header.addWidget(lbl_links)
        link_header.addStretch()
        link_header.addWidget(btn_auto)
        link_header.addWidget(btn_add)
        link_header.addWidget(btn_del)
        layout.addLayout(link_header)

        self.youtube_link_list = QListWidget()
        self.youtube_link_list.setFixedHeight(55)
        self.youtube_link_list.itemClicked.connect(self._on_youtube_link_clicked)
        layout.addWidget(self.youtube_link_list)

        # 영상 설명
        layout.addWidget(self._make_separator())
        desc_header = QHBoxLayout()
        lbl_desc = QLabel(TR["video_desc_label"])
        lbl_desc.setObjectName("field_key")
        self.btn_open_browser = QPushButton(TR["video_open_browser"])
        self.btn_open_browser.setFixedHeight(26)
        self.btn_open_browser.setStyleSheet("font-size: 8pt;")
        self.btn_open_browser.clicked.connect(self._open_youtube_browser)
        self.btn_desc_edit = QPushButton(TR["video_desc_edit"])
        self.btn_desc_edit.setFixedHeight(26)
        self.btn_desc_edit.setFixedWidth(80)
        self.btn_desc_edit.clicked.connect(self._toggle_desc_edit)
        self.btn_desc_save = QPushButton(TR["video_desc_save"])
        self.btn_desc_save.setFixedHeight(26)
        self.btn_desc_save.setFixedWidth(80)
        self.btn_desc_save.setVisible(False)
        self.btn_desc_save.clicked.connect(self._save_youtube_desc)
        desc_header.addWidget(lbl_desc)
        desc_header.addStretch()
        desc_header.addWidget(self.btn_open_browser)
        desc_header.addWidget(self.btn_desc_edit)
        desc_header.addWidget(self.btn_desc_save)
        layout.addLayout(desc_header)

        self.txt_youtube_desc = QTextEdit()
        self.txt_youtube_desc.setFixedHeight(60)
        self.txt_youtube_desc.setReadOnly(True)
        self.txt_youtube_desc.setPlaceholderText("영상 설명이 없습니다.")
        layout.addWidget(self.txt_youtube_desc)

        return widget

    # ── 탭 3: 스냅샷 ──────────────────────────────────────────────
    def _build_tab_snapshot(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 상단: 이미지 미리보기
        self.lbl_snap_preview = QLabel()
        self.lbl_snap_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_snap_preview.setText(TR["snap_select"])
        self.lbl_snap_preview.setMinimumHeight(160)
        self.lbl_snap_preview.setStyleSheet("border: 1px solid #444; border-radius: 4px;")
        layout.addWidget(self.lbl_snap_preview)

        # 새로고침 버튼
        btn_refresh = QPushButton(TR["snap_refresh"])
        btn_refresh.setFixedHeight(28)
        btn_refresh.clicked.connect(self._scan_and_reload_snapshots)
        layout.addWidget(btn_refresh)

        # 하단: 파일 리스트
        self.snap_list = QListWidget()
        self.snap_list.setFixedHeight(80)
        self.snap_list.itemClicked.connect(self._on_snap_clicked)
        layout.addWidget(self.snap_list)

        # 메타데이터 (촬영일시, 게임명, 메모)
        layout.addWidget(self._make_separator())

        meta_grid = QHBoxLayout()
        self.lbl_snap_captured = QLabel(f"{TR['snap_captured']} -")
        self.lbl_snap_captured.setObjectName("field_key")
        self.lbl_snap_captured.setStyleSheet("font-size: 10px;")
        meta_grid.addWidget(self.lbl_snap_captured)
        meta_grid.addStretch()
        layout.addLayout(meta_grid)

        memo_row = QHBoxLayout()
        lbl_memo = QLabel(TR["snap_memo_label"])
        lbl_memo.setObjectName("field_key")
        lbl_memo.setFixedWidth(40)
        self.edit_snap_memo = QLineEdit()
        self.edit_snap_memo.setFixedHeight(24)
        self.edit_snap_memo.setPlaceholderText("메모 입력...")
        btn_memo_save = QPushButton(TR["snap_memo_save"])
        btn_memo_save.setFixedHeight(24)
        btn_memo_save.setFixedWidth(70)
        btn_memo_save.clicked.connect(self._save_snap_memo)
        self.edit_snap_memo.editingFinished.connect(self._save_snap_memo)
        memo_row.addWidget(lbl_memo)
        memo_row.addWidget(self.edit_snap_memo)
        memo_row.addWidget(btn_memo_save)
        layout.addLayout(memo_row)

        self._current_snap_id = None
        return widget

    # ── 유틸 ──────────────────────────────────────────────────────
    def _make_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line

    def _youtube_placeholder_html(self):
        return """
        <html><body style='background:#1a1a2e;color:#888;
        display:flex;align-items:center;justify-content:center;
        height:100%;font-family:sans-serif;font-size:13px;
        margin:0;padding:0;overflow:hidden;'>
        <div style='text-align:center;'>
        <div style='font-size:40px;margin-bottom:10px;'>▶</div>
        <div>유튜브 링크를 추가하면 여기서 재생됩니다</div>
        </div></body></html>
        """

    # ── 게임 데이터 로드 ───────────────────────────────────────────
    def load_game(self, game_id: int):
        d = get_game_detail(game_id)
        if not d:
            return
        self.game_data = d

        # 커버아트
        cover = d.get("cover_path", "")
        if cover and Path(cover).exists():
            pix = QPixmap(cover).scaled(
                self.lbl_cover.width() or 240, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_cover.setPixmap(pix)
        else:
            self.lbl_cover.clear()
            self.lbl_cover.setText(TR["no_cover"])

        # 게임명
        self.lbl_title_kr.setText(d.get("title_kr") or d.get("title_en") or "-")
        self.lbl_title_en.setText(d.get("title_en") or "")

        # 정보 필드
        self.fields["platform"].setText(d.get("platform_name") or TR["no_data"])
        self.fields["emulator"].setText(d.get("emulator_name") or "미설정")
        self.fields["genre"].setText(d.get("genre") or TR["no_data"])
        self.fields["developer"].setText(d.get("developer") or TR["no_data"])
        self.fields["publisher"].setText(d.get("publisher") or TR["no_data"])
        self.fields["release_year"].setText(str(d.get("release_year")) if d.get("release_year") else TR["no_data"])
        self.fields["release_region"].setText(d.get("release_region") or TR["no_data"])

        # 플레이 기록
        self.fields["play_count"].setText(f"{d.get('play_count', 0)}회")
        lp = d.get("last_played")
        self.fields["last_played"].setText(str(lp)[:10] if lp else TR["no_data"])
        total_sec = d.get("total_playtime_sec", 0) or 0
        if total_sec >= 3600:
            pt = f"{total_sec // 3600}시간 {(total_sec % 3600) // 60}분"
        elif total_sec >= 60:
            pt = f"{total_sec // 60}분"
        elif total_sec > 0:
            pt = f"{total_sec}초"
        else:
            pt = TR["no_data"]
        self.fields["total_playtime"].setText(pt)

        # 팁
        self.lbl_tips.setText(d.get("tips") or TR["no_data"])

        # 즐겨찾기
        from database import get_connection
        conn = get_connection()
        fav = conn.execute("SELECT 1 FROM favorites WHERE game_id=?", (game_id,)).fetchone()
        conn.close()
        self.btn_favorite.setText(TR["favorite_remove"] if fav else TR["favorite_add"])

        self.btn_launch.setEnabled(True)
        self.btn_set_emu.setEnabled(True)

        # 유튜브 링크 로드
        self._load_youtube_links()

        # 스냅샷 로드
        self._reload_snapshots()

    def clear(self):
        self.game_data = None
        self.lbl_title_kr.setText(TR["select_game"])
        self.lbl_title_en.setText("")
        self.lbl_cover.clear()
        self.lbl_cover.setText("")
        for v in self.fields.values():
            v.setText(TR["no_data"])
        self.lbl_tips.setText(TR["no_data"])
        self.btn_launch.setEnabled(False)
        self.btn_set_emu.setEnabled(False)
        self.btn_favorite.setText(TR["favorite_add"])
        self.snap_list.clear()
        self.lbl_snap_preview.clear()
        self.lbl_snap_preview.setText(TR["snap_select"])
        self.youtube_link_list.clear()
        self.txt_youtube_desc.clear()
        try:
            self.web_view.setHtml(self._youtube_placeholder_html())
        except Exception:
            pass

    # ── 유튜브 동영상 탭 ───────────────────────────────────────────
    def _load_youtube_links(self):
        """DB에서 유튜브 링크 목록 로드"""
        self.youtube_link_list.clear()
        if not self.game_data:
            return

        import json
        links_json = self.game_data.get("youtube_links", "") or ""
        try:
            links = json.loads(links_json) if links_json else []
        except Exception:
            links = []

        for link in links:
            item = QListWidgetItem(link.get("title", link.get("url", "")))
            item.setData(Qt.ItemDataRole.UserRole, link.get("url", ""))
            self.youtube_link_list.addItem(item)

        # 첫 번째 링크 자동 로드
        if links:
            self._load_youtube_url(links[0].get("url", ""))

        # 영상 설명 로드
        desc = self.game_data.get("youtube_desc", "") or ""
        self.txt_youtube_desc.setPlainText(desc)

    def _on_youtube_link_clicked(self, item):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self._load_youtube_url(url)

    def _load_youtube_url(self, url: str):
        """유튜브 URL을 embed 형식으로 WebEngineView에 로드"""
        if not url:
            return
        try:
            # youtube.com/watch?v=XXX → embed/XXX 변환
            video_id = ""
            if "watch?v=" in url:
                video_id = url.split("watch?v=")[-1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[-1].split("?")[0]
            elif "embed/" in url:
                video_id = url.split("embed/")[-1].split("?")[0]

            if video_id:
                embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=0"
                html = f"""
                <html><body style='margin:0;padding:0;background:#000;'>
                <iframe width='100%' height='100%'
                    src='{embed_url}'
                    frameborder='0'
                    allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture'
                    allowfullscreen>
                </iframe>
                </body></html>
                """
                self.web_view.setHtml(html)
            else:
                self.web_view.setUrl(__import__("PyQt6.QtCore", fromlist=["QUrl"]).QUrl(url))
        except Exception as e:
            print(f"[유튜브] 로드 오류: {e}")

    def _auto_search_youtube(self):
        """YouTube Data API로 재와니 채널 우선 검색 후 링크 자동 추가"""
        from database import get_setting
        from PyQt6.QtWidgets import QMessageBox

        api_key = get_setting("youtube_api_key", "").strip()
        if not api_key:
            QMessageBox.warning(self, "API 키 없음",
                "YouTube Data API 키가 설정되지 않았습니다.\n"
                "환경설정 > 유튜브 탭에서 API 키를 입력해주세요.")
            return

        if not self.current_game_id:
            return

        # 검색 키워드: 영문 제목 우선, 없으면 한글 제목
        from database import get_game_detail
        game = get_game_detail(self.current_game_id)
        title = (game.get("title_en") or game.get("title_kr") or "").strip()
        if not title:
            QMessageBox.warning(self, "검색 불가", "게임 제목이 없습니다.")
            return

        import requests
        channel_url = get_setting("youtube_channel_url",
                                  "https://www.youtube.com/@jewani1004").strip()

        # 채널 핸들에서 채널 ID 추출
        channel_id = None
        try:
            handle = channel_url.rstrip("/").split("@")[-1] if "@" in channel_url else None
            if handle:
                r = requests.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": handle,
                        "type": "channel",
                        "key": api_key,
                        "maxResults": 1,
                    }, timeout=5)
                data = r.json()
                items = data.get("items", [])
                if items:
                    channel_id = items[0]["snippet"]["channelId"]
        except Exception as e:
            print(f"[유튜브] 채널 ID 조회 실패: {e}")

        results = []
        try:
            # 1순위: 재와니 채널 검색
            if channel_id:
                r = requests.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": title,
                        "channelId": channel_id,
                        "type": "video",
                        "key": api_key,
                        "maxResults": 3,
                        "order": "relevance",
                    }, timeout=5)
                data = r.json()
                for item in data.get("items", []):
                    vid = item["id"].get("videoId")
                    ttl = item["snippet"]["title"]
                    if vid:
                        results.append({"url": f"https://www.youtube.com/watch?v={vid}",
                                        "title": ttl})

            # 2순위: 일반 검색 폴백
            if not results:
                r = requests.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": title,
                        "type": "video",
                        "key": api_key,
                        "maxResults": 3,
                        "order": "relevance",
                    }, timeout=5)
                data = r.json()
                for item in data.get("items", []):
                    vid = item["id"].get("videoId")
                    ttl = item["snippet"]["title"]
                    if vid:
                        results.append({"url": f"https://www.youtube.com/watch?v={vid}",
                                        "title": ttl})
        except Exception as e:
            QMessageBox.warning(self, "검색 실패", f"유튜브 검색 중 오류가 발생했습니다.\n{e}")
            return

        if not results:
            QMessageBox.information(self, "결과 없음",
                f"'{title}' 관련 유튜브 영상을 찾을 수 없습니다.")
            return

        # 기존 링크에 추가 (최대 3개)
        import json
        from database import get_game_detail, update_game
        existing = []
        try:
            detail = get_game_detail(self.current_game_id)
            raw = detail.get("youtube_links", "") or ""
            if raw:
                existing = json.loads(raw)
        except Exception:
            pass

        added = 0
        for item in results:
            if len(existing) >= 3:
                break
            if not any(e["url"] == item["url"] for e in existing):
                existing.append(item)
                added += 1

        if added > 0:
            update_game(self.current_game_id, youtube_links=json.dumps(existing, ensure_ascii=False))
            self._load_youtube_links()
            print(f"[유튜브] '{title}' 검색 결과 {added}개 추가됨")
        else:
            QMessageBox.information(self, "완료",
                "검색된 영상이 이미 모두 추가되어 있습니다.")

    def _add_youtube_link(self):
        """유튜브 링크 추가"""
        if not self.game_data:
            return

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        import json

        dlg = QDialog(self)
        dlg.setWindowTitle("유튜브 링크 추가")
        dlg.setFixedWidth(400)
        v = QVBoxLayout(dlg)

        v.addWidget(QLabel("유튜브 URL:"))
        edit_url = QLineEdit()
        edit_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        edit_url.setFixedHeight(26)
        v.addWidget(edit_url)

        v.addWidget(QLabel("표시 이름 (선택):"))
        edit_title = QLineEdit()
        edit_title.setPlaceholderText("비워두면 URL로 표시")
        edit_title.setFixedHeight(26)
        v.addWidget(edit_title)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("추가")
        btn_ok.setFixedHeight(28)
        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedHeight(28)
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        v.addLayout(btn_row)

        from theme import get_current_theme, build_stylesheet
        dlg.setStyleSheet(build_stylesheet(get_current_theme()))

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        url = edit_url.text().strip()
        title = edit_title.text().strip() or url
        if not url:
            return

        # 최대 3개 제한
        links_json = self.game_data.get("youtube_links", "") or ""
        try:
            links = json.loads(links_json) if links_json else []
        except Exception:
            links = []

        if len(links) >= 3:
            QMessageBox.warning(self, "제한", "유튜브 링크는 최대 3개까지 추가할 수 있습니다.")
            return

        links.append({"url": url, "title": title})
        self._save_youtube_links(links)
        self._load_youtube_links()

    def _del_youtube_link(self):
        """선택된 유튜브 링크 삭제"""
        if not self.game_data:
            return
        item = self.youtube_link_list.currentItem()
        if not item:
            return

        import json
        url = item.data(Qt.ItemDataRole.UserRole)
        links_json = self.game_data.get("youtube_links", "") or ""
        try:
            links = json.loads(links_json) if links_json else []
        except Exception:
            links = []

        links = [l for l in links if l.get("url") != url]
        self._save_youtube_links(links)
        self._load_youtube_links()

        if not links:
            try:
                self.web_view.setHtml(self._youtube_placeholder_html())
            except Exception:
                pass

    def _save_youtube_links(self, links: list):
        """유튜브 링크 목록 DB 저장"""
        import json
        from database import get_connection
        links_json = json.dumps(links, ensure_ascii=False)
        conn = get_connection()
        conn.execute("UPDATE game_meta SET youtube_links=? WHERE game_id=?",
                     (links_json, self.game_data["id"]))
        conn.commit()
        conn.close()
        self.game_data["youtube_links"] = links_json

    def _open_youtube_browser(self):
        """현재 선택된 링크를 브라우저로 열기"""
        import webbrowser
        item = self.youtube_link_list.currentItem()
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url:
                webbrowser.open(url)
        elif self.game_data:
            url = self.game_data.get("youtube_url", "")
            if url:
                webbrowser.open(url)

    def _toggle_desc_edit(self):
        """영상 설명 편집 모드 토글"""
        is_readonly = self.txt_youtube_desc.isReadOnly()
        self.txt_youtube_desc.setReadOnly(not is_readonly)
        self.btn_desc_edit.setVisible(is_readonly)
        self.btn_desc_save.setVisible(not is_readonly)
        if is_readonly:
            # 편집 모드 진입 - 배경색 밝게
            self.txt_youtube_desc.setStyleSheet("background: #2a2a4a; color: #ffffff; border: 1px solid #6a6aaa;")
        else:
            self.txt_youtube_desc.setReadOnly(True)
            self.btn_desc_edit.setVisible(True)
            self.btn_desc_save.setVisible(False)
            self.txt_youtube_desc.setStyleSheet("")

    def _save_youtube_desc(self):
        """영상 설명 DB 저장"""
        if not self.game_data:
            return
        desc = self.txt_youtube_desc.toPlainText()
        from database import get_connection
        conn = get_connection()
        conn.execute("UPDATE game_meta SET youtube_desc=? WHERE game_id=?",
                     (desc, self.game_data["id"]))
        conn.commit()
        conn.close()
        self.game_data["youtube_desc"] = desc
        self.txt_youtube_desc.setReadOnly(True)
        self.btn_desc_edit.setVisible(True)
        self.btn_desc_save.setVisible(False)
        print("[유튜브] 설명 저장 완료")

    # ── 스냅샷 탭 ─────────────────────────────────────────────────
    def _scan_and_reload_snapshots(self):
        """Screenshots 폴더에서 새 파일 감지 후 DB 등록 + 목록 새로고침"""
        if not self.game_data:
            return
        from folders import get_screenshot_folder
        from database import get_connection
        import re

        game_title = (self.game_data.get("title_kr")
                      or self.game_data.get("title_en")
                      or Path(self.game_data["rom_path"]).stem)
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', game_title)[:40]

        shot_dir = get_screenshot_folder()
        if not shot_dir.exists():
            self._reload_snapshots()
            return

        conn = get_connection()
        existing = set(
            r["file_path"] for r in conn.execute(
                "SELECT file_path FROM screenshots WHERE game_id=?",
                (self.game_data["id"],)
            ).fetchall()
        )

        new_count = 0
        for f in sorted(shot_dir.glob(f"{safe_title}*.png")):
            if str(f) not in existing:
                conn.execute(
                    "INSERT INTO screenshots (game_id, file_path) VALUES (?, ?)",
                    (self.game_data["id"], str(f))
                )
                new_count += 1
        conn.commit()
        conn.close()

        print(f"[스냅샷] 새 파일 {new_count}개 등록" if new_count else "[스냅샷] 새 파일 없음")
        self._reload_snapshots()

    def _reload_snapshots(self):
        """스냅샷 탭 목록 새로고침"""
        if not self.game_data:
            return
        from database import get_connection
        self.snap_list.clear()
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, file_path, captured_at, memo FROM screenshots WHERE game_id=? ORDER BY captured_at DESC",
            (self.game_data["id"],)
        ).fetchall()
        conn.close()
        for r in rows:
            p = Path(r["file_path"])
            if p.exists():
                item = QListWidgetItem(p.name)
                item.setData(Qt.ItemDataRole.UserRole, {"id": r["id"], "path": str(p),
                                                         "captured_at": r["captured_at"],
                                                         "memo": r["memo"] or ""})
                self.snap_list.addItem(item)

        # 첫 번째 자동 선택
        if self.snap_list.count() > 0:
            self.snap_list.setCurrentRow(0)
            self._on_snap_clicked(self.snap_list.item(0))

    def _on_snap_clicked(self, item):
        """스냅샷 클릭 시 미리보기 + 메타데이터 표시"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        path = data.get("path", "")
        if path and Path(path).exists():
            pixmap = QPixmap(path).scaled(
                self.lbl_snap_preview.width() or 280,
                160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_snap_preview.setPixmap(pixmap)

        # 메타데이터 표시
        captured_at = data.get("captured_at", "")
        self.lbl_snap_captured.setText(f"{TR['snap_captured']} {str(captured_at)[:19] if captured_at else '-'}")
        self.edit_snap_memo.setText(data.get("memo", ""))
        self._current_snap_id = data.get("id")

    def _save_snap_memo(self):
        """스냅샷 메모 저장"""
        if not self._current_snap_id:
            return
        memo = self.edit_snap_memo.text().strip()
        from database import get_connection
        conn = get_connection()
        conn.execute("UPDATE screenshots SET memo=? WHERE id=?", (memo, self._current_snap_id))
        conn.commit()
        conn.close()
        print(f"[스냅샷] 메모 저장: {memo}")

    # ── 게임 실행 ─────────────────────────────────────────────────
    def launch_game(self, game_id: int):
        data = get_game_detail(game_id)
        if not data:
            return

        exe = data.get("emulator_path", "")
        if not exe or not Path(exe).exists():
            from database import get_connection
            conn = get_connection()
            row = conn.execute("""
                SELECT exe_path, args FROM emulators
                WHERE platform_id=? AND is_default=1
                LIMIT 1
            """, (data["platform_id"],)).fetchone()
            conn.close()
            if row:
                exe = row["exe_path"]
                data["args"] = row["args"] or ""
            else:
                QMessageBox.warning(self, "에뮬레이터 없음",
                    "연결된 에뮬레이터가 없거나 경로가 잘못되었습니다.\n에뮬레이터 메뉴에서 등록해주세요.")
                return

        rom  = data["rom_path"]
        args = data.get("args", "")

        from PyQt6.QtWidgets import QApplication
        self._main_window = QApplication.activeWindow()
        if get_setting("minimize_on_launch", "1") == "1" and self._main_window:
            self._main_window.showMinimized()

        self.launch_worker = LaunchWorker(exe, args, rom)
        self.launch_worker.finished.connect(lambda sec: self._on_game_exited(game_id, sec))
        self.launch_worker.start()

    def _on_game_exited(self, game_id, playtime_sec):
        update_play_history(game_id, playtime_sec)
        win = getattr(self, "_main_window", None)
        if win:
            win.showNormal()
            win.activateWindow()
            win.raise_()

    def _launch_current(self):
        if self.game_data:
            self.launch_game(self.game_data["id"])

    def _toggle_favorite(self):
        if self.game_data:
            result = toggle_favorite(self.game_data["id"])
            self.btn_favorite.setText(TR["favorite_remove"] if result else TR["favorite_add"])
            from PyQt6.QtWidgets import QApplication
            win = QApplication.activeWindow()
            if win and hasattr(win, "_on_tab_changed"):
                win._on_tab_changed(win.tab_bar.currentIndex())

    # ── 메타데이터 / 이미지 검색 ──────────────────────────────────
    def _refresh_metadata(self):
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from PyQt6.QtCore import Qt
        from database import get_setting, update_game

        if not self.game_data:
            return

        if not get_setting("ss_user_id", "") or not get_setting("ss_user_password", ""):
            QMessageBox.warning(
                self, "계정 정보 없음",
                "메타데이터 자동검색을 사용하려면\n"
                "환경설정 > 메타데이터 API에서\n"
                "ScreenScraper 아이디/비밀번호를 입력해주세요.\n\n"
                "가입: https://www.screenscraper.fr"
            )
            return

        title_en  = self.game_data.get("title_en", "").strip()
        title_kr  = self.game_data.get("title_kr", "").strip()
        file_stem = Path(self.game_data.get("rom_path", "")).stem

        candidates = []
        if title_en:
            candidates.append(title_en)
        if file_stem and all(ord(c) < 128 for c in file_stem):
            if file_stem not in candidates:
                candidates.append(file_stem)
        if title_kr and title_kr not in candidates:
            candidates.append(title_kr)
        if not candidates:
            candidates.append(file_stem)

        title = candidates[0]
        platform_short = self.game_data.get("short_name", "")

        dlg = QProgressDialog("메타데이터 검색 중...", "취소", 0, 0, self)
        dlg.setWindowTitle("검색 중")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.show()

        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            from metadata_api import search_metadata, download_cover
            result = None
            for candidate in candidates:
                print(f"[메타데이터] 검색 시도: {candidate}")
                rom_filename = Path(self.game_data.get("rom_path", "")).name
                result = search_metadata(candidate, platform_short, romnom=rom_filename)
                if result:
                    break
        finally:
            dlg.close()

        if not result:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl

            dlg2 = QDialog(self)
            dlg2.setWindowTitle("검색 결과 없음")
            dlg2.setMinimumWidth(400)
            v = QVBoxLayout(dlg2)
            v.setSpacing(10)
            has_korean_stem = any(ord(c) >= 0xAC00 for c in file_stem)
            korean_hint = (
                "\n\n💡 파일명이 한글인 경우 ScreenScraper에서 검색이 되지 않습니다.\n"
                "   게임 정보 편집에서 영문 제목을 입력한 후 다시 검색해보세요."
            ) if has_korean_stem and not title_en else ""

            msg = QLabel(
                "다음 검색어로 찾을 수 없습니다:\n" +
                "\n".join(f"  • {c}" for c in candidates) +
                "\n\n아래 사이트에서 직접 검색 후 게임 정보 편집에서 입력해주세요." +
                korean_hint
            )

            msg.setWordWrap(True)
            v.addWidget(msg)
            for name, url in [("ScreenScraper", "https://www.screenscraper.fr"),
                               ("MobyGames",     "https://www.mobygames.com"),
                               ("TheGamesDB",    "https://www.thegamesdb.net")]:
                btn = QPushButton(f"🌐  {name}")
                btn.setFixedHeight(28)
                btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
                v.addWidget(btn)
            btn_close = QPushButton("닫기")
            btn_close.setFixedHeight(28)
            btn_close.clicked.connect(dlg2.accept)
            v.addWidget(btn_close)
            from theme import get_current_theme, build_stylesheet
            dlg2.setStyleSheet(build_stylesheet(get_current_theme()))
            dlg2.exec()
            return

        preview = (
            f"게임명: {result.get('title_en', '')}\n"
            f"장르: {result.get('genre', '')}\n"
            f"개발사: {result.get('developer', '')}\n"
            f"퍼블리셔: {result.get('publisher', '')}\n"
            f"출시연도: {result.get('release_year', '')}\n\n"
            "이 정보로 업데이트하시겠습니까?"
        )
        reply = QMessageBox.question(
            self, "메타데이터 확인", preview,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        update_kwargs = {}
        for k in ["title_en", "genre", "developer", "publisher", "release_year", "description"]:
            if result.get(k):
                update_kwargs[k] = result[k]
        update_game(self.game_data["id"], **update_kwargs)

        if result.get("cover_url"):
            from folders import get_gamedata_path
            gdata_path = get_gamedata_path(platform_short, title)
            cover_path = str(gdata_path / "cover.jpg")
            from metadata_api import download_cover
            if download_cover(result["cover_url"], cover_path):
                update_game(self.game_data["id"], cover_path=cover_path)

        QMessageBox.information(self, "완료", "메타데이터가 업데이트되었습니다.")
        self.load_game(self.game_data["id"])

    def _refresh_image(self):
        from database import get_setting, update_game

        if not self.game_data:
            return

        platform_short = self.game_data.get("short_name", "")
        cover_folder = get_setting(f"cover_art_folder_{platform_short}", "")
        if not cover_folder:
            QMessageBox.warning(
                self, "폴더 미지정",
                f"[{platform_short}] 플랫폼의 커버아트 폴더가 설정되어 있지 않습니다.\n"
                "환경설정 > 폴더 설정에서 커버아트 폴더를 지정해주세요."
            )
            return

        cover_dir = Path(cover_folder)
        if not cover_dir.exists():
            QMessageBox.warning(self, "폴더 없음", f"지정된 커버아트 폴더가 존재하지 않습니다.\n{cover_folder}")
            return

        rom_stem  = Path(self.game_data.get("rom_path", "")).stem
        title_en  = self.game_data.get("title_en", "").strip()
        title_kr  = self.game_data.get("title_kr", "").strip()
        candidates = list(dict.fromkeys(filter(None, [rom_stem, title_en, title_kr])))

        img_exts = [".png", ".jpg", ".jpeg", ".bmp", ".webp"]
        found_path = None
        for name in candidates:
            for ext in img_exts:
                p = cover_dir / f"{name}{ext}"
                if p.exists():
                    found_path = p
                    break
            if found_path:
                break

        if not found_path:
            QMessageBox.information(
                self, "이미지 없음",
                "다음 파일명으로 이미지를 찾을 수 없습니다:\n" +
                "\n".join(f"  • {c}" for c in candidates) +
                f"\n\n폴더: {cover_folder}"
            )
            return

        from folders import get_gamedata_path
        import shutil
        title = title_en or title_kr or rom_stem
        save_dir = get_gamedata_path(platform_short, title)
        dest = save_dir / f"cover{found_path.suffix}"
        shutil.copy2(str(found_path), str(dest))
        update_game(self.game_data["id"], cover_path=str(dest))
        QMessageBox.information(self, "완료", f"커버아트가 적용되었습니다.\n{found_path.name}")
        self.load_game(self.game_data["id"])

    def enter_edit_mode(self):
        if not self.game_data:
            return
        from emulator_dialog import GameEmulatorDialog
        dlg = GameEmulatorDialog(
            game_id=self.game_data["id"],
            platform_id=self.game_data["platform_id"],
            current_emu_id=self.game_data.get("emulator_id"),
            parent=self
        )
        if dlg.exec():
            self.load_game(self.game_data["id"])

    def _open_edit_dialog(self):
        if not self.game_data:
            return
        from edit_game_dialog import EditGameDialog
        dlg = EditGameDialog(game_id=self.game_data["id"], parent=self)
        if dlg.exec():
            self.load_game(self.game_data["id"])

    # ── 스크린샷 ──────────────────────────────────────────────────
    def take_screenshot(self):
        """F12 - 에뮬레이터 창 캡처"""
        if not self.game_data:
            print("[스크린샷] 게임이 선택되지 않음")
            return

        try:
            from folders import get_screenshot_folder, get_base_path
            from database import get_connection
            import re, shutil

            game_title = (self.game_data.get("title_kr")
                          or self.game_data.get("title_en")
                          or Path(self.game_data["rom_path"]).stem)
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', game_title)[:40]

            save_dir = get_screenshot_folder()
            save_dir.mkdir(parents=True, exist_ok=True)

            n = 1
            while (save_dir / f"{safe_title}_{n:03d}.png").exists():
                n += 1
            save_path = save_dir / f"{safe_title}_{n:03d}.png"

            worker = getattr(self, "launch_worker", None)
            exe_name = ""
            if worker and hasattr(worker, "exe_path"):
                exe_name = Path(worker.exe_path).stem.lower()

            if "mesen" in exe_name:
                mesen_shot_dir = get_base_path() / "Emulators" / "Mesen" / "Screenshots"
                if not mesen_shot_dir.exists():
                    print(f"[스크린샷] Mesen 스크린샷 폴더 없음: {mesen_shot_dir}")
                    return
                files = sorted(mesen_shot_dir.glob("*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
                if not files:
                    print("[스크린샷] Mesen 스크린샷 파일 없음")
                    return
                shutil.copy2(str(files[0]), str(save_path))
                print(f"[스크린샷] Mesen 캡처 연결: {files[0].name} → {save_path.name}")
            else:
                try:
                    import mss, mss.tools
                    monitor = None
                    try:
                        import pygetwindow as gw
                        if exe_name:
                            wins = [w for w in gw.getAllWindows()
                                    if w.title and exe_name in w.title.lower()
                                    and w.width > 100 and w.height > 100]
                            if wins:
                                w = wins[0]
                                monitor = {"top": max(0, w.top), "left": max(0, w.left),
                                           "width": w.width, "height": w.height}
                    except Exception as e:
                        print(f"[스크린샷] 창 탐색 실패: {e}")
                    with mss.mss() as sct:
                        sct_img = sct.grab(monitor if monitor else sct.monitors[1])
                        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(save_path))
                    print(f"[스크린샷] 저장: {save_path.name}")
                except ImportError:
                    print("[스크린샷] mss 없음 → pip install mss")
                    return

            conn = get_connection()
            conn.execute("INSERT INTO screenshots (game_id, file_path) VALUES (?, ?)",
                         (self.game_data["id"], str(save_path)))
            conn.commit()
            conn.close()
            self._reload_snapshots()

        except Exception as e:
            print(f"[스크린샷] 오류: {e}")

    # ── 녹화 ──────────────────────────────────────────────────────
    def toggle_record(self):
        exe  = get_setting("recorder_exe_path", "")
        args = get_setting("recorder_args", "")

        if not exe:
            QMessageBox.warning(self, "녹화 프로그램 없음",
                "녹화 프로그램이 설정되어 있지 않습니다.\n환경설정 > 녹화 프로그램에서 설정해주세요.")
            return

        if not self.is_recording:
            if not Path(exe).exists():
                QMessageBox.warning(self, "파일 없음", f"녹화 프로그램을 찾을 수 없습니다:\n{exe}")
                return
            try:
                cmd = [exe] + args.split() if args else [exe]
                self._recorder_proc = subprocess.Popen(cmd)
                self.is_recording = True
                print(f"[녹화] 시작: {Path(exe).name}")
            except Exception as e:
                print(f"[녹화] 시작 오류: {e}")
        else:
            if hasattr(self, "_recorder_proc") and self._recorder_proc:
                try:
                    self._recorder_proc.terminate()
                    self._recorder_proc = None
                    print("[녹화] 종료")
                except Exception as e:
                    print(f"[녹화] 종료 오류: {e}")
            self.is_recording = False

    def pause_record(self):
        print("[녹화] 일시정지/재개는 녹화 프로그램에서 직접 조작해주세요.")

    def toggle_ocr_overlay(self):
        print("[기능] OCR 오버레이 - 추후 구현")

    def screenshot_ocr(self):
        print("[기능] 스크린샷 OCR - 추후 구현")

    def save_state(self):
        print("[기능] 상태저장 - 추후 구현")

    def load_state(self):
        print("[기능] 상태 불러오기 - 추후 구현")

    # ── 스타일 ────────────────────────────────────────────────────
    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        self.setStyleSheet(build_stylesheet(t) + f"""
            QLabel#field_key {{
                color: {t['text_dim']};
                font-size: 11px;
            }}
            QLabel#field_val {{
                color: {t['text_main']};
                font-size: 11px;
            }}
            QLabel#tips_val {{
                color: {t['text_sub']};
                font-size: 11px;
                padding: 4px;
            }}
            QFrame#separator {{
                color: {t['border']};
            }}
            QPushButton#btn_launch {{
                background: {t['bg_selected']};
                color: {t['text_main']};
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        self.btn_launch.setStyleSheet(f"""
            QPushButton {{
                background: {t['bg_selected']};
                color: {t['text_main']};
                border: none; border-radius: 6px;
                font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {t['bg_hover']}; }}
            QPushButton:disabled {{ background: {t['bg_panel']}; color: {t['text_dim']}; }}
        """)