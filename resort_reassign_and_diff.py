# resort_reassign_and_diff.py
import json, re, unicodedata
from pathlib import Path

LINKS_IN   = "breeds_links_resorted.json"
MERGED_IN  = "breeds_merged_aligned.json"
LINKS_OUT  = "breeds_links_resorted_updated.json"
MERGED_OUT = "breeds_merged_alphabetical.json"
REPORT     = "resort_reassign_ids_report.json"

def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    # 1) Charger
    links_data  = json.loads(Path(LINKS_IN).read_text(encoding="utf-8"))
    merged_data = json.loads(Path(MERGED_IN).read_text(encoding="utf-8"))
    links  = links_data.get("breeds", [])
    merged = merged_data.get("breeds", [])

    # Nettoyage léger nom
    for b in links:
        if "breed" in b and isinstance(b["breed"], str):
            b["breed"] = b["breed"].strip()
    for b in merged:
        if "breed" in b and isinstance(b["breed"], str):
            b["breed"] = b["breed"].strip()

    # === A) DIFF AVANT MODIFS ===
    links_by_id  = {int(x["id"]): x for x in links if x.get("id") is not None}
    merged_by_id = {int(x["id"]): x for x in merged if x.get("id") is not None}

    # 1) manquants / extras (par ID)
    missing_in_merged = []
    for lid, lrow in links_by_id.items():
        if lid not in merged_by_id:
            missing_in_merged.append({"id": lid, "breed_links": lrow.get("breed","")})
    extras_in_merged = []
    for mid, mrow in merged_by_id.items():
        if mid not in links_by_id:
            extras_in_merged.append({"id": mid, "breed_merged": mrow.get("breed","")})

    # 2) mismatch de noms pour un même ID
    name_mismatches_by_id = []
    for bid, lrow in links_by_id.items():
        mrow = merged_by_id.get(bid)
        if not mrow:
            continue
        if norm_key(lrow.get("breed","")) != norm_key(mrow.get("breed","")):
            name_mismatches_by_id.append({
                "id": bid,
                "breed_links": lrow.get("breed",""),
                "breed_merged": mrow.get("breed","")
            })

    # 3) mismatch d’ID pour un même NOM (normalisé)
    links_name_to_id  = {}
    merged_name_to_id = {}
    dup_names_links = []
    dup_names_merged = []
    for x in links:
        k = norm_key(x.get("breed",""))
        if k in links_name_to_id and links_name_to_id[k] != x.get("id"):
            dup_names_links.append(x.get("breed",""))
        links_name_to_id.setdefault(k, x.get("id"))
    for x in merged:
        k = norm_key(x.get("breed",""))
        if k in merged_name_to_id and merged_name_to_id[k] != x.get("id"):
            dup_names_merged.append(x.get("breed",""))
        merged_name_to_id.setdefault(k, x.get("id"))

    id_mismatches_by_name = []
    all_names = set(links_name_to_id.keys()).intersection(set(merged_name_to_id.keys()))
    for k in sorted(all_names):
        lid = links_name_to_id.get(k)
        mid = merged_name_to_id.get(k)
        if lid != mid:
            id_mismatches_by_name.append({
                "name_norm": k,
                "id_links": lid,
                "id_merged": mid,
                "breed_links": next((x["breed"] for x in links if norm_key(x["breed"]) == k), ""),
                "breed_merged": next((x["breed"] for x in merged if norm_key(x["breed"]) == k), "")
            })

    # === B) RÉORDONNER LINKS & RÉASSIGNER IDs ===
    links_sorted = sorted(links, key=lambda x: norm_key(x.get("breed","")))
    id_changes_links = []
    for i, row in enumerate(links_sorted, start=1):
        old_id = row.get("id")
        if old_id != i:
            id_changes_links.append({"breed": row.get("breed",""), "old_id": old_id, "new_id": i})
        row["id"] = i

    # mapping nom normalisé -> NOUVEL id
    name_to_newid = {}
    duplicate_names_after_sort = []
    for row in links_sorted:
        k = norm_key(row.get("breed",""))
        if k in name_to_newid:
            duplicate_names_after_sort.append(row.get("breed",""))
        else:
            name_to_newid[k] = row["id"]

    # === C) APPLIQUER LES NOUVEAUX IDs AU MERGED (sans toucher aux autres champs) ===
    id_changes_merged = []
    not_found_in_links = []
    merged_corrected = []
    for item in merged:
        breed_name = (item.get("breed") or "").strip()
        k = norm_key(breed_name)
        new_id = name_to_newid.get(k)

        corrected = dict(item)  # on ne touche pas aux autres champs
        if new_id is None:
            not_found_in_links.append({"old_id": item.get("id"), "breed": breed_name})
            merged_corrected.append(corrected)
            continue

        old_id = corrected.get("id")
        if old_id != new_id:
            id_changes_merged.append({"breed": breed_name, "old_id": old_id, "new_id": new_id})
            corrected["id"] = new_id

        merged_corrected.append(corrected)

    merged_corrected.sort(key=lambda x: (x.get("id") is None, x.get("id") or 0, norm_key(x.get("breed",""))))

    # === D) ÉCRIRE SORTIES ===
    Path(LINKS_OUT).write_text(json.dumps({"breeds": links_sorted}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(MERGED_OUT).write_text(json.dumps({"breeds": merged_corrected}, ensure_ascii=False, indent=2), encoding="utf-8")

    # === E) RAPPORT COMPLET ===
    report = {
        "input_links_count": len(links),
        "input_merged_count": len(merged),

        # Diff AVANT modifs
        "diff_before": {
            "missing_in_merged_count": len(missing_in_merged),
            "extras_in_merged_count": len(extras_in_merged),
            "name_mismatches_by_id_count": len(name_mismatches_by_id),
            "id_mismatches_by_name_count": len(id_mismatches_by_name),
            "duplicate_names_in_links_count": len(dup_names_links),
            "duplicate_names_in_merged_count": len(dup_names_merged),
            "examples_missing_in_merged": missing_in_merged[:20],
            "examples_extras_in_merged": extras_in_merged[:20],
            "examples_name_mismatches_by_id": name_mismatches_by_id[:20],
            "examples_id_mismatches_by_name": id_mismatches_by_name[:20],
        },

        # Changements d'IDs suite au tri
        "reassign_after_sort": {
            "links_ids_changed_count": len(id_changes_links),
            "merged_ids_changed_count": len(id_changes_merged),
            "examples_links_ids_changed": id_changes_links[:20],
            "examples_merged_ids_changed": id_changes_merged[:20],
            "not_found_in_links_count": len(not_found_in_links),
            "examples_not_found_in_links": not_found_in_links[:20],
            "duplicate_names_after_sort_count": len(duplicate_names_after_sort),
            "examples_duplicate_names_after_sort": duplicate_names_after_sort[:20],
        },

        "outputs": {
            "links_output_file": LINKS_OUT,
            "merged_output_file": MERGED_OUT
        }
    }
    Path(REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Console résumé
    print("✔ Diff & ré-ordonnancement terminés.")
    print(f"   • Entrées: links={len(links)}, merged={len(merged)}")
    print("   ◦ Diff (avant):")
    print(f"     - Manquants (links→merged): {len(missing_in_merged)}")
    print(f"     - Extras (merged¬links)   : {len(extras_in_merged)}")
    print(f"     - Noms différents (même id): {len(name_mismatches_by_id)}")
    print(f"     - IDs différents (même nom): {len(id_mismatches_by_name)}")
    print("   ◦ Changements après tri:")
    print(f"     - IDs modifiés dans links : {len(id_changes_links)}")
    print(f"     - IDs modifiés dans merged: {len(id_changes_merged)}")
    if id_changes_merged[:10]:
        for r in id_changes_merged[:10]:
            print(f"       · {r['breed']}: {r['old_id']} → {r['new_id']}")
    if not_found_in_links:
        print(f"     - Introuvables dans links : {len(not_found_in_links)} (voir rapport)")
    print(f"→ Fichiers: {LINKS_OUT}, {MERGED_OUT}")
    print(f"→ Rapport : {REPORT}")

if __name__ == "__main__":
    main()
