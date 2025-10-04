# fix_capfirst_images_and_json.py
import json, re
from pathlib import Path

IMAGES_DIR = Path("images")
JSON_FILES = [Path("breeds_links.json")]   # ajoute ici d'autres JSON si besoin
OUT_SUFFIX = "_fixed"                      # écrit p.ex. breeds_links_fixed.json

def cap_first(s: str) -> str:
    s = s or ""
    return (s[:1].upper() + s[1:]) if s else s

def rename_images_capfirst(images_dir: Path):
    """
    Renomme ID_nom.ext -> ID_Nom.ext en ne capitalisant que la 1re lettre du segment nom.
    Compatible Windows (double hop).
    """
    pat = re.compile(r"^(\d{1,})_([^.]+)\.(jpg|jpeg|png)$", re.IGNORECASE)
    changed = 0; skipped = 0; problems = 0

    if not images_dir.exists():
        print(f"⚠️  Dossier {images_dir} introuvable.")
        return

    for p in images_dir.iterdir():
        if not p.is_file():
            continue
        m = pat.match(p.name)
        if not m:
            continue

        bid, breed_seg, ext = m.groups()
        # capitaliser uniquement la 1re lettre du segment (laisser underscores/traits tels quels)
        new_breed = cap_first(breed_seg)
        new_name  = f"{int(bid):03d}_{new_breed}.{ext.lower()}"

        if new_name == p.name:
            skipped += 1
            continue

        try:
            tmp = p.with_name(f"__tmp__{p.name}")  # double renommage pour forcer la casse
            p.rename(tmp)
            dest = p.with_name(new_name)
            if dest.exists():
                dest.unlink()  # overwrite
            tmp.rename(dest)
            changed += 1
            print(f"✓ {p.name} -> {dest.name}")
        except Exception as e:
            problems += 1
            print(f"✗ {p.name} : {e}")

    print(f"Images: {changed} renommées, {skipped} inchangées, {problems} erreurs.")

def fix_json_capfirst(json_path: Path):
    if not json_path.exists():
        print(f"⚠️  {json_path} introuvable.")
        return
    data = json.loads(json_path.read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])
    changed = 0
    for b in breeds:
        old = (b.get("breed") or "")
        new = cap_first(old.strip())
        if new != old:
            b["breed"] = new
            changed += 1
    out_path = json_path.with_name(json_path.stem + OUT_SUFFIX + json_path.suffix)
    out_path.write_text(json.dumps({"breeds": breeds}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {changed} noms corrigés → {out_path.name}")

if __name__ == "__main__":
    rename_images_capfirst(IMAGES_DIR)
    for jf in JSON_FILES:
        fix_json_capfirst(jf)
