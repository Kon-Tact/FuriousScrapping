# reconcile_remaining_and_merge.py
import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any

# --- Fichiers d'entrée/sortie ---
LINKS_FILE   = "breeds_links_resorted.json"                  # Référence ID+breed (+url)
RECENT_FILE  = "breeds_with_origin_list_and_type_updated.json"  # Fichier prioritaire
REMAIN_FILE  = "breeds_remaining_incomplete.json"            # Incomplets à corriger

OUT_STRUCT   = "breeds_remaining_incomplete_structured_2.json" # incomplets normalisés
OUT_MERGED   = "breeds_all_merged_2.json"                      # fusion finale

# --- Utils ---
def strip_accents(s: str) -> str:
    if s is None: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_key(s: str) -> str:
    s = strip_accents(str(s or "")).casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_list(x) -> List[str]:
    if x is None: return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):
        s = x.strip()
        return [s] if s else []
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
    """Prend pref si non vide, sinon alt."""
    pref = (pref or "").strip()
    alt  = (alt or "").strip()
    return pref if pref else alt

# --- Normalisation d'une race (structure finale unifiée) ---
def normalize_entry(raw: Dict[str, Any]) -> Dict[str, Any]:
    e = dict(raw)
    e["alias"] = to_list(e.get("alias"))

    feats = dict(e.get("features", {}) or {})
    # champs scalaires
    feats.setdefault("poil", "")
    feats.setdefault("energy", "")
    # listes
    feats["origin"] = to_list(feats.get("origin"))
    feats["type"]   = to_list(feats.get("type"))
    feats["robe"]   = to_list(feats.get("robe"))
    # size/weight restent des strings normalisées
    feats["size"]   = (feats.get("size") or "").strip()
    feats["weight"] = (feats.get("weight") or "").strip()

    e["features"] = feats
    # sécurité id
    if "id" in e and isinstance(e["id"], str) and e["id"].isdigit():
        e["id"] = int(e["id"])
    return e

def main():
    # 1) Charger références & données
    links = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8")).get("breeds", [])
    recent = json.loads(Path(RECENT_FILE).read_text(encoding="utf-8")).get("breeds", [])
    remaining = json.loads(Path(REMAIN_FILE).read_text(encoding="utf-8")).get("breeds", [])

    # 2) Index de référence par nom normalisé -> (id, breed, url, …)
    ref_by_name = {norm_key(b.get("breed","")): b for b in links if b.get("breed")}
    ref_by_id   = {b.get("id"): b for b in links if b.get("id") is not None}

    # 3) Corriger les incomplets (ids + noms) via la référence, puis normaliser la structure
    structured_remaining = []
    not_found = []
    for row in remaining:
        # trouver la référence par nom
        k = norm_key(row.get("breed",""))
        ref = ref_by_name.get(k)
        if not ref:
            not_found.append(row.get("breed",""))
            # on garde quand même, sans id si inconnu
            fixed_id = row.get("id")
            fixed_name = row.get("breed","").strip()
        else:
            fixed_id = ref.get("id")
            fixed_name = ref.get("breed","").strip()

        fixed = dict(row)
        fixed["id"] = fixed_id
        fixed["breed"] = fixed_name
        structured_remaining.append(normalize_entry(fixed))

    Path(OUT_STRUCT).write_text(
        json.dumps({"breeds": structured_remaining}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✔ Écrit {OUT_STRUCT} ({len(structured_remaining)} races).")
    if not_found:
        print(f"⚠️ Non trouvés dans la référence ({len(not_found)}): "
              + ", ".join(not_found[:10]) + (" ..." if len(not_found) > 10 else ""))

    # 4) Normaliser aussi le fichier “récent” (au cas où)
    recent_norm = [normalize_entry(x) for x in recent]

    # 5) Fusion avec priorité au fichier récent
    #    Clé de fusion = id si dispo, sinon nom normalisé.
    merged: Dict[str, Dict[str,Any]] = {}

    def key_for(e: Dict[str,Any]) -> str:
        if e.get("id") is not None:
            return f"id:{int(e['id'])}"
        return f"name:{norm_key(e.get('breed',''))}"

    # a) injecter le récent en premier (priorité)
    for e in recent_norm:
        merged[key_for(e)] = e

    # b) injecter les incomplets structurés : compléter ce qui manque
    for e in structured_remaining:
        k = key_for(e)
        if k not in merged:
            merged[k] = e
            continue

        base = merged[k]  # prioritaire (récent)
        # racine
        base["id"]    = base.get("id") if base.get("id") is not None else e.get("id")
        base["breed"] = base.get("breed") or e.get("breed")
        base["alias"] = union_keep_order(to_list(base.get("alias")), to_list(e.get("alias")))

        # features
        bf = dict(base.get("features", {}) or {})
        ef = dict(e.get("features", {}) or {})

        # scalaires: on garde non vide du récent, sinon celui des incomplets
        bf["size"]   = better_scalar(bf.get("size",""),   ef.get("size",""))
        bf["weight"] = better_scalar(bf.get("weight",""), ef.get("weight",""))
        bf["poil"]   = better_scalar(bf.get("poil",""),   ef.get("poil",""))
        bf["energy"] = better_scalar(bf.get("energy",""), ef.get("energy",""))

        # listes: union, priorité à l'ordre du récent
        bf["origin"] = union_keep_order(to_list(bf.get("origin")), to_list(ef.get("origin")))
        bf["type"]   = union_keep_order(to_list(bf.get("type")),   to_list(ef.get("type")))
        bf["robe"]   = union_keep_order(to_list(bf.get("robe")),   to_list(ef.get("robe")))

        base["features"] = bf
        merged[k] = normalize_entry(base)

    # 6) Liste finale, tri par id si présent (sinon par nom)
    items = list(merged.values())
    items.sort(key=lambda x: (9999999 if x.get("id") is None else int(x["id"]), norm_key(x.get("breed",""))))

    Path(OUT_MERGED).write_text(
        json.dumps({"breeds": items}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✔ Écrit {OUT_MERGED} ({len(items)} races).")

if __name__ == "__main__":
    main()
