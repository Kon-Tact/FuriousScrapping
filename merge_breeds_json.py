# merge_breeds_json.py
import json
import unicodedata
from pathlib import Path

IN1 = "breeds_clean_post.json"
IN2 = "breeds_incomplete_subset.json"
OUT = "breeds_merged.json"

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def norm_key(name: str) -> str:
    return strip_accents((name or "").strip()).casefold()

def cap_first(s: str) -> str:
    return (s[:1].upper() + s[1:]) if s else s

def better(a: str, b: str) -> str:
    """Retourne la valeur prioritaire : b si non vide, sinon a."""
    a = a if isinstance(a, str) else ""
    b = b if isinstance(b, str) else ""
    return b if b.strip() else a

def merge_robe(a_list, b_list):
    """Union simple en conservant l'ordre, priorité à b."""
    out, seen = [], set()
    for src in (b_list or []):  # priorité aux nouvelles valeurs
        if src not in seen:
            seen.add(src); out.append(src)
    for src in (a_list or []):
        if src not in seen:
            seen.add(src); out.append(src)
    return out

def load_breeds(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("breeds", [])

def main():
    a = load_breeds(IN1)  # fichier clean complet
    b = load_breeds(IN2)  # corrections/incomplets prioritaire

    merged = {}

    def add_or_merge(item, source_name):
        name = item.get("breed", "")
        key = norm_key(name)
        name_cap = cap_first(name.strip())

        if key not in merged:
            merged[key] = {
                "id": 0,
                "breed": name_cap,
                "features": {
                    "origin": item.get("features", {}).get("origin", ""),
                    "size":   item.get("features", {}).get("size", ""),
                    "weight": item.get("features", {}).get("weight", ""),
                    "robe":   item.get("features", {}).get("robe", []),
                }
            }
            return

        # fusion si déjà présent
        cur = merged[key]
        curF, newF = cur.get("features", {}), item.get("features", {})
        changed = []

        for field in ["origin", "size", "weight"]:
            old_val, new_val = curF.get(field, ""), newF.get(field, "")
            chosen = better(old_val, new_val)
            if chosen != old_val and new_val.strip():
                changed.append(f"{field}: '{old_val}' -> '{new_val}'")
            curF[field] = chosen

        # robe: union, mais priorité b
        old_robe, new_robe = curF.get("robe", []), newF.get("robe", [])
        merged_robe = merge_robe(old_robe, new_robe)
        if merged_robe != old_robe:
            changed.append(f"robe: {old_robe} -> {merged_robe}")
        curF["robe"] = merged_robe

        cur["features"] = curF
        cur["breed"] = cap_first(cur["breed"] or name_cap)

        if changed:
            print(f"⚡ Fusion '{cur['breed']}' (source {source_name}):")
            for c in changed:
                print("   -", c)

    # On passe d'abord fichier 1 (base), puis fichier 2 (prioritaire)
    for it in a:
        add_or_merge(it, "clean_post")
    for it in b:
        add_or_merge(it, "incomplete_subset")

    # tri alphabétique + réattribution des id
    items = list(merged.values())
    items.sort(key=lambda x: norm_key(x.get("breed", "")))
    for i, it in enumerate(items, 1):
        it["id"] = i

    Path(OUT).write_text(json.dumps({"breeds": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✔ Fusion terminée : {OUT}")
    print(f"  - Entrées fichier 1 : {len(a)}")
    print(f"  - Entrées fichier 2 : {len(b)}")
    print(f"  - Total fusionné    : {len(items)}")

if __name__ == "__main__":
    main()
