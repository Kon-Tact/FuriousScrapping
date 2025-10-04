# split_origins_resort_and_index.py
import json
import re
import unicodedata
from pathlib import Path

INFILE = "breeds_merged.json"            # ou ton fichier modifié
OUT_BREEDS = "breeds_with_origin_list.json"
OUT_ORIGINS = "origins_index.json"

# ---------- helpers ----------
def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_sort_key(s: str) -> str:
    s = strip_accents(s or "").casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def cap_first(s: str) -> str:
    return (s[:1].upper() + s[1:]) if s else s

def clean_piece(s: str) -> str:
    if not s: return ""
    s = re.sub(r"\([^)]*\)", "", s)        # retire parenthèses
    s = s.strip().strip(",;./·–—-").strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_origins(raw: str):
    if not raw: return []
    txt = f" {raw} "
    txt = txt.replace(" et/ou ", ",")
    txt = re.sub(r"\bet\b", ",", txt, flags=re.I)
    txt = re.sub(r"[;/]", ",", txt)
    txt = re.sub(r"[\u2012-\u2015\-]+", ",", txt)  # divers tirets → virgule
    txt = re.sub(r",+", ",", txt)
    pieces = [clean_piece(p) for p in txt.split(",")]

    seen, out = set(), []
    for p in pieces:
        if not p: 
            continue
        key = norm_sort_key(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out

# ---------- main ----------
def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    # 1) normalise la majuscule initiale (au cas où des noms ont été modifiés)
    for it in breeds:
        if isinstance(it.get("breed"), str):
            it["breed"] = cap_first(it["breed"].strip())

    # 2) tri alphabétique (sans accents) puis réattribution des IDs 1..N
    breeds.sort(key=lambda x: norm_sort_key(x.get("breed", "")))
    for i, it in enumerate(breeds, start=1):
        it["id"] = i

    # 3) transformer origin (string -> liste)
    all_origins = set()
    for it in breeds:
        feats = it.get("features", {}) or {}
        raw_origin = feats.get("origin", "")
        origin_list = split_origins(raw_origin)
        feats["origin"] = origin_list
        it["features"] = feats
        for o in origin_list:
            all_origins.add(o)

    # 4) construire l’index des origines (alpha + ids)
    origin_list_sorted = sorted(all_origins, key=norm_sort_key)
    origins_index = [{"id": i+1, "name": o} for i, o in enumerate(origin_list_sorted)]

    # 5) écrire les sorties
    Path(OUT_BREEDS).write_text(json.dumps({"breeds": breeds}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(OUT_ORIGINS).write_text(json.dumps({"origins": origins_index}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ {OUT_BREEDS} écrit ({len(breeds)} races)")
    print(f"✔ {OUT_ORIGINS} écrit ({len(origins_index)} origines uniques)")

if __name__ == "__main__":
    main()
