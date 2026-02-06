import streamlit as st
import pandas as pd
from PIL import Image
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
    historique_df["DATE_PROD"], errors="coerce"
)

# Nettoyage des espaces
for df in [options_df, accessoires_df, conditions_bennes_df, conditions_accessoires_df]:
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

# ======================================================
# MAPPING DES OPTIONS
# ======================================================
OPTION_MAPPING = {
    "code_benne": ["modele"],
    "longueur": ["longueur"],
    "hauteur": ["hauteur_cote"],
    "porte": ["hauteur_porte"],
    "reservoir": ["reservoir"]
}

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def parse_dimension(val):
    if val is None:
        return None
    val = str(val).strip()
    match = re.match(r"^(\d+)\s*'\s*-?\s*(\d+)?", val)
    if match:
        pieds = int(match.group(1))
        pouces = int(match.group(2) or 0)
        return pieds + pouces / 12
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

def get_mapped_option(selection_options, possibles):
    for key, value in selection_options.items():
        if key.lower() in possibles:
            return value
    return None

def valider_dimensions(code_benne, longueur, hauteur, porte, conditions_df):
    erreurs = []
    if code_benne is None:
        return ["❌ Code de benne manquant"]

    lignes = conditions_df[
        conditions_df["prefixes"].apply(
            lambda x: any(str(code_benne).startswith(p) for p in str(x).split("|"))
        )
    ]

    if lignes.empty:
        return ["❌ Aucune règle de dimensions trouvée pour ce code de benne"]

    for _, row in lignes.iterrows():
        erreurs_locales = []

        if not (row["long_min"] <= longueur <= row["long_max"]):
            erreurs_locales.append(
                f"❌ Longueur invalide ({format_longueur(longueur)}). "
                f"Attendu {format_longueur(row['long_min'])} – {format_longueur(row['long_max'])}"
            )
        if not (row["height_min"] <= hauteur <= row["height_max"]):
            erreurs_locales.append(
                f"❌ Hauteur de côté invalide ({int(hauteur)}\"). "
                f"Attendu {int(row['height_min'])} – {int(row['height_max'])}\""
            )
        if not (row["door_height_min"] <= porte <= row["door_height_max"]):
            erreurs_locales.append(
                f"❌ Hauteur de porte invalide ({int(porte)}\"). "
                f"Attendu {int(row['door_height_min'])} – {int(row['door_height_max'])}\""
            )

        if not erreurs_locales:
            return []

        erreurs.extend(erreurs_locales)

    return erreurs

def valider_conditions_accessoires(code_benne, accessoires, conditions_df):
    erreurs = []
    if not code_benne:
        return erreurs
    for _, row in conditions_df.iterrows():
        prefixes = str(row["prefixes"]).split("|")
        if "*" not in prefixes and not any(code_benne.startswith(p) for p in prefixes if p):
            continue
        if row["type"] == "incompatible":
            if row["code_a"] in accessoires and row["code_b"] in accessoires:
                erreurs.append(f"❌ {row['message']}")
        if row["type"] == "interdit":
            if row["code_a"] in accessoires:
                erreurs.append(f"❌ {row['message']}")
    return erreurs

def afficher_accessoire(code):
    ligne = accessoires_df[accessoires_df["NOM OPTION"] == code]
    if not ligne.empty:
        return f"{ligne.iloc[0]['NOM VENTE']} – {ligne.iloc[0]['DESCRIPTION']}"
    return code

def traduire_production(accessoires):
    lignes = []
    for acc in accessoires:
        ligne = accessoires_df[accessoires_df["NOM OPTION"] == acc]
        if not ligne.empty:
            lignes.append({
                "Code": ligne.iloc[0].get("production_code", acc),
                "Description": ligne.iloc[0]["DESCRIPTION"]
            })
    return pd.DataFrame(lignes)

# ======================================================
# INTERFACE
# ======================================================
logo = Image.open("logo.jpg")
col1, col2 = st.columns([1, 5])
with col1:
    st.image(logo, width=250)
with col2:
    st.markdown("<h1 style='text-align:center;'>Validation des options de bennes</h1>", unsafe_allow_html=True)

# ======================================================
# CONFIGURATION BENNE
# ======================================================
st.header("Configuration de la benne")
options_a_afficher = [opt for opt in options_df["option"].unique() if opt.lower() != "type_porte"]
selection_options = {}
col1, col2 = st.columns(2)
for i, opt in enumerate(options_a_afficher):
    valeurs = options_df[options_df["option"] == opt]["label"].unique()
    with col1 if i % 2 == 0 else col2:
        selection_options[opt.lower()] = st.selectbox(opt.replace("_", " ").capitalize(), valeurs)

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
st.header("Accessoires")
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

    code_benne = get_mapped_option(selection_options, OPTION_MAPPING["code_benne"])
    longueur = parse_dimension(get_mapped_option(selection_options, OPTION_MAPPING["longueur"]))
    hauteur = parse_dimension(get_mapped_option(selection_options, OPTION_MAPPING["hauteur"]))
    porte = parse_dimension(get_mapped_option(selection_options, OPTION_MAPPING["porte"]))
    reservoir = get_mapped_option(selection_options, OPTION_MAPPING["reservoir"])

    if not code_benne:
        erreurs_config.append("❌ Code de benne manquant")
    if longueur is None:
        erreurs_config.append("❌ Longueur invalide (ex: 11'-6 ou 11.5)")
    if hauteur is None:
        erreurs_config.append("❌ Hauteur de côté invalide")
    if porte is None:
        erreurs_config.append("❌ Hauteur de porte invalide")
    if not reservoir:
        erreurs_config.append("❌ Réservoir non sélectionné")

    if code_benne and longueur and hauteur and porte:
        erreurs_config.extend(valider_dimensions(code_benne, longueur, hauteur, porte, conditions_bennes_df))

    erreurs_config.extend(valider_conditions_accessoires(code_benne, accessoires_selectionnes, conditions_accessoires_df))

    st.subheader("Résultat de validation")
    if erreurs_config:
        st.markdown("<h3 style='background-color:salmon; padding:10px; text-align:center;'>❌ CONFIGURATION MAUVAISE</h3>", unsafe_allow_html=True)
        for err in erreurs_config:
            st.write("•", err)
    else:
        st.markdown("<h3 style='background-color:lightgreen; padding:10px; text-align:center;'>✅ CONFIGURATION BONNE</h3>", unsafe_allow_html=True)

        # ======================================================
        # EXPORT + HISTORIQUE
        # ======================================================
        st.divider()
        st.subheader("Export – Codes de production")

        # Traduire les accessoires pour l'export
        df_accessoires = traduire_production(accessoires_selectionnes)
        if df_accessoires.empty:
            df_accessoires = pd.DataFrame(columns=["Code", "Description"])
        codes_accessoires = ",".join(df_accessoires["Code"].tolist())

        # Configuration compacte
        config_compacte = f"{code_benne} {format_longueur(longueur)} x {int(hauteur)} x {int(porte)}{type_porte} {reservoir}"

        # Affichage tableau export avant téléchargement
        export_df = pd.DataFrame({
            "Configuration": [config_compacte],
            "Options": [codes_accessoires]
        })
        st.table(export_df)

        # Vérification historique
        if not historique_df.empty and codes_accessoires:
            historique_trouves = historique_df[
                historique_df["CONFIG_OPTIONS"].notna() &
                historique_df["CONFIG_OPTIONS"].str.contains(codes_accessoires)
            ]
            if not historique_trouves.empty:
                date_existante = historique_trouves["DATE_PROD"].max().strftime("%d-%b-%Y")
                st.warning(f"⚠️ Une benne avec ces options existe déjà (dernière date : {date_existante})")

        # Bouton téléchargement CSV
        st.download_button(
            "📤 Télécharger la configuration",
            export_df.to_csv(index=False),
            "configuration_production.csv",
            "text/csv"
        )
