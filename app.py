import streamlit as st
import pandas as pd

# Titre de l'application
st.title("Validation des options des bennes")

# Charger les données des options
options_file = "options.csv"  # fichier CSV avec toutes les options
regles_file = "regles.csv"    # fichier CSV avec les règles de validation

# Lecture des CSV
try:
    options_df = pd.read_csv(options_file)
    regles_df = pd.read_csv(regles_file)
except FileNotFoundError:
    st.error("Les fichiers options.csv et regles.csv doivent être dans le même dossier que app.py")
    st.stop()

# Sélection de l'option par l'utilisateur
option_choisie = st.selectbox("Choisis une option :", options_df['Option'])

# Validation simple
if st.button("Valider"):
    if option_choisie in regles_df['Option_valide'].values:
        st.success(f"L'option '{option_choisie}' est valide ✅")
    else:
        st.error(f"L'option '{option_choisie}' n'est pas valide ❌")
