# normalize_origins_and_add_type.py
import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict

IN_BREEDS  = "breeds_with_global_ids_extended.json"
IN_ORIGINS = "origins_index.json"
OUT_FILE   = "breeds_with_origin_list_and_type.json"

# ---------- utils ----------
def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_list(x) -> List[str]:
    if x is None: return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):
        x = x.strip()
        return [x] if x else []
    # autre type → string
    s = str(x).strip()
    return [s] if s else []

def split_candidates(raw: str) -> List[str]:
    """Découpe léger si origin est une chaîne (séparateurs usuels)."""
    if not raw: return []
    txt = f" {raw} "
    txt = txt.replace(" et/ou ", ",")
    txt = re.sub(r"\bet\b", ",", txt, flags=re.I)
    txt = re.sub(r"[;/]", ",", txt)
    txt = re.sub(r"[\u2012-\u2015\-]+", ",", txt)  # tirets → virgule
    txt = re.sub(r",+", ",", txt)
    parts = [p.strip().strip(".") for p in txt.split(",")]
    return [p for p in parts if p]

# ---------- main ----------
def main():
    # 1) charge index des origines (canon)
    origins_data = json.loads(Path(IN_ORIGINS).read_text(encoding="utf-8"))
    # map clé normalisée -> libellé canonique
    origin_map: Dict[str, str] = {
        norm_key(o["name"]): o["name"]
        for o in origins_data.get("origins", [])
        if isinstance(o.get("name"), str) and o["name"].strip()
    }
    allowed_keys = set(origin_map.keys())

    # 2) charge breeds
    data = json.loads(Path(IN_BREEDS).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    changed = 0
    for it in breeds:
        feats = dict(it.get("features", {}) or {})

        # ----- origin -> list filtrée par origins_index -----
        raw_origin = feats.get("origin", [])

        # a) transforme en candidats (liste de chaînes)
        if isinstance(raw_origin, list):
            candidates = [str(x).strip() for x in raw_origin if str(x).strip()]
        elif isinstance(raw_origin, str):
            candidates = split_candidates(raw_origin)
        else:
            candidates = []

        # b) garde seulement ce qui est dans origins_index (matching sans accents/casse)
        seen = set()
        final_origins: List[str] = []
        for cand in candidates:
            key = norm_key(cand)
            if key in allowed_keys and key not in seen:
                seen.add(key)
                final_origins.append(origin_map[key])

        # c) remplace
        feats["origin"] = final_origins

        # ----- type -> liste -----
        feats["type"] = to_list(feats.get("type"))

        # remet dans l’objet
        it["features"] = feats
        changed += 1

    # 3) écrit la sortie
    out = {"breeds": breeds}
    Path(OUT_FILE).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ {OUT_FILE} écrit. Races traitées: {changed}")
    # petit aperçu
    for b in breeds[:5]:
        print(f"- {b.get('breed')}: origin={b['features'].get('origin', [])}, type={b['features'].get('type', [])}")

if __name__ == "__main__":
    main()
