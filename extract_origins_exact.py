# extract_origins_exact.py
import json
import unicodedata
import re
from pathlib import Path

INFILE = "breeds_with_origin_list.json"
OUTFILE = "origins_index.json"

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def sort_key(s: str) -> str:
    # Tri alpha sans accents / insensible casse, mais on garde le libellé exact en sortie
    s = strip_accents(s).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    # Déduplication stricte par valeur exacte (après strip)
    seen = set()
    origins = []
    for it in breeds:
        feats = it.get("features", {}) or {}
        ori_list = feats.get("origin", [])
        if isinstance(ori_list, str):
            ori_list = [ori_list]  # tolérance si jamais un string traîne
        for o in ori_list:
            if not isinstance(o, str):
                continue
            label = o.strip()
            if not label:
                continue
            if label not in seen:
                seen.add(label)
                origins.append(label)

    # Tri + réattribution d'IDs 1..N
    origins_sorted = sorted(origins, key=sort_key)
    out = {"origins": [{"id": i+1, "name": name} for i, name in enumerate(origins_sorted)]}

    Path(OUTFILE).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ {OUTFILE} écrit ({len(out['origins'])} origines)")

if __name__ == "__main__":
    main()
