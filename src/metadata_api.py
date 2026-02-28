# metadata_api.py - 수정 후
"""
JRGS - 재와니의 레트로 게임 보관소
metadata_api.py - 메타데이터 자동검색 (ScreenScraper → TheGamesDB → MobyGames 폴백)
"""

import requests
from database import get_setting

# ── ScreenScraper 시스템 ID ──────────────────────────────
SCREENSCRAPER_SYSTEM_MAP = {
    "FC":   "3",   "SFC":  "4",   "GB":   "9",   "GBA":  "12",
    "GBC":  "10",  "PCE":  "31",  "SMS":  "2",   "MD":   "1",
    "MDCD": "20",  "WS":   "45",  "NDS":  "15",  "MSX":  "13",
    "PS1":  "57",  "PS2":  "58",  "GP32": None,
}

# ── TheGamesDB 플랫폼 ID ─────────────────────────────────
THEGAMESDB_PLATFORM_MAP = {
    "FC":   "7",   "SFC":  "6",   "GB":   "4",   "GBA":  "5",
    "GBC":  "41",  "PCE":  "34",  "SMS":  "35",  "MD":   "36",
    "MDCD": "21",  "NDS":  "8",   "MSX":  "press",  "PS1": "10",
    "PS2":  "11",  "WS":   "57",
}

# ── MobyGames 플랫폼 ID ──────────────────────────────────
MOBYGAMES_PLATFORM_MAP = {
    "FC":   "22",  "SFC":  "15",  "GB":   "10",  "GBA":  "12",
    "GBC":  "11",  "PCE":  "40",  "SMS":  "26",  "MD":   "16",
    "MDCD": "20",  "NDS":  "44",  "MSX":  "57",  "PS1":  "6",
    "PS2":  "7",   "WS":   "98",
}

SS_BASE_URL  = "https://www.screenscraper.fr/api2/jeuInfos.php"
TDB_BASE_URL = "https://api.thegamesdb.net/v1"
MBG_BASE_URL = "https://api.mobygames.com/v1"
SS_SOFTNAME  = "JRGS"


# ════════════════════════════════════════════════════════
#  공개 진입점
# ════════════════════════════════════════════════════════

def search_metadata(title: str, platform_short: str, romnom: str = ""):
    """
    ScreenScraper → TheGamesDB → MobyGames 순으로 폴백 검색.
    반환값: dict or None
    """
    # 1순위: ScreenScraper
    result = _search_screenscraper(title, platform_short, romnom)
    if result:
        print(f"[메타데이터] ScreenScraper 성공: {title}")
        return result

    # 2순위: TheGamesDB
    result = _search_thegamesdb(title, platform_short)
    if result:
        print(f"[메타데이터] TheGamesDB 성공: {title}")
        return result

    # 3순위: MobyGames
    result = _search_mobygames(title, platform_short)
    if result:
        print(f"[메타데이터] MobyGames 성공: {title}")
        return result

    print(f"[메타데이터] 모든 API 검색 실패: {title}")
    return None


def download_cover(url: str, save_path: str) -> bool:
    """커버아트 URL에서 이미지 다운로드"""
    try:
        resp = requests.get(url, timeout=15, stream=True)
        if resp.status_code != 200:
            return False
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(f"[커버아트] 다운로드 완료: {save_path}")
        return True
    except Exception as e:
        print(f"[커버아트] 다운로드 실패: {e}")
        return False


# ════════════════════════════════════════════════════════
#  ScreenScraper
# ════════════════════════════════════════════════════════

def _search_screenscraper(title: str, platform_short: str, romnom: str = ""):
    userid = get_setting("ss_user_id", "")
    userpw = get_setting("ss_user_password", "")
    if not userid or not userpw:
        print("[ScreenScraper] 계정 정보 없음 — 스킵")
        return None

    devid  = get_setting("ss_dev_id", "")
    devpw  = get_setting("ss_dev_password", "")
    system_id = SCREENSCRAPER_SYSTEM_MAP.get(platform_short, "")

    params = {
        "softname":   SS_SOFTNAME,
        "output":     "json",
        "ssid":       userid,
        "sspassword": userpw,
        "romnom":     romnom or title,
    }
    if devid:
        params["devid"]      = devid
        params["devpassword"] = devpw
    if system_id:
        params["systemeid"] = system_id

    try:
        resp = requests.get(SS_BASE_URL, params=params, timeout=15)
        if resp.status_code == 404:
            print(f"[ScreenScraper] 결과 없음: {title}")
            return None
        if resp.status_code != 200:
            print(f"[ScreenScraper] HTTP {resp.status_code} — 다음 API로 폴백")
            return None
        game = resp.json().get("response", {}).get("jeu")
        if not game:
            return None
        return _parse_screenscraper(game)
    except Exception as e:
        print(f"[ScreenScraper] 오류: {e}")
        return None


def _parse_screenscraper(game: dict) -> dict:
    title_en = title_kr = ""
    for n in game.get("noms", []):
        r, t = n.get("region", ""), n.get("text", "")
        if r in ("us", "wor", "eu") and not title_en:
            title_en = t
        if r == "ko":
            title_kr = t
    if not title_en:
        noms = game.get("noms", [])
        title_en = noms[0].get("text", "") if noms else ""

    genre = ""
    for g in game.get("genres", []):
        for gn in g.get("noms", []):
            if gn.get("langue") == "en":
                genre = gn.get("text", "")
                break
        if genre:
            break

    developer = publisher = ""
    dev, pub = game.get("developpeur"), game.get("editeur")
    if isinstance(dev, dict):  developer = dev.get("text", "")
    elif isinstance(dev, list) and dev: developer = dev[0].get("text", "")
    if isinstance(pub, dict):  publisher = pub.get("text", "")
    elif isinstance(pub, list) and pub: publisher = pub[0].get("text", "")

    release_year = None
    release_region = ""
    for d in game.get("dates", []):
        s = d.get("text", "")
        if s and len(s) >= 4:
            try: release_year = int(s[:4])
            except ValueError: pass
        r = d.get("region", "")
        if r in ("jp", "us", "wor", "eu"):
            release_region = r.upper()
        break

    description = ""
    for s in game.get("synopsis", []):
        if s.get("langue") == "en":
            description = s.get("text", "")
            break
    if not description:
        synops = game.get("synopsis", [])
        description = synops[0].get("text", "") if synops else ""

    cover_url = ""
    for m in game.get("medias", []):
        if m.get("type") in ("box-2D", "box-2D-side") and m.get("url"):
            cover_url = m["url"]
            break
    if not cover_url:
        for m in game.get("medias", []):
            if m.get("url"):
                cover_url = m["url"]
                break

    return dict(title_en=title_en, title_kr=title_kr, genre=genre,
                developer=developer, publisher=publisher,
                release_year=release_year, release_region=release_region,
                description=description, cover_url=cover_url)


# ════════════════════════════════════════════════════════
#  TheGamesDB
# ════════════════════════════════════════════════════════

def _search_thegamesdb(title: str, platform_short: str):
    api_key = get_setting("tgdb_api_key", "")
    if not api_key:
        print("[TheGamesDB] API 키 없음 — 스킵")
        return None

    platform_id = THEGAMESDB_PLATFORM_MAP.get(platform_short, "")
    params = {
        "apikey":   api_key,
        "name":     title,
        "fields":   "genres,developers,publishers,overview,rating",
        "include":  "boxart",
    }
    if platform_id:
        params["filter[platform]"] = platform_id

    try:
        resp = requests.get(f"{TDB_BASE_URL}/Games/ByGameName", params=params, timeout=15)
        if resp.status_code != 200:
            print(f"[TheGamesDB] HTTP {resp.status_code}")
            return None
        data = resp.json()
        games = data.get("data", {}).get("games", [])
        if not games:
            print(f"[TheGamesDB] 결과 없음: {title}")
            return None
        return _parse_thegamesdb(games[0], data)
    except Exception as e:
        print(f"[TheGamesDB] 오류: {e}")
        return None


def _parse_thegamesdb(game: dict, full_data: dict) -> dict:
    title_en = game.get("game_title", "")

    release_date = game.get("release_date", "")
    release_year = None
    if release_date and len(release_date) >= 4:
        try: release_year = int(release_date[:4])
        except ValueError: pass

    # 장르
    genre = ""
    genre_ids = game.get("genres", [])
    genres_map = full_data.get("include", {}).get("genres", {}).get("data", {})
    if genre_ids and genres_map:
        genre = genres_map.get(str(genre_ids[0]), {}).get("genre", "")

    # 개발사
    developer = ""
    dev_ids = game.get("developers", [])
    devs_map = full_data.get("include", {}).get("developers", {}).get("data", {})
    if dev_ids and devs_map:
        developer = devs_map.get(str(dev_ids[0]), {}).get("name", "")

    # 퍼블리셔
    publisher = ""
    pub_ids = game.get("publishers", [])
    pubs_map = full_data.get("include", {}).get("publishers", {}).get("data", {})
    if pub_ids and pubs_map:
        publisher = pubs_map.get(str(pub_ids[0]), {}).get("name", "")

    # 커버아트
    cover_url = ""
    boxart = full_data.get("include", {}).get("boxart", {})
    base_url = boxart.get("base_url", {}).get("original", "")
    game_id  = str(game.get("id", ""))
    images   = boxart.get("data", {}).get(game_id, [])
    for img in images:
        if img.get("side") == "front":
            cover_url = base_url + img.get("filename", "")
            break
    if not cover_url and images:
        cover_url = base_url + images[0].get("filename", "")

    return dict(title_en=title_en, title_kr="", genre=genre,
                developer=developer, publisher=publisher,
                release_year=release_year, release_region="",
                description=game.get("overview", ""), cover_url=cover_url)


# ════════════════════════════════════════════════════════
#  MobyGames
# ════════════════════════════════════════════════════════

def _search_mobygames(title: str, platform_short: str):
    api_key = get_setting("mobygames_api_key", "")
    if not api_key:
        print("[MobyGames] API 키 없음 — 스킵")
        return None

    platform_id = MOBYGAMES_PLATFORM_MAP.get(platform_short, "")
    params = {"api_key": api_key, "title": title, "limit": 1}
    if platform_id:
        params["platform"] = platform_id

    try:
        resp = requests.get(f"{MBG_BASE_URL}/games", params=params, timeout=15)
        if resp.status_code != 200:
            print(f"[MobyGames] HTTP {resp.status_code}")
            return None
        games = resp.json().get("games", [])
        if not games:
            print(f"[MobyGames] 결과 없음: {title}")
            return None

        game = games[0]
        game_id = game.get("game_id")

        # 상세 정보 추가 요청
        detail_resp = requests.get(
            f"{MBG_BASE_URL}/games/{game_id}",
            params={"api_key": api_key},
            timeout=15
        )
        detail = detail_resp.json() if detail_resp.status_code == 200 else {}
        return _parse_mobygames(game, detail)
    except Exception as e:
        print(f"[MobyGames] 오류: {e}")
        return None


def _parse_mobygames(game: dict, detail: dict) -> dict:
    title_en = game.get("title", "")

    # 장르
    genre = ""
    genres = detail.get("genres", [])
    if genres:
        genre = genres[0].get("genre_name", "")

    # 개발사 / 퍼블리셔
    developer = publisher = ""
    for company in detail.get("involved_companies", []):
        role = company.get("role", "")
        name = company.get("company", {}).get("company_name", "")
        if "developer" in role.lower() and not developer:
            developer = name
        if "publisher" in role.lower() and not publisher:
            publisher = name

    # 출시연도
    release_year = None
    release_date = game.get("first_release_date", "")
    if release_date and len(release_date) >= 4:
        try: release_year = int(release_date[:4])
        except ValueError: pass

    # 커버아트
    cover_url = ""
    for cover in detail.get("cover_art", []):
        if cover.get("scan_of", "").lower() == "front cover":
            cover_url = cover.get("image", "")
            break
    if not cover_url:
        covers = detail.get("cover_art", [])
        if covers:
            cover_url = covers[0].get("image", "")

    description = detail.get("description", "")

    return dict(title_en=title_en, title_kr="", genre=genre,
                developer=developer, publisher=publisher,
                release_year=release_year, release_region="",
                description=description, cover_url=cover_url)