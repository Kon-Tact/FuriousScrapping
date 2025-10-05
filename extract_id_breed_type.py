# extract_id_breed_type.py
import json
from pathlib import Path

INFILE   = "breeds_with_origin_list_and_type.json"
OUT_JSON = "breeds_id_breed_type.json"    # pour que tu puisses le remplir puis refusionner
OUT_CSV  = "breeds_id_breed_type.csv"     # optionnel: pratique pour Excel

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    slim = []
    for b in breeds:
        bid = b.get("id")
        name = b.get("breed", "").strip()
        t = (b.get("features") or {}).get("type", [])
        # normalise: toujours une liste
        if isinstance(t, str):
            t = [t] if t.strip() else []
        elif not isinstance(t, list):
            t = []
        slim.append({"id": bid, "breed": name, "type": t})

    Path(OUT_JSON).write_text(json.dumps({"breeds": slim}, ensure_ascii=False, indent=2), encoding="utf-8")

    # (optionnel) CSV à plat: type listé comme chaîne séparée par "|"
    try:
        import csv
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "breed", "type"])  # type = "Sportif|Compagnie|..."
            for r in slim:
                w.writerow([r["id"], r["breed"], "|".join(r["type"])])
    except Exception:
        pass

    print(f"✔ Écrit {OUT_JSON} ({len(slim)} races)")
    print(f"✔ Écrit {OUT_CSV} (optionnel)")

if __name__ == "__main__":
    main()
