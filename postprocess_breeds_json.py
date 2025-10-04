# postprocess_breeds_json.py
import json
import re
import math
from pathlib import Path

INFILE = "breeds_clean.json"
OUTFILE = "breeds_clean_post.json"

num_re = re.compile(r"\d+(?:[.,]\d+)?")

def cap_first(s: str) -> str:
    s = s or ""
    return (s[:1].upper() + s[1:]) if s else s

def parse_numbers(text: str):
    nums = [float(t.replace(",", ".")) for t in num_re.findall(text or "")]
    return nums

def detect_unit(text: str, default_unit: str):
    t = (text or "").lower()
    if "kg" in t:
        return "kgs"
    if "cm" in t:
        return "cm"
    return default_unit

def fmt_measure(raw: str, default_unit: str):
    """
    - Arrondit tous les nombres à l'unité supérieure (ceil).
    - Si un seul nombre: "~N <unit>"
    - Si plusieurs: "min à max <unit>"
    - Garde l'unité détectée (kg/cm) en la normalisant ("kgs", "cm").
    """
    if not raw:
        return raw
    unit = detect_unit(raw, default_unit)
    nums = parse_numbers(raw)
    if not nums:
        return raw  # rien à faire

    # arrondi supérieur
    ceils = [int(math.ceil(x)) for x in nums]

    if len(ceils) == 1:
        return f"~{ceils[0]} {unit}"
    else:
        lo, hi = min(ceils), max(ceils)
        return f"{lo} à {hi} {unit}"

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    for item in breeds:
        # 1) Capitaliser la 1re lettre du nom de race
        if "breed" in item and isinstance(item["breed"], str):
            item["breed"] = cap_first(item["breed"])

        # 2) Corriger size/weight
        feats = item.get("features", {})
        if isinstance(feats, dict):
            if "size" in feats and isinstance(feats["size"], str):
                feats["size"] = fmt_measure(feats["size"], "cm")
            if "weight" in feats and isinstance(feats["weight"], str):
                feats["weight"] = fmt_measure(feats["weight"], "kgs")

    Path(OUTFILE).write_text(json.dumps({"breeds": breeds}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ Transformations appliquées. Fichier écrit : {OUTFILE}")
    print(f"  Races traitées : {len(breeds)}")

if __name__ == "__main__":
    main()
