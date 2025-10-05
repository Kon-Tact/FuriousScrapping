# extract_and_compare_origins.py
import json
import re
import unicodedata
from pathlib import Path

MERGED_FILE   = "breeds_merged_aligned.json"
INDEX_FILE    = "origins_index.json"
OUT_ALL       = "all_origins_from_merged.json"
OUT_MISSING   = "new_origins_missing_from_index.json"

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    s = str(x).strip()
    return [s] if s else []

def main():
    # 1) Lire le merged et extraire toutes les origins
    merged = json.loads(Path(MERGED_FILE).read_text(encoding="utf-8")).get("breeds", [])
    key_to_label = {}  # on garde la 1ère graphie rencontrée pour chaque clé normalisée
    for it in merged:
        feats = it.get("features", {}) or {}
        for o in to_list(feats.get("origin")):
            k = norm_key(o)
            if k and k not in key_to_label:
                key_to_label[k] = o  # conserver la graphie d'origine

    # 2) Construire la liste complète triée
    all_keys_sorted = sorted(key_to_label.keys())
    all_origins = [{"id": i+1, "name": key_to_label[k]} for i, k in enumerate(all_keys_sorted)]

    Path(OUT_ALL).write_text(json.dumps({"origins": all_origins}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ {OUT_ALL} écrit ({len(all_origins)} origines extraites du merged).")

    # 3) Charger l'index existant et comparer (par clé normalisée)
    index = json.loads(Path(INDEX_FILE).read_text(encoding="utf-8")).get("origins", [])
    index_keys = {norm_key(o.get("name","")) for o in index if isinstance(o.get("name"), str)}

    missing_keys = [k for k in all_keys_sorted if k not in index_keys]
    missing_list = [{"id": i+1, "name": key_to_label[k]} for i, k in enumerate(missing_keys)]

    Path(OUT_MISSING).write_text(json.dumps({"origins": missing_list}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ {OUT_MISSING} écrit ({len(missing_list)} nouvelles origines non présentes dans origins_index).")

    if missing_list[:10]:
        print("Aperçu manquants :", ", ".join(o["name"] for o in missing_list[:10]))

if __name__ == "__main__":
    main()
