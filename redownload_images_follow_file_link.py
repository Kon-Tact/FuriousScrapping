# redownload_images_follow_file_link.py
import json
import csv
import os
import re
import time
import math
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, unquote, urljoin
import requests
from bs4 import BeautifulSoup

# ---------- Config ----------
BREEDS_JSON = "breeds_links.json"         # format: {"breeds":[{"id":1,"breed":"Affenpinscher","url":"https://..."}, ...]}
BREEDS_CSV  = "dog_breeds_structured.csv" # fallback si pas de JSON (colonnes: Nom,URL)
OUT_DIR     = Path("images")
REPORT_FILE = "download_report.json"

USER_AGENT   = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36 furious-scraper/1.1 +https://example.com")
TIMEOUT      = 25
MAX_RETRIES  = 2
PAUSE_SECONDS = 1.0
THUMB_SIZE    = 1200  # largeur souhaitée pour les vignettes (SVG surtout)

OVERWRITE     = True  # remplace les fichiers si déjà présents

# ---------- Session ----------
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fr,en;q=0.8"})

# ---------- Utils ----------
def norm_name_for_filename(name: str) -> str:
    s = re.sub(r"[^\w\-\s]", "", name, flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "breed"

def polite_sleep():
    time.sleep(PAUSE_SECONDS)

def safe_request(method, url, **kwargs):
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = session.request(method, url, timeout=TIMEOUT, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            polite_sleep()
    raise last

def api_endpoint(page_url: str) -> str:
    p = urlparse(page_url)
    return f"{p.scheme}://{p.netloc}/w/api.php"

def extract_title_from_url(page_url: str) -> str | None:
    m = re.search(r"/wiki/(.+)$", urlparse(page_url).path)
    return m.group(1) if m else None

def is_bad_placeholder(url: str) -> bool:
    # tente d'identifier les icônes & placeholders minuscules
    name = unquote(Path(urlparse(url).path).name)
    if re.search(r"(^|\D)\d{1,3}px-", name):  # 40px-, 64px-, 120px-
        return True
    if "Dog.svg" in name or "Placeholder" in name or "Question_book" in name:
        return True
    return False

# ---------- MediaWiki API: page -> image ----------
def fetch_image_via_page_api(page_url: str) -> tuple[str | None, str]:
    ep = api_endpoint(page_url)
    title = extract_title_from_url(page_url)
    if not title:
        return None, "no-title"
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "titles": title,
        "prop": "pageimages",
        "piprop": "original|thumbnail",
        "pithumbsize": THUMB_SIZE
    }
    try:
        r = safe_request("GET", ep, params=params)
        data = r.json()
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None, "api-no-pages"
        page = pages[0]
        # 1) original si dispo
        if "original" in page and page["original"].get("source"):
            url = page["original"]["source"]
            if not is_bad_placeholder(url):
                return url, "pageapi-original"
        # 2) sinon grande vignette
        if "thumbnail" in page and page["thumbnail"].get("source"):
            url = page["thumbnail"]["source"]
            if not is_bad_placeholder(url):
                return url, "pageapi-thumb"
        return None, "pageapi-no-image"
    except Exception as e:
        return None, f"pageapi-error:{e}"

# ---------- HTML parsing: trouver lien Fichier: depuis l'infobox ----------
def find_file_page_from_html(page_url: str) -> str | None:
    try:
        r = safe_request("GET", page_url)
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    # Cherche d'abord dans l'infobox
    infobox = None
    for t in soup.find_all("table"):
        cls = " ".join((t.get("class") or [])).lower()
        if "infobox" in cls:
            infobox = t
            break
    scope = infobox or soup  # fallback: toute la page
    a = scope.find("a", href=True)
    # on veut un <a href="/wiki/File:...">
    for link in scope.find_all("a", href=True):
        href = link["href"]
        if "/wiki/File:" in href or "/wiki/Fichier:" in href:
            return urljoin(page_url, href)
        # parfois l'<img> est cliquable: parent a -> href file
        if link.find("img") and ("/wiki/File:" in href or "/wiki/Fichier:" in href):
            return urljoin(page_url, href)
    # fallback meta og:image -> page du fichier ?
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        # og:image pointe souvent directement sur upload.wikimedia.org (image finale)
        return meta["content"]
    return None

# ---------- MediaWiki API: file page -> original/large thumb ----------
def fetch_image_from_file_api(file_page_url: str) -> tuple[str | None, str]:
    # Si on nous a passé directement une URL upload.wikimedia.org (og:image), renvoyer telle quelle
    netloc = urlparse(file_page_url).netloc
    if "upload.wikimedia.org" in netloc:
        return file_page_url, "og-image"

    ep = api_endpoint(file_page_url)
    # File title
    title = extract_title_from_url(file_page_url)
    if not title:
        return None, "file-no-title"

    # Parfois le chemin est /wiki/Fichier:..., harmoniser en File:
    title = title.replace("Fichier:", "File:")

    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": THUMB_SIZE,  # fournit aussi thumburl
    }
    try:
        r = safe_request("GET", ep, params=params)
        data = r.json()
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None, "fileapi-no-pages"
        page = pages[0]
        infos = page.get("imageinfo", [])
        if not infos:
            return None, "fileapi-no-imageinfo"
        ii = infos[0]
        # si SVG, prendre thumburl (PNG raster) ; sinon, l'original url
        mime = ii.get("mime", "")
        if mime == "image/svg+xml" and ii.get("thumburl"):
            return ii["thumburl"], "fileapi-thumb-svg"
        if ii.get("url"):
            return ii["url"], "fileapi-original"
        if ii.get("thumburl"):
            return ii["thumburl"], "fileapi-thumb"
        return None, "fileapi-no-url"
    except Exception as e:
        return None, f"fileapi-error:{e}"

# ---------- Download & convert to JPG ----------
def download_to_jpg(img_url: str, dest_path: Path) -> tuple[bool, str]:
    """Télécharge l'image et convertit en JPEG (ID_Name.jpg)."""
    try:
        r = safe_request("GET", img_url, stream=True)
        content = r.content
        # Conversion en JPEG avec Pillow
        try:
            from PIL import Image
        except ImportError:
            return False, "Pillow not installed (pip install pillow)"

        im = Image.open(BytesIO(content))
        # Convertir en RGB si besoin (PNG avec alpha, etc.)
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest_path, format="JPEG", quality=90, optimize=True)
        return True, str(dest_path)
    except Exception as e:
        return False, f"download/convert-error:{e}"

# ---------- Input loaders ----------
def load_breeds():
    if Path(BREEDS_JSON).exists():
        data = json.loads(Path(BREEDS_JSON).read_text(encoding="utf-8"))
        return [{"id": b.get("id"), "breed": b.get("breed"), "url": b.get("url")} for b in data.get("breeds", [])]

    if Path(BREEDS_CSV).exists():
        items = []
        with open(BREEDS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("Nom") or "").strip()
                url  = (row.get("URL") or "").strip()
                if name:
                    items.append({"id": None, "breed": name, "url": url})
        # attribue des ids alpha si absents
        items.sort(key=lambda x: x["breed"].casefold())
        for i, it in enumerate(items, 1):
            it["id"] = i
        return items

    raise SystemExit("Aucune source trouvée (breeds_links.json ou dog_breeds_structured.csv).")

# ---------- Main ----------
def main():
    try:
        from PIL import Image  # vérifie la dispo de Pillow en amont
    except Exception:
        print("⚠️  Ce script convertit en JPEG. Installe Pillow avant:  pip install pillow")
        return

    breeds = load_breeds()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = []

    total = len(breeds)
    print(f"Lancement: {total} races. Pause={PAUSE_SECONDS}s, thumb={THUMB_SIZE}px")

    for idx, item in enumerate(breeds, 1):
        bid   = item.get("id") or idx
        breed = (item.get("breed") or f"breed_{idx}").strip()
        url   = (item.get("url") or "").strip()
        fname = f"{int(bid):03d}_{norm_name_for_filename(breed)}.jpg"
        dest  = OUT_DIR / fname

        res = {"id": bid, "breed": breed, "url": url, "file": str(dest), "status": None, "note": None}

        try:
            # overwrite si demandé
            if dest.exists() and not OVERWRITE:
                res["status"] = "skipped-exists"
                report.append(res)
                print(f"[{idx}/{total}] {breed} -> SKIP (existe)")
                continue

            # 1) API page
            img_url, note = fetch_image_via_page_api(url) if url else (None, "no-url")
            polite_sleep()

            # 2) fallback: HTML -> lien Fichier: -> API file
            if not img_url:
                fpage = find_file_page_from_html(url) if url else None
                polite_sleep()
                if fpage:
                    img_url, note2 = fetch_image_from_file_api(fpage)
                    note = f"{note} ; {note2}"
                    polite_sleep()

            if not img_url or is_bad_placeholder(img_url):
                res["status"] = "failed"
                res["note"] = f"no-valid-image ({note})"
                print(f"[{idx}/{total}] {breed} -> ❌ NO VALID IMAGE ({note})")
                report.append(res)
                continue

            ok, out = download_to_jpg(img_url, dest)
            if ok:
                res["status"] = "ok"
                res["note"] = note
                print(f"[{idx}/{total}] {breed} -> ✅ {dest.name} ({note})")
            else:
                res["status"] = "failed"
                res["note"] = out
                print(f"[{idx}/{total}] {breed} -> ❌ {out}")

        except Exception as e:
            res["status"] = "failed"
            res["note"] = f"exception:{e}"
            print(f"[{idx}/{total}] {breed} -> ❌ exception: {e}")

        report.append(res)

    Path(REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Terminé. Rapport: {REPORT_FILE}")

if __name__ == "__main__":
    main()
