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
    dtype=str
)

# Nettoyage
for df in [options_df, accessoires_df, conditions_bennes_df, conditions_accessoires_df]:
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

historique_df.columns = historique_df.columns.str.strip()
historique_df["Historique"] = historique_df["Historique"].str.strip()
historique_df["Date"] = pd.to_datetime(
    historique_df["Date"],
    format="%d-%m-%y",
    errors="coerce"
)

# ======================================================
# MAPPING
# ======================================================
OPTION_MAPPING = {
    "code_benne": ["modele"],
    "longueur": ["longueur"],
    "hauteur": ["hauteur_cote"],
    "porte": ["hauteur_porte"],
    "type_porte": ["type_porte"],
    "reservoir": ["reservoir"],
    "type_sol": ["type_sol"],
    "type_devant": ["type_devant"]
}

# ======================================================
# FONCTIONS
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
    try:
        return float(val.replace('"', '').replace("'", ""))
    except:
        return None

def format_longueur(val):
    pieds = int(val)
    pouces = int(round((val - pieds) * 12))
    if pouces == 12:
        pieds += 1
        pouces = 0
    return f"{pieds}'-{pouces}"

def get_mapped_option(selection, possibles):
    for key, value in selection.items():
        if key.lower() in possibles:
            return value
    return None

def construire_base_config(code_benne, longueur, hauteur, porte, reservoir, type_porte):
    porte_avec_type = f"{int(porte)}{type_porte}"
    return f"{code_benne} {format_longueur(longueur)} x {int(hauteur)} x {porte_avec_type} {reservoir}"

# 🔎 HISTORIQUE
def chercher_historique(df, code_benne, longueur, hauteur, porte, reservoir, type_porte, accessoires_selectionnes):
    base = construire_base_config(code_benne, longueur, hauteur, porte, reservoir, type_porte).strip()
    correspondances = []

    for _, row in df.iterrows():
        ligne = str(row["Historique"]).strip()
        if not ligne.startswith(base):
            continue

        reste = ligne[len(base):].strip()
        accessoires_hist = [a.strip() for a in reste.split(",") if a.strip()] if reste else []

        if all(acc in accessoires_hist for acc in accessoires_selectionnes):
            correspondances.append(row)

    if not correspondances:
        return None

    df_match = pd.DataFrame(correspondances)
    return df_match["Date"].max()

def afficher_accessoire(code):
    ligne = accessoires_df[accessoires_df["NOM OPTION"] == code]
    if not ligne.empty:
        return f"{ligne.iloc[0]['NOM VENTE']} – {ligne.iloc[0]['DESCRIPTION']}"
    return code

def traduire_production(accessoires):
    codes = []
    for acc in accessoires:
        ligne = accessoires_df[accessoires_df["NOM OPTION"] == acc]
        if not ligne.empty:
            codes.append(ligne.iloc[0].get("production_code", acc))
    return codes

# ======================================================
# INTERFACE
# ======================================================
logo = Image.open("logo.jpg")
c1, c2 = st.columns([1, 5])
with c1:
    st.image(logo, width=250)
with c2:
    st.markdown("<h1 style='text-align:center;'>Validation des options de bennes</h1>", unsafe_allow_html=True)

# ======================================================
# CONFIGURATION BENNE
# ======================================================
st.header("Configuration de la benne")
selection_options = {}
opts = [o for o in options_df["option"].unique() if o.lower() not in ["hauteur_poteau", "cylindre", "type_devant", "type_sol", "type_porte", "reservoir"]]

c1, c2 = st.columns(2)
for i, opt in enumerate(opts):
    valeurs = options_df[options_df["option"] == opt]["label"].unique()
    with c1 if i % 2 == 0 else c2:
        selection_options[opt.lower()] = st.selectbox(
            opt.replace("_", " ").capitalize(),
            valeurs
        )

# Type de porte et Type de réservoir côte à côte
c1, c2 = st.columns(2)
with c1:
    type_porte = st.selectbox(
        "Type de porte",
        options=["D", "I"],
        index=0,
        help="D = Droite, I = Inclinée"
    )
    selection_options["type_porte"] = type_porte
with c2:
    reservoir_options = options_df[options_df["option"] == "reservoir"]["label"].unique()
    reservoir = st.selectbox(
        "Type de réservoir",
        reservoir_options,
        index=0,
        help="Sélectionnez le type de réservoir"
    )
    selection_options["reservoir"] = reservoir

# ======================================================
# ACCESSOIRES
# ======================================================
st.header("Accessoires")

# Type devant (multiselect)
type_devant_options = options_df[options_df["option"] == "type_devant"]["label"].tolist()
type_devant_selection = st.multiselect(
    "Type devant",
    type_devant_options,
    default=[],
    help="Sélectionnez le type devant"
)
selection_options["type_devant"] = type_devant_selection[0] if type_devant_selection else None

# Type de sol (multiselect)
type_sol_options = options_df[options_df["option"] == "type_sol"]["label"].tolist()
type_sol_selection = st.multiselect(
    "Type de sol",
    type_sol_options,
    default=[],
    help="Sélectionnez le type de sol"
)
selection_options["type_sol"] = type_sol_selection[0] if type_sol_selection else None

# Autres accessoires
accessoires_selectionnes = st.multiselect(
    "Autres accessoires",
    accessoires_df["NOM OPTION"].tolist(),
    format_func=afficher_accessoire,
    default=[]
)

# ======================================================
# VALIDATION
# ======================================================
if st.button("Valider la configuration"):

    code_benne = get_mapped_option(selection_options, OPTION_MAPPING["code_benne"])
    longueur = parse_dimension(get_mapped_option(selection_options, OPTION_MAPPING["longueur"]))
    hauteur = parse_dimension(get_mapped_option(selection_options, OPTION_MAPPING["hauteur"]))
    porte = parse_dimension(get_mapped_option(selection_options, OPTION_MAPPING["porte"]))
    type_porte = selection_options["type_porte"]
    reservoir = selection_options["reservoir"]

    st.success("✅ CONFIGURATION BONNE")

    codes_accessoires = traduire_production(accessoires_selectionnes)
    base_config = construire_base_config(code_benne, longueur, hauteur, porte, reservoir, type_porte)

    # Ajouter les accessoires type devant et type de sol
    if selection_options["type_devant"]:
        codes_accessoires.append(selection_options["type_devant"])
    if selection_options["type_sol"]:
        codes_accessoires.append(selection_options["type_sol"])

    config_complete = base_config
    if codes_accessoires:
        config_complete += " " + ",".join(codes_accessoires)

    # 🔎 Recherche historique
    date_prod = chercher_historique(
        historique_df,
        code_benne,
        longueur,
        hauteur,
        porte,
        reservoir,
        type_porte,
        codes_accessoires
    )

    if date_prod is not None and not pd.isna(date_prod):
        st.warning(f"⚠️ Dernière production similaire : {date_prod.strftime('%d-%m-%Y')}")
    else:
        st.info("Aucune production antérieure trouvée")

    st.subheader("Export – Codes de production")
    export_df = pd.DataFrame([{
        "Configuration": config_complete,
        "Options": ", ".join(codes_accessoires)
    }])
    st.dataframe(export_df, use_container_width=True, hide_index=True)
    st.download_button(
        "📤 Télécharger la configuration",
        export_df.to_csv(index=False),
        "configuration_production.csv",
        "text/csv"
    )
