import streamlit as st
import pandas as pd
import json
from groq import Groq

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Analyseur Excel Intelligent & Métier", page_icon="📊", layout="wide")

st.title("📊 Analyseur Excel Guidé par le Métier")
st.write("Importez votre fichier, nettoyez les données, et donnez des instructions précises à l'IA sur ce qui compte vraiment pour votre métier.")

# --- CONFIGURATION GROQ ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]


try:
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"Erreur d'initialisation de Groq : {e}")

# --- BARRE LATÉRALE : IMPORTATION ---
st.sidebar.header("1. Importer le fichier")
fichier_upload = st.sidebar.file_uploader("Choisissez un fichier Excel (.xlsx)", type=["xlsx"])

if fichier_upload is not None:
    try:
        # Détection de l'en-tête
        df_brut = pd.read_excel(fichier_upload, header=None, nrows=10)
        ligne_entete = 0
        for index, row in df_brut.iterrows():
            valeurs_remplies = row.dropna()
            if len(valeurs_remplies) > 2:
                ligne_entete = index
                break

        fichier_upload.seek(0)
        df = pd.read_excel(fichier_upload, header=ligne_entete)
        st.success(f"✅ Fichier chargé ! En-tête détecté à la ligne {ligne_entete + 1}.")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        st.stop()

    # --- ÉTAPE 2 : SÉCURITÉ & CHOIX DES COLONNES ---
    st.header("🔒 2. Validation de la Sécurité (Anonymisation)")
    colonnes = list(df.columns)
    mots_cles_sensibles = ["nom", "prenom", "email", "telephone", "adresse", "salaire", "carte", "password", "mdp", "id"]
    suggestions_par_defaut = [col for col in colonnes if any(mot in str(col).lower() for mot in mots_cles_sensibles)]

    colonnes_a_supprimer = []
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Colonnes à supprimer (Sécurité) :")
        for col in colonnes:
            est_sensible = col in suggestions_par_defaut
            if st.checkbox(f"Supprimer : **{col}**", value=est_sensible, key=f"del_{col}"):
                colonnes_a_supprimer.append(col)

    with col2:
        st.write("### Aperçu des données :")
        st.dataframe(df.head(5))

    # --- ÉTAPE 3 : CADRAGE MÉTIER (NOUVEAU !) ---
    st.header("🎯 3. Cadrage Métier & Priorités")
    st.write("Aidez l'IA à comprendre ce qui est important pour votre analyse.")
    
    col_metier1, col_metier2 = st.columns(2)
    with col_metier1:
        objectif_analyse = st.text_input(
            "Quel est l'objectif principal de cette analyse ?", 
            placeholder="Ex: Identifier les retards de livraison, ou trouver les meilleures ventes..."
        )
    with col_metier2:
        colonnes_prioritaires = st.text_input(
            "Quelles sont les colonnes les plus importantes sur lesquelles se concentrer ?", 
            placeholder="Ex: Montant, Date, Région (laissez vide si tout est important)"
        )

    # Bouton pour lancer l'analyse
    if st.button("🚀 Lancer l'Analyse Intelligente", type="primary"):
        
        # 1. Nettoyage des données
        df_securise = df.drop(columns=colonnes_a_supprimer)
        
        with st.spinner("🧮 Calcul des statistiques en local..."):
            # 2. Stats locales
            stats_resume = {}
            stats_resume["nombre_de_lignes"] = len(df_securise)
            
            stats_numeriques = {}
            stats_textuelles = {}
            
            for col in df_securise.columns:
                if pd.api.types.is_numeric_dtype(df_securise[col]):
                    stats_numeriques[col] = {
                        "somme": float(df_securise[col].sum()),
                        "moyenne": float(df_securise[col].mean()),
                        "minimum": float(df_securise[col].min()),
                        "maximum": float(df_securise[col].max())
                    }
                else:
                    top_valeurs = df_securise[col].value_counts().head(3).to_dict()
                    stats_textuelles[col] = top_valeurs

            stats_resume["stats_chiffres"] = stats_numeriques
            stats_resume["stats_categories"] = stats_textuelles

        with st.spinner("🤖 L'IA analyse les données selon vos critères métier..."):
            # 3. Appel à Groq enrichi avec le contexte métier
            stats_texte = json.dumps(stats_resume, ensure_ascii=False, indent=2)
            aperçu_donnees = df_securise.head(5).to_string()

            # On intègre les consignes métier dans le prompt de l'IA
            prompt_systeme = (
                "Tu es un directeur financier et un consultant expert en stratégie d'entreprise. "
                "Ton rôle est d'analyser rigoureusement des données d'entreprise en te concentrant sur ce qui a de la valeur métier. "
                "Ignore les colonnes de données techniques ou sans intérêt."
            )

            prompt_utilisateur = f"""
Voici le contexte métier fourni par l'utilisateur :
- Objectif de l'analyse : {objectif_analyse if objectif_analyse else "Analyser globalement les performances"}
- Colonnes à privilégier / prioritaires : {colonnes_prioritaires if colonnes_prioritaires else "Toutes les colonnes importantes"}

Voici les statistiques exactes calculées sur le fichier anonymisé :
{stats_texte}

Voici un aperçu de la structure des données sécurisées :
{aperçu_donnees}

Génère un rapport professionnel structuré ainsi :
1. **Synthèse orientée Métier** (en lien direct avec l'objectif de l'utilisateur).
2. **Analyse approfondie des indicateurs prioritaires** (mets en avant les chiffres clés qui comptent vraiment).
3. **Plan d'action concret et opérationnel** (avec des recommandations étape par étape).
"""

            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[
                        {"role": "system", "content": prompt_systeme},
                        {"role": "user", "content": prompt_utilisateur}
                    ],
                    temperature=0.3
                )
                rapport = response.choices[0].message.content
                
                # --- AFFICHAGE DES RÉSULTATS ---
                st.success("✅ Analyse métier terminée avec succès !")
                
                st.header("📈 Statistiques Clés")
                st.json(stats_resume)

                st.header("📝 Rapport Stratégique & Plan d'Action")
                st.markdown(rapport)

            except Exception as e:
                st.error(f"❌ Erreur lors de l'appel à Groq : {e}")

else:
    st.info("👈 Veuillez importer un fichier Excel dans la barre latérale pour commencer.")
