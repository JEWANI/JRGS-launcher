"""
JRGS - 재와니의 레트로 게임 보관소
icon_crop_dialog.py - 아이콘 크롭/편집 다이얼로그
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QSizePolicy, QSpinBox, QScrollArea,
    QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QTransform


# ── 크롭 캔버스 위젯 ─────────────────────────────────────────────
class CropCanvas(QWidget):
    """이미지를 표시하고 마우스 드래그로 크롭 영역을 선택하는 위젯"""
    crop_changed = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None   # 원본(표시용) 픽스맵
        self._scale = 1.0                      # 표시 배율
        self._origin = QPoint(0, 0)            # 픽스맵 표시 시작점
        self._drag_start: QPoint | None = None
        self._crop_rect = QRect()              # 화면 좌표 기준 크롭 박스
        self.setMinimumSize(400, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._crop_rect = QRect()
        self._fit()
        self.update()

    def _fit(self):
        """위젯 크기에 맞게 배율/원점 계산"""
        if not self._pixmap:
            return
        w, h = self.width(), self.height()
        pw, ph = self._pixmap.width(), self._pixmap.height()
        self._scale = min(w / pw, h / ph, 1.0)
        disp_w = int(pw * self._scale)
        disp_h = int(ph * self._scale)
        self._origin = QPoint((w - disp_w) // 2, (h - disp_h) // 2)

    def resizeEvent(self, e):
        self._fit()
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        if not self._pixmap:
            return
        pw = int(self._pixmap.width() * self._scale)
        ph = int(self._pixmap.height() * self._scale)
        painter.drawPixmap(self._origin.x(), self._origin.y(), pw, ph, self._pixmap)

        if not self._crop_rect.isNull() and self._crop_rect.isValid():
            # 어두운 오버레이
            overlay = QColor(0, 0, 0, 120)
            full = self.rect()
            cr = self._crop_rect.normalized()
            painter.fillRect(QRect(full.left(), full.top(), full.width(), cr.top() - full.top()), overlay)
            painter.fillRect(QRect(full.left(), cr.bottom(), full.width(), full.bottom() - cr.bottom()), overlay)
            painter.fillRect(QRect(full.left(), cr.top(), cr.left() - full.left(), cr.height()), overlay)
            painter.fillRect(QRect(cr.right(), cr.top(), full.right() - cr.right(), cr.height()), overlay)
            # 크롭 박스
            pen = QPen(QColor("#00d4ff"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(cr)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.pos()
            self._crop_rect = QRect()
            self.update()

    def mouseMoveEvent(self, e):
        if self._drag_start:
            self._crop_rect = QRect(self._drag_start, e.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drag_start:
            self._crop_rect = QRect(self._drag_start, e.pos()).normalized()
            self._drag_start = None
            self.crop_changed.emit(self._crop_rect)
            self.update()

    def get_crop_pixmap(self) -> QPixmap | None:
        """크롭된 원본 해상도 픽스맵 반환"""
        if not self._pixmap or self._crop_rect.isNull():
            return self._pixmap  # 크롭 없으면 전체 반환
        # 화면 좌표 → 원본 픽스맵 좌표로 변환
        cr = self._crop_rect.normalized()
        ox, oy = self._origin.x(), self._origin.y()
        x = int((cr.x() - ox) / self._scale)
        y = int((cr.y() - oy) / self._scale)
        w = int(cr.width() / self._scale)
        h = int(cr.height() / self._scale)
        x = max(0, x); y = max(0, y)
        w = min(w, self._pixmap.width() - x)
        h = min(h, self._pixmap.height() - y)
        if w <= 0 or h <= 0:
            return self._pixmap
        return self._pixmap.copy(x, y, w, h)


# ── 메인 다이얼로그 ──────────────────────────────────────────────
class IconCropDialog(QDialog):
    def __init__(self, game_id: int, parent=None):
        super().__init__(parent)
        self.game_id = game_id
        self._rotation = 0
        self._flipped = False
        self._base_pixmap: QPixmap | None = None  # 불러온 원본

        from database import get_game_detail
        self.data = get_game_detail(game_id) or {}

        self.setWindowTitle("아이콘 편집")
        self.setMinimumSize(560, 520)
        self.setModal(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── 상단 버튼 ──
        top = QHBoxLayout()
        self.btn_load = QPushButton("📂 이미지 불러오기")
        self.btn_load.clicked.connect(self._load_image)
        top.addWidget(self.btn_load)
        top.addStretch()

        self.btn_rotate = QPushButton("↺ 회전")
        self.btn_flip   = QPushButton("↔ 반전")
        self.btn_reset_crop = QPushButton("✖ 크롭 초기화")
        self.btn_rotate.clicked.connect(self._rotate)
        self.btn_flip.clicked.connect(self._flip)
        self.btn_reset_crop.clicked.connect(self._reset_crop)
        top.addWidget(self.btn_rotate)
        top.addWidget(self.btn_flip)
        top.addWidget(self.btn_reset_crop)
        layout.addLayout(top)

        # ── 크롭 캔버스 ──
        self.canvas = CropCanvas()
        layout.addWidget(self.canvas, stretch=1)

        # ── 하단: 크기 선택 + 미리보기 ──
        bottom = QHBoxLayout()

        size_lbl = QLabel("저장 크기:")
        self.combo_size = QComboBox()
        self.combo_size.addItems(["32 × 32", "64 × 64", "128 × 128", "사용자 지정"])
        self.combo_size.setCurrentIndex(1)  # 기본 64x64
        self.combo_size.currentIndexChanged.connect(self._on_size_changed)

        self.spin_w = QSpinBox(); self.spin_w.setRange(16, 512); self.spin_w.setValue(64)
        self.spin_h = QSpinBox(); self.spin_h.setRange(16, 512); self.spin_h.setValue(64)
        self.spin_w.setVisible(False)
        self.spin_h.setVisible(False)

        bottom.addWidget(size_lbl)
        bottom.addWidget(self.combo_size)
        bottom.addWidget(QLabel("W:"))
        bottom.addWidget(self.spin_w)
        bottom.addWidget(QLabel("H:"))
        bottom.addWidget(self.spin_h)
        bottom.addStretch()

        # 미리보기
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(64, 64)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setObjectName("preview_box")
        bottom.addWidget(QLabel("미리보기:"))
        bottom.addWidget(self.lbl_preview)
        layout.addLayout(bottom)

        self.canvas.crop_changed.connect(self._update_preview)

        # ── 저장/취소 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save   = QPushButton("💾 저장")
        self.btn_cancel = QPushButton("✖ 취소")
        self.btn_save.setFixedSize(90, 32)
        self.btn_cancel.setFixedSize(90, 32)
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "",
            "이미지 파일 (*.jpg *.jpeg *.png *.bmp *.ico *.webp)"
        )
        if not path:
            return
        px = QPixmap(path)
        if px.isNull():
            QMessageBox.warning(self, "오류", "이미지를 불러올 수 없습니다.")
            return
        self._rotation = 0
        self._flipped = False
        self._base_pixmap = px
        self.canvas.set_pixmap(px)
        self._update_preview(QRect())

    def _get_transformed_pixmap(self) -> QPixmap | None:
        if not self._base_pixmap:
            return None
        t = QTransform()
        t.rotate(self._rotation)
        if self._flipped:
            t.scale(-1, 1)
        return self._base_pixmap.transformed(t, Qt.TransformationMode.SmoothTransformation)

    def _rotate(self):
        self._rotation = (self._rotation + 90) % 360
        px = self._get_transformed_pixmap()
        if px:
            self.canvas.set_pixmap(px)
            self._update_preview(QRect())

    def _flip(self):
        self._flipped = not self._flipped
        px = self._get_transformed_pixmap()
        if px:
            self.canvas.set_pixmap(px)
            self._update_preview(QRect())

    def _reset_crop(self):
        self.canvas._crop_rect = QRect()
        self.canvas.update()
        self._update_preview(QRect())

    def _on_size_changed(self, idx):
        custom = (idx == 3)
        self.spin_w.setVisible(custom)
        self.spin_h.setVisible(custom)

    def _get_save_size(self) -> tuple[int, int]:
        idx = self.combo_size.currentIndex()
        sizes = [(32, 32), (64, 64), (128, 128)]
        if idx < 3:
            return sizes[idx]
        return self.spin_w.value(), self.spin_h.value()

    def _update_preview(self, rect: QRect):
        cropped = self.canvas.get_crop_pixmap()
        if not cropped:
            return
        w, h = self._get_save_size()
        preview = cropped.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        self.lbl_preview.setPixmap(preview)

    def _save(self):
        cropped = self.canvas.get_crop_pixmap()
        if not cropped:
            QMessageBox.warning(self, "저장 실패", "이미지를 먼저 불러오세요.")
            return

        w, h = self._get_save_size()
        final = cropped.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)

        # 저장 경로
        from folders import get_gamedata_path
        d = self.data
        platform = d.get("short_name") or "Unknown"
        title = d.get("title_kr") or d.get("title_en") or Path(d.get("rom_path", "unknown")).stem
        dest_dir = get_gamedata_path(platform, title)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "icon.png"

        if final.save(str(dest), "PNG"):
            # DB 갱신
            from database import get_connection
            conn = get_connection()
            conn.execute(
                "UPDATE game_meta SET icon_path=? WHERE game_id=?",
                (str(dest), self.game_id)
            )
            conn.commit()
            conn.close()
            self.accept()
        else:
            QMessageBox.warning(self, "저장 실패", f"파일 저장에 실패했습니다.\n{dest}")

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        t = get_current_theme()
        self.setStyleSheet(build_stylesheet(t) + f"""
            QLabel#preview_box {{
                border: 1px solid {t['border']};
                background: {t['bg_deep']};
                border-radius: 4px;
            }}
        """)