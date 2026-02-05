import streamlit as st
import pandas as pd
from PIL import Image
from datetime import datetime
import re

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
# CORRECTION DES ANNÉES SUR 2 CHIFFRES
# ======================================================
def corriger_annee(dt):
    """
    00–30  -> 2000–2030
    31–99  -> 1900–1999
    """
    if pd.isna(dt):
        return dt

    annee = dt.year
    if annee < 100:
        if annee <= 30:
            annee += 2000
        else:
            annee += 1900
        return dt.replace(year=annee)
    return dt

historique_df["DATE_PROD"] = historique_df["DATE_PROD"].apply(corriger_annee)

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
    """
    Convertit une dimension en float.
    Supporte :
    - format pieds-pouces : 11'-6
    - ancien format numérique : 11.5, 11
    - format avec guillemets ou apostrophe : 11", 11'
    """
    if val is None:
        return None

    val = str(val).strip()

    # Format pieds-pouces : 11'-6 ou 11'-0
    match = re.match(r"^(\d+)\s*'\s*-\s*(\d+)$", val)
    if match:
        pieds = int(match.group(1))
        pouces = int(match.group(2))
        return pieds + pouces / 12

    # Ancien format : 11', 11", 11.5, 11
    val = val.replace('"', '').replace("'", "")
    try:
        return float(val)
    except:
        return None

def format_longueur(val):
    pieds = int(val)
    pouces = int(round((val - pieds) * 12))
    if pouces == 12:
        pieds += 1
        pouces = 0
    return f"{pieds}'-{pouces}"

def get_option_value(selection_options, keywords):
    for key, value in selection_options.items():
        if any(k in key.lower() for k in keywords):
            return value
    return None

def valider_dimensions(code_benne, longueur, hauteur, porte, conditions_df):
    erreurs = []
    lignes_applicables = []

    for _, row in conditions_df.iterrows():
        prefixes = str(row["prefixes"]).split("|")
        if any(code_benne.startswith(p) for p in prefixes):
            lignes_applicables.append(row)

    if not lignes_applicables:
        return ["❌ Aucune règle de dimensions trouvée pour ce code de benne"]

    for row in lignes_applicables:
        erreurs_locales = []

        if not (row["long_min"] <= longueur <= row["long_max"]):
            erreurs_locales.append(
                f"❌ Longueur invalide ({format_longueur(longueur)}). "
                f"Attendu {format_longueur(row['long_min'])}–{format_longueur(row['long_max'])}"
            )

        if not (row["height_min"] <= hauteur <= row["height_max"]):
            erreurs_locales.append(
                f"❌ Hauteur de côté invalide ({int(hauteur)}\"). "
                f"Attendu {int(row['height_min'])}–{int(row['height_max'])}\""
            )

        if not (row["door_height_min"] <= porte <= row["door_height_max"]):
            erreurs_locales.append(
                f"❌ Hauteur de porte invalide ({int(porte)}\"). "
                f"Attendu {int(row['door_height_min'])}–{int(row['door_height_max'])}\""
            )

        # Si aucune erreur locale, c'est OK pour cette ligne
        if not erreurs_locales:
            return []

        erreurs.extend(erreurs_locales)

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

options_a_afficher = [
    opt for opt in options_df["option"].unique()
    if opt.lower() != "type_porte"
]

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
# TYPE DE PORTE
# ======================================================
type_porte = st.selectbox(
    "Type de porte",
    ["D", "I"],
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

    code_benne = get_option_value(selection_options, ["code", "modele", "prefix", "benne"])
    longueur = parse_dimension(get_option_value(selection_options, ["long"]))
    hauteur = parse_dimension(get_option_value(selection_options, ["height", "hauteur"]))
    porte = parse_dimension(get_option_value(selection_options, ["porte", "door"]))
    reservoir_selectionne = get_option_value(selection_options, ["reservoir"])

    if None in [code_benne, longueur, hauteur, porte, reservoir_selectionne]:
        erreurs_config.append(
            "❌ Dimensions invalides. Format attendu : 11'-6 ou valeur numérique (ex: 11.5)"
        )
    else:
        erreurs_config.extend(
            valider_dimensions(code_benne, longueur, hauteur, porte, conditions_bennes_df)
        )

    erreurs_config.extend(
        valider_conditions_accessoires(code_benne, accessoires_selectionnes, conditions_accessoires_df)
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

    # ======================================================
    # EXPORT + HISTORIQUE
    # ======================================================
    st.divider()
    st.subheader("Export – Codes de production")

    if not erreurs_config:
        df_accessoires = traduire_production(accessoires_selectionnes, accessoires_df)
        codes_accessoires = df_accessoires["Code"].tolist() if not df_accessoires.empty else []

        config_compacte = (
            f"{code_benne} "
            f"{format_longueur(longueur)} x "
            f"{int(hauteur)} x "
            f"{int(porte)}{type_porte} "
            f"{reservoir_selectionne}"
        )
        options_str = ",".join(codes_accessoires)

        historique_trouves = historique_df[
            historique_df["CONFIG_OPTIONS"].str.contains(options_str, na=False)
        ]

        if not historique_trouves.empty:
            date_existante = historique_trouves["DATE_PROD"].max().strftime("%d-%b-%Y")
            st.warning(f"⚠️ Une benne avec ces options existe déjà (dernière date : {date_existante})")

        df_export_final = pd.DataFrame({
            "Configuration": [config_compacte],
            "Options": [options_str]
        })

        st.download_button(
            "📤 Télécharger la configuration (CSV production)",
            df_export_final.to_csv(index=False),
            "configuration_production.csv",
            "text/csv"
        )

        st.dataframe(df_export_final, use_container_width=True)
