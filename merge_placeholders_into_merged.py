# merge_placeholders_into_merged.py
import json, re, unicodedata
from pathlib import Path
from typing import Any, Dict, List

MAIN_FILE   = "breeds_merged_with_global_ids.json"   # principal (prioritaire)
GAPS_FILE   = "breeds_placeholders_for_gaps.json"    # ajouts / compléments
OUT_FILE    = "breeds_merged_final.json"
REPORT_FILE = "merge_placeholders_report.json"

def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_list(x) -> List[str]:
    if x is None: return []
    if isinstance(x, list):  return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):   return [x.strip()] if x.strip() else []
    s = str(x).strip()
    return [s] if s else []

def better_scalar(pref: str, alt: str) -> str:
    pref = (pref or "").strip()
    alt  = (alt or "").strip()
    return pref if pref else alt

def union_keep_order(primary: List[Any], secondary: List[Any]) -> List[Any]:
    out, seen = [], set()
    for v in (primary or []):
        if v not in seen:
            seen.add(v); out.append(v)
    for v in (secondary or []):
        if v not in seen:
            seen.add(v); out.append(v)
    return out

def normalize_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    # copie superficielle
    x = dict(e)

    # alias : accepte éventuellement un alias mal rangé dans features (on le remonte)
    feats_src = dict(x.get("features", {}) or {})
    alias_in_features = feats_src.pop("alias", None)
    x["features"] = feats_src

    alias_root = x.get("alias", None)
    alias_all = to_list(alias_root) + to_list(alias_in_features)
    x["alias"] = to_list(alias_all)

    # features : types & formats
    f = dict(x.get("features", {}) or {})
    f["origin"] = to_list(f.get("origin"))
    f["type"]   = to_list(f.get("type"))
    f["robe"]   = to_list(f.get("robe"))
    f["size"]   = (f.get("size") or "").strip()
    f["weight"] = (f.get("weight") or "").strip()
    f["poil"]   = (f.get("poil") or "").strip()
    f["energy"] = (f.get("energy") or "").strip()
    x["features"] = f

    # id -> int si possible
    if isinstance(x.get("id"), str) and x["id"].isdigit():
        x["id"] = int(x["id"])
    return x

def main():
    main_data = json.loads(Path(MAIN_FILE).read_text(encoding="utf-8")).get("breeds", [])
    gaps_data = json.loads(Path(GAPS_FILE).read_text(encoding="utf-8")).get("breeds", [])

    main_norm = [normalize_entry(b) for b in main_data]
    gaps_norm = [normalize_entry(b) for b in gaps_data]

    # index principal par id (clé obligatoire pour fusion)
    by_id: Dict[int, Dict[str,Any]] = {}
    for b in main_norm:
        bid = b.get("id")
        if bid is None:
            continue
        by_id[bid] = b

    added = 0
    fused = 0
    name_conflicts = []

    for g in gaps_norm:
        gid = g.get("id")
        if gid is None:
            continue
        if gid not in by_id:
            by_id[gid] = g
            added += 1
            continue

        base = by_id[gid]  # prioritaire
        # nom : garder celui du principal, mais reporter si différent
        if norm_key(base.get("breed","")) != norm_key(g.get("breed","")) and g.get("breed"):
            name_conflicts.append({
                "id": gid,
                "main_breed": base.get("breed",""),
                "gap_breed": g.get("breed","")
            })

        # alias : union (ordre du principal)
        base["alias"] = union_keep_order(to_list(base.get("alias")), to_list(g.get("alias")))

        # features : scalaires + listes
        bf, gf = dict(base.get("features", {}) or {}), dict(g.get("features", {}) or {})
        bf["size"]   = better_scalar(bf.get("size",""),   gf.get("size",""))
        bf["weight"] = better_scalar(bf.get("weight",""), gf.get("weight",""))
        bf["poil"]   = better_scalar(bf.get("poil",""),   gf.get("poil",""))
        bf["energy"] = better_scalar(bf.get("energy",""), gf.get("energy",""))

        bf["origin"] = union_keep_order(to_list(bf.get("origin")), to_list(gf.get("origin")))
        bf["type"]   = union_keep_order(to_list(bf.get("type")),   to_list(gf.get("type")))
        bf["robe"]   = union_keep_order(to_list(bf.get("robe")),   to_list(gf.get("robe")))

        base["features"] = bf
        by_id[gid] = base
        fused += 1

    # sortie triée par id
    out_list = [by_id[k] for k in sorted(by_id.keys())]
    Path(OUT_FILE).write_text(json.dumps({"breeds": out_list}, ensure_ascii=False, indent=2), encoding="utf-8")

    # rapport
    report = {
        "added_from_placeholders": added,
        "fused_with_placeholders": fused,
        "name_conflicts_count": len(name_conflicts),
        "name_conflicts_examples": name_conflicts[:20],
        "output": OUT_FILE
    }
    Path(REPORT_FILE).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ Fusion effectuée → {OUT_FILE}")
    print(f"   + Ajoutés (nouveaux IDs) : {added}")
    print(f"   * Fusionnés (ids existants): {fused}")
    if name_conflicts:
        print(f"   ⚠️ Conflits de nom: {len(name_conflicts)} (voir {REPORT_FILE})")
    print(f"→ Rapport : {REPORT_FILE}")

if __name__ == "__main__":
    main()
