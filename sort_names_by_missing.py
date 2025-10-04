# sort_names_by_missing.py
import sys
import pandas as pd

INFILE = sys.argv[1] if len(sys.argv) > 1 else "dog_breeds_selected.csv"
OUTFILE = "dog_breeds_names_sorted.txt"

FIELDS = ["Région", "Taille", "Poids", "Robe"]

def is_empty(x: str) -> bool:
    if pd.isna(x):
        return True
    s = str(x).strip()
    return s == "" or s in {"-", "—", "N/A", "n/a", "na", "None", "null"}

def main():
    df = pd.read_csv(INFILE, dtype=str).fillna("")

    # Ajoute une colonne du nombre de champs manquants
    df["nb_manquantes"] = df[FIELDS].apply(lambda r: sum(is_empty(v) for v in r), axis=1)

    # Trie du plus de manquantes → moins
    df_sorted = df.sort_values(by=["nb_manquantes", "Nom"], ascending=[False, True])

    # Ne garde que la colonne Nom
    names = df_sorted["Nom"].tolist()

    # Écrit dans un fichier texte
    with open(OUTFILE, "w", encoding="utf-8") as f:
        for n in names:
            f.write(n + "\n")

    print(f"✔ Liste des noms triée écrite dans {OUTFILE}")
    print("Aperçu :")
    print("\n".join(names[:20]))

if __name__ == "__main__":
    main()
