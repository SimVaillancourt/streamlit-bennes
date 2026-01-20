import streamlit as st
import pandas as pd
from PIL import Image

# ======================================================
# CONFIGURATION PAGE
# ======================================================
st.set_page_config(
    page_title="Validation Bennes",
    page_icon="favicon.ico",  # <-- Favicon ajouté ici
    layout="wide"
)

# ======================================================
# LOGO + TITRE
# ======================================================
logo = Image.open("logo.jpg")
col1, col2 = st.columns([1, 5])

with col1:
    st.image(logo, width=250)

with col2:
    st.markdown(
        "<h1 style='text-align:center;'>Validation des options de bennes</h1>",
        unsafe_allow_html=True
    )

# ======================================================
# CHARGEMENT DES DONNÉES
# ======================================================
options_df = pd.read_csv("options.csv")
accessoires_df = pd.read_csv("accessoires.csv")
conditions_bennes_df = pd.read_csv("conditions_bennes.csv")

# ======================================================
# NETTOYAGE DES DONNÉES
# ======================================================
for df in [options_df, accessoires_df, conditions_bennes_df]:
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def parse_dimension(val):
    """
    Convertit :
    8'-0" -> 8
    13'   -> 13
    36"   -> 36
    """
    if val is None:
        return None

    val = str(val).strip()

    # Pieds
    if "'" in val:
        try:
            return float(val.split("'")[0])
        except:
            return None

    # Pouces
    val = val.replace('"', '')
    try:
        return float(val)
    except:
        return None


def get_option_value(selection_options, keywords):
    """
    Trouve automatiquement une option selon des mots-clés
    (robuste aux noms dans options.csv)
    """
    for key, value in selection_options.items():
        key_lower = key.lower()
        if any(k in key_lower for k in keywords):
            return value
    return None


def valider_dimensions(code_benne, longueur, hauteur, porte, conditions_df):
    erreurs = []

    # Trouver les lignes applicables selon les prefixes
    lignes_applicables = []

    for _, row in conditions_df.iterrows():
        prefixes = row["prefixes"].split("|")
        if any(code_benne.startswith(p) for p in prefixes):
            lignes_applicables.append(row)

    if not lignes_applicables:
        return ["❌ Aucune règle de dimensions trouvée pour ce code de benne"]

    # Valider dimensions
    for row in lignes_applicables:
        erreurs_locales = []

        if not (row["long_min"] <= longueur <= row["long_max"]):
            erreurs_locales.append(
                f"❌ Longueur invalide ({longueur}'). "
                f"Attendu {row['long_min']}–{row['long_max']}'"
            )

        if not (row["height_min"] <= hauteur <= row["height_max"]):
            erreurs_locales.append(
                f"❌ Hauteur invalide ({hauteur}\"). "
                f"Attendu {row['height_min']}–{row['height_max']}\""
            )

        if not (row["door_height_min"] <= porte <= row["door_height_max"]):
            erreurs_locales.append(
                f"❌ Hauteur de porte invalide ({porte}\"). "
                f"Attendu {row['door_height_min']}–{row['door_height_max']}\""
            )

        # Si une règle passe complètement → OK
        if not erreurs_locales:
            return []

        erreurs.extend(erreurs_locales)

    return erreurs

# ======================================================
# SÉLECTION CONFIGURATION EN 2 COLONNES
# ======================================================
st.header("Configuration de la benne")

options_a_afficher = options_df["option"].unique()
selection_options = {}

# Créer deux colonnes
col1, col2 = st.columns(2)

for i, opt in enumerate(options_a_afficher):
    valeurs = options_df[options_df["option"] == opt]["label"].unique()
    
    # Alterner entre col1 et col2
    if i % 2 == 0:
        with col1:
            selection_options[opt] = st.selectbox(
                opt.replace("_", " ").capitalize(),
                valeurs
            )
    else:
        with col2:
            selection_options[opt] = st.selectbox(
                opt.replace("_", " ").capitalize(),
                valeurs
            )

# ======================================================
# ACCESSOIRES
# ======================================================
st.header("Accessoires et options")

accessoires_selectionnes = st.multiselect(
    "Sélectionnez les accessoires",
    accessoires_df["Code"].tolist()
)

# ======================================================
# VALIDATION
# ======================================================
if st.button("Valider la configuration"):

    erreurs_config = []
    st.subheader("Résultat de validation")

    # --------------------------------------------------
    # VALIDATION DES DIMENSIONS
    # --------------------------------------------------
    code_benne = get_option_value(selection_options, ["code", "modele", "prefix", "benne"])
    longueur_raw = get_option_value(selection_options, ["long"])
    hauteur_raw = get_option_value(selection_options, ["height", "hauteur"])
    porte_raw = get_option_value(selection_options, ["porte", "door"])

    longueur = parse_dimension(longueur_raw)
    hauteur = parse_dimension(hauteur_raw)
    porte = parse_dimension(porte_raw)

    if None in [code_benne, longueur, hauteur, porte]:
        erreurs_config.append(
            f"❌ Impossible de lire les dimensions "
            f"(code={code_benne}, long={longueur}, haut={hauteur}, porte={porte})"
        )
    else:
        erreurs_dimensions = valider_dimensions(
            code_benne,
            longueur,
            hauteur,
            porte,
            conditions_bennes_df
        )
        erreurs_config.extend(erreurs_dimensions)

    # --------------------------------------------------
    # VERDICT CONFIGURATION
    # --------------------------------------------------
    if erreurs_config:
        st.markdown(
            "<h3 style='background-color:salmon; padding:10px; text-align:center;'>❌ CONFIGURATION MAUVAISE</h3>",
            unsafe_allow_html=True
        )
        for err in erreurs_config:
            st.write("•", err)
    else:
        st.markdown(
            "<h3 style='background-color:lightgreen; padding:10px; text-align:center;'>✅ CONFIGURATION BONNE</h3>",
            unsafe_allow_html=True
        )

    # --------------------------------------------------
    # VALIDATION ACCESSOIRES
    # --------------------------------------------------
    if accessoires_selectionnes:
        st.write("Accessoires sélectionnés :")
        for acc in accessoires_selectionnes:
            st.write("•", acc)
    else:
        st.info("Aucun accessoire sélectionné.")
