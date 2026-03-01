"""
JRGS - 재와니의 레트로 게임 보관소
folders.py - 폴더 구조 생성 및 ROM 스캔
"""

import os
import re
from pathlib import Path
from database import get_connection, get_all_platforms, add_game, get_setting, set_setting


# 플랫폼별 기본 ROM 폴더명 매핑
PLATFORM_FOLDERS = {
    "FC":   "Famicom_ROM",
    "SFC":  "SFC_ROM",
    "GB":   "GB_ROM",
    "GBA":  "GBA_ROM",
    "PCE":  "PCEngine_ROM",
    "SMS":  "SMS_ROM",
    "MD":   "MegaDrive_ROM",
    "MDCD": "MegaDriveCD_ROM",
    "WS":   "WonderSwan_ROM",
    "NDS":  "NDS_ROM",
    "MSX":  "MSX_ROM",
    "PS1":  "PS1_ROM",
    "PS2":  "PS2_ROM",
    "GP32": "GP32_ROM",
}


def get_base_path():
    """JRGS 루트 폴더 경로"""
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller 빌드 환경: EXE 파일 위치 기준
        return Path(sys.executable).resolve().parent
    else:
        # 개발 환경: src/ 의 상위 폴더
        return Path(__file__).resolve().parent.parent


def get_rom_root():
    """ROM 루트 폴더 경로 (설정 또는 기본값)"""
    custom = get_setting("rom_root_folder", "")
    if custom and Path(custom).exists():
        return Path(custom)
    return get_base_path() / "ROM_File"


def get_platform_rom_folder(short_name: str) -> Path:
    """플랫폼별 개별 ROM 폴더 경로 (설정 또는 기본값)"""
    custom = get_setting(f"rom_folder_{short_name}", "")
    if custom and Path(custom).exists():
        return Path(custom)
    return get_rom_root() / PLATFORM_FOLDERS.get(short_name, short_name + "_ROM")


def set_platform_rom_folder(short_name: str, path: str):
    """플랫폼별 ROM 폴더 경로 저장"""
    set_setting(f"rom_folder_{short_name}", path)


def get_gamedata_root():
    """GameData 폴더 경로"""
    return get_base_path() / "GameData"


def get_screenshot_folder():
    """스크린샷 저장 폴더"""
    custom = get_setting("screenshot_folder", "")
    if custom:
        return Path(custom)
    return get_base_path() / "Screenshots"


def get_record_folder():
    """녹화 저장 폴더"""
    custom = get_setting("record_folder", "")
    if custom:
        return Path(custom)
    return get_base_path() / "Records"


def init_folders():
    """최초 실행 시 기본 폴더 구조 생성"""
    base = get_base_path()
    rom_root = get_rom_root()
    gamedata = get_gamedata_root()

    # ROM 플랫폼별 기본 폴더 생성
    for folder_name in PLATFORM_FOLDERS.values():
        (rom_root / folder_name).mkdir(parents=True, exist_ok=True)

    # GameData 폴더 생성
    gamedata.mkdir(parents=True, exist_ok=True)

    # Emulators 폴더 생성
    (base / "Emulators").mkdir(exist_ok=True)
    (base / "Emulators" / "Mesen").mkdir(exist_ok=True)
    (base / "Emulators" / "Fusion").mkdir(exist_ok=True)
    (base / "Emulators" / "DeSmuME").mkdir(exist_ok=True)
    (base / "Emulators" / "Oswan").mkdir(exist_ok=True)
    (base / "Emulators" / "MSX").mkdir(exist_ok=True)

    # 플랫폼 기본 아이콘 폴더 생성
    (base / "ICON").mkdir(exist_ok=True)

    # 스크린샷/녹화 폴더 생성
    get_screenshot_folder().mkdir(parents=True, exist_ok=True)
    get_record_folder().mkdir(parents=True, exist_ok=True)

    print(f"[폴더] 기본 구조 생성 완료: {base}")


def get_platform_extensions():
    """플랫폼별 확장자 딕셔너리 반환 {'.nes': platform_id, ...}"""
    platforms = get_all_platforms()
    ext_map = {}
    for p in platforms:
        for ext in p["extensions"].split():
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = "." + ext
            ext_map[ext] = p["id"]
    return ext_map

def scan_rom_folder(progress_callback=None, platform_short: str = None):
    """ROM 폴더 전체 스캔 후 DB에 등록 (connection 1개로 처리)"""
    ext_map = get_platform_extensions()
    platforms = {p["short_name"]: p["id"] for p in get_all_platforms()}

    added = 0
    skipped = 0
    missing = 0
    total_files = []

    scan_targets = [platform_short] if platform_short else list(PLATFORM_FOLDERS.keys())

    from database import get_platform_rom_folders
    for short_name in scan_targets:
        platform_id = platforms.get(short_name)
        if not platform_id:
            continue

        folder_paths = get_platform_rom_folders(short_name)
        default = get_platform_rom_folder(short_name)
        all_paths = list(dict.fromkeys([str(default)] + folder_paths))

        for folder_str in all_paths:
            folder = Path(folder_str)
            if not folder.exists():
                continue
            for f in folder.rglob("*"):
                if f.is_file():
                    total_files.append((f, platform_id, short_name))

    total = len(total_files)

    # connection 하나로 전체 스캔 처리
    conn = get_connection()
    try:
        for i, (f, platform_id, short_name) in enumerate(total_files):
            ext = f.suffix.lower()
            if ext not in ext_map:
                skipped += 1
                if progress_callback:
                    progress_callback(i + 1, total, f.name)
                continue

            rom_path = str(f)
            title = f.stem
            clean_title = re.sub(r'\s*[\(\[（【][^\)\]）】]*[\)\]）】]', '', title).strip()

            try:
                game_id = add_game(platform_id, rom_path, title_en=clean_title, conn=conn)
                if game_id:
                    added += 1
                    _auto_link_cover_conn(game_id, short_name, f.stem, clean_title, conn)
                else:
                    skipped += 1
            except Exception as e:
                print(f"[스캔] 파일 처리 오류: {f.name} - {e}")
                skipped += 1

            if progress_callback:
                progress_callback(i + 1, total, f.name)

        # 100건마다 중간 commit
        conn.commit()

        # 삭제된 ROM 감지
        all_games = conn.execute("SELECT id, rom_path FROM games WHERE is_missing=0").fetchall()
        for game in all_games:
            if not Path(game["rom_path"]).exists():
                conn.execute("UPDATE games SET is_missing=1 WHERE id=?", (game["id"],))
                missing += 1
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"[스캔] 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

    result = {"added": added, "skipped": skipped, "missing": missing, "total": total}
    print(f"[스캔] 완료 - 추가: {added}, 건너뜀: {skipped}, 누락: {missing}")
    return result

IMG_EXTS = [".png", ".jpg", ".jpeg", ".bmp", ".webp"]

def _auto_link_cover(game_id: int, platform_short: str, rom_stem: str, clean_title: str):
    """커버아트 폴더에서 ROM명/제목과 일치하는 이미지를 찾아 자동 연결"""
    cover_folder = get_setting(f"cover_art_folder_{platform_short}", "")
    if not cover_folder:
        return

    cover_dir = Path(cover_folder)
    if not cover_dir.exists():
        return

    # 이미 커버아트 있으면 스킵
    conn = get_connection()
    row = conn.execute(
        "SELECT cover_path FROM game_meta WHERE game_id=?", (game_id,)
    ).fetchone()
    conn.close()
    if row and row["cover_path"] and Path(row["cover_path"]).exists():
        return

    # 검색 후보: ROM 파일명 → 정리된 제목 순
    candidates = list(dict.fromkeys(filter(None, [rom_stem, clean_title])))
    found = None
    for name in candidates:
        for ext in IMG_EXTS:
            p = cover_dir / f"{name}{ext}"
            if p.exists():
                found = p
                break
        if found:
            break

    if not found:
        return

    # GameData에 복사 후 DB 저장
    import shutil
    save_dir = get_gamedata_path(platform_short, clean_title)
    dest = save_dir / f"cover{found.suffix}"
    try:
        shutil.copy2(str(found), str(dest))
        conn = get_connection()
        conn.execute(
            "UPDATE game_meta SET cover_path=? WHERE game_id=?",
            (str(dest), game_id)
        )
        conn.commit()
        conn.close()
        print(f"[커버아트] 자동 연결: {found.name} → {clean_title}")
    except Exception as e:
        print(f"[커버아트] 자동 연결 실패: {e}")

def _auto_link_cover_conn(game_id: int, platform_short: str, rom_stem: str, clean_title: str, conn):
    """커버아트 자동 연결 - 외부 connection 재사용 버전"""
    cover_folder = get_setting(f"cover_art_folder_{platform_short}", "")
    if not cover_folder:
        return

    cover_dir = Path(cover_folder)
    if not cover_dir.exists():
        return

    row = conn.execute(
        "SELECT cover_path FROM game_meta WHERE game_id=?", (game_id,)
    ).fetchone()
    if row and row["cover_path"] and Path(row["cover_path"]).exists():
        return

    candidates = list(dict.fromkeys(filter(None, [rom_stem, clean_title])))
    found = None
    for name in candidates:
        for ext in IMG_EXTS:
            p = cover_dir / f"{name}{ext}"
            if p.exists():
                found = p
                break
        if found:
            break

    if not found:
        return

    import shutil
    save_dir = get_gamedata_path(platform_short, clean_title)
    dest = save_dir / f"cover{found.suffix}"
    try:
        shutil.copy2(str(found), str(dest))
        conn.execute(
            "UPDATE game_meta SET cover_path=? WHERE game_id=?",
            (str(dest), game_id)
        )
        print(f"[커버아트] 자동 연결: {found.name} → {clean_title}")
    except Exception as e:
        print(f"[커버아트] 자동 연결 실패: {e}")

def get_gamedata_path(platform_short: str, game_title: str):
    """게임별 GameData 경로 반환 (없으면 생성)"""
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', game_title)[:50]
    path = get_gamedata_root() / platform_short / safe_title
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_savestate_path(platform_short: str, game_title: str):
    """세이브스테이트 저장 경로"""
    path = get_gamedata_path(platform_short, game_title) / "savestate"
    path.mkdir(exist_ok=True)
    return path


def auto_register_mesen():
    """Mesen 에뮬레이터 자동 등록 (Emulators/Mesen/Mesen.exe 존재 시)"""
    mesen_exe = get_base_path() / "Emulators" / "Mesen" / "Mesen.exe"
    if not mesen_exe.exists():
        return

    from database import get_connection
    mesen_platforms = ["FC", "SFC", "GB", "GBA", "PCE"]

    conn = get_connection()
    platforms = {p["short_name"]: p["id"] for p in conn.execute("SELECT * FROM platforms").fetchall()}

    for short in mesen_platforms:
        platform_id = platforms.get(short)
        if not platform_id:
            continue
        existing = conn.execute(
            "SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)
        ).fetchone()
        if existing["cnt"] > 0:
            continue
        conn.execute("""
            INSERT INTO emulators (platform_id, name, exe_path, args, is_default)
            VALUES (?, 'Mesen', ?, '', 1)
        """, (platform_id, str(mesen_exe)))
        print(f"[Mesen] {short} 자동 등록 완료")

    conn.commit()
    conn.close()

def auto_register_fusion():
    """Fusion 에뮬레이터 자동 등록 (Emulators/Fusion/Fusion.exe 존재 시 MD, SMS 자동 등록)"""
    fusion_exe = get_base_path() / "Emulators" / "Fusion" / "Fusion.exe"
    if not fusion_exe.exists():
        return

    from database import get_connection
    fusion_platforms = ["MD", "SMS", "MDCD"]

    conn = get_connection()
    platforms = {p["short_name"]: p["id"] for p in conn.execute("SELECT * FROM platforms").fetchall()}

    for short in fusion_platforms:
        platform_id = platforms.get(short)
        if not platform_id:
            continue
        existing = conn.execute(
            "SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)
        ).fetchone()
        if existing["cnt"] > 0:
            continue
        conn.execute("""
            INSERT INTO emulators (platform_id, name, exe_path, args, is_default)
            VALUES (?, 'Fusion', ?, '', 1)
        """, (platform_id, str(fusion_exe)))
        print(f"[Fusion] {short} 자동 등록 완료")

    conn.commit()
    conn.close()

def auto_register_desmume():
    """DeSmuME 에뮬레이터 자동 등록 (Emulators/DeSmuME/DeSmuME_0.9.13_x64[K].exe 존재 시)"""
    exe = get_base_path() / "Emulators" / "DeSmuME" / "DeSmuME_0.9.13_x64[K].exe"
    if not exe.exists():
        return

    from database import get_connection
    conn = get_connection()
    platforms = {p["short_name"]: p["id"] for p in conn.execute("SELECT * FROM platforms").fetchall()}
    platform_id = platforms.get("NDS")
    if not platform_id:
        conn.close()
        return
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)
    ).fetchone()
    if existing["cnt"] == 0:
        conn.execute("""
            INSERT INTO emulators (platform_id, name, exe_path, args, is_default)
            VALUES (?, 'DeSmuME', ?, '', 1)
        """, (platform_id, str(exe)))
        print(f"[DeSmuME] NDS 자동 등록 완료")
    conn.commit()
    conn.close()


def auto_register_oswan():
    """Oswan 에뮬레이터 자동 등록 (Emulators/Oswan/Oswan.exe 존재 시)"""
    exe = get_base_path() / "Emulators" / "Oswan" / "Oswan.exe"
    if not exe.exists():
        return

    from database import get_connection
    conn = get_connection()
    platforms = {p["short_name"]: p["id"] for p in conn.execute("SELECT * FROM platforms").fetchall()}
    platform_id = platforms.get("WS")
    if not platform_id:
        conn.close()
        return
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)
    ).fetchone()
    if existing["cnt"] == 0:
        conn.execute("""
            INSERT INTO emulators (platform_id, name, exe_path, args, is_default)
            VALUES (?, 'Oswan', ?, '', 1)
        """, (platform_id, str(exe)))
        print(f"[Oswan] WonderSwan 자동 등록 완료")
    conn.commit()
    conn.close()


def auto_register_bluemsx():
    """blueMSX 에뮬레이터 자동 등록 (Emulators/MSX/blueMSX.exe 존재 시)"""
    exe = get_base_path() / "Emulators" / "MSX" / "blueMSX.exe"
    if not exe.exists():
        return

    from database import get_connection
    conn = get_connection()
    platforms = {p["short_name"]: p["id"] for p in conn.execute("SELECT * FROM platforms").fetchall()}
    platform_id = platforms.get("MSX")
    if not platform_id:
        conn.close()
        return
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM emulators WHERE platform_id=?", (platform_id,)
    ).fetchone()
    if existing["cnt"] == 0:
        conn.execute("""
            INSERT INTO emulators (platform_id, name, exe_path, args, is_default)
            VALUES (?, 'blueMSX', ?, '', 1)
        """, (platform_id, str(exe)))
        print(f"[blueMSX] MSX 자동 등록 완료")
    conn.commit()
    conn.close()