# stats_dialog.py — 신규 생성
"""
JRGS - 재와니의 레트로 게임 보관소
stats_dialog.py - 플레이 기록 통계 다이얼로그
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database import get_connection


def _fmt_time(sec: int) -> str:
    if sec >= 3600:
        return f"{sec // 3600}시간 {(sec % 3600) // 60}분"
    elif sec >= 60:
        return f"{sec // 60}분"
    elif sec > 0:
        return f"{sec}초"
    return "-"


def get_stats_summary():
    """전체 통계 요약"""
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(DISTINCT ph.game_id) as played_games,
            SUM(ph.play_count) as total_plays,
            SUM(ph.total_playtime_sec) as total_sec
        FROM play_history ph
        WHERE ph.play_count > 0
    """).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_stats_by_game(order_by="total_playtime_sec"):
    """게임별 플레이 기록 목록"""
    allowed = {"total_playtime_sec", "play_count", "last_played"}
    if order_by not in allowed:
        order_by = "total_playtime_sec"
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT
            COALESCE(g.title_kr, g.title_en, g.rom_path) as title,
            p.short_name as platform,
            ph.play_count,
            ph.last_played,
            ph.total_playtime_sec
        FROM play_history ph
        JOIN games g ON ph.game_id = g.id
        JOIN platforms p ON g.platform_id = p.id
        WHERE ph.play_count > 0
        ORDER BY ph.{order_by} DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class StatsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("플레이 기록 통계")
        self.setMinimumSize(580, 480)
        self.setModal(True)
        self._init_ui()
        self._load_data()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 헤더 ──
        lbl_title = QLabel("플레이 기록 통계")
        lbl_title.setFont(QFont("맑은 고딕", 14, QFont.Weight.Bold))
        layout.addWidget(lbl_title)

        layout.addWidget(self._make_separator())

        # ── 요약 카드 3개 ──
        summary_layout = QHBoxLayout()

        self.card_games    = self._make_card("플레이한 게임", "-")
        self.card_plays    = self._make_card("총 플레이 횟수", "-")
        self.card_playtime = self._make_card("총 플레이 시간", "-")

        for card in [self.card_games, self.card_plays, self.card_playtime]:
            summary_layout.addWidget(card)
        layout.addLayout(summary_layout)

        layout.addWidget(self._make_separator())

        # ── 정렬 선택 ──
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("정렬:"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["총 플레이 시간순", "플레이 횟수순", "최근 플레이순"])
        self.combo_sort.setFixedWidth(160)
        self.combo_sort.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.combo_sort)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # ── 게임별 테이블 ──
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["게임명", "플랫폼", "횟수", "마지막 플레이", "총 시간"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # ── 닫기 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("닫기")
        btn_close.setFixedSize(90, 32)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _make_card(self, label: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("stat_card")
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)

        lbl_val = QLabel(value)
        lbl_val.setFont(QFont("맑은 고딕", 18, QFont.Weight.Bold))
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_val.setObjectName("card_value")

        lbl_key = QLabel(label)
        lbl_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_key.setObjectName("card_label")

        card_layout.addWidget(lbl_val)
        card_layout.addWidget(lbl_key)

        # 값 레이블 참조 저장
        frame._value_label = lbl_val
        return frame

    def _load_data(self, order_by="total_playtime_sec"):
        # 요약
        s = get_stats_summary()
        self.card_games._value_label.setText(str(s.get("played_games") or 0))
        self.card_plays._value_label.setText(str(s.get("total_plays") or 0))
        self.card_playtime._value_label.setText(_fmt_time(s.get("total_sec") or 0))

        # 테이블
        rows = get_stats_by_game(order_by)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["title"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["platform"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["play_count"])))
            last = (r["last_played"] or "")[:10]
            self.table.setItem(i, 3, QTableWidgetItem(last))
            self.table.setItem(i, 4, QTableWidgetItem(_fmt_time(r["total_playtime_sec"] or 0)))

    def _on_sort_changed(self, idx):
        keys = ["total_playtime_sec", "play_count", "last_played"]
        self._load_data(keys[idx])

    def _make_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        self.setStyleSheet(build_stylesheet(t) + f"""
            QFrame#stat_card {{
                background: {t['bg_panel']};
                border: 1px solid {t['border']};
                border-radius: 8px;
            }}
            QLabel#card_value {{
                color: {t['text_main']};
            }}
            QLabel#card_label {{
                color: {t['text_dim']};
                font-size: 11px;
            }}
            QFrame#separator {{
                color: {t['border']};
            }}
            QTableWidget {{
                background: {t['bg_deep']};
                gridline-color: {t['border']};
                color: {t['text_main']};
            }}
            QHeaderView::section {{
                background: {t['bg_panel']};
                color: {t['text_sub']};
                border: none;
                padding: 4px;
            }}
            QTableWidget::item:selected {{
                background: {t['bg_selected']};
            }}
            QTableWidget::item:alternate {{
                background: {t['bg_base']};
            }}
        """)