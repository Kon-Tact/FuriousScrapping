# scrape_wiki_dog_infobox.py
import time
import csv
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from collections import OrderedDict
from urllib.parse import urljoin, urlparse

COMMONS_URL = "https://commons.wikimedia.org/wiki/List_of_dog_breeds?uselang=fr"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://commons.wikimedia.org/"
}
REQUEST_TIMEOUT = 20
PAUSE_SECONDS = 0.7       # Politesse entre requêtes
MAX_RETRIES = 2           # Petites relances si échec
TEST_LIMIT = None         # Mets un nombre (ex. 20) pour tester vite

def fetch(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, retries=MAX_RETRIES):
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.2)
            else:
                raise last_err

def find_commons_table_with_local_names(soup):
    # On cherche une table ayant un header avec "Local" (en anglais)
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        head_cells = rows[0].find_all(["th", "td"])
        if len(head_cells) >= 3:
            header_texts = [c.get_text(strip=True).lower() for c in head_cells]
            if any("local" in h for h in header_texts):
                return t
    # fallback: première table à >= 3 colonnes
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        head_cells = rows[0].find_all(["th", "td"])
        if len(head_cells) >= 3:
            return t
    return None

def get_local_name_links_from_commons():
    resp = fetch(COMMONS_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    table = find_commons_table_with_local_names(soup)
    if not table:
        raise RuntimeError("Impossible de localiser la table avec les noms locaux sur Commons.")

    # Déterminer l'index de la colonne "Local names"
    header_cells = table.find("tr").find_all(["th", "td"])
    col_index = None
    for i, c in enumerate(header_cells):
        if "local" in c.get_text(strip=True).lower():
            col_index = i
            break
    if col_index is None:
        col_index = 2  # par défaut, 3e colonne

    links = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all(["td", "th"])
        if len(tds) <= col_index:
            continue
        # dans la 3e col, il peut y avoir plusieurs <a>
        for a in tds[col_index].find_all("a"):
            name = a.get_text(strip=True)
            href = a.get("href")
            if not name or not href:
                continue
            url = urljoin("https://commons.wikimedia.org", href)
            links.append((name, url))
    # déduplication en conservant l’ordre
    seen, out = set(), []
    for name, url in links:
        key = (name, url)
        if key not in seen:
            seen.add(key)
            out.append((name, url))
    return out

def to_clean_text(node):
    if not node:
        return ""
    # Remplacer <br> et listes par séparateurs
    text = node.get_text(separator=" ", strip=True)
    # Supprimer les références [1], [réf. nécessaire], etc.
    text = re.sub(r"\[\d+\]|\[\s*réf\.\s*nécessaire\s*\]", "", text, flags=re.I)
    # Espaces normalisés
    text = re.sub(r"\s+", " ", text).strip(" ,;")
    return text

def is_infobox_table(table):
    cls = " ".join(table.get("class", [])).lower()
    return ("infobox" in cls) or ("infobox_v2" in cls) or ("infobox" in cls)

def extract_infobox_pairs(html):
    soup = BeautifulSoup(html, "html.parser")
    # Chercher la première table "infobox"
    table = None
    for t in soup.find_all("table"):
        if is_infobox_table(t):
            table = t
            break
    if table is None:
        return OrderedDict()

    data = OrderedDict()
    # Parcourir les lignes; garder celles th+td (étiquette + valeur)
    for tr in table.find_all("tr"):
        # Ignorer les lignes “titre de section” (souvent th avec colspan)
        th = tr.find("th")
        td = tr.find("td")
        if th and td and th.get("colspan") is None:
            key = to_clean_text(th)
            val = to_clean_text(td)
            if key and val:
                # Uniformiser quelques clés fréquentes
                key = (key
                       .replace("Région d’origine", "Région")
                       .replace("Région d'origine", "Région")
                       .replace("Caractéristiques", ""))
                key = key.strip(" :")
                if key:
                    # éviter d’écraser si doublon: concaténer
                    if key in data and val not in data[key]:
                        data[key] += " ; " + val
                    else:
                        data[key] = val
    return data

def follow_if_wikipedia(url):
    """
    Les liens depuis Commons peuvent pointer vers Wikipedia (fr/en/…)
    ou rester sur Commons. On suit le lien ; si c'est une page Commons,
    on tente de trouver un lien 'Wikipedia' dans la barre latérale.
    """
    r = fetch(url)
    # Si on est déjà sur un domaine wikipedia.*, traiter
    domain = urlparse(r.url).netloc
    if "wikipedia.org" in domain:
        return r.url, r.text

    # Sinon, essayer d'attraper un lien vers Wikipedia depuis la page Commons
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "wikipedia.org/wiki/" in href:
            full = urljoin(r.url, href)
            rr = fetch(full)
            return rr.url, rr.text

    # Si rien trouvé, on retournera quand même la page (peut contenir une infobox)
    return r.url, r.text

def main():
    all_links = get_local_name_links_from_commons()
    if TEST_LIMIT:
        all_links = all_links[:TEST_LIMIT]
    print(f"Races trouvées dans la 3e colonne : {len(all_links)}")

    flat_lines = []
    rows_for_csv = []

    for idx, (display_name, commons_href) in enumerate(all_links, 1):
        print(f"[{idx}/{len(all_links)}] {display_name} -> {commons_href}")
        try:
            final_url, html = follow_if_wikipedia(commons_href)
            info = extract_infobox_pairs(html)
            # Construire la version "plate" demandée
            parts = [display_name]
            for k, v in info.items():
                parts.append(f"{k}: {v}")
            flat_line = ", ".join(parts)
            flat_lines.append(flat_line)

            # Pour le CSV structuré, on met au moins Nom + URL + champs
            row = OrderedDict()
            row["Nom"] = display_name
            row["URL"] = final_url
            for k, v in info.items():
                row[k] = v
            rows_for_csv.append(row)
        except Exception as e:
            print(f"  -> ERREUR: {e}")
        time.sleep(PAUSE_SECONDS)

    # Écriture du .txt “plat”
    with open("dog_breeds_flat.txt", "w", encoding="utf-8") as f:
        for line in flat_lines:
            f.write(line + "\n")
    print("✔ dog_breeds_flat.txt écrit.")

    # Écriture du CSV “structuré”
    # Normaliser l’ensemble des colonnes (union de toutes les clés)
    all_keys = OrderedDict()
    for r in rows_for_csv:
        for k in r.keys():
            all_keys[k] = True
    fieldnames = list(all_keys.keys())

    with open("dog_breeds_structured.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows_for_csv:
            w.writerow(r)
    print("✔ dog_breeds_structured.csv écrit.")

    # Bonus: export XLSX
    try:
        df = pd.DataFrame(rows_for_csv)
        df.to_excel("dog_breeds_structured.xlsx", index=False)
        print("✔ dog_breeds_structured.xlsx écrit.")
    except Exception as e:
        print(f"(XLSX facultatif) Impossible d’écrire l’Excel: {e}")

if __name__ == "__main__":
    main()
