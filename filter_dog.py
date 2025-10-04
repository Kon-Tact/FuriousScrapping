# filter_dogs.py
import sys
import pandas as pd

INFILE  = sys.argv[1] if len(sys.argv) > 1 else "dog_breeds_structured.csv"
OUTCSV  = "dog_breeds_selected.csv"
OUTTXT  = "dog_breeds_selected.txt"   # format "plat" : Nom, Région: ..., Taille: ...

# Aliases possibles rencontrés dans ton CSV
ALIASES = {
    "Nom": ["Nom", "Name"],
    "Région": [
        "Région", "Région d’origine", "Région d'origine",
        "Origin", "Země původu", "Région d'élevage"
    ],
    "Taille": [
        "Taille", "Height", "Výška*", "Hauteur"
    ],
    "Poids": [
        "Poids", "Weight", "Hmotnost"
    ],
    "Robe": [
        "Robe", "Color", "Colour", "Barva", "Coat", "Toison"
    ],
}

def pick_first_nonempty(row, candidates):
    for col in candidates:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    return ""

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")

    # Construire un DataFrame propre avec nos 5 colonnes
    out = pd.DataFrame()
    out["Nom"]    = df.apply(lambda r: pick_first_nonempty(r, ALIASES["Nom"]), axis=1)
    out["Région"] = df.apply(lambda r: pick_first_nonempty(r, ALIASES["Région"]), axis=1)
    out["Taille"] = df.apply(lambda r: pick_first_nonempty(r, ALIASES["Taille"]), axis=1)
    out["Poids"]  = df.apply(lambda r: pick_first_nonempty(r, ALIASES["Poids"]), axis=1)
    out["Robe"]   = df.apply(lambda r: pick_first_nonempty(r, ALIASES["Robe"]), axis=1)

    # Optionnel : retirer les lignes sans Nom
    out = out[out["Nom"].str.strip() != ""]

    # Sauvegarde CSV
    out.to_csv(OUTCSV, index=False, encoding="utf-8")
    print(f"✔ Écrit {OUTCSV} ({len(out)} lignes)")

    # Sauvegarde texte "plat" : Nom, Région: ..., Taille: ...
    with open(OUTTXT, "w", encoding="utf-8") as f:
        for _, r in out.iterrows():
            pieces = [r["Nom"]]
            if r["Région"]: pieces.append(f"Région: {r['Région']}")
            if r["Taille"]: pieces.append(f"Taille: {r['Taille']}")
            if r["Poids"]:  pieces.append(f"Poids: {r['Poids']}")
            if r["Robe"]:   pieces.append(f"Robe: {r['Robe']}")
            f.write(", ".join(pieces) + "\n")
    print(f"✔ Écrit {OUTTXT}")

if __name__ == "__main__":
    main()
