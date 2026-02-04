import streamlit as st
import pandas as pd
from PIL import Image

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

# Historique : FORMAT
# CONFIG_OPTIONS ; DD-MM-YY
historique_df = pd.read_csv(
    "historique_commande.csv",
    sep=";",
    names=["CONFIG_OPTIONS", "DATE_PROD"],
    engine="python"
)
historique_df["DATE_PROD"] = pd.to_datetime(
    historique_df["DATE_PROD"],
    dayfirst=True,
    errors="coerce"
)

# ======================================================
# NETTOYAGE DES DONNÉES
# ======================================================
for df in [
    options_df,
    accessoires_df,
    conditions_bennes_df,
    conditions_accessoires_df,
]:
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def parse_dimension(val):
    if val is None:
        return None
    val = str(val).replace('"', "").strip()
    if "'" in val:
        try:
            return float(val.split("'")[0])
        except ValueError:
            return None
    try:
        return float(val)
    except ValueError:
        return None

def get_option_value(selection_options, keywords):
    for key, value in selection_options.items():
        if any(k in key.lower() for k in keywords):
            return value
    return None

def valider_dimensions(code_benne, longueur, hauteur, porte, conditions_df):
    erreurs = []
    lignes = []

    for _, row in conditions_df.iterrows():
        prefixes = str(row["prefixes"]).split("|")
        if any(code_benne.startswith(p) for p in prefixes):
            lignes.append(row)

    if not lignes:
        return ["❌ Aucune règle de dimensions trouvée pour ce code de benne"]

    for row in lignes:
        local = []

        if not (row["long_min"] <= longueur <= row["long_max"]):
            local.append(
                f"❌ Longueur invalide ({longueur}'). Attendu {row['long_min']}–{row['long_max']}'"
            )

        if not (row["height_min"] <= hauteur <= row["height_max"]):
            local.append(
                f"❌ Hauteur invalide ({hauteur}\"). Attendu {row['height_min']}–{row['height_max']}\""
            )

        if not (row["door_height_min"] <= porte <= row["door_height_max"]):
            local.append(
                f"❌ Porte invalide ({porte}\"). Attendu {row['door_height_min']}–{row['door_height_max']}\""
            )

        if not local:
            return []

        erreurs.extend(local)

    return erreurs

def valider_conditions_accessoires(code_benne, accessoires, conditions_df):
    erreurs = []

    for _, row in conditions_df.iterrows():
        prefixes = str(row["prefixes"]).split("|")
        if not ("*" in prefixes or any(code_benne.startswith(p) for p in prefixes)):
            continue

        if row["type"] == "incompatible":
            if row["code_a"] in accessoires and row["code_b"] in accessoires:
                erreurs.append(f"❌ {row['message']}")

        if row["type"] == "interdit":
            if row["code_a"] in accessoires:
                erreurs.append(f"❌ {row['message']}")

    return erreurs

def traduire_production(accessoires, accessoires_df):
    lignes = []

    for acc in accessoires:
        ligne = accessoires_df[accessoires_df["NOM OPTION"] == acc]
        if not ligne.empty:
            prod = ligne.iloc[0].get("production_code", acc)
            lignes.append({
                "Code": prod,
                "Description": ligne.iloc[0]["DESCRIPTION"]
            })

    return pd.DataFrame(lignes)

def afficher_accessoire(code):
    ligne = accessoires_df[accessoires_df["NOM OPTION"] == code]
    if not ligne.empty:
        return f"{ligne.iloc[0]['NOM VENTE']} – {ligne.iloc[0]['DESCRIPTION']}"
    return code

# ======================================================
# LOGO + TITRE
# ======================================================
logo = Image.open("logo.jpg")
c1, c2 = st.columns([1, 5])

with c1:
    st.image(logo, width=220)

with c2:
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

# TYPE DE PORTE (UN SEUL ENDROIT – STABLE)
st.selectbox(
    "Type de porte",
    ["D", "I"],
    key="type_porte",
    format_func=lambda x: "Droite (D)" if x == "D" else "Inclinée (I)"
)

# ======================================================
# ACCESSOIRES
# ======================================================
st.header("Accessoires et options")

accessoires_selectionnes = st.multiselect(
    "Tous les accessoires",
    accessoires_df["NOM OPTION"].tolist(),
    format_func=afficher_accessoire
)

# ======================================================
# VALIDATION
# ======================================================
if st.button("Valider la configuration"):

    erreurs_config = []
    st.subheader("Résultat de validation")

    code_benne = get_option_value(selection_options, ["code", "modele", "benne"])
    longueur = parse_dimension(get_option_value(selection_options, ["long"]))
    hauteur = parse_dimension(get_option_value(selection_options, ["height", "hauteur"]))
    porte = parse_dimension(get_option_value(selection_options, ["porte", "door"]))
    reservoir = get_option_value(selection_options, ["reservoir"])

    if None in [code_benne, longueur, hauteur, porte, reservoir]:
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
        st.stop()

    st.markdown(
        "<h3 style='background-color:lightgreen; padding:10px; text-align:center;'>✅ CONFIGURATION BONNE</h3>",
        unsafe_allow_html=True
    )

    # ======================================================
    # EXPORT
    # ======================================================
    st.divider()
    st.subheader("Export – Codes de production")

    type_porte = st.session_state.get("type_porte", "D")

    df_accessoires = traduire_production(accessoires_selectionnes, accessoires_df)
    codes_accessoires = df_accessoires["Code"].tolist() if not df_accessoires.empty else []

    config_compacte = (
        f"{code_benne} {int(longueur)}' x {int(hauteur)} x {int(porte)}{type_porte} {reservoir}"
    )

    options_str = ",".join(codes_accessoires)

    historique_trouves = historique_df[
        historique_df["CONFIG_OPTIONS"].str.contains(options_str, na=False)
    ]

    if not historique_trouves.empty:
        date_max = historique_trouves["DATE_PROD"].max().strftime("%d-%m-%y")
        st.warning(f"⚠️ Configuration déjà produite (dernière fois : {date_max})")

    df_export = pd.DataFrame({
        "Configuration": [config_compacte],
        "Options": [options_str]
    })

    st.download_button(
        "📤 Télécharger la configuration (CSV production)",
        df_export.to_csv(index=False),
        "configuration_production.csv",
        "text/csv"
    )

    st.dataframe(df_export, use_container_width=True)
