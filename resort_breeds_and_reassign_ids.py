# resort_breeds_and_reassign_ids.py
import json
import re
import unicodedata
from pathlib import Path

INFILE  = "breeds_links_fixed.json"     # ton fichier source
OUTFILE = "breeds_links_resorted.json"  # sortie avec IDs réassignés

def strip_accents(s: str) -> str:
    if s is None: 
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s))
        if unicodedata.category(c) != "Mn"
    )

def norm_sort_key(s: str) -> str:
    s = strip_accents(s).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])
    if not isinstance(breeds, list):
        raise SystemExit("Le JSON doit contenir une clé 'breeds' avec une liste.")

    # Nettoyage léger des noms (trim) pour le tri
    for b in breeds:
        if "breed" in b and isinstance(b["breed"], str):
            b["breed"] = b["breed"].strip()

    # Tri alphabétique (sans accents / insensible casse)
    breeds.sort(key=lambda x: norm_sort_key(x.get("breed", "")))

    # Réattribution des IDs 1..N
    for i, b in enumerate(breeds, start=1):
        b["id"] = i

    Path(OUTFILE).write_text(json.dumps({"breeds": breeds}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ Réordonné et réattribué {len(breeds)} IDs.")
    print(f"→ Fichier écrit : {OUTFILE}")
    print("Aperçu des 10 premiers :")
    for b in breeds[:10]:
        print(f"  {b['id']:03d} — {b.get('breed','')}")

if __name__ == "__main__":
    main()
