# download_breed_images.py
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests
from bs4 import BeautifulSoup

# ---------------- Config ----------------
BREEDS_JSON = "breeds_links.json"   # ou ton fichier qui contient "breeds": [{ "id","breed","url" }, ...]
OUT_DIR = Path("images")
PAUSE_SECONDS = 1.0   # délai poli entre requêtes (augmente si tu télécharges bcp d'images)
TIMEOUT = 20
MAX_RETRIES = 2
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36 furious-scraper/1.0 +https://example.com")

# Taille de vignette demandée via l'API (en px) — augmente si tu veux images plus grandes
THUMB_SIZE = 1000

# ---------------- Helpers ----------------
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fr,en;q=0.8"})

def safe_get(url, *, timeout=TIMEOUT, allow_redirects=True):
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=timeout, allow_redirects=allow_redirects)
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            time.sleep(1.0 + attempt)
    raise last_exc

def filename_from_url(url):
    # essai d'extraire un nom de fichier lisible depuis l'url
    p = urlparse(url)
    name = unquote(Path(p.path).name)
    # retirer query string fragments et caractères bizarres
    name = re.sub(r"[^\w\-\._]+", "_", name)
    if not name:
        name = "image"
    return name

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

# ---------------- MediaWiki API method ----------------
def fetch_image_via_api(page_url):
    """
    Tente d'utiliser l'API MediaWiki pour récupérer la pageimage (thumbnail) URL.
    Retourne (image_url, source_note) ou (None, reason)
    """
    parsed = urlparse(page_url)
    domain = parsed.netloc
    # On supporte wikipedia.org et commons.wikimedia.org
    if not domain.endswith(("wikipedia.org", "commons.wikimedia.org")):
        return None, "domain-not-wikipedia/commons"

    # Déduire le API endpoint (ex: fr.wikipedia.org -> https://fr.wikipedia.org/w/api.php)
    api_base = f"{parsed.scheme}://{domain}/w/api.php"

    # Extraire le titre de la page depuis le path (/wiki/Titre)
    # Path may include /wiki/Title or other; get segment after /wiki/
    m = re.search(r"/wiki/(.+)$", parsed.path)
    if not m:
        return None, "no-title-in-url"
    title = m.group(1)

    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages|imageinfo",
        "piprop": "original|thumbnail",
        "pithumbsize": THUMB_SIZE,
        "format": "json",
        "formatversion": 2
    }

    try:
        r = safe_get(api_base, timeout=TIMEOUT)
        # use POST to avoid very long URLs
        r = session.post(api_base, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        # data["query"]["pages"][0]["thumbnail"]["source"] maybe present
        pages = data.get("query", {}).get("pages", [])
        if pages:
            page = pages[0]
            # first prefer 'original' if present
            if "original" in page:
                return page["original"]["source"], f"api-original ({domain})"
            if "thumbnail" in page:
                return page["thumbnail"]["source"], f"api-thumb ({domain})"
        return None, "api-no-image"
    except Exception as e:
        return None, f"api-error:{e}"

# ---------------- HTML fallback (infobox) ----------------
def fetch_image_via_infobox(page_url):
    """
    Parse la page HTML et récupère la première image dans la table 'infobox' (class inclut 'infobox').
    Retourne (image_url, source_note) ou (None, reason)
    """
    try:
        r = safe_get(page_url)
    except Exception as e:
        return None, f"http-error:{e}"

    soup = BeautifulSoup(r.text, "html.parser")
    # cherche table infobox
    infobox = None
    for t in soup.find_all("table"):
        cls = " ".join(t.get("class", [])).lower()
        if "infobox" in cls or "biography" in cls or "infobox_v2" in cls:
            infobox = t
            break
    if not infobox:
        # fallback: trouver la première image large de la page <img> inside content
        img = soup.find("img")
        if img and img.get("src"):
            src = img["src"]
            # convert protocol-relative //upload.wikimedia.org/...
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}{src}"
            return src, "html-first-img"
        return None, "no-infobox-no-img"

    # dans l'infobox, prendre la première <img>
    img = infobox.find("img")
    if not img or not img.get("src"):
        return None, "infobox-no-img"
    src = img["src"]
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/"):
        src = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}{src}"
    return src, "infobox-img"

# ---------------- Download helper ----------------
def download_image(url, dest_path: Path):
    try:
        r = safe_get(url, timeout=TIMEOUT)
    except Exception as e:
        return False, f"download-error:{e}"
    # try to determine extension
    ext = ""
    ct = r.headers.get("content-type","")
    if ct:
        if "jpeg" in ct or "jpg" in ct:
            ext = ".jpg"
        elif "png" in ct:
            ext = ".png"
        elif "gif" in ct:
            ext = ".gif"
    if not ext:
        ext = Path(urlparse(url).path).suffix or ".jpg"
    # final filename: ensure unique
    final = dest_path.with_suffix(ext)
    with open(final, "wb") as f:
        f.write(r.content)
    return True, str(final)

# ---------------- Main flow ----------------
def main():
    if not Path(BREEDS_JSON).exists():
        print("❌ Fichier", BREEDS_JSON, "introuvable. Génère d'abord breeds_links.json")
        return

    breeds = json.loads(Path(BREEDS_JSON).read_text(encoding="utf-8")).get("breeds", [])
    report = []
    total = len(breeds)
    print(f"Starting download for {total} breeds (pause {PAUSE_SECONDS}s)...")

    for i, item in enumerate(breeds, start=1):
        name = item.get("breed") or item.get("name") or f"breed_{i}"
        page_url = item.get("url") or item.get("URL") or ""
        safe_name = re.sub(r"[^\w\-_ ]+", "_", name).strip()
        dest_folder = OUT_DIR / safe_name
        ensure_dir(dest_folder)

        result = {"id": item.get("id", i), "breed": name, "url": page_url, "image": None, "note": None}
        if not page_url:
            result["note"] = "no-url"
            report.append(result)
            continue

        # 1) try API
        img_url, note = fetch_image_via_api(page_url)
        time.sleep(0.2)
        # 2) fallback to infobox if API fails
        if not img_url:
            img_url, note = fetch_image_via_infobox(page_url)

        if not img_url:
            result["note"] = f"no-image-found ({note})"
            print(f"[{i}/{total}] {name} -> NO IMAGE ({note})")
            report.append(result)
            time.sleep(PAUSE_SECONDS)
            continue

        # Some Wikimedia thumbnails include /thumb/ path with extra parts: prefer original by removing /thumb/.../<filename>
        # but we simply download the URL found (it may be already large)
        # create candidate filename
        fname = filename_from_url(img_url)
        dest = dest_folder / fname
        ok, out = download_image(img_url, dest)
        if ok:
            result["image"] = out
            result["note"] = note
            print(f"[{i}/{total}] {name} -> saved {out} ({note})")
        else:
            result["note"] = out
            print(f"[{i}/{total}] {name} -> ERROR {out}")

        report.append(result)
        time.sleep(PAUSE_SECONDS)

    # write a report summary
    Path("download_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Done. Report saved to download_report.json")

if __name__ == "__main__":
    main()
