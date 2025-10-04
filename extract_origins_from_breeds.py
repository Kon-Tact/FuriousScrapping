# extract_origins_from_breeds.py
import json
import re
import unicodedata
from pathlib import Path

INFILE = "breeds_with_origin_list.json"
OUTFILE = "origins_index.json"

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    # clé de normalisation pour dédup/tri : sans accents, minuscule, espaces compressés
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    # Canonicalisation: on conserve la première graphie rencontrée pour chaque clé normalisée
    key_to_label = {}

    for it in breeds:
        feats = it.get("features", {}) or {}
        origins = feats.get("origin", [])
        # Sécurité : si ce n'est pas une liste, on tente de l'envelopper
        if isinstance(origins, str):
            origins = [origins]
        elif not isinstance(origins, list):
            continue

        for o in origins:
            if not isinstance(o, str):
                continue
            label = o.strip()
            if not label:
                continue
            k = norm_key(label)
            if k and k not in key_to_label:
                key_to_label[k] = label  # garder la 1re graphie vue

    # Tri alpha par clé normalisée
    items = [{"id": i + 1, "name": key_to_label[k]}
             for i, k in enumerate(sorted(key_to_label.keys()))]

    Path(OUTFILE).write_text(json.dumps({"origins": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ {OUTFILE} écrit ({len(items)} origines uniques)")
    if items[:10]:
        print("Aperçu :", ", ".join(o["name"] for o in items[:10]))

if __name__ == "__main__":
    main()
