"""
JRGS - 재와니의 레트로 게임 보관소
game_grid.py - 게임 그리드 위젯
"""

from PyQt6.QtWidgets import (
    QWidget,
    QScrollArea,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QStyledItemDelegate,
    QStyle,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QMimeData, QRect
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QPainter

from pathlib import Path

# 아이콘 크기 단계
ICON_SIZES = [48, 64, 80, 96, 112, 128, 160]
DEFAULT_SIZE_INDEX = 2  # 80px


def _truncate_title(text: str, max_px: int, char_px: int = 7) -> str:
    """픽셀 너비 기준 말줄임 (한글=2단위, 영문=1단위)"""
    limit = max(6, max_px // char_px)
    weight = sum(2 if ord(c) > 127 else 1 for c in text)
    if weight <= limit:
        return text
    result, w = [], 0
    for c in text:
        cw = 2 if ord(c) > 127 else 1
        if w + cw + 3 > limit:
            break
        result.append(c)
        w += cw
    return "".join(result) + "..."


class NameListDelegate(QStyledItemDelegate):
    """이름만 뷰 전용 delegate — 아이콘 왼쪽 + 텍스트 오른쪽"""

    ICON_SIZE = 20
    PADDING = 4

    def paint(self, painter, option, index):
        painter.save()

        # 선택/호버 배경
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(
                option.rect, option.palette.highlight().color().lighter(160)
            )

        # 아이콘
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_rect = QRect(
            option.rect.left() + self.PADDING,
            option.rect.top() + (option.rect.height() - self.ICON_SIZE) // 2,
            self.ICON_SIZE,
            self.ICON_SIZE,
        )
        if icon and not icon.isNull():
            icon.paint(painter, icon_rect)

        # 텍스트
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_color = index.data(Qt.ItemDataRole.ForegroundRole)
        if text_color:
            painter.setPen(
                text_color.color()
                if hasattr(text_color, "color")
                else QColor(text_color)
            )
        elif option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        text_x = icon_rect.right() + self.PADDING * 2
        text_rect = QRect(
            text_x,
            option.rect.top(),
            option.rect.right() - text_x - self.PADDING,
            option.rect.height(),
        )
        painter.drawText(
            text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text
        )
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(280, 26)


class GameGridWidget(QWidget):
    game_selected = pyqtSignal(int)  # game_id
    game_launched = pyqtSignal(int)  # game_id (더블클릭)
    request_add_rom = pyqtSignal()  # ROM 추가 요청
    request_scan = pyqtSignal()  # ROM 스캔 요청

    def __init__(self):
        super().__init__()
        self.games = []
        self.view_mode = "small"  # name / small / large
        self.icon_size_index = DEFAULT_SIZE_INDEX
        self.current_platform_id = None  # None = 즐겨찾기
        self.current_platform_extensions = []  # 현재 탭 허용 확장자 목록
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.list_widget = QListWidget()
        from theme import get_current_theme

        t = get_current_theme()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {t['bg_deep']};
                border: none;
                outline: none;
                font-size: 12px;
            }}
            QListWidget::item {{
                color: {t['text_main']};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background: {t['bg_selected']};
                color: {t['text_main']};
            }}
            QListWidget::item:hover {{
                background: {t['bg_hover']};
            }}
        """)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_double_clicked)
        self.list_widget.installEventFilter(self)
        layout.addWidget(self.list_widget)

    def load_games(self, games: list):
        """게임 목록 로드"""
        self.games = games
        self._refresh_view()

    def _install_wheel_filter(self):
        self.list_widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent

        if obj is self.list_widget and event.type() == QEvent.Type.Wheel:
            modifiers = event.modifiers()
            if (
                modifiers & Qt.KeyboardModifier.ControlModifier
                and modifiers & Qt.KeyboardModifier.ShiftModifier
            ):
                delta = event.angleDelta().y()
                if delta > 0:
                    self.increase_icon_size()
                elif delta < 0:
                    self.decrease_icon_size()
                return True
        return super().eventFilter(obj, event)

    def set_view_mode(self, mode: str):
        """뷰 모드 변경: name / small / large"""
        self.view_mode = mode
        self._refresh_view()

    def increase_icon_size(self):
        """아이콘 크기 증가"""
        if self.icon_size_index < len(ICON_SIZES) - 1:
            self.icon_size_index += 1
            self._refresh_view()

    def decrease_icon_size(self):
        """아이콘 크기 감소"""
        if self.icon_size_index > 0:
            self.icon_size_index -= 1
            self._refresh_view()

    def wheelEvent(self, event):
        """Ctrl+Shift+휠로 아이콘 크기 조절"""
        modifiers = event.modifiers()
        if (
            modifiers & Qt.KeyboardModifier.ControlModifier
            and modifiers & Qt.KeyboardModifier.ShiftModifier
        ):
            delta = event.angleDelta().y()
            if delta > 0:
                self.increase_icon_size()
            elif delta < 0:
                self.decrease_icon_size()
            event.accept()
        else:
            super().wheelEvent(event)

    def rename_selected_game(self):
        """선택된 게임 이름 변경 (F2 또는 우클릭 메뉴)"""
        try:
            from PyQt6.QtWidgets import QInputDialog
            from pathlib import Path

            item = self.list_widget.currentItem()
            if not item:
                return
            data = item.data(Qt.ItemDataRole.UserRole)
            if not data:
                return
            if isinstance(data, int):
                game_id = data
                from database import get_game_detail

                detail = get_game_detail(game_id)
                if not detail:
                    return
                current_title = (
                    detail.get("title_kr")
                    or detail.get("title_en")
                    or Path(detail["rom_path"]).stem
                )
            else:
                game_id = data.get("id")
                current_title = (
                    data.get("title_kr")
                    or data.get("title_en")
                    or Path(data["rom_path"]).stem
                )
            new_name, ok = QInputDialog.getText(
                self, "게임 이름 변경", "새 이름:", text=current_title
            )
            if ok and new_name.strip():
                from database import update_game

                update_game(game_id, title_kr=new_name.strip())
                item.setText(new_name.strip())
        except Exception as e:
            print(f"[이름 변경] 오류: {e}")
            import traceback

            traceback.print_exc()

    def _refresh_view(self):
        """현재 뷰 모드에 맞게 목록 새로고침"""
        try:
            self.list_widget.setUpdatesEnabled(False)
            self.list_widget.clearSelection()
            self.list_widget.clear()
            if self.view_mode == "name":
                self._load_name_view()
            elif self.view_mode == "small":
                self._load_icon_view(small=True)
            else:
                self._load_icon_view(small=False)
        except Exception as e:
            import traceback

            print(f"[그리드 오류] {e}")
            traceback.print_exc()
        finally:
            self.list_widget.setUpdatesEnabled(True)

    def _load_name_view(self):
        """이름만 표시 - 탐색기 목록 스타일 (가로 우선 다열, 세로 스크롤)"""
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.list_widget.setWrapping(True)
        self.list_widget.setIconSize(QSize(20, 20))
        self.list_widget.setGridSize(QSize(280, 26))
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setWordWrap(False)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setSpacing(0)
        self.list_widget.setItemDelegate(NameListDelegate(self.list_widget))

        default_icon = self._make_default_icon(24)
        for game in self.games:
            title = (
                game.get("title_kr")
                or game.get("title_en")
                or Path(game["rom_path"]).stem
            )
            missing = game.get("is_missing", 0)
            display = f"⚠ {title}" if missing else title

            icon_path = game.get("icon_path", "")
            cover_path = game.get("cover_path", "")
            if icon_path and Path(icon_path).exists():
                icon = QIcon(
                    QPixmap(icon_path).scaled(
                        24, 24, Qt.AspectRatioMode.KeepAspectRatio
                    )
                )
            elif cover_path and Path(cover_path).exists():
                icon = QIcon(
                    QPixmap(cover_path).scaled(
                        24, 24, Qt.AspectRatioMode.KeepAspectRatio
                    )
                )
            else:
                icon = (
                    self._get_platform_icon(game.get("short_name", ""), 24)
                    or default_icon
                )

            item = QListWidgetItem(icon, display)
            item.setData(Qt.ItemDataRole.UserRole, game["id"])
            if missing:
                item.setForeground(QColor("#ff6666"))
            self.list_widget.addItem(item)

    def _load_icon_view(self, small: bool):
        """아이콘 그리드뷰"""
        self.list_widget.setItemDelegate(QStyledItemDelegate(self.list_widget))
        self.list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.list_widget.setWrapping(True)
        icon_px = (
            ICON_SIZES[self.icon_size_index]
            if not small
            else max(48, ICON_SIZES[self.icon_size_index] // 2 + 16)
        )
        if not small:
            icon_px = ICON_SIZES[self.icon_size_index]

        font_size = max(9, icon_px // 7 + 2)
        from PyQt6.QtGui import QFont

        font = QFont()
        font.setPointSize(font_size)

        self.list_widget.setFont(font)
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(icon_px, icon_px))
        self.list_widget.setGridSize(QSize(icon_px + 20, icon_px + 52))
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setWordWrap(True)

        default_icon = self._make_default_icon(icon_px)

        for game in self.games:
            title = (
                game.get("title_kr")
                or game.get("title_en")
                or Path(game["rom_path"]).stem
            )
            missing = game.get("is_missing", 0)
            display = f"⚠{title}" if missing else title

            # 아이콘 로드
            icon_path = game.get("icon_path", "")
            if icon_path and Path(icon_path).exists():
                pixmap = QPixmap(icon_path).scaled(
                    icon_px,
                    icon_px,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon = QIcon(pixmap)
            else:
                # 커버아트로 대체 시도
                cover_path = game.get("cover_path", "")
                if cover_path and Path(cover_path).exists():
                    pixmap = QPixmap(cover_path).scaled(
                        icon_px,
                        icon_px,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    icon = QIcon(pixmap)
                else:
                    icon = (
                        self._get_platform_icon(game.get("short_name", ""), icon_px)
                        or default_icon
                    )

            # 긴 이름 말줄임 처리 (한글/영문 혼용 픽셀 기준)
            display_short = _truncate_title(display, icon_px + 16)
            item = QListWidgetItem(icon, display_short)
            item.setData(Qt.ItemDataRole.UserRole, game["id"])
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            )
            item.setToolTip(title)
            if missing:
                item.setForeground(QColor("#ff6666"))
            self.list_widget.addItem(item)

    def _make_default_icon(self, size: int) -> QIcon:
        from PyQt6.QtGui import QPainter
        from theme import get_current_theme

        t = get_current_theme()
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(t["icon_bg"]))
        painter = QPainter(pixmap)
        painter.setPen(QColor(t["icon_border"]))
        painter.setFont(QFont("Arial", size // 4))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎮")
        painter.end()
        return QIcon(pixmap)

    def _get_platform_icon(self, short_name: str, size: int) -> QIcon | None:
        """ICON 폴더에서 플랫폼 기본 아이콘 로드"""
        if not short_name:
            return None
        from folders import get_base_path

        icon_path = get_base_path() / "ICON" / f"{short_name}.ico"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if not pixmap.isNull():
                return QIcon(pixmap)
        return None

    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if items:
            game_id = items[0].data(Qt.ItemDataRole.UserRole)
            if game_id:
                self.game_selected.emit(game_id)

    def _on_double_clicked(self, item):
        game_id = item.data(Qt.ItemDataRole.UserRole)
        if game_id:
            self.game_launched.emit(game_id)

    def contextMenuEvent(self, event):
        """우클릭 컨텍스트 메뉴"""
        from PyQt6.QtWidgets import QMenu, QMessageBox, QInputDialog
        from theme import get_current_theme

        menu = QMenu(self)
        t = get_current_theme()
        menu.setStyleSheet(f"""
            QMenu {{
                background: {t['bg_panel']}; color: {t['text_main']};
                border: 1px solid {t['border_light']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{ background: {t['bg_selected']}; }}
            QMenu::item:disabled {{ color: {t['text_dim']}; }}
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 3px 0; }}
        """)

        pos = self.list_widget.mapFromGlobal(event.globalPos())
        item = self.list_widget.itemAt(pos)

        if item:
            game_id = item.data(Qt.ItemDataRole.UserRole)

            # 세이브스테이트 존재 여부 확인
            from database import get_game_detail
            from pathlib import Path

            data = get_game_detail(game_id)
            has_savestate = False
            if data:
                from folders import get_gamedata_path

                platform = data.get("short_name", "")
                title = (
                    data.get("title_kr")
                    or data.get("title_en")
                    or Path(data["rom_path"]).stem
                )
                ss_dir = get_gamedata_path(platform, title) / "savestate"
                has_savestate = ss_dir.exists() and any(ss_dir.iterdir())

            act_rename = menu.addAction("✏  게임 이름 변경")
            menu.addSeparator()
            act_launch = menu.addAction("▶  게임 실행")
            act_load_ss = menu.addAction("📂  상태 불러오기")
            act_load_ss.setEnabled(has_savestate)
            menu.addSeparator()
            act_fav = menu.addAction("★  즐겨찾기 추가/제거")
            act_icon = menu.addAction("🎨  아이콘 변경")
            act_edit = menu.addAction("🖊  게임 정보 편집")
            menu.addSeparator()
            act_reset = menu.addAction("🔄  플레이 기록 초기화")
            act_folder = menu.addAction("📁  게임 폴더 열기")
            menu.addSeparator()
            act_delete = menu.addAction("🗑  목록에서 제거")

            chosen = menu.exec(event.globalPos())

            if chosen == act_rename:
                self.rename_selected_game()

            elif chosen == act_launch:
                self.game_launched.emit(game_id)

            elif chosen == act_load_ss:
                from PyQt6.QtWidgets import QApplication

                win = QApplication.activeWindow()
                if win and hasattr(win, "info_panel"):
                    win.info_panel.load_state()

            elif chosen == act_fav:
                from database import toggle_favorite

                toggle_favorite(game_id)
                self.game_selected.emit(game_id)

            elif chosen == act_icon:
                from icon_crop_dialog import IconCropDialog

                dlg = IconCropDialog(game_id=game_id, parent=self)
                if dlg.exec():
                    updated = get_game_detail(game_id)
                    if updated:
                        icon_path = updated.get("icon_path", "")
                        if icon_path and Path(icon_path).exists():
                            new_icon = QIcon(
                                QPixmap(icon_path).scaled(
                                    self.list_widget.iconSize(),
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation,
                                )
                            )
                            item.setIcon(new_icon)

            elif chosen == act_edit:
                from edit_game_dialog import EditGameDialog

                dlg = EditGameDialog(game_id=game_id, parent=self)
                if dlg.exec():
                    updated = get_game_detail(game_id)
                    if updated:
                        new_title = (
                            updated.get("title_kr")
                            or updated.get("title_en")
                            or Path(updated["rom_path"]).stem
                        )
                        item.setText(new_title)
                    self.game_selected.emit(game_id)

            elif chosen == act_reset:
                reply = QMessageBox.question(
                    self,
                    "플레이 기록 초기화",
                    "이 게임의 플레이 횟수와 시간을 초기화합니다.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    from database import get_connection

                    conn = get_connection()
                    conn.execute(
                        """
                        UPDATE play_history
                        SET play_count=0, total_playtime_sec=0, last_played=NULL
                        WHERE game_id=?
                    """,
                        (game_id,),
                    )
                    conn.commit()
                    conn.close()
                    self.game_selected.emit(game_id)

            elif chosen == act_folder:
                import subprocess

                if data:
                    rom_dir = str(Path(data["rom_path"]).parent)
                    subprocess.Popen(f'explorer "{rom_dir}"')

            elif chosen == act_delete:
                reply = QMessageBox.question(
                    self,
                    "게임 제거",
                    "목록에서 제거합니다. ROM 파일은 삭제되지 않습니다.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    from database import delete_game

                    delete_game(game_id)
                    row = self.list_widget.row(item)
                    self.list_widget.takeItem(row)
                    self.games = [g for g in self.games if g["id"] != game_id]
                    from PyQt6.QtWidgets import QApplication

                    win = QApplication.activeWindow()
                    if win and hasattr(win, "_update_game_count"):
                        win._update_game_count(len(self.games))

        else:
            # 즐겨찾기 탭이면 메뉴 없음
            if self.current_platform_id is None:
                return

            act_add_file = menu.addAction("📄  ROM 파일 추가")
            act_add_path = menu.addAction("➕  ROM 경로 추가")
            menu.addSeparator()
            act_scan = menu.addAction("🔍  ROM 폴더 스캔 (F5)")
            menu.addSeparator()
            act_clear_grid = menu.addAction("🗑  그리드 초기화")

            chosen = menu.exec(event.globalPos())
            if chosen == act_add_file:
                self._add_rom_file_for_platform()
            elif chosen == act_add_path:
                self._add_rom_folder_for_platform()
            elif chosen == act_scan:
                self.request_scan.emit()
            elif chosen == act_clear_grid:
                from PyQt6.QtWidgets import QMessageBox

                reply = QMessageBox.question(
                    self,
                    "그리드 초기화",
                    "현재 플랫폼의 게임 목록을 초기화합니다.\n"
                    "ROM 파일과 메타데이터는 삭제되지 않습니다.\n"
                    "F5를 눌러 다시 스캔할 수 있습니다.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # platform_id 안전검사
                    if not self.current_platform_id:
                        QMessageBox.warning(self, "오류", "플랫폼 정보가 없습니다.")
                        return

                try:
                    from database import get_connection

                    conn = get_connection()
                    conn.execute("PRAGMA foreign_keys = OFF")

                    conn.execute(
                     "DELETE FROM games WHERE platform_id=?",
                     (self.current_platform_id,)
                    )

                    conn.execute("PRAGMA foreign_keys = ON")

                    conn.commit()
                    conn.close()

                    self.games = []
                    self.list_widget.clear()

                    # 스캔 자동 실행 제거 (충돌 방지)
                    # self.request_scan.emit()

                    # 대신 상위 탭 새로고침만 요청
                    from PyQt6.QtWidgets import QApplication

                    win = QApplication.activeWindow()
                    if win and hasattr(win, "_on_tab_changed"):
                        win._on_tab_changed(win.tab_bar.currentIndex())

                except Exception as e:
                    import traceback

                    print(f"[그리드 초기화 오류] {e}")
                    traceback.print_exc()
                    QMessageBox.critical(
                        self, "DB 오류", "그리드 초기화 중 오류가 발생했습니다."
                    )

    def _add_rom_folder_for_platform(self):
        """현재 플랫폼의 ROM 폴더 경로 추가"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from database import add_platform_rom_folder, get_connection

        if not self.current_platform_id:
            return

        folder = QFileDialog.getExistingDirectory(self, "ROM 폴더 선택")
        if not folder:
            return

        # 플랫폼 short_name 조회
        conn = get_connection()
        row = conn.execute(
            "SELECT short_name FROM platforms WHERE id=?", (self.current_platform_id,)
        ).fetchone()
        conn.close()
        if not row:
            return

        short_name = row["short_name"]
        add_platform_rom_folder(short_name, folder)
        QMessageBox.information(
            self,
            "폴더 추가 완료",
            f"ROM 폴더가 추가되었습니다.\n{folder}\n\nF5를 눌러 ROM을 스캔해주세요.",
        )

    def _add_rom_file_for_platform(self):
        """현재 플랫폼 탭에 맞는 ROM 파일 추가 (확장자 검증 포함)"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from database import get_connection, add_game
        from pathlib import Path

        # 허용 확장자 필터 문자열 생성
        exts = self.current_platform_extensions
        if exts:
            ext_filter = (
                "ROM 파일 (" + " ".join(f"*{e}" for e in exts) + ");;모든 파일 (*)"
            )
        else:
            ext_filter = "모든 파일 (*)"

        path, _ = QFileDialog.getOpenFileName(self, "ROM 파일 선택", "", ext_filter)
        if not path:
            return

        ext = Path(path).suffix.lower()
        if exts and ext not in exts:
            QMessageBox.warning(
                self,
                "확장자 오류",
                f"현재 플랫폼(탭.그리드)에서 지원하지 않는 파일 형식입니다.\n"
                f"지원 확장자: {', '.join(exts)}\n"
                f"선택한 파일: {ext}",
            )
            return

        add_game(self.current_platform_id, path, title_en=Path(path).stem)
        from PyQt6.QtWidgets import QApplication

        win = QApplication.activeWindow()
        if win and hasattr(win, "_on_tab_changed"):
            win._on_tab_changed(win.tab_bar.currentIndex())
