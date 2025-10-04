# extend_breeds_schema.py
import json
from pathlib import Path

INFILE  = "breeds_with_global_ids.json"
OUTFILE = "breeds_with_global_ids_extended.json"

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    extended = []
    for it in breeds:
        # sécuriser la structure
        breed = dict(it)  # copie superficielle
        feats = dict(breed.get("features", {}))

        # alias au niveau racine (ajout seulement s'il n'existe pas)
        if "alias" not in breed:
            # si tu veux forcer même s'il existe, remplace par: breed["alias"] = ""
            breed["alias"] = ""

        # champs dans features (ajout seulement s'ils n'existent pas)
        if "poil" not in feats:
            feats["poil"] = ""
        if "energy" not in feats:
            feats["energy"] = ""

        breed["features"] = feats
        extended.append(breed)

    out = {"breeds": extended}
    Path(OUTFILE).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ Ajouts effectués. Fichier écrit : {OUTFILE} (races: {len(extended)})")

if __name__ == "__main__":
    main()
