# build_placeholders_for_gaps.py
import json
from pathlib import Path

GAPS_FILE   = "id_gaps.json"                 # {"gaps":[...]}
LINKS_FILE  = "breeds_links_resorted.json"   # {"breeds":[{"id":..,"breed":"..", ...}, ...]}
OUT_FILE    = "breeds_placeholders_for_gaps.json"

def main():
    gaps = json.loads(Path(GAPS_FILE).read_text(encoding="utf-8")).get("gaps", [])
    links = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8")).get("breeds", [])

    # map id -> breed
    id_to_breed = {int(b["id"]): b.get("breed","") for b in links if b.get("id") is not None}

    placeholders = []
    missing_ids = []
    for gid in sorted(int(x) for x in gaps):
        breed_name = id_to_breed.get(gid)
        if not breed_name:
            missing_ids.append(gid)
            # on crée quand même un placeholder avec un nom vide
            breed_name = ""

        placeholders.append({
            "id": gid,
            "breed": breed_name,
            "alias": [],
            "features": {
                "origin": [],
                "type": [],
                "robe": [],
                "size": "",
                "weight": "",
                "poil": "",
                "energy": ""
            }
        })

    Path(OUT_FILE).write_text(
        json.dumps({"breeds": placeholders}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"✔ Écrit {OUT_FILE} ({len(placeholders)} entrées).")
    if missing_ids:
        print(f"⚠️ IDs absents de {LINKS_FILE}: {len(missing_ids)} → {missing_ids[:20]}{' ...' if len(missing_ids)>20 else ''}")

if __name__ == "__main__":
    main()
