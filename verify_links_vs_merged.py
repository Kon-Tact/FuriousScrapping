# verify_links_vs_merged.py
import json, re, unicodedata, csv
from pathlib import Path

LINKS_FILE  = "breeds_links_resorted.json"     # source de vérité {breeds:[{id,breed,url?}, ...]}
MERGED_FILE = "breeds_merged_aligned.json"       # fichier vérifié {breeds:[{id,breed,alias,features...}, ...]}
OUT_JSON    = "coverage_report2.json"
OUT_CSV     = "coverage_report2.csv"

def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(s).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def main():
    links = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8")).get("breeds", [])
    merged = json.loads(Path(MERGED_FILE).read_text(encoding="utf-8")).get("breeds", [])

    # Index par ID
    links_by_id  = {int(b["id"]): b for b in links if b.get("id") is not None}
    merged_by_id = {}
    merged_dupes = []
    for b in merged:
        bid = b.get("id")
        if bid is None:
            continue
        if bid in merged_by_id:
            merged_dupes.append(bid)
        merged_by_id[bid] = b

    missing_in_merged = []   # dans links mais pas dans merged
    name_mismatches   = []   # même id mais nom différent (normalisation)
    extras_in_merged  = []   # id présent dans merged mais pas dans links

    for lid, lrow in links_by_id.items():
        mrow = merged_by_id.get(lid)
        if not mrow:
            missing_in_merged.append({"id": lid, "breed_links": lrow.get("breed","")})
            continue
        # comparer noms normalisés
        nb = norm_key(lrow.get("breed",""))
        mb = norm_key(mrow.get("breed",""))
        if nb != mb:
            name_mismatches.append({
                "id": lid,
                "breed_links": lrow.get("breed",""),
                "breed_merged": mrow.get("breed","")
            })

    # extras (IDs dans merged non présents dans links)
    links_ids = set(links_by_id.keys())
    for mid, mrow in merged_by_id.items():
        if mid not in links_ids:
            extras_in_merged.append({"id": mid, "breed_merged": mrow.get("breed","")})

    # Résumé
    report = {
        "links_count": len(links_by_id),
        "merged_count": len([b for b in merged if b.get("id") is not None]),
        "missing_in_merged_count": len(missing_in_merged),
        "name_mismatches_count": len(name_mismatches),
        "duplicate_ids_in_merged_count": len(set(merged_dupes)),
        "extras_in_merged_count": len(extras_in_merged),
        "missing_in_merged": sorted(missing_in_merged, key=lambda x: x["id"])[:200],
        "name_mismatches": sorted(name_mismatches, key=lambda x: x["id"])[:200],
        "duplicate_ids_in_merged": sorted(list(set(merged_dupes)))[:200],
        "extras_in_merged": sorted(extras_in_merged, key=lambda x: x["id"])[:200],
    }

    Path(OUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV (une ligne par problème)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["issue","id","breed_links","breed_merged"])
        for r in missing_in_merged:
            w.writerow(["missing_in_merged", r["id"], r.get("breed_links",""), ""])
        for r in name_mismatches:
            w.writerow(["name_mismatch", r["id"], r.get("breed_links",""), r.get("breed_merged","")])
        for rid in sorted(set(merged_dupes)):
            w.writerow(["duplicate_id_in_merged", rid, "", ""])
        for r in extras_in_merged:
            w.writerow(["extra_in_merged", r["id"], "", r.get("breed_merged","")])

    # Console
    print(f"✔ Vérification terminée")
    print(f"   • Races dans links  : {report['links_count']}")
    print(f"   • Races dans merged : {report['merged_count']}")
    print(f"   ❌ Manquants (links→merged)  : {report['missing_in_merged_count']}")
    print(f"   ⚠️  Noms différents (même id) : {report['name_mismatches_count']}")
    print(f"   ⚠️  IDs dupliqués (merged)    : {report['duplicate_ids_in_merged_count']}")
    print(f"   ⚠️  Extras (merged¬links)     : {report['extras_in_merged_count']}")
    if report['missing_in_merged_count']:
        ex = report["missing_in_merged"][:5]
        print("   Exemples manquants :", ", ".join(f"{e['id']}:{e['breed_links']}" for e in ex))
    if report['name_mismatches_count']:
        ex = report["name_mismatches"][:5]
        print("   Exemples mismatchs :", ", ".join(f"{e['id']}:{e['breed_links']}→{e['breed_merged']}" for e in ex))
    print(f"→ Rapport JSON : {OUT_JSON}")
    print(f"→ Rapport CSV  : {OUT_CSV}")

if __name__ == "__main__":
    main()
