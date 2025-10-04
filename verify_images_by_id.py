# verify_images_by_id.py
import json
import csv
from pathlib import Path
import glob

JSON_FILE = "breeds_with_global_ids.json"
IMAGES_DIR = Path("images")
MISSING_OUT = "missing_images.json"
REPORT_CSV = "image_check_report.csv"

EXTS = ("jpg", "jpeg", "png")  # extensions acceptées

def candidates_for_id(bid: int):
    """Génère des patterns glob pour un id, paddé et non paddé."""
    pad = f"{bid:03d}_*"
    nop = f"{bid}_*"
    pats = []
    for ext in EXTS:
        pats.append(str(IMAGES_DIR / f"{pad}.{ext}"))
        pats.append(str(IMAGES_DIR / f"{nop}.{ext}"))
    return pats

def find_matches(bid: int):
    matches = []
    for pat in candidates_for_id(bid):
        matches.extend(glob.glob(pat))
    # dédoublonne en gardant l'ordre
    seen = set()
    uniq = []
    for m in matches:
        if m not in seen:
            seen.add(m); uniq.append(m)
    return uniq

def is_file_ok(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except Exception:
        return False

def main():
    data = json.loads(Path(JSON_FILE).read_text(encoding="utf-8"))
    breeds = data.get("breeds", [])

    if not IMAGES_DIR.exists():
        print(f"⚠️ Dossier {IMAGES_DIR} introuvable.")
        return

    report_rows = []
    missing = []

    ok_count = 0
    multi_count = 0

    for item in breeds:
        bid = int(item.get("id"))
        name = item.get("breed", "").strip()

        matches = find_matches(bid)
        # garde seulement fichiers OK (taille > 0)
        ok_matches = [m for m in matches if is_file_ok(Path(m))]

        status = "missing"
        chosen = ""

        if len(ok_matches) == 1:
            status = "ok"
            chosen = ok_matches[0]
            ok_count += 1
        elif len(ok_matches) > 1:
            status = "multiple"
            # on peut choisir le .jpg de préférence si présent
            jpgs = [m for m in ok_matches if m.lower().endswith(".jpg") or m.lower().endswith(".jpeg")]
            chosen = (jpgs[0] if jpgs else ok_matches[0])
            multi_count += 1
        else:
            missing.append({"id": bid, "breed": name})

        report_rows.append({
            "id": bid,
            "breed": name,
            "status": status,
            "chosen_file": chosen,
            "all_matches": ";".join(matches) if matches else ""
        })

    # Export JSON des manquants
    Path(MISSING_OUT).write_text(json.dumps({"missing": missing}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Export CSV du rapport complet
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","breed","status","chosen_file","all_matches"])
        w.writeheader()
        w.writerows(report_rows)

    total = len(breeds)
    print(f"✔ Vérification terminée sur {total} races")
    print(f"   ✓ OK           : {ok_count}")
    print(f"   ⚠️ Multiples    : {multi_count}")
    print(f"   ❌ Manquants    : {len(missing)}")
    if missing[:10]:
        print("   Exemples manquants :", ", ".join(f"{m['id']:03d}_{m['breed']}" for m in missing[:10]))
    print(f"→ Détails CSV : {REPORT_CSV}")
    print(f"→ Manquants   : {MISSING_OUT}")

if __name__ == "__main__":
    main()
