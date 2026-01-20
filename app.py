import streamlit as st
import pandas as pd
from PIL import Image
import re

# ======================================================
# CONFIGURATION PAGE
# ======================================================
st.set_page_config(
    page_title="Validation Bennes",
    page_icon="logo.jpg",
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
regles_df = pd.read_csv("regles.csv")
accessoires_df = pd.read_csv("accessoires.csv")
regles_accessoires_df = pd.read_csv("regles_accessoires.csv")
conditions_bennes_df = pd.read_csv("conditions_bennes.csv")

# ======================================================
# NETTOYAGE DES DONNÉES
# ======================================================
for df in [
    options_df,
    regles_df,
    accessoires_df,
    regles_accessoires_df,
    conditions_bennes_df
]:
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
# SÉLECTION CONFIGURATION
# ======================================================
st.header("Configuration de la benne")

options_a_afficher = options_df["option"].unique()
selection_options = {}

for opt in options_a_afficher:
    valeurs = options_df[options_df["option"] == opt]["label"].unique()
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
    # ÉTAPE 1 & 2 : règles existantes
    # --------------------------------------------------
    for _, regle in regles_df.iterrows():
        cond_opt = regle["condition_option"]
        cond_code = regle["condition_code"]
        action_opt = regle["option_affectee"]
        action_val = str(regle["valeur"])
        action_type = regle["regle"]

        if selection_options.get(cond_opt) == cond_code:
            if action_type == "interdit" and selection_options.get(action_opt) == action_val:
                erreurs_config.append(
                    f"{action_opt} = {action_val} est interdit pour {cond_opt} = {cond_code}"
                )

            elif action_type == "obligatoire" and selection_options.get(action_opt) != action_val:
                erreurs_config.append(
                    f"{action_opt} doit être {action_val} pour {cond_opt} = {cond_code}"
                )

            elif action_type == "min":
                try:
                    if float(selection_options.get(action_opt)) < float(action_val):
                        erreurs_config.append(f"{action_opt} doit être ≥ {action_val}")
                except:
                    pass

            elif action_type == "max":
                try:
                    if float(selection_options.get(action_opt)) > float(action_val):
                        erreurs_config.append(f"{action_opt} doit être ≤ {action_val}")
                except:
                    pass

    # --------------------------------------------------
    # ÉTAPE 3 : VALIDATION DES DIMENSIONS
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
    resultats = []
    for acc in accessoires_selectionnes:
        row = regles_accessoires_df[regles_accessoires_df["Code"] == acc]
        statut = "Bon" if not row.empty else "A valider"
        resultats.append({"Accessoire": acc, "Statut": statut})

    if resultats:
        df_res = pd.DataFrame(resultats)

        def color_row(row):
            if row["Statut"] == "Bon":
                return ["background-color: lightgreen"] * len(row)
            elif row["Statut"] == "Mauvais":
                return ["background-color: salmon"] * len(row)
            else:
                return ["background-color: khaki"] * len(row)

        st.dataframe(df_res.style.apply(color_row, axis=1))
    else:
        st.info("Aucun accessoire sélectionné.")
