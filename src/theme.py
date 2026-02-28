"""
JRGS - 재와니의 레트로 게임 보관소
theme.py - 테마/스킨 정의 및 적용
"""

import json
from pathlib import Path
from database import get_setting, set_setting


# ── 기본 스킨 정의 ────────────────────────────────────────
THEMES = {
    "dark": {
        "name": "🌙 다크",
        "font_family":  "SUIT-Medium",
        "bg_deep":      "#12121e",
        "bg_base":      "#1e1e2e",
        "bg_panel":     "#2a2a3e",
        "bg_hover":     "#3a3a6a",
        "bg_selected":  "#4a4a8a",
        "border":       "#3a3a5a",
        "border_light": "#4a4a6a",
        "text_main":    "#ccccee",
        "text_sub":     "#aaaacc",
        "text_dim":     "#888899",
        "tab_font":     "bold",
        "btn_radius":   "4px",
        "tab_radius":   "4px 4px 0 0",
        "missing":      "#ff6666",
        "icon_bg":      "#2a2a4a",
        "icon_border":  "#4a4a8a",
    },
    "beige": {
        "name": "📜 레트로 베이지",
        "font_family":  "SUIT-Medium",
        "bg_deep":      "#e8d5b0",
        "bg_base":      "#f5ead8",
        "bg_panel":     "#ede0c8",
        "bg_hover":     "#d4b896",
        "bg_selected":  "#6b3a1f",
        "border":       "#6b3a1f",
        "border_light": "#8b5e3c",
        "text_main":    "#1a0f00",
        "text_sub":     "#2a1500",
        "text_dim":     "#5a3a20",
        "tab_font":     "bold",
        "btn_radius":   "2px",
        "tab_radius":   "2px 2px 0 0",
        "missing":      "#cc2200",
        "icon_bg":      "#ddc898",
        "icon_border":  "#6b3a1f",
    },
    "green": {
        "name": "🟢 그린 레트로",
        "font_family":  "SUIT-Medium",
        "bg_deep":      "#0a1a0a",
        "bg_base":      "#0f2410",
        "bg_panel":     "#1a3a1a",
        "bg_hover":     "#2a5a2a",
        "bg_selected":  "#3a7a3a",
        "border":       "#2a4a2a",
        "border_light": "#3a6a3a",
        "text_main":    "#88ff88",
        "text_sub":     "#66cc66",
        "text_dim":     "#448844",
        "tab_font":     "bold",
        "btn_radius":   "0px",
        "tab_radius":   "0px",
        "missing":      "#ff4444",
        "icon_bg":      "#1a3a1a",
        "icon_border":  "#3a7a3a",
    },
}

# 커스텀 슬롯
CUSTOM_SLOTS = ["custom1", "custom2", "custom3"]

CUSTOM_SLOT_NAMES = {
    "custom1": "🎨 커스텀 1",
    "custom2": "🎨 커스텀 2",
    "custom3": "🎨 커스텀 3",
}

# 커스텀 1 기본값 — Windows 기본 색상
CUSTOM1_DEFAULT = {
    "font_family":  "SUIT-Medium",
    "bg_deep":      "#f0f0f0",
    "bg_base":      "#f0f0f0",
    "bg_panel":     "#e1e1e1",
    "bg_hover":     "#cce4f7",
    "bg_selected":  "#0078d7",
    "border":       "#adadad",
    "border_light": "#c0c0c0",
    "text_main":    "#000000",
    "text_sub":     "#333333",
    "text_dim":     "#666666",
    "missing":      "#cc0000",
    "icon_bg":      "#e1e1e1",
    "icon_border":  "#adadad",
}

# 커스텀 2/3 기본값 — 다크 기반
CUSTOM_OTHER_DEFAULT = {k: v for k, v in THEMES["dark"].items()
                        if k not in ("name", "tab_font", "btn_radius", "tab_radius")}

# 색상 항목 레이블
CUSTOM_COLOR_LABELS = {
    "bg_deep":      "그리드 배경",
    "bg_base":      "기본 배경",
    "bg_panel":     "패널 배경",
    "bg_hover":     "호버 색상",
    "bg_selected":  "선택 색상",
    "border":       "테두리",
    "border_light": "테두리 (밝은)",
    "text_main":    "주요 글자색",
    "text_sub":     "보조 글자색",
    "text_dim":     "흐린 글자색",
    "missing":      "누락 ROM 색상",
    "icon_bg":      "기본 아이콘 배경",
    "icon_border":  "기본 아이콘 테두리",
}

THEME_KEYS = list(THEMES.keys()) + CUSTOM_SLOTS


def _get_custom_path(slot: str) -> Path:
    base = Path(__file__).parent.parent
    return base / f"custom_theme_{slot}.json"


def _get_slot_default(slot: str) -> dict:
    if slot == "custom1":
        return CUSTOM1_DEFAULT.copy()
    return CUSTOM_OTHER_DEFAULT.copy()


def get_custom_theme(slot: str) -> dict:
    """슬롯별 커스텀 테마 불러오기"""
    path = _get_custom_path(slot)
    default = _get_slot_default(slot)

    base = THEMES["dark"].copy()
    base.update(default)

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            base.update(data)
        except Exception:
            pass

    # JSON에 저장된 display_name 우선, 없으면 기본 슬롯명
    saved_name = base.get("display_name", "")
    base["name"] = saved_name if saved_name else CUSTOM_SLOT_NAMES[slot]
    base["tab_font"] = "bold"
    base["btn_radius"] = "4px"
    base["tab_radius"] = "4px 4px 0 0"
    base.setdefault("font_family", "SUIT-Medium")
    return base


def save_custom_theme(slot: str, color_dict: dict):
    path = _get_custom_path(slot)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(color_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[테마] 커스텀 저장 오류: {e}")


def get_current_theme() -> dict:
    key = get_setting("theme", "dark")
    if key in CUSTOM_SLOTS:
        return get_custom_theme(key)
    return THEMES.get(key, THEMES["dark"])


def get_current_theme_key() -> str:
    return get_setting("theme", "dark")


def set_theme(key: str):
    if key in THEME_KEYS:
        set_setting("theme", key)


def build_stylesheet(t: dict) -> str:
    try:
        from database import get_setting
        font = get_setting("font", t.get("font_family", "SUIT-Medium"))
    except Exception:
        font = t.get("font_family", "SUIT-Medium")
    return f"""
        QMainWindow, QDialog, QWidget {{
            background: {t['bg_base']};
            color: {t['text_main']};
            font-family: "{font}";
        }}
        QMenuBar {{
            background: {t['bg_base']};
            color: {t['text_main']};
            border-bottom: 1px solid {t['border']};
            padding: 2px;
        }}
        QMenuBar::item:selected {{
            background: {t['bg_hover']};
            border-radius: 3px;
        }}
        QMenu {{
            background: {t['bg_panel']};
            color: {t['text_main']};
            border: 1px solid {t['border_light']};
        }}
        QMenu::item {{
            padding: 5px 32px 5px 24px;
        }}
        QMenu::item:selected {{ background: {t['bg_selected']}; color: {t['text_main']}; }}
        QMenu::separator {{ height: 1px; background: {t['border']}; }}
        QTabBar::tab {{
            background: {t['bg_panel']};
            color: {t['text_sub']};
            padding: 8px 16px;
            font-size: 12px;
            font-weight: {t['tab_font']};
            border-radius: {t['tab_radius']};
            margin-right: 2px;
            border: none;
        }}
        QTabBar::tab:selected {{
            background: {t['bg_selected']};
            color: {t['text_main']};
        }}
        QTabBar::tab:hover {{
            background: {t['bg_hover']};
            color: {t['text_main']};
        }}
        QTabWidget::pane {{
            border: 1px solid {t['border']};
            background: {t['bg_base']};
        }}
        QPushButton {{
            background: {t['bg_panel']};
            color: {t['text_sub']};
            border: 1px solid {t['border_light']};
            border-radius: {t['btn_radius']};
            padding: 5px 13px;
        }}
        QPushButton:hover {{ background: {t['bg_hover']}; color: {t['text_main']}; }}
        QPushButton:pressed {{ background: {t['bg_selected']}; }}
        QPushButton:checked {{ background: {t['bg_selected']}; color: {t['text_main']}; }}
        QListWidget {{
            background: {t['bg_deep']};
            border: none;
            outline: none;
            color: {t['text_main']};
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
        QGroupBox {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
            color: {t['text_sub']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
        }}
        QCheckBox {{ spacing: 6px; color: {t['text_main']}; }}
        QCheckBox::indicator {{
            width: 16px; height: 16px;
            border: 1px solid {t['border_light']};
            border-radius: 3px;
            background: {t['bg_panel']};
        }}
        QCheckBox::indicator:checked {{
            background: {t['bg_selected']};
        }}
        QComboBox, QLineEdit, QSpinBox {{
            background: {t['bg_panel']};
            border: 1px solid {t['border_light']};
            border-radius: {t['btn_radius']};
            padding: 4px 8px;
            color: {t['text_main']};
        }}
        QScrollBar:vertical {{
            background: {t['bg_panel']};
            width: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['bg_selected']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QStatusBar {{
            background: {t['bg_panel']};
            color: {t['text_dim']};
            border-top: 1px solid {t['border']};
            font-size: 12px;
        }}
        QSplitter::handle {{ background: transparent; }}
        QDialogButtonBox QPushButton {{ min-width: 72px; }}
        QScrollArea {{ background: transparent; }}
    """


def _is_light(hex_color: str) -> bool:
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000 > 128
    except Exception:
        return False


# ── 커스텀 테마 편집 다이얼로그 ───────────────────────────
class CustomThemeDialog:

    @staticmethod
    def open(slot: str, parent=None):
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
            QScrollArea, QWidget, QFormLayout, QDialogButtonBox, QFrame
        )
        from PyQt6.QtGui import QColor

        current = get_custom_theme(slot)
        edited = {k: current.get(k, "#000000") for k in CUSTOM_COLOR_LABELS}

        dlg = QDialog(parent)
        dlg.setWindowTitle(f"{CUSTOM_SLOT_NAMES[slot]} 색상 편집")
        dlg.setMinimumSize(420, 540)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 8)

        # 슬롯 이름 변경
        from PyQt6.QtWidgets import QLineEdit
        name_row = QHBoxLayout()
        name_lbl = QLabel("테마 이름:")
        name_lbl.setFixedWidth(80)
        name_edit = QLineEdit()
        name_edit.setFixedHeight(28)
        name_edit.setMaxLength(20)
        name_edit.setPlaceholderText(CUSTOM_SLOT_NAMES[slot])
        name_edit.setText(current.get("display_name", ""))
        name_edit.textChanged.connect(lambda t: edited.update({"display_name": t.strip()}))
        name_row.addWidget(name_lbl)
        name_row.addWidget(name_edit)
        layout.addLayout(name_row)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep0)

        # 기반 테마 초기화 버튼
        lbl_base = QLabel("기반 테마로 초기화:")
        layout.addWidget(lbl_base)
        base_row = QHBoxLayout()

        color_buttons = {}  # 먼저 선언 (버튼 refresh에서 참조)

        for key, info in THEMES.items():
            btn = QPushButton(info["name"])
            btn.setFixedHeight(28)
            def _load_theme(_, k=key):
                src = THEMES[k]
                for ck in CUSTOM_COLOR_LABELS:
                    edited[ck] = src.get(ck, "#000000")
                CustomThemeDialog._refresh_buttons(color_buttons, edited)
            btn.clicked.connect(_load_theme)
            base_row.addWidget(btn)

        btn_win = QPushButton("🖥 Windows 기본")
        btn_win.setFixedHeight(28)
        def _load_win(_):
            for ck in CUSTOM_COLOR_LABELS:
                edited[ck] = CUSTOM1_DEFAULT.get(ck, "#000000")
            CustomThemeDialog._refresh_buttons(color_buttons, edited)
        btn_win.clicked.connect(_load_win)
        base_row.addWidget(btn_win)
        layout.addLayout(base_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # 색상 항목 스크롤
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        from PyQt6.QtCore import Qt as _Qt
        scroll.setVerticalScrollBarPolicy(_Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(_Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        form = QFormLayout(content)
        form.setSpacing(8)
        form.setContentsMargins(8, 8, 8, 8)

        for key, label in CUSTOM_COLOR_LABELS.items():
            btn = CustomThemeDialog._make_color_btn(dlg, key, edited)
            color_buttons[key] = btn
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(140)
            row.addWidget(lbl)
            row.addWidget(btn)
            row.addStretch()
            form.addRow(row)

        # 폰트 선택
        from PyQt6.QtGui import QFontDatabase
        from PyQt6.QtWidgets import QComboBox
        font_row = QHBoxLayout()
        font_lbl = QLabel("폰트")
        font_lbl.setFixedWidth(140)

        font_combo = QComboBox()
        font_combo.setFixedWidth(200)

        # fonts/ 폴더 폰트 우선 + 시스템 폰트
        from pathlib import Path as _Path
        fonts_dir = _Path(__file__).resolve().parent.parent / "fonts"
        bundled = []
        if fonts_dir.exists():
            for f in sorted(fonts_dir.glob("*.ttf")) + sorted(fonts_dir.glob("*.otf")):
                fid = QFontDatabase.addApplicationFont(str(f))
                families = QFontDatabase.applicationFontFamilies(fid)
                bundled.extend(families)

        all_fonts = bundled + [f for f in QFontDatabase.families() if f not in bundled]
        font_combo.addItems(all_fonts)

        current_font = edited.get("font_family", "SUIT-Medium")
        idx = font_combo.findText(current_font)
        if idx >= 0:
            font_combo.setCurrentIndex(idx)

        font_combo.currentTextChanged.connect(lambda f: edited.update({"font_family": f}))

        font_row.addWidget(font_lbl)
        font_row.addWidget(font_combo)
        font_row.addStretch()
        form.addRow(font_row)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # 확인/취소
        btn_box = QDialogButtonBox()
        btn_box.addButton("저장", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(lambda: (save_custom_theme(slot, edited), dlg.accept()))
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)

        t = get_current_theme()
        dlg.setStyleSheet(build_stylesheet(t))
        return dlg.exec()

    @staticmethod
    def _make_color_btn(dlg, key: str, edited: dict):
        from PyQt6.QtWidgets import QPushButton, QColorDialog
        from PyQt6.QtGui import QColor

        btn = QPushButton(edited[key])
        btn.setFixedSize(130, 28)
        CustomThemeDialog._update_btn_style(btn, edited[key])

        def _pick(_):
            color = QColorDialog.getColor(QColor(edited[key]), dlg,
                                          f"{CUSTOM_COLOR_LABELS[key]} 선택")
            if color.isValid():
                hex_val = color.name()
                edited[key] = hex_val
                btn.setText(hex_val)
                CustomThemeDialog._update_btn_style(btn, hex_val)

        btn.clicked.connect(_pick)
        return btn

    @staticmethod
    def _update_btn_style(btn, hex_color: str):
        text_color = "#000000" if _is_light(hex_color) else "#ffffff"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {hex_color};
                color: {text_color};
                border: 1px solid #888;
                border-radius: 4px;
                font-size: 11px;
            }}
        """)

    @staticmethod
    def _refresh_buttons(color_buttons: dict, edited: dict):
        for k, btn in color_buttons.items():
            hex_val = edited[k]
            btn.setText(hex_val)
            CustomThemeDialog._update_btn_style(btn, hex_val)