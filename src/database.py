"""
JRGS - 재와니의 레트로 게임 보관소
database.py - SQLite DB 초기화 및 관리
"""

import sqlite3
import os
from pathlib import Path


def get_db_path():
    """JRGS 실행 폴더 기준 DB 경로 반환"""
    base = Path(__file__).resolve().parent.parent
    return base / "jrgs.db"


def get_connection():
    """DB 연결 반환"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """DB 테이블 초기화 (최초 실행 시)"""
    conn = get_connection()
    cur = conn.cursor()

    # 플랫폼 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS platforms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            short_name  TEXT NOT NULL UNIQUE,
            extensions  TEXT NOT NULL,
            icon_path   TEXT,
            tab_order   INTEGER DEFAULT 0,
            is_visible  INTEGER DEFAULT 1,
            display_name TEXT
        )
    """)

    # 에뮬레이터 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS emulators (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_id INTEGER NOT NULL,
            name        TEXT NOT NULL,
            exe_path    TEXT NOT NULL,
            args        TEXT DEFAULT '',
            is_default  INTEGER DEFAULT 0,
            FOREIGN KEY (platform_id) REFERENCES platforms(id)
        )
    """)

    # 게임 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_id     INTEGER NOT NULL,
            rom_path        TEXT NOT NULL UNIQUE,
            title_kr        TEXT DEFAULT '',
            title_en        TEXT DEFAULT '',
            genre           TEXT DEFAULT '',
            developer       TEXT DEFAULT '',
            publisher       TEXT DEFAULT '',
            release_year    INTEGER,
            release_region  TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            rating          TEXT DEFAULT '',
            is_missing      INTEGER DEFAULT 0,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (platform_id) REFERENCES platforms(id)
        )
    """)

    # 게임 메타데이터 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_meta (
            game_id             INTEGER PRIMARY KEY,
            cover_path          TEXT DEFAULT '',
            package_path        TEXT DEFAULT '',
            icon_path           TEXT DEFAULT '',
            tips                TEXT DEFAULT '',
            emulator_id         INTEGER,
            youtube_url         TEXT DEFAULT '',
            youtube_auto        INTEGER DEFAULT 1,
            youtube_updated_at  DATETIME,
            youtube_links       TEXT DEFAULT '',
            youtube_desc        TEXT DEFAULT '',
            ocr_enabled         INTEGER DEFAULT 0,
            ocr_mode            TEXT DEFAULT 'screenshot',
            ocr_translate_api   TEXT DEFAULT 'google',
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            FOREIGN KEY (emulator_id) REFERENCES emulators(id)
        )
    """)

    # 플레이 기록 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS play_history (
            game_id             INTEGER PRIMARY KEY,
            last_played         DATETIME,
            play_count          INTEGER DEFAULT 0,
            total_playtime_sec  INTEGER DEFAULT 0,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)

    # 즐겨찾기 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            game_id     INTEGER PRIMARY KEY,
            added_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)

    # 스크린샷 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS screenshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id     INTEGER NOT NULL,
            file_path   TEXT NOT NULL,
            captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            memo        TEXT DEFAULT '',
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)

    # 플랫폼별 다중 ROM 폴더 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS platform_rom_folders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            short_name  TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            UNIQUE(short_name, folder_path)
        )
    """)

    # 설정 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key     TEXT PRIMARY KEY,
            value   TEXT
        )
    """)

    # 기본 플랫폼 데이터 삽입 (출시연도 기준 순서)
    platforms = [
        ("Famicom",           "FC",   ".nes",              0),
        ("Super Famicom",     "SFC",  ".smc .sfc",         1),
        ("Game Boy",          "GB",   ".gb .gbc",          2),
        ("Game Boy Advance",  "GBA",  ".gba",              3),
        ("PC Engine",         "PCE",  ".pce .cue .iso",    4),
        ("Sega Master System","SMS",  ".sms",              5),
        ("Mega Drive",        "MD",   ".md .gen .bin",     6),
        ("Mega Drive CD",     "MDCD", ".iso .cue .bin",    7),
        ("WonderSwan",        "WS",   ".ws .wsc",          8),
        ("Nintendo DS",       "NDS",  ".nds",              9),
        ("MSX",               "MSX",  ".rom .dsk",         10),
        ("PlayStation 1",     "PS1",  ".iso .bin .cue",    11),
        ("PlayStation 2",     "PS2",  ".iso .bin",         12),
        ("GP32",              "GP32", ".gxb .smc",         13),
    ]

    for name, short, exts, order in platforms:
        cur.execute("""
            INSERT OR IGNORE INTO platforms (name, short_name, extensions, tab_order, display_name)
            VALUES (?, ?, ?, ?, ?)
        """, (name, short, exts, order, name))

    # GP32, PS1, PS2 기본 숨김 처리
    for short in ('GP32', 'PS1', 'PS2', 'MSX'):
        cur.execute("UPDATE platforms SET is_visible=0 WHERE short_name=?", (short,))

    # 탭 순서 강제 동기화 (출시연도 기준)
    order_map = {
        'FC': 0, 'SFC': 1, 'GB': 2, 'GBA': 3, 'PCE': 4,
        'SMS': 5, 'MD': 6, 'MDCD': 7, 'WS': 8, 'NDS': 9,
        'MSX': 10, 'PS1': 11, 'PS2': 12, 'GP32': 13
    }
    for short, order in order_map.items():
        cur.execute("UPDATE platforms SET tab_order=? WHERE short_name=?", (order, short))

    # 기본 설정값 삽입
    defaults = [
        ("language",            "ko"),
        ("auto_scan_on_start",  "1"),
        ("minimize_on_launch",  "1"),
        ("window_width",        "1280"),
        ("window_height",       "800"),
        ("grid_view_mode",      "small"),  # name / small / large
        ("grid_icon_size",      "80"),
        ("default_youtube_channel", "https://www.youtube.com/@jewani1004"),
        ("blog_url",            "https://blog.naver.com/akrsodhk"),
        ("translate_api",       "google"),
        ("screenshot_folder",   ""),
        ("record_folder",       ""),
        ("mobygames_api_key",   ""),
        ("thegamesdb_api_key",  ""),
        ("igdb_api_key",        ""),
        ("youtube_api_key",     ""),
        ("deepl_api_key",       ""),
    ]

    for key, val in defaults:
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    # 마이그레이션: 기존 DB에 신규 컬럼 추가
    migrations = [
        ("ALTER TABLE game_meta ADD COLUMN youtube_links TEXT DEFAULT ''"),
        ("ALTER TABLE game_meta ADD COLUMN youtube_desc TEXT DEFAULT ''"),
        ("ALTER TABLE screenshots ADD COLUMN memo TEXT DEFAULT ''"),
    ]
    for sql in migrations:
        try:
            cur.execute(sql)
        except Exception:
            pass  # 이미 컬럼 존재 시 무시

    conn.commit()
    conn.close()
    print("[DB] 초기화 완료")


def get_setting(key: str, default=None):
    """설정값 가져오기"""
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """설정값 저장"""
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_all_platforms():
    """전체 플랫폼 목록 반환 (탭 순서대로)"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM platforms ORDER BY tab_order ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_games_by_platform(platform_id: int):
    """플랫폼별 게임 목록 반환"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT g.*, m.cover_path, m.icon_path, 
               ph.play_count, ph.last_played,
               CASE WHEN f.game_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite,
               p.short_name
        FROM games g
        LEFT JOIN game_meta m ON g.id = m.game_id
        LEFT JOIN play_history ph ON g.id = ph.game_id
        LEFT JOIN favorites f ON g.id = f.game_id
        LEFT JOIN platforms p ON g.platform_id = p.id
        WHERE g.platform_id = ?
        ORDER BY COALESCE(g.title_kr, g.title_en, g.rom_path) ASC
    """, (platform_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_favorite_games():
    """즐겨찾기 게임 목록 반환"""
    conn = get_connection()
    rows = conn.execute("""
        SELECT g.*, m.cover_path, m.icon_path,
               p.short_name,
               ph.play_count, ph.last_played
        FROM favorites f
        JOIN games g ON f.game_id = g.id
        LEFT JOIN game_meta m ON g.id = m.game_id
        LEFT JOIN play_history ph ON g.id = ph.game_id
        JOIN platforms p ON g.platform_id = p.id
        ORDER BY f.added_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_game_detail(game_id: int):
    """게임 상세 정보 반환"""
    conn = get_connection()
    row = conn.execute("""
        SELECT g.*, m.*, p.name as platform_name, p.short_name,
               ph.play_count, ph.last_played, ph.total_playtime_sec,
               CASE WHEN f.game_id IS NOT NULL THEN 1 ELSE 0 END as is_favorite,
               e.name as emulator_name, e.exe_path as emulator_path
        FROM games g
        LEFT JOIN game_meta m ON g.id = m.game_id
        LEFT JOIN platforms p ON g.platform_id = p.id
        LEFT JOIN play_history ph ON g.id = ph.game_id
        LEFT JOIN favorites f ON g.id = f.game_id
        LEFT JOIN emulators e ON m.emulator_id = e.id
        WHERE g.id = ?
    """, (game_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_game(platform_id: int, rom_path: str, title_kr="", title_en="", conn=None):
    """게임 추가 (conn 전달 시 외부 connection 재사용, commit/close 안 함)"""
    _external_conn = conn is not None
    if not _external_conn:
        conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO games (platform_id, rom_path, title_kr, title_en)
            VALUES (?, ?, ?, ?)
        """, (platform_id, rom_path, title_kr, title_en))
        game_id = cur.lastrowid

        if game_id:
            cur.execute("INSERT OR IGNORE INTO game_meta (game_id) VALUES (?)", (game_id,))
            cur.execute("INSERT OR IGNORE INTO play_history (game_id) VALUES (?)", (game_id,))

        if not _external_conn:
            conn.commit()
        return game_id
    except Exception as e:
        if not _external_conn:
            conn.rollback()
        print(f"[DB] 게임 추가 오류: {e}")
        return None
    finally:
        if not _external_conn:
            conn.close()


def update_game(game_id: int, **kwargs):
    """게임 정보 업데이트"""
    if not kwargs:
        return

    game_fields = {"title_kr", "title_en", "genre", "developer", "publisher",
                   "release_year", "release_region", "description", "rating"}
    meta_fields = {"cover_path", "package_path", "icon_path", "tips", "emulator_id",
                   "youtube_url", "youtube_auto", "ocr_enabled", "ocr_mode", "ocr_translate_api",
                   "youtube_links", "youtube_desc"}

    game_data = {k: v for k, v in kwargs.items() if k in game_fields}
    meta_data = {k: v for k, v in kwargs.items() if k in meta_fields}

    conn = get_connection()
    try:
        if game_data:
            sets = ", ".join(f"{k}=?" for k in game_data)
            conn.execute(f"UPDATE games SET {sets} WHERE id=?",
                         (*game_data.values(), game_id))
        if meta_data:
            sets = ", ".join(f"{k}=?" for k in meta_data)
            conn.execute(f"UPDATE game_meta SET {sets} WHERE game_id=?",
                         (*meta_data.values(), game_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB] 게임 업데이트 오류: {e}")
    finally:
        conn.close()


def toggle_favorite(game_id: int):
    """즐겨찾기 토글"""
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM favorites WHERE game_id=?", (game_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM favorites WHERE game_id=?", (game_id,))
        result = False
    else:
        conn.execute("INSERT INTO favorites (game_id) VALUES (?)", (game_id,))
        result = True
    conn.commit()
    conn.close()
    return result

def delete_game(game_id: int):
    """게임 목록에서 제거 (ROM 파일은 삭제하지 않음)"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM game_meta WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM play_history WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM favorites WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM screenshots WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB] 게임 삭제 오류: {e}")
    finally:
        conn.close()

def update_play_history(game_id: int, playtime_sec: int):
    """플레이 기록 업데이트"""
    conn = get_connection()
    conn.execute("""
        INSERT INTO play_history (game_id, last_played, play_count, total_playtime_sec)
        VALUES (?, CURRENT_TIMESTAMP, 1, ?)
        ON CONFLICT(game_id) DO UPDATE SET
            last_played = CURRENT_TIMESTAMP,
            play_count = play_count + 1,
            total_playtime_sec = total_playtime_sec + ?
    """, (game_id, playtime_sec, playtime_sec))
    conn.commit()
    conn.close()

def get_platform_rom_folders(short_name: str) -> list:
    """플랫폼별 ROM 폴더 목록 반환"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT folder_path FROM platform_rom_folders WHERE short_name=? ORDER BY id ASC",
        (short_name,)
    ).fetchall()
    conn.close()
    return [r["folder_path"] for r in rows]


def add_platform_rom_folder(short_name: str, folder_path: str):
    """플랫폼별 ROM 폴더 추가"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO platform_rom_folders (short_name, folder_path) VALUES (?, ?)",
            (short_name, folder_path)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] 폴더 추가 오류: {e}")
    finally:
        conn.close()

def remove_platform_rom_folder(short_name: str, folder_path: str):
    """플랫폼별 ROM 폴더 제거"""
    conn = get_connection()
    conn.execute(
        "DELETE FROM platform_rom_folders WHERE short_name=? AND folder_path=?",
        (short_name, folder_path)
    )
    conn.commit()
    conn.close()


def update_platform_tab(short_name: str, is_visible: int, tab_order: int, display_name: str):
    """플랫폼 탭 표시/순서/이름 업데이트"""
    conn = get_connection()
    conn.execute("""
        UPDATE platforms SET is_visible=?, tab_order=?, display_name=?
        WHERE short_name=?
    """, (is_visible, tab_order, display_name, short_name))
    conn.commit()
    conn.close()