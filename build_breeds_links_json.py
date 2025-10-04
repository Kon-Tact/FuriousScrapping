# build_breed_links_json.py
import pandas as pd
import unicodedata
import re
import json
from pathlib import Path

INFILE = "dog_breeds_structured.csv"
OUTFILE = "breeds_links.json"

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def norm_sort_key(s: str) -> str:
    s = strip_accents(s or "").casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")

    # Vérifie colonnes attendues
    if not {"Nom", "URL"}.issubset(df.columns):
        raise SystemExit("❌ Le CSV doit contenir les colonnes 'Nom' et 'URL'.")

    # Prépare la liste races
    items = []
    for _, row in df.iterrows():
        name = row["Nom"].strip()
        url = row["URL"].strip()
        if not name:
            continue
        items.append({"breed": name, "url": url})

    # Tri alpha par nom (ignorer accents/casse)
    items.sort(key=lambda x: norm_sort_key(x["breed"]))

    # Ajout des IDs
    for i, it in enumerate(items, start=1):
        it["id"] = i

    # Export JSON
    out = {"breeds": items}
    Path(OUTFILE).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ {OUTFILE} écrit ({len(items)} races)")

if __name__ == "__main__":
    main()
