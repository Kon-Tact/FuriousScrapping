# extract_breed_names.py
import json
from pathlib import Path

INFILE  = "breeds_with_global_ids_extended.json"
OUTFILE = "breeds_list.txt"

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    names = [b.get("breed", "").strip() for b in breeds if b.get("breed")]
    text = ", ".join(names)

    Path(OUTFILE).write_text(text, encoding="utf-8")
    print(f"✔ {len(names)} races extraites → {OUTFILE}")
    print(f"Aperçu : {text[:200]}...")

if __name__ == "__main__":
    main()
