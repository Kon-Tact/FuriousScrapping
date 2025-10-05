# bump_image_ids.py
import re
from pathlib import Path

IMAGES_DIR = Path("images")  # dossier des images
MIN_ID = 114    # inclut 114_Carolina_Dog.jpg
MAX_ID = 148    # inclut 148_Chien_de_Castro_Laboreiro.jpg
DELTA  = 1      # +1
DRY_RUN = False  # fais un test d'abord !

# Fichiers pris en compte
PATTERN = re.compile(r"^(\d+)_([^.]+)\.(jpg|jpeg|png)$", re.IGNORECASE)

def in_range(n: int) -> bool:
    if MIN_ID is not None and n < MIN_ID: return False
    if MAX_ID is not None and n > MAX_ID: return False
    return True

def main():
    if not IMAGES_DIR.exists():
        print(f"❌ Dossier introuvable: {IMAGES_DIR}")
        return

    files = [p for p in IMAGES_DIR.iterdir() if p.is_file() and PATTERN.match(p.name)]
    if not files:
        print("Aucun fichier correspondant.")
        return

    # 1) Construire les renommages cibles
    plans = []
    for p in files:
        m = PATTERN.match(p.name)
        old_id_str, rest, ext = m.groups()
        width = len(old_id_str)
        old_id = int(old_id_str)
        if not in_range(old_id):
            continue
        new_id = old_id + DELTA
        new_name = f"{str(new_id).zfill(width)}_{rest}.{ext.lower()}"
        plans.append((p, p.with_name(new_name)))

    if not plans:
        print("Rien à renommer pour l’intervalle demandé.")
        return

    # 2) Phase temporaire (éviter les collisions)
    temp_map = []
    for src, dst in plans:
        tmp = src.with_name(f"__tmp__{src.name}")
        if DRY_RUN:
            print(f"[DRY] {src.name} -> {dst.name}")
        else:
            src.rename(tmp)
        temp_map.append((tmp, dst))

    if DRY_RUN:
        print(f"[DRY] {len(plans)} fichiers seraient renommés.")
        return

    # 3) Phase finale
    renamed = 0
    for tmp, dst in temp_map:
        if dst.exists():
            dst.unlink()  # overwrite si besoin
        tmp.rename(dst)
        renamed += 1
        print(f"✓ {dst.name}")

    print(f"✔ Fini : {renamed} fichiers renommés (+{DELTA}).")

if __name__ == "__main__":
    main()
