# merge_two_breed_jsons.py
import json, re, unicodedata
from pathlib import Path
from typing import Any, List, Dict

RECENT_FILE = "breeds_with_origin_list_and_type_updated.json"
INCOMPLETE_FILE = "breeds_remaining_incomplete_structured.json"
OUT_FILE = "breeds_merged.json"

def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_list(x) -> List[Any]:
    if x is None: return []
    if isinstance(x, list): return [v for v in x if (str(v).strip() if isinstance(v, str) else True)]
    if isinstance(x, str):  return [x.strip()] if x.strip() else []
    s = str(x).strip()
    return [s] if s else []

def union_keep_order(primary: List[Any], secondary: List[Any]) -> List[Any]:
    out, seen = [], set()
    for v in (primary or []):
        if v not in seen:
            seen.add(v); out.append(v)
    for v in (secondary or []):
        if v not in seen:
            seen.add(v); out.append(v)
    return out

def better_scalar(pref: str, alt: str) -> str:
    pref = (pref or "").strip()
    alt  = (alt or "").strip()
    return pref if pref else alt

def normalize_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    # copie légère + garde la structure cible
    x = dict(e)
    x["alias"] = to_list(x.get("alias"))
    f = dict(x.get("features", {}) or {})
    f["origin"] = to_list(f.get("origin"))
    f["type"]   = to_list(f.get("type"))
    f["robe"]   = to_list(f.get("robe"))
    f["size"]   = (f.get("size") or "").strip()
    f["weight"] = (f.get("weight") or "").strip()
    f["poil"]   = (f.get("poil") or "").strip()
    f["energy"] = (f.get("energy") or "").strip()
    x["features"] = f
    if isinstance(x.get("id"), str) and x["id"].isdigit():
        x["id"] = int(x["id"])
    return x

def key_for(e: Dict[str, Any]) -> str:
    if e.get("id") is not None:
        return f"id:{int(e['id'])}"
    return f"name:{norm_key(e.get('breed',''))}"

def main():
    recent = json.loads(Path(RECENT_FILE).read_text(encoding="utf-8")).get("breeds", [])
    incom = json.loads(Path(INCOMPLETE_FILE).read_text(encoding="utf-8")).get("breeds", [])

    recent = [normalize_entry(x) for x in recent]
    incom  = [normalize_entry(x) for x in incom]

    merged: Dict[str, Dict[str, Any]] = {}

    # 1) Injecte le "récent" (prioritaire)
    for e in recent:
        merged[key_for(e)] = e

    # 2) Complète avec l'incomplet
    for e in incom:
        k = key_for(e)
        if k not in merged:
            merged[k] = e
            continue

        base = merged[k]               # prioritaire
        base["id"]    = base.get("id") if base.get("id") is not None else e.get("id")
        base["breed"] = base.get("breed") or e.get("breed")
        base["alias"] = union_keep_order(to_list(base.get("alias")), to_list(e.get("alias")))

        bf, ef = dict(base["features"]), dict(e["features"])
        # scalaires (non vide du récent, sinon autre)
        bf["size"]   = better_scalar(bf.get("size",""),   ef.get("size",""))
        bf["weight"] = better_scalar(bf.get("weight",""), ef.get("weight",""))
        bf["poil"]   = better_scalar(bf.get("poil",""),   ef.get("poil",""))
        bf["energy"] = better_scalar(bf.get("energy",""), ef.get("energy",""))
        # listes (union)
        bf["origin"] = union_keep_order(bf.get("origin", []), ef.get("origin", []))
        bf["type"]   = union_keep_order(bf.get("type",   []), ef.get("type",   []))
        bf["robe"]   = union_keep_order(bf.get("robe",   []), ef.get("robe",   []))

        base["features"] = bf
        merged[k] = base

    # 3) Tri & sortie
    items = list(merged.values())
    items.sort(key=lambda x: (9999999 if x.get("id") is None else int(x["id"]), norm_key(x.get("breed",""))))

    Path(OUT_FILE).write_text(json.dumps({"breeds": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ Fusion effectuée → {OUT_FILE}")
    print(f"   - entrées 'récent' : {len(recent)}")
    print(f"   - entrées 'incomplet' : {len(incom)}")
    print(f"   - total fusionné : {len(items)}")

if __name__ == "__main__":
    main()
