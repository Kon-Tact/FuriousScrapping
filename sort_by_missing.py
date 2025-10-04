# sort_by_missing.py
import sys
import pandas as pd

INFILE = sys.argv[1] if len(sys.argv) > 1 else "dog_breeds_selected.csv"
OUTFILE = "dog_breeds_sorted_by_missing.csv"

# Colonnes à contrôler (adapte si nécessaire)
FIELDS = ["Région", "Taille", "Poids", "Robe"]

def is_empty(x: str) -> bool:
    if pd.isna(x):
        return True
    s = str(x).strip()
    return s == "" or s in {"-", "—", "N/A", "n/a", "na", "None", "null"}

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")
    # s'assure qu'on a les colonnes (au minimum Nom + champs)
    for col in ["Nom"] + FIELDS:
        if col not in df.columns:
            df[col] = ""

    # calcule nb manquantes + la liste des champs manquants
    df["nb_manquantes"] = df[FIELDS].apply(lambda r: sum(is_empty(v) for v in r), axis=1)
    df["infos_manquantes"] = df[FIELDS].apply(
        lambda r: ", ".join(c for c, v in zip(FIELDS, r) if is_empty(v)) if any(is_empty(v) for v in r) else "",
        axis=1
    )

    # tri : plus manquantes -> moins manquantes, puis par Nom (alpha)
    df_sorted = df.sort_values(by=["nb_manquantes", "Nom"], ascending=[False, True])

    df_sorted.to_csv(OUTFILE, index=False, encoding="utf-8")
    print(f"✔ Tri effectué. Fichier écrit : {OUTFILE}")

    # Petit récap
    counts = df_sorted["nb_manquantes"].value_counts().sort_index(ascending=False)
    print("\nRépartition par nb_manquantes (du plus manquant au moins manquant) :")
    for k, v in counts.items():
        print(f"  {k} manquantes : {v} races")

if __name__ == "__main__":
    main()
