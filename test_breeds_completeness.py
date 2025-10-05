# test_breeds_completeness.py
import json
import csv
from pathlib import Path
from typing import Any, Dict, List

INFILE = "breeds_merged_final.json"
OUT_JSON = "breeds_missing_fields.json"
OUT_CSV  = "breeds_missing_fields.csv"

# Champs à vérifier (alias explicitement exclu)
REQUIRED_FIELDS = [
    ("id",                 "scalar"),
    ("breed",              "scalar"),
    ("features.origin",    "list"),
    ("features.type",      "list"),
    ("features.robe",      "list"),
    ("features.size",      "scalar"),
    ("features.weight",    "scalar"),
    ("features.poil",      "scalar"),
    ("features.energy",    "scalar"),
]

def get_path(d: Dict[str, Any], dotted: str):
    cur = d
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

def is_nonempty_scalar(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (int, float)):
        # id peut être int ; autres scalaires attendus sont strings
        return True if isinstance(v, int) else str(v).strip() != ""
    if isinstance(v, str):
        return v.strip() != ""
    return str(v).strip() != ""

def is_nonempty_list(v: Any) -> bool:
    if not isinstance(v, list):
        return False
    # au moins un élément non vide après strip si string
    for x in v:
        if isinstance(x, str) and x.strip():
            return True
        if not isinstance(x, str) and x is not None:
            return True
    return False

def check_entry(e: Dict[str, Any]) -> List[str]:
    missing = []
    for path, kind in REQUIRED_FIELDS:
        val = get_path(e, path)
        if kind == "scalar":
            ok = is_nonempty_scalar(val)
            # cas particulier id : doit être int
            if path == "id":
                ok = ok and isinstance(val, int)
        else:  # list
            ok = is_nonempty_list(val)
        if not ok:
            missing.append(path)
    return missing

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    items = data.get("breeds", [])
    if not isinstance(items, list):
        raise SystemExit("❌ JSON invalide : clé 'breeds' absente ou non-liste.")

    report_rows = []
    missing_entries = []

    ok_count = 0
    for e in items:
        breed = (e.get("breed") or "").strip()
        bid = e.get("id")
        missing = check_entry(e)
        if missing:
            missing_entries.append({
                "id": bid,
                "breed": breed,
                "missing": missing
            })
            report_rows.append({
                "id": bid,
                "breed": breed,
                "missing_fields": "|".join(missing)
            })
        else:
            ok_count += 1

    # sorties
    Path(OUT_JSON).write_text(json.dumps({"failures": missing_entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","breed","missing_fields"])
        w.writeheader()
        w.writerows(report_rows)

    total = len(items)
    failed = len(missing_entries)
    print(f"✔ Test terminé sur {total} races")
    print(f"   ✓ Complets  : {ok_count}")
    print(f"   ❌ Incomplets (hors alias) : {failed}")
    if failed:
        print("   Exemples :")
        for ex in missing_entries[:10]:
            print(f"     - {ex['id']}: {ex['breed']} -> {', '.join(ex['missing'])}")
    print(f"→ Détails JSON : {OUT_JSON}")
    print(f"→ Détails CSV  : {OUT_CSV}")

if __name__ == "__main__":
    main()
