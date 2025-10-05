# merge_types_into_breeds.py
import json
from pathlib import Path

SRC_TYPES = "breeds_id_breed_type.json"                 # { "breeds": [ {id, breed, type:[...]}, ... ] }
TARGET    = "breeds_with_origin_list_and_type.json"     # { "breeds": [ {id, breed, features:{ origin:[], type:[...] }}, ... ] }
OUTFILE   = "breeds_with_origin_list_and_type_updated.json"

def to_list_type(x):
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):
        s = x.strip()
        return [s] if s else []
    s = str(x).strip()
    return [s] if s else []

def main():
    # Charge les deux fichiers
    src = json.loads(Path(SRC_TYPES).read_text(encoding="utf-8"))
    tgt = json.loads(Path(TARGET).read_text(encoding="utf-8"))

    src_breeds = src.get("breeds", [])
    tgt_breeds = tgt.get("breeds", [])

    # Index source par id et par breed (secours)
    by_id   = {b.get("id"): b for b in src_breeds if b.get("id") is not None}
    by_name = {str(b.get("breed","")).strip(): b for b in src_breeds if str(b.get("breed","")).strip()}

    updated = 0
    missing = []

    for it in tgt_breeds:
        bid = it.get("id")
        name = str(it.get("breed","")).strip()
        feats = dict(it.get("features", {}) or {})

        src_row = by_id.get(bid) or by_name.get(name)
        if not src_row:
            # pas trouvé côté source
            missing.append({"id": bid, "breed": name})
            continue

        feats["type"] = to_list_type(src_row.get("type"))
        it["features"] = feats
        updated += 1

    # Écrit le fichier mis à jour
    Path(OUTFILE).write_text(json.dumps({"breeds": tgt_breeds}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Petit récap
    print(f"✔ Types reportés dans {OUTFILE}")
    print(f"   Mis à jour : {updated}")
    if missing:
        print(f"   Non trouvés dans {SRC_TYPES} : {len(missing)}")
        print("   Exemples :", ", ".join(f"{m['id']}:{m['breed']}" for m in missing[:10]))

if __name__ == "__main__":
    main()
