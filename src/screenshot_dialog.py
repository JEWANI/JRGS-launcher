# screenshot_dialog.py — 신규 생성
"""
JRGS - 재와니의 레트로 게임 보관소
screenshot_dialog.py - 스크린샷 설정 다이얼로그
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt
from database import get_setting, set_setting
from folders import get_screenshot_folder


class ScreenshotSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("스크린샷 설정")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._init_ui()
        self._load()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # 저장 폴더
        layout.addWidget(QLabel("저장 폴더:"))
        folder_row = QHBoxLayout()
        self.edit_folder = QLineEdit()
        self.edit_folder.setReadOnly(True)
        btn_browse = QPushButton("찾아보기")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.edit_folder)
        folder_row.addWidget(btn_browse)
        layout.addLayout(folder_row)

        layout.addWidget(self._make_separator())

        # 파일명 형식
        layout.addWidget(QLabel("파일명 형식:"))
        self.edit_format = QLineEdit()
        self.edit_format.setPlaceholderText("%G_%D_%T")
        layout.addWidget(self.edit_format)

        # 토큰 안내
        hint = QLabel(
            "토큰: %G = 게임명  %D = 날짜(20260227)  %T = 시간(143022)  %N = 순번(001)"
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 미리보기
        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("미리보기:"))
        self.lbl_preview = QLabel()
        self.lbl_preview.setObjectName("preview")
        preview_row.addWidget(self.lbl_preview)
        preview_row.addStretch()
        layout.addLayout(preview_row)
        self.edit_format.textChanged.connect(self._update_preview)

        layout.addWidget(self._make_separator())

        # 확인/취소
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("✔ 저장")
        btn_cancel = QPushButton("✖ 취소")
        btn_ok.setFixedSize(90, 32)
        btn_cancel.setFixedSize(90, 32)
        btn_ok.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _load(self):
        self.edit_folder.setText(str(get_screenshot_folder()))
        fmt = get_setting("screenshot_format", "%G_%N")
        self.edit_format.setText(fmt)
        self._update_preview(fmt)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "스크린샷 저장 폴더 선택")
        if path:
            self.edit_folder.setText(path)

    def _update_preview(self, fmt: str):
        from datetime import datetime
        now = datetime.now()
        sample = fmt
        sample = sample.replace("%G", "SuperMario")
        sample = sample.replace("%D", now.strftime("%Y%m%d"))
        sample = sample.replace("%T", now.strftime("%H%M%S"))
        sample = sample.replace("%N", "001")
        self.lbl_preview.setText(f"{sample}.png")

    def _save(self):
        from database import set_setting
        set_setting("screenshot_folder", self.edit_folder.text())
        set_setting("screenshot_format", self.edit_format.text() or "%G_%D_%T")
        self.accept()

    def _make_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        self.setStyleSheet(build_stylesheet(t) + f"""
            QLabel#hint {{ color: {t['text_dim']}; font-size: 11px; }}
            QLabel#preview {{ color: {t['text_sub']}; font-size: 11px; }}
            QFrame#separator {{ color: {t['border']}; }}
        """)