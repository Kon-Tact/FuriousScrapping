# apply_global_ids.py
import json
import unicodedata
import re
from pathlib import Path

LINKS_FILE = "breeds_links.json"   # contient tous les breeds avec ID global
MERGED_FILE = "breeds_merged.json" # ton fichier enrichi
OUT_FILE = "breeds_with_global_ids.json"

# --- helpers ---
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    # Charger le fichier d'IDs globaux
    links_data = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8"))
    links = links_data.get("breeds", [])

    # Construire un mapping nom normalisé -> id global
    global_ids = {norm_key(b["breed"]): b["id"] for b in links}

    # Charger breeds_merged
    merged_data = json.loads(Path(MERGED_FILE).read_text(encoding="utf-8"))
    breeds = merged_data.get("breeds", [])

    # Appliquer l'ID global
    not_found = []
    for b in breeds:
        key = norm_key(b.get("breed", ""))
        if key in global_ids:
            b["id"] = global_ids[key]
        else:
            not_found.append(b.get("breed"))

    # Sauvegarder avec IDs globaux
    out = {"breeds": breeds}
    Path(OUT_FILE).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ {OUT_FILE} écrit ({len(breeds)} races)")
    if not_found:
        print("⚠️ Races sans ID global trouvé :", ", ".join(not_found))

if __name__ == "__main__":
    main()
