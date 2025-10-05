# merge_new_origins_into_index.py
import json
import re
import unicodedata
from pathlib import Path

INDEX_FILE = "origins_index.json"                   # existant: {"origins":[{"id":..,"name":"..","image":"..?"}, ...]}
NEW_FILE   = "new_origins_missing_from_index.json"  # nouveaux: {"origins":[{"name":"..","flagUrl":"..?"}, ...]}
OUT_FILE   = "origins_index_updated.json"
REPORT     = "origins_index_merge_report.json"

def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(s).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    # charge fichiers
    idx_data = json.loads(Path(INDEX_FILE).read_text(encoding="utf-8"))
    new_data = json.loads(Path(NEW_FILE).read_text(encoding="utf-8"))
    idx_list = idx_data.get("origins", [])
    new_list = new_data.get("origins", [])

    # index existant par clé normalisée
    by_key = {}
    kept_existing = 0
    for o in idx_list:
        name = (o.get("name") or "").strip()
        if not name: 
            continue
        key = norm_key(name)
        # on conserve la 1re occurrence
        if key not in by_key:
            by_key[key] = {
                "name": name,
                "image": o.get("image", "") or ""
            }
            kept_existing += 1

    # intégrer les nouveaux (flagUrl -> image)
    added = 0
    updated_image = 0
    skipped_dupe = 0
    for o in new_list:
        name = (o.get("name") or "").strip()
        if not name:
            continue
        key = norm_key(name)
        flag = (o.get("flagUrl") or "").strip()
        if key in by_key:
            # déjà présent : si pas d'image dans l'existant et flag disponible → compléter
            if not by_key[key].get("image") and flag:
                by_key[key]["image"] = flag
                updated_image += 1
            else:
                skipped_dupe += 1
        else:
            by_key[key] = {
                "name": name,
                "image": flag
            }
            added += 1

    # reconstituer liste triée alpha et réattribuer ids
    items = [by_key[k] for k in sorted(by_key.keys())]
    for i, it in enumerate(items, start=1):
        it["id"] = i

    # sortie
    Path(OUT_FILE).write_text(json.dumps({"origins": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    # rapport
    report = {
        "existing_count": kept_existing,
        "new_input_count": len(new_list),
        "added": added,
        "updated_image_on_existing": updated_image,
        "duplicates_skipped": skipped_dupe,
        "output_count": len(items),
        "output_file": OUT_FILE
    }
    Path(REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # console
    print(f"✔ Fusion effectuée → {OUT_FILE}")
    print(f"   • existants conservés : {kept_existing}")
    print(f"   • nouveaux intégrés   : {added}")
    print(f"   • images complétées   : {updated_image}")
    print(f"   • doublons ignorés    : {skipped_dupe}")
    print(f"→ Rapport : {REPORT}")

if __name__ == "__main__":
    main()
