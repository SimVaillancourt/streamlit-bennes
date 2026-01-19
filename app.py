import streamlit as st
import pandas as pd
from PIL import Image


# --- Configuration de la page ---
st.set_page_config(
    page_title="Validation Bennes",
    page_icon="logo.jpg",  # favicon dans l'onglet
    layout="wide"          # permet de mieux gérer les colonnes
)

# --- Charger le logo ---
logo = Image.open("logo.jpg")

# --- Placer le logo en haut à gauche ---
col1, col2 = st.columns([1, 5])  # colonne 1 petite pour le logo, colonne 2 pour le reste

with col1:
    st.image(logo, width=300)  # plus gros logo

with col2:
    st.title("Validation des options de bennes")  # titre à côté du logo

# --- 1. Charger les fichiers CSV ---
options_df = pd.read_csv("options.csv")  # Colonnes : Benne, Longueur, TypePorte, Option
regles_df = pd.read_csv("regles.csv")    # Colonnes : Option, Statut

# Nettoyer les colonnes
options_df.columns = options_df.columns.str.strip()
regles_df.columns = regles_df.columns.str.strip()


# --- 2. Listes de validation ---
bonnes_options = regles_df[regles_df["Statut"] == "Bon"]["Option"].tolist()
mauvaises_options = regles_df[regles_df["Statut"] == "Mauvais"]["Option"].tolist()

# --- 3. Sélecteurs pour filtrer la benne ---
st.header("Sélectionnez votre benne")

type_benne = st.selectbox(
    "Type de benne",
    options_df["Benne"].unique()
)

longueur_benne = st.selectbox(
    "Longueur (pieds)",
    sorted(options_df["Longueur"].unique())
)

type_porte = st.selectbox(
    "Type de porte",
    options_df["TypePorte"].unique()
)

# --- 4. Bouton de validation ---
if st.button("Valider"):

    # Filtrer le dataframe selon les choix
    filtre = options_df[
        (options_df["Benne"] == type_benne) &
        (options_df["Longueur"] == int(longueur_benne)) &
        (options_df["TypePorte"] == type_porte)
    ]

    if filtre.empty:
        st.warning("Aucune option trouvée pour cette combinaison.")
    else:
        # Déterminer le statut pour chaque option
        def valider_option(option):
            if option in bonnes_options:
                return "✅ Bon"
            elif option in mauvaises_options:
                return "❌ Mauvais"
            else:
                return "🟨 À valider"

        filtre["Statut"] = filtre["Option"].apply(valider_option)

        # Affichage du tableau coloré
        st.markdown(
            "✅ Vert = Bon | ❌ Rouge = Mauvais | 🟨 Jaune = À valider"
        )

        def color_row(row):
            if row["Statut"] == "✅ Bon":
                return ['background-color: lightgreen']*len(row)
            elif row["Statut"] == "❌ Mauvais":
                return ['background-color: salmon']*len(row)
            else:
                return ['background-color: yellow']*len(row)

        st.dataframe(filtre.style.apply(color_row, axis=1))
