"""
JRGS - 재와니의 레트로 게임 보관소
batch_meta_dialog.py - 메타데이터 일괄 갱신 다이얼로그
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QComboBox, QTextEdit, QWidget, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class BatchMetaWorker(QThread):
    """백그라운드 메타데이터 갱신 스레드"""
    progress = pyqtSignal(int, int, str)   # current, total, game_title
    log      = pyqtSignal(str)             # 로그 메시지
    finished = pyqtSignal(int, int, int)   # success, fail, skip

    def __init__(self, games: list, overwrite: bool = False):
        super().__init__()
        self.games = games
        self.overwrite = overwrite
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self._run_inner()
        except Exception as e:
            import traceback
            self.log.emit(f"[치명적 오류] {e}\n{traceback.format_exc()}")
            self.finished.emit(0, 0, 0)

    def _run_inner(self):
        from metadata_api import search_metadata, download_cover
        from database import update_game
        from folders import get_gamedata_path
        from pathlib import Path

        success = fail = skip = 0
        total = len(self.games)
        consecutive_fail = 0
        MAX_CONSECUTIVE_FAIL = 10

        for i, game in enumerate(self.games):
            if self._stop:
                self.log.emit("[중단] 사용자 요청으로 중단됨")
                break

            title = game.get("title_en") or game.get("title_kr") or ""
            platform_short = game.get("short_name", "")
            game_id = game["id"]

            self.progress.emit(i + 1, total, title or f"game_{game_id}")

            # 이미 메타데이터 있고 덮어쓰기 비활성이면 스킵
            if not self.overwrite and game.get("genre") and game.get("developer"):
                skip += 1
                self.log.emit(f"[스킵] {title} — 이미 정보 있음")
                continue

            if not title:
                fail += 1
                self.log.emit(f"[실패] game_{game_id} — 검색할 제목 없음")
                continue

            try:
                rom_filename = Path(game.get("rom_path", "")).name
                result = search_metadata(title, platform_short, romnom=rom_filename)
            except Exception as e:
                fail += 1
                self.log.emit(f"[오류] {title} — {e}")
                import time
                time.sleep(1)
                continue

            if not result:
                fail += 1
                consecutive_fail += 1
                self.log.emit(f"[실패] {title} — 검색 결과 없음")
                if consecutive_fail >= MAX_CONSECUTIVE_FAIL:
                    self.log.emit(f"[중단] 연속 {MAX_CONSECUTIVE_FAIL}회 실패 — ScreenScraper 연결 문제 가능성")
                    break
                import time
                time.sleep(0.3)
                continue

            consecutive_fail = 0
            import time
            time.sleep(0.5)  # ScreenScraper rate limit 방지

            # DB 업데이트
            update_kwargs = {}
            if result.get("title_en"):
                update_kwargs["title_en"] = result["title_en"]
            if result.get("title_kr"):
                update_kwargs["title_kr"] = result["title_kr"]
            if result.get("genre"):
                update_kwargs["genre"] = result["genre"]
            if result.get("developer"):
                update_kwargs["developer"] = result["developer"]
            if result.get("publisher"):
                update_kwargs["publisher"] = result["publisher"]
            if result.get("release_year"):
                update_kwargs["release_year"] = result["release_year"]
            if result.get("release_region"):
                update_kwargs["release_region"] = result["release_region"]

            # 커버아트 다운로드
            cover_url = result.get("cover_url", "")
            if cover_url and (self.overwrite or not game.get("cover_path")):
                try:
                    game_title_safe = (result.get("title_en") or title)[:50]
                    save_dir = get_gamedata_path(platform_short, game_title_safe)
                    ext = Path(cover_url.split("?")[0]).suffix or ".jpg"
                    cover_path = save_dir / f"cover{ext}"
                    if download_cover(cover_url, str(cover_path)):
                        update_kwargs["cover_path"] = str(cover_path)
                except Exception as e:
                    self.log.emit(f"[커버아트] {title} 다운로드 실패: {e}")

            if update_kwargs:
                update_game(game_id, **update_kwargs)
                success += 1
                self.log.emit(f"[완료] {title}")
            else:
                fail += 1
                self.log.emit(f"[실패] {title} — 갱신할 데이터 없음")

        self.finished.emit(success, fail, skip)


class BatchMetaDialog(QDialog):
    def __init__(self, current_platform_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("메타데이터 일괄 갱신")
        self.setMinimumSize(520, 480)
        self.setModal(True)
        self.current_platform_id = current_platform_id
        self._worker = None
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # 대상 선택
        row_target = QHBoxLayout()
        lbl_target = QLabel("갱신 대상:")
        lbl_target.setFixedWidth(70)
        self.cmb_target = QComboBox()
        self.cmb_target.setFixedHeight(26)
        self._load_target_combo()
        row_target.addWidget(lbl_target)
        row_target.addWidget(self.cmb_target)
        layout.addLayout(row_target)

        # 옵션
        from theme import get_current_theme
        t = get_current_theme()
        label = "이미 정보가 있는 게임도 덮어쓰기"
        self.chk_overwrite = QPushButton(f"☐  {label}")
        self.chk_overwrite.setCheckable(True)
        self.chk_overwrite.setFixedHeight(28)
        self.chk_overwrite.setStyleSheet("")
        self.chk_overwrite.toggled.connect(
            lambda checked, b=self.chk_overwrite, l=label:
            b.setText(f"✔  {l}" if checked else f"☐  {l}")
        )
        layout.addWidget(self.chk_overwrite)

        lbl_warn = QLabel("※ ScreenScraper 계정 설정이 필요합니다. (환경설정 > 메타데이터 API)")
        lbl_warn.setStyleSheet("font-size: 10px; color: #888899;")
        lbl_warn.setWordWrap(True)
        layout.addWidget(lbl_warn)

        # 프로그레스바
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("대기 중...")
        self.lbl_progress.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_progress)

        # 로그창
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.log_edit)

        # 결과 요약
        self.lbl_result = QLabel("")
        self.lbl_result.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(self.lbl_result)

        # 버튼
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ 갱신 시작")
        self.btn_start.setFixedHeight(32)
        self.btn_start.clicked.connect(self._start)

        self.btn_stop = QPushButton("■ 중단")
        self.btn_stop.setFixedHeight(32)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        self.btn_close = QPushButton("닫기")
        self.btn_close.setFixedHeight(32)
        self.btn_close.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    def _load_target_combo(self):
        from database import get_all_platforms
        self.cmb_target.clear()
        self.cmb_target.addItem("전체 게임", None)
        platforms = get_all_platforms()
        for p in platforms:
            if p.get("is_visible", 1):
                self.cmb_target.addItem(
                    p.get("display_name") or p["short_name"],
                    p["id"]
                )
        # 현재 플랫폼 선택
        if self.current_platform_id:
            for i in range(self.cmb_target.count()):
                if self.cmb_target.itemData(i) == self.current_platform_id:
                    self.cmb_target.setCurrentIndex(i)
                    break

    def _get_games(self):
        from database import get_games_by_platform, get_all_platforms, get_connection
        platform_id = self.cmb_target.currentData()
        if platform_id is None:
            # 전체 게임
            conn = get_connection()
            rows = conn.execute("""
                SELECT g.*, p.short_name
                FROM games g
                LEFT JOIN platforms p ON g.platform_id = p.id
                ORDER BY p.tab_order, g.title_en, g.title_kr
            """).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        else:
            return get_games_by_platform(platform_id)

    def _start(self):
        games = self._get_games()
        if not games:
            self.lbl_progress.setText("갱신할 게임이 없습니다.")
            return

        self.log_edit.clear()
        self.lbl_result.setText("")
        self.progress_bar.setMaximum(len(games))
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._worker = BatchMetaWorker(games, self.chk_overwrite.isChecked())
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _stop(self):
        if self._worker:
            self._worker.stop()
        self.btn_stop.setEnabled(False)

    def _on_progress(self, current, total, title):
        self.progress_bar.setValue(current)
        self.lbl_progress.setText(f"처리 중 ({current}/{total}): {title}")

    def _on_log(self, msg):
        self.log_edit.append(msg)
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def _on_finished(self, success, fail, skip):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_progress.setText("완료")
        self.lbl_result.setText(f"✔ 완료: {success}개  ✖ 실패: {fail}개  ◎ 스킵: {skip}개")
        self.log_edit.append(f"\n[갱신 완료] 성공: {success}, 실패: {fail}, 스킵: {skip}")

    def _apply_style(self):
        from theme import get_current_theme, build_stylesheet
        self.setStyleSheet(build_stylesheet(get_current_theme()))