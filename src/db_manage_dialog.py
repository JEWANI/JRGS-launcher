"""
JRGS - 재와니의 레트로 게임 보관소
db_manage_dialog.py - DB 관리 다이얼로그
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import get_db_path, get_connection


def get_db_info() -> dict:
    """DB 파일 정보 및 통계 반환"""
    db_path = get_db_path()
    size_bytes = db_path.stat().st_size if db_path.exists() else 0
    size_kb = size_bytes / 1024

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM games")
    game_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM platforms")
    platform_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM emulators")
    emulator_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM play_history WHERE play_count > 0")
    played_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM favorites")
    favorite_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM screenshots")
    screenshot_count = cur.fetchone()[0]

    conn.close()

    return {
        "path": str(db_path),
        "size_kb": size_kb,
        "game_count": game_count,
        "platform_count": platform_count,
        "emulator_count": emulator_count,
        "played_count": played_count,
        "favorite_count": favorite_count,
        "screenshot_count": screenshot_count,
    }


def count_orphan_data() -> dict:
    """고아 데이터 개수 반환"""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM game_meta
        WHERE game_id NOT IN (SELECT id FROM games)
    """)
    meta = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM play_history
        WHERE game_id NOT IN (SELECT id FROM games)
    """)
    history = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM screenshots
        WHERE game_id NOT IN (SELECT id FROM games)
    """)
    screenshots = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM favorites
        WHERE game_id NOT IN (SELECT id FROM games)
    """)
    favorites = cur.fetchone()[0]

    conn.close()
    return {
        "meta": meta,
        "history": history,
        "screenshots": screenshots,
        "favorites": favorites,
        "total": meta + history + screenshots + favorites,
    }


def clean_orphan_data() -> int:
    """고아 데이터 삭제 후 삭제된 총 개수 반환"""
    conn = get_connection()
    cur = conn.cursor()
    total = 0

    for table, col in [
        ("game_meta", "game_id"),
        ("play_history", "game_id"),
        ("screenshots", "game_id"),
        ("favorites", "game_id"),
    ]:
        cur.execute(f"""
            DELETE FROM {table}
            WHERE {col} NOT IN (SELECT id FROM games)
        """)
        total += cur.rowcount

    conn.commit()
    conn.close()
    return total


def vacuum_db():
    """VACUUM 실행"""
    import sqlite3
    conn = sqlite3.connect(get_db_path())
    conn.execute("VACUUM")
    conn.close()


class DBManageDialog(QDialog):
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme or {}
        self.setWindowTitle("DB 관리")
        self.setFixedWidth(460)
        self.setModal(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── DB 정보 ──
        grp_info = QGroupBox("DB 정보")
        grid = QGridLayout(grp_info)
        grid.setSpacing(6)

        info = get_db_info()

        self._lbl_path = QLabel(info["path"])
        self._lbl_path.setWordWrap(True)
        self._lbl_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._lbl_size = QLabel(f"{info['size_kb']:.1f} KB")
        self._lbl_games = QLabel(f"{info['game_count']}개")
        self._lbl_platforms = QLabel(f"{info['platform_count']}개")
        self._lbl_emulators = QLabel(f"{info['emulator_count']}개")
        self._lbl_played = QLabel(f"{info['played_count']}개")
        self._lbl_favorites = QLabel(f"{info['favorite_count']}개")
        self._lbl_screenshots = QLabel(f"{info['screenshot_count']}개")

        rows = [
            ("경로", self._lbl_path),
            ("파일 크기", self._lbl_size),
            ("등록 게임", self._lbl_games),
            ("플랫폼", self._lbl_platforms),
            ("에뮬레이터", self._lbl_emulators),
            ("플레이한 게임", self._lbl_played),
            ("즐겨찾기", self._lbl_favorites),
            ("스크린샷", self._lbl_screenshots),
        ]
        grid.setColumnMinimumWidth(0, 80)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        for i, (label, widget) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            bold_font = QFont()
            bold_font.setBold(True)
            lbl.setFont(bold_font)
            grid.addWidget(lbl, i, 0)
            widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(widget, i, 1)

        layout.addWidget(grp_info)

        # ── VACUUM ──
        grp_vac = QGroupBox("DB 최적화 (VACUUM)")
        vac_layout = QVBoxLayout(grp_vac)
        vac_desc = QLabel(
            "삭제된 데이터의 빈 공간을 정리하여 DB 파일 크기를 줄입니다.\n"
            "게임 수가 많을수록 시간이 걸릴 수 있습니다."
        )
        vac_desc.setWordWrap(True)
        self._btn_vacuum = QPushButton("🗜 VACUUM 실행")
        self._btn_vacuum.setFixedHeight(34)
        self._btn_vacuum.clicked.connect(self._on_vacuum)
        vac_layout.addWidget(vac_desc)
        vac_layout.addWidget(self._btn_vacuum)
        layout.addWidget(grp_vac)

        # ── 고아 데이터 정리 ──
        grp_orphan = QGroupBox("고아 데이터 정리")
        orphan_layout = QVBoxLayout(grp_orphan)
        orphan_desc = QLabel(
            "게임 목록에서 제거된 게임의 메타데이터, 플레이 기록,\n"
            "스크린샷, 즐겨찾기 데이터를 정리합니다."
        )
        orphan_desc.setWordWrap(True)

        orphan_count = count_orphan_data()
        self._lbl_orphan = QLabel(f"현재 고아 데이터: {orphan_count['total']}건")
        self._lbl_orphan_detail = QLabel(
            f"  메타데이터 {orphan_count['meta']}건 / "
            f"플레이기록 {orphan_count['history']}건 / "
            f"스크린샷 {orphan_count['screenshots']}건 / "
            f"즐겨찾기 {orphan_count['favorites']}건"
        )
        self._lbl_orphan_detail.setWordWrap(True)

        self._btn_clean = QPushButton("🧹 고아 데이터 정리")
        self._btn_clean.setFixedHeight(34)
        self._btn_clean.setEnabled(orphan_count["total"] > 0)
        self._btn_clean.clicked.connect(self._on_clean_orphan)

        orphan_layout.addWidget(orphan_desc)
        orphan_layout.addWidget(self._lbl_orphan)
        orphan_layout.addWidget(self._lbl_orphan_detail)
        orphan_layout.addWidget(self._btn_clean)
        layout.addWidget(grp_orphan)

        # ── 닫기 ──
        btn_close = QPushButton("닫기")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _refresh_info(self):
        """DB 정보 갱신"""
        info = get_db_info()
        self._lbl_size.setText(f"{info['size_kb']:.1f} KB")
        self._lbl_games.setText(f"{info['game_count']}개")
        self._lbl_platforms.setText(f"{info['platform_count']}개")
        self._lbl_emulators.setText(f"{info['emulator_count']}개")
        self._lbl_played.setText(f"{info['played_count']}개")
        self._lbl_favorites.setText(f"{info['favorite_count']}개")
        self._lbl_screenshots.setText(f"{info['screenshot_count']}개")

        orphan_count = count_orphan_data()
        self._lbl_orphan.setText(f"현재 고아 데이터: {orphan_count['total']}건")
        self._lbl_orphan_detail.setText(
            f"  메타데이터 {orphan_count['meta']}건 / "
            f"플레이기록 {orphan_count['history']}건 / "
            f"스크린샷 {orphan_count['screenshots']}건 / "
            f"즐겨찾기 {orphan_count['favorites']}건"
        )
        self._btn_clean.setEnabled(orphan_count["total"] > 0)

    def _on_vacuum(self):
        reply = QMessageBox.question(
            self, "VACUUM 실행",
            "DB를 최적화합니다. 계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._btn_vacuum.setEnabled(False)
        self._btn_vacuum.setText("실행 중...")
        try:
            vacuum_db()
            self._refresh_info()
            QMessageBox.information(self, "완료", "VACUUM이 완료되었습니다.")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"VACUUM 실패:\n{e}")
        finally:
            self._btn_vacuum.setEnabled(True)
            self._btn_vacuum.setText("🗜 VACUUM 실행")

    def _on_clean_orphan(self):
        orphan_count = count_orphan_data()
        if orphan_count["total"] == 0:
            QMessageBox.information(self, "알림", "정리할 고아 데이터가 없습니다.")
            return

        reply = QMessageBox.question(
            self, "고아 데이터 정리",
            f"고아 데이터 {orphan_count['total']}건을 삭제합니다. 계속하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = clean_orphan_data()
            self._refresh_info()
            QMessageBox.information(self, "완료", f"고아 데이터 {deleted}건을 정리했습니다.")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"정리 실패:\n{e}")

    def _apply_style(self):
        if not self.theme:
            return
        bg = self.theme.get("bg_main", "#1e1e1e")
        bg2 = self.theme.get("bg_panel", "#2a2a2a")
        text = self.theme.get("text_main", "#ffffff")
        text2 = self.theme.get("text_sub", "#aaaaaa")
        border = self.theme.get("border", "#444444")
        sel = self.theme.get("bg_selected", "#3a7bd5")

        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {text}; }}
            QGroupBox {{
                background: {bg2}; color: {text};
                border: 1px solid {border}; border-radius: 4px;
                margin-top: 8px; padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 8px;
            }}
            QLabel {{ color: {text}; background: transparent; }}
            QPushButton {{
                background: {bg2}; color: {text};
                border: 1px solid {border}; border-radius: 3px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: {sel}; }}
            QPushButton:disabled {{ color: {text2}; }}
        """)