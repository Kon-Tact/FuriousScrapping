# find_missing_ids.py
import json
from pathlib import Path

INFILE = "breeds_merged.json"
OUT_MISSING = "breeds_missing_ids.json"
OUT_GAPS = "id_gaps.json"

def is_missing_id(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return not val.strip().isdigit()
    if isinstance(val, (int, float)):
        # accepte les entiers uniquement
        return not (isinstance(val, int))
    return True

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    # 1) Entrées sans id valide
    missing = []
    present_ids = set()
    for b in breeds:
        bid = b.get("id")
        if is_missing_id(bid):
            missing.append({"breed": b.get("breed", "").strip(), "id": bid})
        else:
            present_ids.add(int(bid))

    # 2) Trous d'IDs dans la séquence 1..max_id
    gaps = []
    if present_ids:
        max_id = max(present_ids)
        gaps = [i for i in range(1, max_id + 1) if i not in present_ids]

    # Ecrit les sorties
    Path(OUT_MISSING).write_text(json.dumps({"missing": missing}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(OUT_GAPS).write_text(json.dumps({"gaps": gaps}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ Analysé {len(breeds)} races")
    print(f"   ❌ Races sans id : {len(missing)} → {OUT_MISSING}")
    if missing[:10]:
        print("     Exemples :", ", ".join(m['breed'] for m in missing[:10]))
    print(f"   🔢 Trous d'IDs   : {len(gaps)} → {OUT_GAPS}")
    if gaps[:20]:
        print("     Premiers gaps :", ", ".join(map(str, gaps[:20])))

if __name__ == "__main__":
    main()
