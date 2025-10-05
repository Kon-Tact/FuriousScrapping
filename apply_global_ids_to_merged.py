# apply_global_ids_to_merged.py
import json
import re
import unicodedata
from pathlib import Path

LINKS_FILE = "breeds_links_resorted.json"   # source de vérité des IDs
MERGED_FILE = "breeds_merged.json"          # à corriger
OUT_FILE = "breeds_merged_with_global_ids.json"
REPORT_FILE = "apply_global_ids_report.json"

SORT_BY_ID = True  # met True pour trier le résultat par ID croissant

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(s).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    # 1) Charger les fichiers
    links_data = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8"))
    merged_data = json.loads(Path(MERGED_FILE).read_text(encoding="utf-8"))

    links = links_data.get("breeds", [])
    merged = merged_data.get("breeds", [])

    # 2) Mapping nom normalisé -> ID global (+ nom d’origine pour log)
    name_to_id = {norm_key(b["breed"]): int(b["id"])
                  for b in links if b.get("breed") and b.get("id") is not None}

    # 3) Appliquer / corriger les IDs
    updated = 0
    already_ok = 0
    missing_in_links = []
    mismatches = []  # pour log: (old_id, new_id, breed)

    for item in merged:
        breed_name = (item.get("breed") or "").strip()
        key = norm_key(breed_name)

        global_id = name_to_id.get(key)
        if global_id is None:
            missing_in_links.append(breed_name)
            continue

        cur_id = item.get("id")
        if cur_id is None or (isinstance(cur_id, str) and not cur_id.isdigit()):
            item["id"] = int(global_id)
            updated += 1
            mismatches.append({"breed": breed_name, "old_id": cur_id, "new_id": global_id})
        else:
            cur_id = int(cur_id)
            if cur_id != global_id:
                item["id"] = int(global_id)
                updated += 1
                mismatches.append({"breed": breed_name, "old_id": cur_id, "new_id": global_id})
            else:
                already_ok += 1

    # 4) Tri optionnel par ID (puis nom)
    if SORT_BY_ID:
        merged.sort(key=lambda x: (x.get("id") is None, x.get("id") or 0, norm_key(x.get("breed",""))))

    # 5) Écrire la sortie + rapport
    Path(OUT_FILE).write_text(json.dumps({"breeds": merged}, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "updated_count": updated,
        "already_ok": already_ok,
        "missing_in_links_count": len(missing_in_links),
        "missing_in_links_examples": missing_in_links[:20],
        "changes": mismatches[:50],  # on tronque l’aperçu
        "output_file": OUT_FILE
    }
    Path(REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6) Console summary
    print(f"✔ IDs appliqués depuis {LINKS_FILE} vers {MERGED_FILE}")
    print(f"   ↳ Modifiés      : {updated}")
    print(f"   ↳ Déjà OK       : {already_ok}")
    print(f"   ↳ Introuvables  : {len(missing_in_links)} (voir {REPORT_FILE})")
    if mismatches[:10]:
        print("   Exemples de corrections :")
        for ex in mismatches[:10]:
            print(f"     - {ex['breed']}: {ex['old_id']} -> {ex['new_id']}")
    print(f"→ Écrit : {OUT_FILE}")
    print(f"→ Rapport : {REPORT_FILE}")

if __name__ == "__main__":
    main()
