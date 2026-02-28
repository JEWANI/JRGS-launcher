"""
JRGS - 재와니의 레트로 게임 보관소
emulator_dialog.py - 에뮬레이터 등록/편집 다이얼로그
"""

import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QLineEdit, QComboBox, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox, QFormLayout,
    QGroupBox, QDialogButtonBox, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database import get_connection, get_all_platforms, get_setting


# ── DB 헬퍼 함수 ─────────────────────────────────────────────

def get_all_emulators():
    """전체 에뮬레이터 목록 반환"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.*, p.short_name, p.name as platform_name
        FROM emulators e
        JOIN platforms p ON e.platform_id = p.id
        ORDER BY p.tab_order, e.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_emulators_by_platform(platform_id: int):
    """플랫폼별 에뮬레이터 목록"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM emulators WHERE platform_id=? ORDER BY is_default DESC, name
    """, (platform_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_emulator(platform_id: int, name: str, exe_path: str, args: str = "", is_default: int = 0):
    conn = get_connection()
    # 해당 플랫폼에 등록된 에뮬레이터가 없으면 자동으로 기본 설정
    existing = conn.execute("SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)).fetchone()
    conn.close()
    if existing["cnt"] == 0:
        is_default = 1
    """에뮬레이터 추가"""
    conn = get_connection()
    try:
        if is_default:
            conn.execute("UPDATE emulators SET is_default=0 WHERE platform_id=?", (platform_id,))
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO emulators (platform_id, name, exe_path, args, is_default)
            VALUES (?, ?, ?, ?, ?)
        """, (platform_id, name, exe_path, args, is_default))
        emu_id = cur.lastrowid
        conn.commit()
        return emu_id
    except Exception as e:
        conn.rollback()
        print(f"[DB] 에뮬레이터 추가 오류: {e}")
        return None
    finally:
        conn.close()


def update_emulator(emu_id: int, name: str, exe_path: str, args: str, is_default: int):
    """에뮬레이터 수정"""
    conn = get_connection()
    try:
        if is_default:
            # 먼저 같은 플랫폼의 기본 에뮬 해제
            row = conn.execute("SELECT platform_id FROM emulators WHERE id=?", (emu_id,)).fetchone()
            if row:
                conn.execute("UPDATE emulators SET is_default=0 WHERE platform_id=?", (row["platform_id"],))
        conn.execute("""
            UPDATE emulators SET name=?, exe_path=?, args=?, is_default=?
            WHERE id=?
        """, (name, exe_path, args, is_default, emu_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB] 에뮬레이터 수정 오류: {e}")
    finally:
        conn.close()


def delete_emulator(emu_id: int):
    """에뮬레이터 삭제"""
    conn = get_connection()
    conn.execute("DELETE FROM emulators WHERE id=?", (emu_id,))
    conn.commit()
    conn.close()


def set_game_emulator(game_id: int, emu_id: int):
    """게임별 에뮬레이터 지정"""
    conn = get_connection()
    conn.execute("UPDATE game_meta SET emulator_id=? WHERE game_id=?", (emu_id, game_id))
    conn.commit()
    conn.close()


# ── 에뮬레이터 등록/편집 다이얼로그 ────────────────────────────

class EmulatorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("에뮬레이터 등록/편집")
        self.setMinimumSize(700, 480)
        self.setModal(True)
        self.platforms = get_all_platforms()
        self._selected_emu_id = None
        self._init_ui()
        self._apply_style()
        self._load_emulator_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # ── 좌측: 에뮬레이터 목록 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)

        lbl = QLabel("등록된 에뮬레이터")
        lbl.setStyleSheet("color: #aaaacc; font-weight: bold; font-size: 12px;")
        left_layout.addWidget(lbl)

        self.list_emus = QListWidget()
        self.list_emus.currentItemChanged.connect(self._on_emu_selected)
        left_layout.addWidget(self.list_emus)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ 추가")
        self.btn_del = QPushButton("🗑 삭제")
        for btn in [self.btn_add, self.btn_del]:
            btn.setFixedHeight(28)
        self.btn_add.clicked.connect(self._on_add)
        self.btn_del.clicked.connect(self._on_delete)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_del)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        # ── 우측: 에뮬레이터 편집 폼 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)

        lbl2 = QLabel("에뮬레이터 정보")
        lbl2.setStyleSheet("color: #aaaacc; font-weight: bold; font-size: 12px;")
        right_layout.addWidget(lbl2)

        group = QGroupBox()
        group.setStyleSheet("QGroupBox { border: 1px solid #3a3a5a; border-radius: 6px; padding: 8px; }")
        form = QFormLayout(group)
        form.setSpacing(10)

        # 플랫폼 선택
        self.cmb_platform = QComboBox()
        for p in self.platforms:
            self.cmb_platform.addItem(
                f"{p.get('display_name') or p['short_name']}  ({p['short_name']})",
                p["id"]
            )
        form.addRow("플랫폼:", self.cmb_platform)

        # 에뮬레이터 이름
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("예: RetroArch, FCEUX, Snes9x ...")
        form.addRow("이름:", self.edit_name)

        # EXE 경로
        exe_row = QHBoxLayout()
        self.edit_exe = QLineEdit()
        self.edit_exe.setPlaceholderText("에뮬레이터 EXE 경로")
        self.edit_exe.setReadOnly(True)
        btn_browse = QPushButton("찾아보기")
        btn_browse.setFixedWidth(72)
        btn_browse.clicked.connect(self._browse_exe)
        exe_row.addWidget(self.edit_exe)
        exe_row.addWidget(btn_browse)
        form.addRow("EXE 경로:", exe_row)

        # 실행 인자
        self.edit_args = QLineEdit()
        self.edit_args.setPlaceholderText("예: -f  (없으면 비워두세요)")
        form.addRow("실행 인자:", self.edit_args)

        # 기본 에뮬레이터 여부
        self.chk_default = QPushButton("☐  이 플랫폼의 기본 에뮬레이터로 설정")
        self.chk_default.setCheckable(True)
        self.chk_default.setFixedHeight(28)
        self.chk_default.toggled.connect(
            lambda checked: self.chk_default.setText(
                "✔  이 플랫폼의 기본 에뮬레이터로 설정" if checked else "☐  이 플랫폼의 기본 에뮬레이터로 설정"
            )
        )
        form.addRow(self.chk_default)

        right_layout.addWidget(group)

        # 테스트 실행 버튼
        self.btn_test = QPushButton("⚙ 에뮬레이터만 실행 (테스트)")
        self.btn_test.setFixedHeight(30)
        self.btn_test.clicked.connect(self._run_emulator_only)
        right_layout.addWidget(self.btn_test)

        # 저장 버튼
        self.btn_save = QPushButton("💾 저장")
        self.btn_save.setFixedHeight(34)
        self.btn_save.clicked.connect(self._on_save)
        right_layout.addWidget(self.btn_save)

        right_layout.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([220, 400])

         # 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self._set_form_enabled(False)

    def _load_emulator_list(self):
        """에뮬레이터 목록 새로고침"""
        self.list_emus.clear()
        emus = get_all_emulators()
        for e in emus:
            label = f"{'★ ' if e['is_default'] else ''}[{e['short_name']}] {e['name']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, e["id"])
            self.list_emus.addItem(item)

    def _on_emu_selected(self, current, previous):
        if not current:
            self._set_form_enabled(False)
            return
        emu_id = current.data(Qt.ItemDataRole.UserRole)
        self._selected_emu_id = emu_id
        self._load_emu_to_form(emu_id)
        self._set_form_enabled(True)

    def _load_emu_to_form(self, emu_id: int):
        """선택한 에뮬레이터 정보를 폼에 로드"""
        conn = get_connection()
        row = conn.execute("SELECT * FROM emulators WHERE id=?", (emu_id,)).fetchone()
        conn.close()
        if not row:
            return
        e = dict(row)

        # 플랫폼 콤보 선택
        for i in range(self.cmb_platform.count()):
            if self.cmb_platform.itemData(i) == e["platform_id"]:
                self.cmb_platform.setCurrentIndex(i)
                break

        self.edit_name.setText(e["name"])
        self.edit_exe.setText(e["exe_path"])
        self.edit_args.setText(e.get("args", ""))
        self.chk_default.setChecked(bool(e["is_default"]))

    def _on_add(self):
        """새 에뮬레이터 추가 모드"""
        self._selected_emu_id = None
        self.edit_name.clear()
        self.edit_exe.clear()
        self.edit_args.clear()
        self.chk_default.setChecked(False)
        self._set_form_enabled(True)
        self.edit_name.setFocus()
        self.list_emus.clearSelection()

    def _on_delete(self):
        if not self._selected_emu_id:
            return
        ret = QMessageBox.question(self, "삭제 확인", "선택한 에뮬레이터를 삭제할까요?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            delete_emulator(self._selected_emu_id)
            self._selected_emu_id = None
            self._load_emulator_list()
            self._set_form_enabled(False)

    def _on_save(self):
        name = self.edit_name.text().strip()
        exe  = self.edit_exe.text().strip()

        if not name:
            QMessageBox.warning(self, "입력 오류", "에뮬레이터 이름을 입력하세요.")
            return
        if not exe:
            QMessageBox.warning(self, "입력 오류", "EXE 경로를 선택하세요.")
            return
        if not Path(exe).exists():
            QMessageBox.warning(self, "경로 오류", "EXE 파일이 존재하지 않습니다.")
            return

        platform_id = self.cmb_platform.currentData()
        args        = self.edit_args.text().strip()
        is_default  = 1 if self.chk_default.isChecked() else 0

        if self._selected_emu_id:
            # 플랫폼 변경 시 platform_id도 업데이트
            conn = get_connection()
            conn.execute(
                "UPDATE emulators SET platform_id=? WHERE id=?",
                (platform_id, self._selected_emu_id)
            )
            conn.commit()
            conn.close()
            update_emulator(self._selected_emu_id, name, exe, args, is_default)
        else:
            # 기존 에뮬레이터 있고 기본으로 설정 시 경고
            conn = get_connection()
            existing = conn.execute(
                "SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)
            ).fetchone()
            conn.close()
            if existing["cnt"] > 0 and is_default:
                ret = QMessageBox.question(self, "기본 에뮬레이터 변경",
                    "이미 등록된 에뮬레이터가 있습니다.\n기본 에뮬레이터를 이걸로 변경할까요?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ret == QMessageBox.StandardButton.No:
                    is_default = 0
            self._selected_emu_id = add_emulator(platform_id, name, exe, args, is_default)

        self._load_emulator_list()
        QMessageBox.information(self, "저장 완료", f"'{name}' 저장되었습니다.")

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "에뮬레이터 EXE 선택", "", "실행 파일 (*.exe);;모든 파일 (*)"
        )
        if path:
            self.edit_exe.setText(path)
            # 이름이 비어있으면 파일명으로 자동 채움
            if not self.edit_name.text().strip():
                self.edit_name.setText(Path(path).stem)

    def _run_emulator_only(self):
        """에뮬레이터만 실행 (ROM 없이 테스트)"""
        exe  = self.edit_exe.text().strip()
        args = self.edit_args.text().strip()

        if not exe or not Path(exe).exists():
            QMessageBox.warning(self, "경로 오류", "유효한 EXE 경로를 먼저 입력하세요.")
            return
        try:
            cmd = [exe] + args.split() if args else [exe]
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.critical(self, "실행 오류", f"에뮬레이터 실행 실패:\n{e}")

    def _set_form_enabled(self, enabled: bool):
        for w in [self.cmb_platform, self.edit_name, self.edit_exe,
                  self.edit_args, self.chk_default, self.btn_save, self.btn_test]:
            w.setEnabled(enabled)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background: #1e1e2e; color: #ccccee; }
            QListWidget {
                background: #12121e; border: 1px solid #3a3a5a;
                border-radius: 4px; outline: none;
            }
            QListWidget::item { padding: 6px 8px; border-radius: 4px; }
            QListWidget::item:selected { background: #3a3a7a; color: #fff; }
            QListWidget::item:hover { background: #2a2a5a; }
            QLineEdit, QComboBox {
                background: #2a2a3e; border: 1px solid #4a4a6a;
                border-radius: 4px; padding: 4px 8px; color: #ccccee;
            }
            QPushButton {
                background: #2a2a3e; color: #aaaacc;
                border: 1px solid #4a4a6a; border-radius: 4px; padding: 5px 12px;
            }
            QPushButton:hover { background: #3a3a6a; color: #fff; }
            QPushButton:disabled { background: #1a1a2a; color: #555566; }
            QCheckBox { spacing: 6px; }
            QCheckBox::indicator {
                width: 13px; height: 13px;
                border: 1px solid #4a4a6a; border-radius: 3px; background: #2a2a3e;
            }
            QCheckBox::indicator:checked { background: #4a4a8a; }
        """)


# ── 게임별 에뮬레이터 지정 다이얼로그 ────────────────────────

class RunEmulatorDialog(QDialog):
    """에뮬레이터만 실행 - 목록에서 선택 후 실행"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("에뮬레이터 실행")
        self.setFixedSize(240, 140)
        self.setModal(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl = QLabel("실행할 에뮬레이터를 선택하세요:")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.setFixedHeight(26)
        self._emus = get_all_emulators()
        for e in self._emus:
            self.combo.addItem(f"[{e['short_name']}] {e['name']}")
        layout.addWidget(self.combo)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("▶ 실행")
        btn_ok.setFixedHeight(28)
        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedHeight(28)
        btn_ok.clicked.connect(self._run)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _run(self):
        idx = self.combo.currentIndex()
        if idx < 0 or not self._emus:
            return
        exe = self._emus[idx]["exe_path"]
        import subprocess, os
        if not os.path.exists(exe):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "오류", f"파일을 찾을 수 없습니다:\n{exe}")
            return
        subprocess.Popen([exe])
        self.accept()

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        self.setStyleSheet(build_stylesheet(get_current_theme()))


class GameEmulatorDialog(QDialog):
    """특정 게임에 에뮬레이터를 지정하는 간단한 다이얼로그"""

    def __init__(self, game_id: int, platform_id: int, current_emu_id: int = None, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self.platform_id = platform_id
        self.current_emu_id = current_emu_id
        self.setWindowTitle("에뮬레이터 지정")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        lbl = QLabel("이 게임에서 사용할 에뮬레이터를 선택하세요.")
        lbl.setStyleSheet("color: #aaaacc; font-size: 12px;")
        layout.addWidget(lbl)

        self.cmb_emu = QComboBox()
        self.cmb_emu.addItem("── 기본 에뮬레이터 사용 ──", None)

        emus = get_emulators_by_platform(self.platform_id)
        for e in emus:
            label = f"{'[기본] ' if e['is_default'] else ''}{e['name']}"
            self.cmb_emu.addItem(label, e["id"])
            if e["id"] == self.current_emu_id:
                self.cmb_emu.setCurrentIndex(self.cmb_emu.count() - 1)

        layout.addWidget(self.cmb_emu)

        # 등록된 에뮬레이터 없을 때 안내
        if not emus:
            lbl_warn = QLabel("⚠ 이 플랫폼에 등록된 에뮬레이터가 없습니다.\n에뮬레이터 메뉴에서 먼저 등록해주세요.")
            lbl_warn.setStyleSheet("color: #ff9966; font-size: 11px;")
            lbl_warn.setWordWrap(True)
            layout.addWidget(lbl_warn)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_ok(self):
        emu_id = self.cmb_emu.currentData()
        set_game_emulator(self.game_id, emu_id)
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background: #1e1e2e; color: #ccccee; }
            QComboBox {
                background: #2a2a3e; border: 1px solid #4a4a6a;
                border-radius: 4px; padding: 5px 8px; color: #ccccee;
            }
            QPushButton {
                background: #2a2a3e; color: #aaaacc;
                border: 1px solid #4a4a6a; border-radius: 4px; padding: 5px 13px;
            }
            QPushButton:hover { background: #3a3a6a; color: #fff; }
        """)
