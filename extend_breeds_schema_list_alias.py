# extend_breeds_schema_list_alias.py
import json
from pathlib import Path

INFILE  = "breeds_with_global_ids.json"
OUTFILE = "breeds_with_global_ids_extended.json"

def to_list_alias(value):
    if value is None:
        return []
    if isinstance(value, list):
        # nettoie: supprime alias vides et cast en str
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    # autres types inattendus -> converti en str si non vide
    s = str(value).strip()
    return [s] if s else []

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    out_breeds = []
    for item in breeds:
        breed = dict(item)  # shallow copy

        # ----- alias en liste -----
        if "alias" in breed:
            breed["alias"] = to_list_alias(breed["alias"])
        else:
            breed["alias"] = []

        # ----- features -----
        feats = dict(breed.get("features", {}))
        feats.setdefault("poil", "")
        feats.setdefault("energy", "")
        breed["features"] = feats

        out_breeds.append(breed)

    Path(OUTFILE).write_text(
        json.dumps({"breeds": out_breeds}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✔ Fichier écrit : {OUTFILE} (races: {len(out_breeds)})")

if __name__ == "__main__":
    main()
