import json
import re
from pathlib import Path

IMAGES_DIR = Path("images")
LINKS_FILE = "breeds_links.json"
OUT_FILE = "breeds_links_fixed.json"

def cap_first(s: str) -> str:
    return (s[:1].upper() + s[1:]) if s else s

def fix_image_names():
    renamed = []
    for p in IMAGES_DIR.glob("*.*"):
        name = p.name
        m = re.match(r"^(\d+)_([^.]+)(\.[^.]+)$", name)
        if not m:
            continue
        bid, breed, ext = m.groups()
        # Majuscule après underscore
        fixed_breed = cap_first(breed)
        new_name = f"{int(bid):03d}_{fixed_breed}{ext.lower()}"
        new_path = p.with_name(new_name)
        if new_path != p:
            p.rename(new_path)
            renamed.append((p.name, new_path.name))
    return renamed

def fix_json_breeds():
    data = json.loads(Path(LINKS_FILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])
    changed = []
    for b in breeds:
        old = b.get("breed","")
        new = cap_first(old.strip())
        if new != old:
            b["breed"] = new
            changed.append((old, new))
    Path(OUT_FILE).write_text(json.dumps({"breeds": breeds}, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed

def main():
    if not IMAGES_DIR.exists():
        print(f"⚠️ Le dossier {IMAGES_DIR} n’existe pas, pas de renommage d’images.")
    else:
        renamed = fix_image_names()
        print(f"✔ Renommage d’images terminé ({len(renamed)} fichiers modifiés)")
        for old,new in renamed[:10]:
            print(f"   {old} -> {new}")

    if not Path(LINKS_FILE).exists():
        print(f"⚠️ Fichier {LINKS_FILE} introuvable.")
    else:
        changed = fix_json_breeds()
        print(f"✔ JSON corrigé ({len(changed)} noms modifiés) → {OUT_FILE}")
        for old,new in changed[:10]:
            print(f"   {old} -> {new}")

if __name__ == "__main__":
    main()
