# getwikipedia.py
import requests
import pandas as pd
from io import StringIO

URL = "https://commons.wikimedia.org/wiki/List_of_dog_breeds?uselang=fr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://commons.wikimedia.org/"
}

resp = requests.get(URL, headers=HEADERS, timeout=20)
resp.raise_for_status()

# Donne le HTML à pandas (évite l’appel direct à l’URL qui 403)
tables = pd.read_html(StringIO(resp.text))  # nécessite lxml ou html5lib
print(f"Tables trouvées : {len(tables)}")

# Si la page change, on peut cibler la table par son nombre de colonnes
target = next((df for df in tables if df.shape[1] >= 3), None)
if target is None:
    raise SystemExit("Aucune table avec >= 3 colonnes trouvée.")

# 3e colonne (index 2) = 'Local names' (noms locaux)
col3 = target.iloc[:, 2].astype(str).str.strip()
col3 = col3[col3 != ""].drop_duplicates().reset_index(drop=True)

# Sauvegarde
out = "local_names_dog_breeds.csv"
col3.to_csv(out, index=False, header=["local_names"])
print(f"{len(col3)} valeurs sauvegardées dans {out}")
print(col3.head(20).to_string(index=False))
