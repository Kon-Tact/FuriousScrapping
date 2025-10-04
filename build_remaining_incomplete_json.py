# build_remaining_incomplete_json.py
import re, json, unicodedata, math
import pandas as pd
from typing import List

INFILE  = "dog_breeds_sorted_by_missing.csv"
OUTFILE = "breeds_remaining_incomplete.json"

# ====== Ta liste (whitelist) à exclure ======
BREEDS_WHITELIST = [
    "Labrador","Bulldog Français","Berger Australien","Golden Retriever","Bulldog",
    "Caniche","Beagle","Rottweiler","Pointer Anglais","Teckel","Corgi","Yorkshire",
    "Boxer","Dogue Allemand","Husky","Cavalier King Charles","Dobermann",
    "Schnauzer Nain","Shih Tzu","Terrier de Boston","Bouvier Bernois","Spitz nain",
    "Bichon Havanais","Cane Corso","Springer Anglais","Berger des Shetland",
    "Epagneul Breton","Cocker","Carlin","Berger Americain miniature","Border Collie",
    "Mastiff","Chihuahua","Braque Hongrois a poil court","Basset Hound","Berger Belge",
    "Bichon Maltais","Braque de Weimer","Colley","Retriever de la Nouvelle-Écosse",
    "Jindo Coreen","Terrier irlandais à poil doux","Dogue de Bordeaux","Landseer",
    "Terrier Bresilien","Sussex Spaniel","Pudelpointer",
    "Retriever de la baie de Chesapeake","Terrier noir russe","Bouvier d'Appenzell",
]

# ====== Couleurs autorisées pour 'robe' ======
ALLOWED_COLORS = [
    "noir et fauve clair","fauve clair et noir","rouge et merle","rouge et gris",
    "rouge et noir","bleu et merle","noir et rouge","noir et gris","citron et abricot",
    "gris et isabelle","foie et blanc","blanc et jaune","jaune et foie",
    "argenté","beige","noir","bleu","bringé","marron","champagne","chocolat",
    "fauve","doré","gris","isabelle","citron","foie","merle","orange","panaché",
    "rouge","sable","fauve clair","blanc","jaune",
]

# -------- utils --------
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def norm_text(s: str) -> str:
    s = strip_accents(str(s or "")).lower()
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
    s = re.sub(r"[;,/•|]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def cap_first(s: str) -> str:
    return (s[:1].upper() + s[1:]) if s else s

def is_empty(x: str) -> bool:
    if pd.isna(x): return True
    s = str(x).strip()
    return s == "" or s in {"-", "—", "n/a", "na", "none", "null"}

def parse_range_to_fmt(s: str, unit: str) -> str:
    nums = [w.replace(",", ".") for w in re.findall(r"\d+(?:[.,]\d+)?", str(s or ""))]
    vals = [math.ceil(float(x)) for x in nums]
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    return f"~{hi} {unit}" if lo == hi else f"{lo} à {hi} {unit}"

def extract_colors(raw_robe: str) -> List[str]:
    base = norm_text(raw_robe)
    normalized_allowed = [(c, norm_text(c)) for c in ALLOWED_COLORS]
    normalized_allowed.sort(key=lambda t: len(t[1]), reverse=True)
    found = []
    for original, needle in normalized_allowed:
        if re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", base):
            if original not in found:
                found.append(original)
    return found

# -------- main --------
def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")
    for col in ["Nom","Région","Taille","Poids","Robe"]:
        if col not in df.columns: df[col] = ""

    # Normalisation de noms pour comparer sans accents/casse
    df["Nom_norm"] = df["Nom"].map(lambda x: strip_accents(str(x)).casefold())
    whitelist_norm = {strip_accents(n).casefold() for n in BREEDS_WHITELIST}

    # 1) Exclure la whitelist
    df = df[~df["Nom_norm"].isin(whitelist_norm)].copy()

    # 2) Garder uniquement celles avec AU MOINS une info manquante
    fields = ["Région","Taille","Poids","Robe"]
    has_missing = df[fields].applymap(is_empty).any(axis=1)
    df = df[has_missing].copy()

    # 3) Tri alpha (sans accents) → IDs 1..N
    df = df.sort_values("Nom_norm").reset_index(drop=True)

    out = []
    for i, r in df.iterrows():
        name   = cap_first(str(r["Nom"]).strip())
        origin = "" if is_empty(r["Région"]) else str(r["Région"]).strip()
        size   = "" if is_empty(r["Taille"]) else parse_range_to_fmt(r["Taille"], "cm")
        weight = "" if is_empty(r["Poids"])  else parse_range_to_fmt(r["Poids"],  "kgs")
        robe   = [] if is_empty(r["Robe"])   else extract_colors(r["Robe"])

        out.append({
            "id": i + 1,
            "breed": name,
            "features": {
                "origin": origin,
                "size": size,
                "weight": weight,
                "robe": robe
            }
        })

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump({"breeds": out}, f, ensure_ascii=False, indent=2)

    print(f"✔ {OUTFILE} écrit ({len(out)} races).")

if __name__ == "__main__":
    main()
