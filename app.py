import streamlit as st
import pandas as pd
from PIL import Image

# --- Configuration page ---
st.set_page_config(
    page_title="Validation Bennes",
    page_icon="logo.jpg",
    layout="wide"
)

# --- Logo + titre ---
logo = Image.open("logo.jpg")
col1, col2 = st.columns([1, 5])

with col1:
    st.image(logo, width=250)

with col2:
    st.markdown("<h1 style='text-align:center;'>Validation des options de bennes</h1>", unsafe_allow_html=True)

# --- Chargement des données ---
options_df = pd.read_csv("options.csv")
regles_df = pd.read_csv("regles.csv")
accessoires_df = pd.read_csv("accessoires.csv")
regles_accessoires_df = pd.read_csv("regles_accessoires.csv")

# --- Nettoyage des colonnes et valeurs ---
for df in [options_df, regles_df, accessoires_df, regles_accessoires_df]:
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

# --- Sélection configuration ---
st.header("Configuration de la benne")

# Définir les options à afficher (les types qui existent dans options.csv)
options_a_afficher = options_df["option"].unique()
selection_options = {}  # dictionnaire pour stocker les choix de l'utilisateur

for opt in options_a_afficher:
    valeurs = options_df[options_df["option"] == opt]["label"].unique()
    selection_options[opt] = st.selectbox(opt.replace("_", " ").capitalize(), valeurs)

# --- Sélection accessoires ---
st.header("Accessoires et options")

accessoires_selectionnes = st.multiselect(
    "Sélectionnez les accessoires",
    accessoires_df["Code"].tolist()
)

# --- Validation ---
if st.button("Valider la configuration"):

    st.subheader("Résultat de validation")

    # ----- Validation configuration principale -----
    erreurs_config = []

    for _, regle in regles_df.iterrows():
        cond_opt = regle["condition_option"]
        cond_code = regle["condition_code"]
        action_opt = regle["option_affectee"]
        action_val = str(regle["valeur"])
        action_type = regle["regle"]

        # Comparer la valeur sélectionnée à la condition
        if selection_options.get(cond_opt) == cond_code:
            if action_type == "interdit" and selection_options.get(action_opt) == action_val:
                erreurs_config.append(f"{action_opt} = {action_val} est interdit pour {cond_opt} = {cond_code}")
            elif action_type == "obligatoire" and selection_options.get(action_opt) != action_val:
                erreurs_config.append(f"{action_opt} doit être {action_val} pour {cond_opt} = {cond_code}")
            elif action_type == "min":
                try:
                    if float(selection_options.get(action_opt).replace('"', '')) < float(action_val):
                        erreurs_config.append(f"{action_opt} doit être ≥ {action_val} pour {cond_opt} = {cond_code}")
                except:
                    pass
            elif action_type == "max":
                try:
                    if float(selection_options.get(action_opt).replace('"', '')) > float(action_val):
                        erreurs_config.append(f"{action_opt} doit être ≤ {action_val} pour {cond_opt} = {cond_code}")
                except:
                    pass

    # Affichage verdict configuration principale
    if erreurs_config:
        st.markdown(f"<h3 style='background-color:salmon; padding:10px; text-align:center;'>❌ CONFIGURATION MAUVAISE</h3>", unsafe_allow_html=True)
        for e in erreurs_config:
            st.write("•", e)
    else:
        st.markdown(f"<h3 style='background-color:lightgreen; padding:10px; text-align:center;'>✅ CONFIGURATION BONNE</h3>", unsafe_allow_html=True)

    # ----- Validation accessoires -----
    resultats = []
    for acc in accessoires_selectionnes:
        row = regles_accessoires_df[regles_accessoires_df["Code"] == acc]
        statut = "Bon" if not row.empty else "A valider"
        resultats.append({"Accessoire": acc, "Statut": statut})

    resultats_df = pd.DataFrame(resultats)

    # Verdict global accessoires
    if not resultats_df.empty:
        def color_row(row):
            if row["Statut"] == "Bon":
                return ["background-color: lightgreen"] * len(row)
            elif row["Statut"] == "Mauvais":
                return ["background-color: salmon"] * len(row)
            else:
                return ["background-color: khaki"] * len(row)

        st.dataframe(resultats_df.style.apply(color_row, axis=1))
    else:
        st.info("Aucun accessoire sélectionné.")
