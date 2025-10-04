# build_breeds_json.py
import re
import json
import unicodedata
import pandas as pd
from typing import List

INFILE  = "dog_breeds_selected.csv"
OUTFILE = "breeds_clean.json"

# --- Liste blanche des couleurs (ordre important: les composés d'abord) ---
ALLOWED_COLORS = [
    "noir et fauve clair",
    "fauve clair et noir",
    "rouge et merle",
    "rouge et gris",
    "rouge et noir",
    "bleu et merle",
    "noir et rouge",
    "noir et gris",
    "citron et abricot",
    "gris et isabelle",
    "foie et blanc",
    "blanc et jaune",
    "jaune et foie",
    # simples
    "argenté","beige","noir","bleu","bringé","marron","champagne","chocolat",
    "fauve","doré","gris","isabelle","citron","foie","merle","orange","panaché",
    "rouge","sable","fauve clair","blanc","jaune",
]

# --- utilitaires ---
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_text(s: str) -> str:
    s = str(s or "")
    s = strip_accents(s).lower()
    # uniformise séparateurs
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
    s = re.sub(r"[;,/•|]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def is_empty(val: str) -> bool:
    if pd.isna(val): return True
    s = str(val).strip()
    return s == "" or s in {"-", "—", "n/a", "na", "none", "null"}

def parse_range_to_fmt(s: str, unit: str) -> str:
    """Extrait toutes les valeurs numériques (dot ou virgule), garde min & max, les renvoie 'min à max <unit>'."""
    # remplace les virgules décimales par des points
    txt = str(s)
    # parfois il y a des nombres du type '55–61' avec tirets
    nums = [w.replace(",", ".") for w in re.findall(r"\d+(?:[.,]\d+)?", txt)]
    vals = [float(x) for x in nums]
    if not vals:
        return ""  # rien à formater
    lo, hi = min(vals), max(vals)
    def fmt(x: float) -> str:
        return str(int(x)) if abs(x - int(x)) < 1e-9 else f"{x}".rstrip("0").rstrip(".")
    return f"{fmt(lo)} à {fmt(hi)} {unit}"

def extract_colors(raw_robe: str) -> List[str]:
    base = norm_text(raw_robe)
    # on normalise aussi la liste blanche pour comparer "sans accents"
    normalized_allowed = [(c, norm_text(c)) for c in ALLOWED_COLORS]
    # trier par longueur desc pour capter d'abord les composés
    normalized_allowed.sort(key=lambda t: len(t[1]), reverse=True)

    found = []
    used_spans = []  # pas indispensable, mais évite doublons d’overlap
    for original, needle in normalized_allowed:
        # recherche simple par sous-chaîne avec bordures approximatives
        # (on tolère qu'il soit entouré d'espaces ou ponctuation)
        pattern = re.compile(rf"(?<!\w){re.escape(needle)}(?!\w)")
        if pattern.search(base):
            if original not in found:
                found.append(original)
    return found

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")
    # garde uniquement les lignes complètes
    required = ["Nom", "Région", "Taille", "Poids", "Robe"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    mask_complete = df[required].applymap(lambda x: not is_empty(x)).all(axis=1)
    df = df[mask_complete].copy()

    # tri alphabétique par Nom (sans accents, insensible casse)
    df["Nom_norm"] = df["Nom"].map(lambda x: strip_accents(str(x)).casefold())
    df = df.sort_values("Nom_norm").drop(columns=["Nom_norm"]).reset_index(drop=True)

    breeds = []
    for idx, row in df.iterrows():
        name   = str(row["Nom"]).strip()
        origin = str(row["Région"]).strip()

        size   = parse_range_to_fmt(row["Taille"], "cm")
        weight = parse_range_to_fmt(row["Poids"], "kgs")
        robes  = extract_colors(row["Robe"])

        # si une normalisation a échoué (extraction vide), on re-sécurise en sautant la ligne
        if not (name and origin and size and weight and robes):
            # on skip si, après nettoyage, une info manque
            continue

        breeds.append({
            "id": idx + 1,  # id = ordre alphabétique (1-based)
            "breed": name,
            "features": {
                "origin": origin,
                "size":   size,
                "weight": weight,
                "robe":   robes
            }
        })

    data = {"breeds": breeds}

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✔ {OUTFILE} écrit ({len(breeds)} races).")

if __name__ == "__main__":
    main()
