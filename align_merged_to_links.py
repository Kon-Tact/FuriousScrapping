# align_merged_to_links.py
import json
from pathlib import Path

LINKS_FILE   = "breeds_links_resorted.json"   # { "breeds": [ {id, breed, url?}, ... ] }
MERGED_FILE  = "breeds_merged_final.json"     # { "breeds": [ {id, breed, alias, features{...}}, ... ] }
OUT_FILE     = "breeds_merged_aligned.json"
REPORT_FILE  = "align_report.json"

def empty_entry(id_: int, breed_name: str) -> dict:
    return {
        "id": id_,
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
    }

def main():
    links_data  = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8"))
    merged_data = json.loads(Path(MERGED_FILE).read_text(encoding="utf-8"))

    links  = links_data.get("breeds", [])
    merged = merged_data.get("breeds", [])

    # index merged par id
    merged_by_id = {}
    dup_ids = set()
    for e in merged:
        bid = e.get("id")
        if bid in merged_by_id:
            dup_ids.add(bid)
        merged_by_id[bid] = e

    added = 0
    renamed = 0
    not_in_links = []  # ids présents dans merged mais absents de links

    # 1) garantir que chaque id de links est présent dans la sortie
    output_by_id = {}
    for link in links:
        lid = link.get("id")
        lbreed = (link.get("breed") or "").strip()

        if lid in merged_by_id:
            row = merged_by_id[lid]
            # si le nom diffère, remplacer par celui de links
            old_name = row.get("breed", "")
            if old_name != lbreed:
                row = dict(row)  # copie superficielle
                row["breed"] = lbreed
                renamed += 1
            output_by_id[lid] = row
        else:
            # ajouter une entrée squelette vide
            output_by_id[lid] = empty_entry(lid, lbreed)
            added += 1

    # 2) détecter les entrées en trop dans merged (id non présent dans links)
    link_ids = {b.get("id") for b in links}
    for e in merged:
        bid = e.get("id")
        if bid not in link_ids:
            not_in_links.append({"id": bid, "breed": e.get("breed", "")})
            # Si tu veux les conserver quand même, décommente la ligne suivante :
            # output_by_id[bid] = e

    # 3) trier par id et écrire
    out_list = [output_by_id[i] for i in sorted(output_by_id.keys())]
    Path(OUT_FILE).write_text(json.dumps({"breeds": out_list}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) rapport
    report = {
        "links_total": len(links),
        "merged_total": len(merged),
        "renamed_count": renamed,
        "added_placeholders_count": added,
        "duplicate_ids_in_merged": sorted(list(dup_ids)),
        "entries_in_merged_not_in_links_count": len(not_in_links),
        "entries_in_merged_not_in_links_examples": not_in_links[:20],
        "output_file": OUT_FILE
    }
    Path(REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # console
    print(f"✔ Alignement terminé → {OUT_FILE}")
    print(f"   • Races dans links  : {len(links)}")
    print(f"   • Races dans merged : {len(merged)}")
    print(f"   ↻ Noms remplacés     : {renamed}")
    print(f"   + Placeholders ajoutés : {added}")
    if dup_ids:
        print(f"   ⚠️ IDs dupliqués dans merged : {len(dup_ids)} (ex: {list(sorted(dup_ids))[:10]})")
    if not_in_links:
        print(f"   ⚠️ {len(not_in_links)} entrées de merged n'existent pas dans links (voir {REPORT_FILE})")
    print(f"→ Rapport : {REPORT_FILE}")

if __name__ == "__main__":
    main()
