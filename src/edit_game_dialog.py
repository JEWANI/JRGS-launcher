# edit_game_dialog.py — 신규 생성
"""
JRGS - 재와니의 레트로 게임 보관소
edit_game_dialog.py - 게임 정보 편집 다이얼로그
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QFileDialog, QFormLayout,
    QGroupBox, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

from database import get_game_detail, update_game


REGIONS = ["", "일본판", "북미판", "유럽판", "한국판", "기타"]


class EditGameDialog(QDialog):
    def __init__(self, game_id: int, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.data = get_game_detail(game_id)
        if not self.data:
            return

        self.new_cover_path = None  # 새로 선택한 커버아트 경로

        self.setWindowTitle("게임 정보 편집")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._init_ui()
        self._load_data()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 상단: 커버아트 + 기본 정보 ──
        top_layout = QHBoxLayout()

        # 커버아트 영역
        cover_layout = QVBoxLayout()
        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(120, 120)
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cover.setObjectName("cover_preview")
        self.btn_cover = QPushButton("🖼 커버아트 변경")
        self.btn_cover.setFixedHeight(28)
        self.btn_cover.clicked.connect(self._browse_cover)
        self.btn_icon = QPushButton("🎨 아이콘 편집")
        self.btn_icon.setFixedHeight(28)
        self.btn_icon.clicked.connect(self._open_icon_crop)
        cover_layout.addWidget(self.lbl_cover)
        cover_layout.addWidget(self.btn_cover)
        cover_layout.addWidget(self.btn_icon)
        cover_layout.addStretch()
        top_layout.addLayout(cover_layout)

        # 기본 정보 폼
        form = QFormLayout()
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.edit_title_kr  = QLineEdit()
        self.edit_title_en  = QLineEdit()
        self.edit_genre     = QLineEdit()
        self.edit_developer = QLineEdit()
        self.edit_publisher = QLineEdit()
        self.edit_year      = QLineEdit()
        self.edit_year.setFixedWidth(80)
        self.combo_region   = QComboBox()
        self.combo_region.addItems(REGIONS)

        form.addRow("게임명 (한글):", self.edit_title_kr)
        form.addRow("게임명 (영문):", self.edit_title_en)
        form.addRow("장르:",         self.edit_genre)
        form.addRow("제작사:",       self.edit_developer)
        form.addRow("퍼블리셔:",     self.edit_publisher)
        form.addRow("출시연도:",     self.edit_year)
        form.addRow("출시국가:",     self.combo_region)

        top_layout.addLayout(form)
        layout.addLayout(top_layout)

        # ── 구분선 ──
        layout.addWidget(self._make_separator())

        # ── 게임 팁 ──
        lbl_tips = QLabel("게임 팁 / 메모:")
        layout.addWidget(lbl_tips)
        self.edit_tips = QTextEdit()
        self.edit_tips.setFixedHeight(80)
        self.edit_tips.setPlaceholderText("플레이 팁, 공략 메모 등 자유롭게 입력...")
        layout.addWidget(self.edit_tips)

        # ── 유튜브 URL ──
        layout.addWidget(self._make_separator())
        yt_layout = QHBoxLayout()
        yt_layout.addWidget(QLabel("유튜브 URL:"))
        self.edit_youtube = QLineEdit()
        self.edit_youtube.setPlaceholderText("https://www.youtube.com/watch?v=...")
        yt_layout.addWidget(self.edit_youtube)
        layout.addLayout(yt_layout)

        # ── 확인 / 취소 ──
        layout.addWidget(self._make_separator())
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok     = QPushButton("✔ 저장")
        self.btn_cancel = QPushButton("✖ 취소")
        self.btn_ok.setFixedSize(90, 32)
        self.btn_cancel.setFixedSize(90, 32)
        self.btn_ok.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _load_data(self):
        d = self.data
        self.edit_title_kr.setText(d.get("title_kr") or "")
        self.edit_title_en.setText(d.get("title_en") or "")
        self.edit_genre.setText(d.get("genre") or "")
        self.edit_developer.setText(d.get("developer") or "")
        self.edit_publisher.setText(d.get("publisher") or "")
        self.edit_year.setText(str(d.get("release_year") or ""))
        region = d.get("release_region") or ""
        idx = self.combo_region.findText(region)
        self.combo_region.setCurrentIndex(idx if idx >= 0 else 0)
        self.edit_tips.setPlainText(d.get("tips") or "")
        self.edit_youtube.setText(d.get("youtube_url") or "")

        # 커버아트 미리보기
        self._update_cover_preview(d.get("cover_path", ""))

    def _update_cover_preview(self, path: str):
        if path and Path(path).exists():
            pixmap = QPixmap(path).scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_cover.setPixmap(pixmap)
        else:
            self.lbl_cover.clear()
            self.lbl_cover.setText("없음")

    def _browse_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "커버아트 선택", "",
            "이미지 파일 (*.jpg *.jpeg *.png *.bmp)"
        )
        if path:
            self.new_cover_path = path
            self._update_cover_preview(path)

    def _open_icon_crop(self):
        from icon_crop_dialog import IconCropDialog
        dlg = IconCropDialog(game_id=self.game_id, parent=self)
        dlg.exec()

    def _save(self):
        year_text = self.edit_year.text().strip()
        year = int(year_text) if year_text.isdigit() else None

        kwargs = dict(
            title_kr       = self.edit_title_kr.text().strip(),
            title_en       = self.edit_title_en.text().strip(),
            genre          = self.edit_genre.text().strip(),
            developer      = self.edit_developer.text().strip(),
            publisher      = self.edit_publisher.text().strip(),
            release_year   = year,
            release_region = self.combo_region.currentText(),
            tips           = self.edit_tips.toPlainText().strip(),
            youtube_url    = self.edit_youtube.text().strip(),
            youtube_auto   = 0 if self.edit_youtube.text().strip() else 1,
        )

        # 커버아트 복사 처리
        if self.new_cover_path:
            dest = self._copy_cover(self.new_cover_path)
            if dest:
                kwargs["cover_path"] = dest

        update_game(self.game_id, **kwargs)
        self.accept()

    def _copy_cover(self, src: str) -> str:
        """커버아트를 GameData 폴더에 복사"""
        import shutil
        from folders import get_gamedata_root

        d = self.data
        platform = d.get("short_name") or d.get("platform_name") or "Unknown"
        title = d.get("title_kr") or d.get("title_en") or Path(d["rom_path"]).stem

        dest_dir = get_gamedata_root() / platform / title
        dest_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(src).suffix.lower() or ".jpg"
        dest = dest_dir / f"cover{ext}"
        try:
            shutil.copy2(src, dest)
            return str(dest)
        except Exception as e:
            print(f"[편집] 커버아트 복사 실패: {e}")
            return src

    def _make_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        self.setStyleSheet(build_stylesheet(t) + f"""
            QLabel#cover_preview {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                color: {t['text_dim']};
                background: {t['bg_deep']};
            }}
            QFrame#separator {{
                color: {t['border']};
            }}
        """)