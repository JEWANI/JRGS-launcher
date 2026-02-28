"""
JRGS - 재와니의 레트로 게임 보관소
version_dialog.py - 버전 정보 및 업데이트 내역 창
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def get_changelog_path():
    """CHANGELOG.md 경로 반환"""
    return Path(__file__).parent.parent / "CHANGELOG.md"


def parse_changelog(text: str) -> list:
    """
    CHANGELOG.md 파싱
    반환: [{"version": "V.1.0.0", "date": "2026-02-27", "sections": [{"type": "신규기능", "items": [...]}]}]
    """
    versions = []
    current_version = None
    current_section = None

    for line in text.splitlines():
        line = line.rstrip()

        # 버전 헤더: ## V.X.X.X
        if line.startswith("## V.") or line.startswith("## v"):
            if current_version:
                if current_section:
                    current_version["sections"].append(current_section)
                versions.append(current_version)
            ver = line.lstrip("#").strip()
            current_version = {"version": ver, "date": "", "sections": []}
            current_section = None

        # 날짜: > 2026-xx-xx
        elif line.startswith("> ") and current_version and not current_version["date"]:
            current_version["date"] = line[2:].strip()

        # 섹션 헤더: ### 🟢 신규기능 / ### 🟡 업데이트 / ### 🔴 버그수정
        elif line.startswith("### ") and current_version:
            if current_section:
                current_version["sections"].append(current_section)
            sec_title = line.lstrip("#").strip()
            # 타입 감지
            if "신규" in sec_title or "🟢" in sec_title:
                sec_type = "신규기능"
            elif "업데이트" in sec_title or "🟡" in sec_title:
                sec_type = "업데이트"
            elif "버그" in sec_title or "🔴" in sec_title:
                sec_type = "버그수정"
            else:
                sec_type = "기타"
            current_section = {"type": sec_type, "items": []}

        # 항목: - 내용
        elif line.startswith("- ") and current_section is not None:
            item = line[2:].strip()
            if item and item != "없음":
                current_section["items"].append(item)

    # 마지막 버전 저장
    if current_version:
        if current_section:
            current_version["sections"].append(current_section)
        versions.append(current_version)

    return versions


# 섹션 타입별 색상
SECTION_COLORS = {
    "신규기능": "#44cc88",   # 초록
    "업데이트": "#ffcc44",   # 노란
    "버그수정": "#ff6666",   # 빨강
    "기타":     "#aaaacc",   # 회색
}

SECTION_ICONS = {
    "신규기능": "🟢",
    "업데이트": "🟡",
    "버그수정": "🔴",
    "기타":     "⚪",
}


class VersionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("버전 정보 및 업데이트 내역")
        self.setMinimumSize(560, 620)
        self.setModal(True)
        self._init_ui()
        self._apply_style()
        self._load_changelog()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 상단 헤더 ──
        header = QWidget()
        header.setFixedHeight(96)
        header.setStyleSheet("background: #0e0e1e;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 12, 24, 12)
        header_layout.setSpacing(2)
        
        # 최신 버전 읽기
        current_ver = ""
        path = get_changelog_path()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("## V.") or line.startswith("## v"):
                    current_ver = " " + line.lstrip("#").strip().split("—")[0].strip()
                    break

        lbl_kr = QLabel(f"재와니의 레트로 게임 보관소{current_ver}")
        lbl_kr.setFont(QFont("맑은 고딕", 18, QFont.Weight.Bold))
        lbl_kr.setStyleSheet("color: #ffffff;")

        lbl_en = QLabel("Jaewani Retro Game Storage")
        lbl_en.setStyleSheet("color: #666688; font-size: 11px;")
        lbl_en.setAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_sub = QLabel("JRGS — 업데이트 내역")
        lbl_sub.setFont(QFont("맑은 고딕", 11))
        lbl_sub.setStyleSheet("color: #aaaacc;")

        header_layout.addWidget(lbl_kr)
        header_layout.addWidget(lbl_en)
        header_layout.addWidget(lbl_sub)
        layout.addWidget(header)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3a3a5a;")
        layout.addWidget(line)

        # ── 스크롤 영역 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: #12121e; }")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: #12121e;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 16, 24, 24)
        self.content_layout.setSpacing(0)

        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)

        # ── 하단 버튼 ──
        btn_bar = QWidget()
        btn_bar.setFixedHeight(48)
        btn_bar.setStyleSheet("background: #1e1e2e; border-top: 1px solid #3a3a5a;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(16, 8, 16, 8)
        btn_layout.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.setFixedSize(80, 30)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addWidget(btn_bar)

    def _load_changelog(self):
        """CHANGELOG.md 읽어서 UI 생성"""
        path = get_changelog_path()
        if not path.exists():
            lbl = QLabel("CHANGELOG.md 파일을 찾을 수 없습니다.")
            lbl.setStyleSheet("color: #ff6666; padding: 20px;")
            self.content_layout.addWidget(lbl)
            return

        text = path.read_text(encoding="utf-8")
        versions = parse_changelog(text)

        for v in versions:
            self._add_version_block(v)

        self.content_layout.addStretch()

    def _add_version_block(self, v: dict):
        """버전 블록 UI 생성"""
        # ── 버전 헤더 ──
        ver_widget = QWidget()
        ver_widget.setStyleSheet("background: #1a1a2e; border-radius: 5px;")
        ver_layout = QVBoxLayout(ver_widget)
        ver_layout.setContentsMargins(16, 14, 16, 14)
        ver_layout.setSpacing(4)

        # 버전명 (가장 크게, 흰색)
        lbl_ver = QLabel(v["version"])
        lbl_ver.setFont(QFont("맑은 고딕", 15, QFont.Weight.Bold))
        lbl_ver.setStyleSheet("color: #ffffff;")
        ver_layout.addWidget(lbl_ver)

        # 날짜
        if v["date"]:
            lbl_date = QLabel(v["date"])
            lbl_date.setStyleSheet("color: #666688; font-size: 11px;")
            ver_layout.addWidget(lbl_date)

        self.content_layout.addWidget(ver_widget)
        self.content_layout.addSpacing(10)

        # ── 섹션별 블록 ──
        for sec in v["sections"]:
            if not sec["items"]:
                continue
            self._add_section_block(sec)

        self.content_layout.addSpacing(20)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2a2a3a;")
        self.content_layout.addWidget(line)
        self.content_layout.addSpacing(20)

    def _add_section_block(self, sec: dict):
        """섹션 블록 (신규기능 / 업데이트 / 버그수정)"""
        color = SECTION_COLORS.get(sec["type"], "#aaaacc")
        icon  = SECTION_ICONS.get(sec["type"], "⚪")

        # 섹션 제목 (크게)
        lbl_title = QLabel(f"{icon}  {sec['type']}")
        lbl_title.setFont(QFont("맑은 고딕", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {color}; padding-left: 4px;")
        self.content_layout.addWidget(lbl_title)
        self.content_layout.addSpacing(4)

        # 항목들 (작게)
        for item in sec["items"]:
            row = QHBoxLayout()
            row.setContentsMargins(16, 0, 0, 0)
            row.setSpacing(6)

            dot = QLabel("•")
            dot.setFixedWidth(10)
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")

            lbl_item = QLabel(item)
            lbl_item.setStyleSheet("color: #aaaacc; font-size: 12px;")
            lbl_item.setWordWrap(True)

            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(lbl_item)

            wrapper = QWidget()
            wrapper.setLayout(row)
            self.content_layout.addWidget(wrapper)

        self.content_layout.addSpacing(12)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #12121e; }
            QPushButton {
                background: #2a2a3e; color: #aaaacc;
                border: 1px solid #4a4a6a; border-radius: 4px;
            }
            QPushButton:hover { background: #3a3a6a; color: #fff; }
        """)
