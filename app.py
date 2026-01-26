import streamlit as st
import pandas as pd
from PIL import Image

import bcrypt


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False


    if st.session_state.authenticated:
        return True


    st.title("🔒 Accès sécurisé")


    password = st.text_input(
        "Mot de passe",
        type="password"
    )


    if st.button("Se connecter"):
        if bcrypt.checkpw(
            password.encode(),
            st.secrets["APP_PASSWORD_HASH"].encode()
        ):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")


    return False




if not check_password():
    st.stop()

# ======================================================
# CONFIGURATION PAGE
# ======================================================
st.set_page_config(
    page_title="Validation Bennes",
    page_icon="favicon.ico",
    layout="wide"
)

# ======================================================
# CHARGEMENT DES DONNÉES
# ======================================================
options_df = pd.read_csv("options.csv")
accessoires_df = pd.read_csv("accessoires.csv")
conditions_bennes_df = pd.read_csv("conditions_bennes.csv")
conditions_accessoires_df = pd.read_csv("conditions_accessoires.csv")

# ======================================================
# NETTOYAGE DES DONNÉES
# ======================================================
for df in [options_df, accessoires_df, conditions_bennes_df, conditions_accessoires_df]:
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def parse_dimension(val):
    if val is None:
        return None
    val = str(val).strip()
    if "'" in val:
        try:
            return float(val.split("'")[0])
        except:
            return None
    val = val.replace('"', '')
    try:
        return float(val)
    except:
        return None


def get_option_value(selection_options, keywords):
    for key, value in selection_options.items():
        if any(k in key.lower() for k in keywords):
            return value
    return None


def afficher_code_description(code, df):
    """Affiche code + description dans la liste, seulement code quand sélectionné"""
    desc = df.loc[df["Code"] == code, "Description"]
    if not desc.empty:
        return f"{code} – {desc.values[0]}"
    return code


def valider_dimensions(code_benne, longueur, hauteur, porte, conditions_df):
    erreurs = []
    lignes_applicables = []

    for _, row in conditions_df.iterrows():
        prefixes = row["prefixes"].split("|")
        if any(code_benne.startswith(p) for p in prefixes):
            lignes_applicables.append(row)

    if not lignes_applicables:
        return ["❌ Aucune règle de dimensions trouvée pour ce code de benne"]

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

        if not erreurs_locales:
            return []

        erreurs.extend(erreurs_locales)

    return erreurs


def valider_conditions_accessoires(code_benne, accessoires, conditions_df):
    erreurs = []

    for _, row in conditions_df.iterrows():
        prefixes = row["prefixes"].split("|")

        if not ("*" in prefixes or any(code_benne.startswith(p) for p in prefixes)):
            continue

        if row["type"] == "incompatible":
            if row["code_a"] in accessoires and row["code_b"] in accessoires:
                erreurs.append(f"❌ {row['message']}")

        if row["type"] == "interdit":
            if row["code_a"] in accessoires:
                erreurs.append(f"❌ {row['message']}")

    return erreurs

def traduire_production(selection_options, accessoires, options_df, accessoires_df):
    lignes = []

    # Options principales
    for option, valeur in selection_options.items():
        ligne = options_df[
            (options_df["option"] == option) &
            (options_df["label"] == valeur)
        ]

        if not ligne.empty:
            prod = ligne.iloc[0].get("production_code", valeur)
            lignes.append({
                "Type": "Option",
                "Code": option,
                "Valeur": valeur,
                "Production": prod
            })

    # Accessoires
    for acc in accessoires:
        ligne = accessoires_df[accessoires_df["Code"] == acc]
        if not ligne.empty:
            prod = ligne.iloc[0].get("production_code", acc)
            lignes.append({
                "Type": "Accessoire",
                "Code": acc,
                "Valeur": ligne.iloc[0]["Description"],
                "Production": prod
            })

    return pd.DataFrame(lignes)


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
# CONFIGURATION BENNE
# ======================================================
st.header("Configuration de la benne")

options_a_afficher = options_df["option"].unique()
selection_options = {}
col1, col2 = st.columns(2)

for i, opt in enumerate(options_a_afficher):
    valeurs = options_df[options_df["option"] == opt]["label"].unique()
    with col1 if i % 2 == 0 else col2:
        selection_options[opt] = st.selectbox(
            opt.replace("_", " ").capitalize(),
            valeurs
        )

# ======================================================
# ACCESSOIRES PAR CATÉGORIE
# ======================================================
st.header("Accessoires et options")

portes_df = accessoires_df[accessoires_df["Categorie"] == "Porte"]
cotes_df = accessoires_df[accessoires_df["Categorie"] == "Cote"]
devant_df = accessoires_df[accessoires_df["Categorie"] == "Devant"]
autres_df = accessoires_df[accessoires_df["Categorie"] == "Autre"]

col1, col2 = st.columns(2)

with col1:
    accessoires_portes = st.multiselect(
        "Options de portes",
        portes_df["Code"].tolist(),
        format_func=lambda x: afficher_code_description(x, portes_df)
    )
    accessoires_cotes = st.multiselect(
        "Options de côtés",
        cotes_df["Code"].tolist(),
        format_func=lambda x: afficher_code_description(x, cotes_df)
    )

with col2:
    accessoires_devant = st.multiselect(
        "Options de devant",
        devant_df["Code"].tolist(),
        format_func=lambda x: afficher_code_description(x, devant_df)
    )
    accessoires_autres = st.multiselect(
        "Autres options",
        autres_df["Code"].tolist(),
        format_func=lambda x: afficher_code_description(x, autres_df)
    )

accessoires_selectionnes = (
    accessoires_portes
    + accessoires_cotes
    + accessoires_devant
    + accessoires_autres
)

# ======================================================
# VALIDATION
# ======================================================
if st.button("Valider la configuration"):

    erreurs_config = []
    st.subheader("Résultat de validation")

    code_benne = get_option_value(selection_options, ["code", "modele", "prefix", "benne"])
    longueur = parse_dimension(get_option_value(selection_options, ["long"]))
    hauteur = parse_dimension(get_option_value(selection_options, ["height", "hauteur"]))
    porte = parse_dimension(get_option_value(selection_options, ["porte", "door"]))

    if None in [code_benne, longueur, hauteur, porte]:
        erreurs_config.append("❌ Impossible de lire les dimensions sélectionnées")
    else:
        erreurs_config.extend(
            valider_dimensions(
                code_benne,
                longueur,
                hauteur,
                porte,
                conditions_bennes_df
            )
        )

    erreurs_config.extend(
        valider_conditions_accessoires(
            code_benne,
            accessoires_selectionnes,
            conditions_accessoires_df
        )
    )

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

    if accessoires_selectionnes:
        st.write("Accessoires sélectionnés :")
        for acc in accessoires_selectionnes:
            st.write("•", acc)
    else:
        st.info("Aucun accessoire sélectionné.")

    # ======================================================
    # EXPORT LANGAGE DE PRODUCTION
    # ======================================================
    st.divider()
    st.subheader("Export – Langage de production")

    if not erreurs_config:
        df_export = traduire_production(
            selection_options,
            accessoires_selectionnes,
            options_df,
            accessoires_df
        )

        st.download_button(
            label="📤 Télécharger la configuration (CSV production)",
            data=df_export.to_csv(index=False),
            file_name="configuration_production.csv",
            mime="text/csv"
        )

        st.dataframe(df_export, use_container_width=True)



