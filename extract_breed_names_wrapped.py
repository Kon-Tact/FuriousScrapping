# extract_breed_names_wrapped.py
import json
from pathlib import Path

INFILE  = "breeds_with_global_ids_extended.json"
OUTFILE = "breeds_list.txt"

def main():
    data = json.loads(Path(INFILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    names = [b.get("breed", "").strip() for b in breeds if b.get("breed")]

    # regroupe par 4
    lines = []
    for i in range(0, len(names), 4):
        group = names[i:i+4]
        lines.append(", ".join(group))

    text = "\n".join(lines)

    Path(OUTFILE).write_text(text, encoding="utf-8")
    print(f"✔ {len(names)} races extraites → {OUTFILE}")
    print("Aperçu :")
    print("\n".join(lines[:3]) + ("\n..." if len(lines) > 3 else ""))

if __name__ == "__main__":
    main()
