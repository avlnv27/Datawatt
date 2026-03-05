"""
=====================================================================================
                  DATAWATT - CORPS PRINCIPAL DE L'APPLICATION 
=====================================================================================
Fichier principal pour l'application DATAWATT - Analyse de courbes de charge énergétiques
Développé pour SIE SA en collaboration avec l'EPFL

ARCHITECTURE DE L'APPLICATION:
- Structure modulaire avec séparation des responsabilités dans le dossier src/
- Interface web Streamlit avec trois onglets principaux
- Gestion d'état via st.session_state pour la persistance des données
- Support multi-utilisateurs (Particuliers/Professionnels)

FONCTIONNALITÉS PRINCIPALES:
1. Upload et analyse de fichiers de courbes de charge (CSV/XLSX)
2. Dashboard synthétique avec indicateurs clés de performance énergétique
3. Clustering automatique pour classification des profils de consommation
4. Analyses détaillées (ratios jour/nuit, semaine/week-end, charge de base)
5. Visualisations interactives (heatmaps, graphiques temporels)
6. Analyses personnalisées selon le type d'utilisateur
7. Calculs de coûts avec tarification flexible (HP/HC ou tarif unique)

STRUCTURE DES DONNÉES:
- DataFrame principal (pdf) contenant les données temporelles de consommation
- Index temporel (DatetimeIndex) pour analyses chronologiques
- Colonnes de consommation en kWh avec résolution 15min typique
- Support optionnel pour données solaires (Autoconsommation/Excédent)

DÉMARRAGE:
1. Installer les dépendances: pip install -r requirements.txt
2. Lancer l'application: streamlit run main.py
3. Accéder via un navigateur à l'adresse affichée  

AMELIORATIONS POUR LE FUTUR:  
1. Intégrer clairement le solaire.  
2. Utiliser des APIs avec la météo pour voir l'évolution de la consommation en fonction de la météo et en déduire 
de potentiels équipements énergivores (aussi bien l'été que l'hiver).  
3. Remettre la section sur les acteurs communaux et les hôtels avec des indicateurs précis. 

AUTEURS: Sven Hominal & Quentin Poindextre (EPFL) - SIE SA
DATE: Février-Août 2025
=====================================================================================
"""

# ============================================================================
# IMPORTATION DES MODULES SYSTÈME ET LIBRAIRIES PRINCIPALES
# ============================================================================
import streamlit as st          # Framework web pour l'interface utilisateur
import pandas as pd             # Manipulation et analyse de données temporelles
import numpy as np              # Calculs numériques et statistiques
import os                       # Opérations système et gestion des chemins
import importlib.util           # Import dynamique pour module de clustering
import sys                      # Configuration du système Python 

# Ajout du répertoire racine au PYTHONPATH pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) 

# ============================================================================
# IMPORTATION DES MODULES INTERNES - STRUCTURE MODULAIRE DU PROJET
# ============================================================================

# Module de gestion des textes et interface utilisateur
from src.textual import text as txt                 # Textes, bannières et messages d'interface

# Modules d'analyse et visualisation interactive
from src.indicators.interactive_plot import (       # Graphiques interactifs principaux
    display_interactive_plot,                       # Plot principal avec vues multiples (année/saison/semaine/jour)
    display_key_indicators_standalone,              # Indicateurs de consommation synthétiques  
    display_user_group_comparison                    # Comparaison avec groupes de référence
)

# Modules de formulaires utilisateur selon le type (particulier/professionnel/communal)
from src.textual.user_form import (
    display_user_form,                              # Formulaire pour particuliers
    display_user_corp_form,                         # Formulaire pour professionnels
    display_user_am_form                            # Formulaire pour acteurs communaux (non utilisé actuellement)
)

# Module de traitement des données d'entrée
from src.database.dataframe_gen import gen_pdf      # Lecture et nettoyage des fichiers CSV/XLSX uploadés

# Utilitaires d'interface
from src.textual.tools import tooltip_info          # Création des info-bulles explicatives

# Modules d'analyse des indicateurs énergétiques principaux
from src.indicators.day_night_ratio import (        # Analyse du ratio de consommation jour/nuit
    calculate_day_night_ratio,                      # Calcul des ratios par période (6h-22h vs 22h-6h)
    display_day_night_ratio                         # Affichage graphique et interprétation
)

from src.indicators.weekday_weekend_ratio import (  # Analyse du ratio semaine/week-end
    calculate_weekday_weekend_ratio,                # Calcul des ratios comportementaux hebdomadaires
    display_weekday_weekend_ratio                   # Visualisation des patterns de consommation
)

from src.indicators.base_load import (              # Analyse de la charge de base (consommation minimale)
    calculate_base_load,                            # Calcul de la puissance de base par année
    display_base_load                               # Affichage des tendances et interprétations
)

# Module de régression linéaire pour analyse des tendances (actuellement intégré dans base_load)
# from src.indicators.linear_regression import (perform_linear_regression, display_linear_regression_results)

# Module du tableau de bord principal
from src.dashboard.dashboard import (               # Dashboard synthétique avec cartes d'indicateurs
    create_dashboard,                               # Génération de l'interface dashboard complète
    calculate_dashboard_consumption_data            # Calculs des métriques pour les cartes de résumé
)

# Modules d'analyse personnalisée selon les données utilisateur
from src.indicators.personalized_analysis import ( # Analyses adaptées aux informations du formulaire
    display_surface_consumption,                    # Consommation par m² avec comparaisons sectorielles
    display_consumption,                            # Consommation per capita vs standards suisses
    generate_personalized_recommendations,          # Génération de recommandations personnalisées
    display_recommendations                         # Affichage formaté des recommandations
)

# Module de clustering et classification automatique des profils
from src.indicators.cluster_indic import (         # Classification des profils de consommation
    create_cluster_decile_comparison,               # Comparaison avec déciles par cluster
    generate_cluster_decile_recommendations,        # Recommandations basées sur le positionnement
    display_cluster_positioning_explanation,        # Explication du système de classification
    display_quick_indicators_summary                # Résumé rapide des caractéristiques du profil
)

# Module Google Analytics pour suivi d'utilisation (optionnel)
from src.analytics.google_analytics import (       # Tracking des interactions utilisateur
    inject_google_analytics,                       # Injection du code de tracking
    track_event,                                   # Suivi d'événements spécifiques
    track_page_view,                               # Suivi des pages visitées
    track_user_interaction,                        # Suivi des interactions (clics, formulaires)
    track_analysis_completion                      # Suivi de completion des analyses
)
from src.analytics.config import (                 # Configuration Google Analytics
    GOOGLE_ANALYTICS_ID,                          # ID de tracking (à configurer)
    ANALYTICS_CONFIG                              # Configuration des options de tracking
)

# Modules d'indicateurs et visualisations supplémentaires
from src.indicators.bar_plot_lin_reg import (      # Graphiques de régression et comparaisons
    bar_plot_lin_reg,                             # Graphiques en barres avec tendances
    bar_plot_lin_reg_surface                      # Comparaisons par surface avec régression
)
from src.indicators.heatmap_plot import display_heatmap                    # Heatmap annuelle de consommation
from src.indicators.weekly_pattern_heatmap import display_weekly_pattern_heatmap  # Heatmap des patterns hebdomadaires
from src.indicators.peak import (                  # Analyses spécialisées pour professionnels
    display_anomaly_analysis,                      # Détection d'anomalies de consommation
    display_peak_shaving_analysis                  # Analyse d'optimisation des pics de puissance
)
from src.indicators.cost_analysis import (         # Analyses économiques et tarifaires
    display_cost_analysis,                        # Interface complète d'analyse des coûts
    calculate_average_price                        # Calcul du prix moyen selon la tarification
)
from src.indicators.solar import display_solar_interactive_plot          # Analyses solaires (autoconsommation/excédent)
from src.indicators.pro_indicators import *       # Indicateurs spécialisés pour professionnels
# from src.indicators.hotel import analyze_hotel_consumption             # Module pour les hôtels (non utilisé actuellement) 

# ============================================================================
# MODULE DE CLUSTERING - CLASSIFICATION AUTOMATIQUE DES PROFILS
# ============================================================================
# Import du module de prédiction de cluster avec gestion d'erreurs robuste
# Le clustering permet de classifier automatiquement les profils de consommation
# en 4 groupes typiques basés sur 8 caractéristiques temporelles
try:
    # Tentative d'import direct depuis le module de clustering
    from Clustering_enhanced.predict_phase import predict_cluster_from_clean_dataset
except (ImportError, SyntaxError):
    # Méthode alternative d'importation en cas d'échec de l'import direct
    # Utile pour différents environnements Python ou structures de dossiers
    clustering_path = os.path.join(os.path.dirname(__file__), 'Clustering_enhanced', 'predict_phase.py')
    spec = importlib.util.spec_from_file_location("predict_module", clustering_path)
    predict_module = importlib.util.module_from_spec(spec)
    sys.modules["predict_module"] = predict_module
    spec.loader.exec_module(predict_module)
    predict_cluster_from_clean_dataset = predict_module.predict_cluster_from_clean_dataset


# ============================================================================
# CONFIGURATION DE L'APPLICATION STREAMLIT
# ============================================================================
# Configuration de la page web avec métadonnées et layout
st.set_page_config(
    page_title="DataWatt",                         # Titre affiché dans l'onglet du navigateur
    page_icon="design/logo_sie_sa.png",            # Icône dans l'onglet (logo SIE SA)
    layout="wide"                                  # Layout large pour optimiser l'espace écran
    # Alternative: "centered" pour un affichage plus compact
)

# ============================================================================
# INJECTION GOOGLE ANALYTICS (OPTIONNEL)
# ============================================================================
# Système de tracking pour analyser l'utilisation de l'application
# Activé uniquement si configuré dans analytics/config.py
if ANALYTICS_CONFIG.get("enabled", True) and GOOGLE_ANALYTICS_ID != "G-XXXXXXXXXX":
    inject_google_analytics(GOOGLE_ANALYTICS_ID)
    # Enregistrement de la visite de la page principale
    track_page_view("DataWatt - Page principale")

# ============================================================================
# INITIALISATION DE L'ÉTAT DE SESSION STREAMLIT
# ============================================================================
# Streamlit utilise st.session_state pour maintenir les données entre interactions
# Ceci évite de recalculer les analyses à chaque action utilisateur

# Données des formulaires selon le type d'utilisateur
st.session_state.setdefault('form_data', None)        # Formulaire particuliers
st.session_state.setdefault('form_data_c', None)      # Formulaire professionnels  
st.session_state.setdefault('form_data_am', None)     # Formulaire acteurs communaux (non utilisé)

# Données principales de l'application
st.session_state.setdefault('pdf', None)              # DataFrame principal des données de consommation
st.session_state.setdefault('flag_solar', 0)          # Flag détection colonnes solaires (0=aucun, 1=excédent, 2=autoconso)

# Données de clustering et profils de consommation
st.session_state.setdefault('cluster_predicted', None)    # Cluster prédit pour l'utilisateur (0-3)
st.session_state.setdefault('cluster_dist_fig', None)     # Graphique de distribution des clusters
st.session_state.setdefault('cluster_daily_fig', None)    # Graphique du profil journalier par cluster
st.session_state.setdefault('cluster_weekly_fig', None)   # Graphique du profil hebdomadaire par cluster

# Configuration tarifaire
st.session_state.setdefault('price', 0.35)            # Prix par défaut (CHF/kWh) pour compatibilité ascendante

# ============================================================================
# FONCTIONS UTILITAIRES POUR L'INTERFACE
# ============================================================================

def load_css(file_name):
    """
    Charge un fichier CSS personnalisé pour styliser l'interface Streamlit
    
    Args:
        file_name (str): Chemin vers le fichier CSS à charger
        
    Note:
        Fonction préparée mais non utilisée actuellement.
        Le styling se fait via st.markdown avec CSS inline.
    """
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file '{file_name}' not found. Using default styles.")
# load_css("style.css")  # Décommentez pour activer le CSS externe

def add_dashboard_return_button():
    """
    Génère un bouton de retour au dashboard avec style SIE SA
    
    Utilise un lien HTML avec ancre pour navigation rapide vers le haut de page.
    Le bouton utilise les couleurs de la charte graphique SIE SA (#e6321e).
    Positionné en bas à droite de chaque section pour navigation fluide.
    """
    st.markdown("""
    <div style="text-align: right; margin: 20px 0;">
        <a href="#dashboard" style="
            display: inline-block;
            padding: 8px 16px;
            background-color: #e6321e;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
            font-weight: bold;
            transition: background-color 0.3s;
        " onmouseover="this.style.backgroundColor='#c22e1a'" onmouseout="this.style.backgroundColor='#e6321e'">
            ⬆️ Retour au tableau de bord
        </a>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# INTERFACE UTILISATEUR PRINCIPALE - DÉBUT DE L'APPLICATION
# ============================================================================

# Affichage du header avec bandeau rouge "DATAWATT"
# Généré par src/textual/text.py pour cohérence visuelle
txt.header_banner()

# ============================================================================
# SECTION UPLOAD DE FICHIER
# ============================================================================
# Ancre HTML pour navigation interne vers cette section
st.markdown("<a id='upload'></a>", unsafe_allow_html=True)

# Traitement de l'upload et génération du DataFrame nettoyé
# gen_pdf() gère l'upload, la validation et le nettoyage des données
# Retourne: (DataFrame, flag_nouveau_fichier)
pdf_uploaded, flag = gen_pdf()  

# Gestion de l'état lors d'un nouvel upload
if flag == 1:
    # Réinitialisation complète des données de session pour nouveau fichier
    st.session_state['form_data'] = None              # Reset formulaire particuliers
    st.session_state['form_data_c'] = None            # Reset formulaire professionnels
    st.session_state['form_data_am'] = None           # Reset formulaire communaux
    st.session_state['cluster_predicted'] = None      # Reset résultats clustering
    st.session_state['cluster_dist_fig'] = None       # Reset graphiques clustering
    st.session_state['cluster_daily_fig'] = None
    st.session_state['cluster_weekly_fig'] = None
    
    # NOUVEAU: Reset cache des heatmaps lors d'un nouvel upload
    cache_keys_to_remove = [key for key in st.session_state.keys() if key.startswith(('heatmaps_', 'weekly_heatmap_', 'annual_heatmap_'))]
    for key in cache_keys_to_remove:
        del st.session_state[key]
    
    flag = 0  # Reset flag pour éviter boucle de rechargement

# Mise à jour de l'état de session avec le nouveau DataFrame
if pdf_uploaded is not None:
    # Stockage du DataFrame dans l'état de session pour persistance
    # Évite de retraiter les données à chaque interaction utilisateur
    st.session_state['pdf'] = pdf_uploaded
    
    # Tracking Google Analytics de l'upload (si activé)
    if ANALYTICS_CONFIG.get("enabled", True) and GOOGLE_ANALYTICS_ID != "G-XXXXXXXXXX":
        track_user_interaction("file_upload", "courbe_charge", "success")
    
    # Note: Réinitialisation optionnelle des formulaires pour nouvel upload
    # Décommentez les lignes suivantes si nécessaire:
    # st.session_state['form_data'] = None
    # st.session_state['form_data_c'] = None  
    # st.session_state['form_data_am'] = None

# Récupération du DataFrame depuis l'état de session pour traitement
pdf = st.session_state.get('pdf')

# ============================================================================
# ANALYSE ET VALIDATION DES DONNÉES TEMPORELLES
# ============================================================================
# Cette section traite les données uploadées et prépare l'interface utilisateur
if pdf is not None and not pdf.empty:
    
    # Analyse de la structure temporelle des données
    years_in_data = sorted(pdf.index.year.unique())   # Années présentes dans le dataset
    
    # Initialisation du flag pour années partielles
    if 'show_all_years' not in st.session_state:
        st.session_state['show_all_years'] = False
    
    # Calcul de la complétude de chaque année
    complete_years = []                                # Années avec données complètes (100%)
    years_completeness = {}                           # Dictionnaire {année: pourcentage_complétude}
    
    for year in years_in_data:
        year_data = pdf[pdf.index.year == year]
        # Compter les jours avec au moins une mesure
        days_with_data = year_data.resample('D').count().iloc[:, 0].gt(0).sum()
        # Déterminer le nombre de jours dans l'année (gestion années bissextiles)
        days_in_year = 366 if pd.Timestamp(year, 12, 31).is_leap_year else 365
        # Calcul du pourcentage de complétude
        completeness = (days_with_data / days_in_year) * 100
        years_completeness[year] = completeness
        
        # Classification comme année complète si 100% de couverture
        if completeness >= 100:
            complete_years.append(year)
    
    # Gestion automatique des années partielles
    # Si aucune année complète disponible, activer automatiquement l'inclusion des années partielles
    if len(complete_years) == 0 and len(years_in_data) >= 1:
        if 'show_all_years' not in st.session_state:
            st.session_state['show_all_years'] = True
        # Forcer l'activation même si déjà initialisé
        elif not st.session_state.get('show_all_years', False):
            st.session_state['show_all_years'] = True 
    
    # ========================================================================
    # CRÉATION DE LA SIDEBAR - INTERFACE DE CONFIGURATION
    # ========================================================================
    with st.sidebar:
        # Logo SIE SA en en-tête de la sidebar
        st.image("design/SIE_Logo_Pos_RVB.png", width=260)
        
        # Expander Conseils en haut de la sidebar
        with st.expander("Contactez SIE SA", expanded=False):
            st.markdown("""
            Pour plus de conseils, prenez rendez-vous avec un expert SIE SA.

            Pour toute question, assistance ou retours sur l'outil, veuillez contacter info@sie.ch.
            """)
        
        # Sélecteur de type d'utilisateur (détermine les analyses disponibles)
        user_type = st.selectbox(
            "Veuillez sélectionner votre type d'utilisateur :",
            ["Particulier", "Professionnel"],           # Options disponibles
            key='user_type_selector',                   # Clé unique pour éviter conflits
            index=0                                     # Particulier par défaut
        )
        st.session_state['user_type'] = user_type     # Sauvegarde dans l'état de session
        
        # Tracking de la sélection utilisateur (Google Analytics)
        if ANALYTICS_CONFIG.get("enabled", True) and GOOGLE_ANALYTICS_ID != "G-XXXXXXXXXX":
            track_user_interaction("user_type_selection", "sidebar", user_type)
    # ========================================================================
    # SECTION SÉLECTION DES DONNÉES D'ANALYSE
    # ========================================================================
    # Interface pour choisir la période d'analyse : données complètes ou année spécifique
    # Deux modes principaux :
    # 1. "Données complètes" : utilise toutes les années disponibles (avec option années partielles)
    # 2. "Année XXXX" : analyse une année spécifique uniquement
    with st.sidebar.expander("📊 Sélection des données d'analyse", expanded=True):
        
        # Construction des options de sélection
        year_selection_options = ["Données complètes"] + [f"Année {year}" for year in years_in_data]
        
        # Initialisation des variables de session pour la sélection temporelle
        if 'year_selection_mode' not in st.session_state:
            st.session_state['year_selection_mode'] = "Données complètes"
        if 'selected_single_year' not in st.session_state:
            st.session_state['selected_single_year'] = years_in_data[-1] if years_in_data else None
        
        # Calcul sécurisé de l'index par défaut
        try:
            default_index = year_selection_options.index(st.session_state['year_selection_mode'])
        except ValueError:
            default_index = 0
            st.session_state['year_selection_mode'] = "Données complètes"
        
        # Widget de sélection de la période d'analyse
        year_selection_mode = st.selectbox(
            "Choisissez la période d'analyse :",
            options=year_selection_options,
            index=default_index,
            help="Sélectionnez une année spécifique ou utilisez toutes les données disponibles. En sélectionnant le mode Données complètes, les calculs et les analyses sont faits sur l'ensemble de la période des données.",
            key="year_selection_widget"
        )
        
        # Gestion du changement de mode avec rechargement de l'interface
        if year_selection_mode != st.session_state.get('year_selection_mode'):
            st.session_state['year_selection_mode'] = year_selection_mode
            # Suppression du cache des figures pour forcer le recalcul
            st.session_state.pop('cached_figures', None)
            # Rechargement de l'application pour appliquer les changements
            st.rerun()
        # Traitement spécifique du mode "Année spécifique"
        if year_selection_mode != "Données complètes":
            # Extraction de l'année sélectionnée depuis le texte "Année XXXX"
            selected_year = int(year_selection_mode.split(" ")[1])
            if selected_year != st.session_state.get('selected_single_year'):
                st.session_state['selected_single_year'] = selected_year
            
            # Analyse de la période réelle des données pour l'année sélectionnée
            year_data = pdf[pdf.index.year == selected_year]
            if not year_data.empty:
                start_date_year = year_data.index.min()
                end_date_year = year_data.index.max()
                
                # Dictionnaires de traduction pour affichage en français
                # Améliore l'expérience utilisateur avec dates localisées
                jours_fr = {
                    'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
                    'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
                }
                mois_fr = {
                    'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
                    'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
                    'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
                }
                
                # Formatage des dates en français pour l'affichage
                start_day_fr = jours_fr.get(start_date_year.strftime('%A'), start_date_year.strftime('%A'))
                end_day_fr = jours_fr.get(end_date_year.strftime('%A'), end_date_year.strftime('%A'))
                start_month_fr = mois_fr.get(start_date_year.strftime('%B'), start_date_year.strftime('%B'))
                end_month_fr = mois_fr.get(end_date_year.strftime('%B'), end_date_year.strftime('%B'))
                
                start_date_year_fr = f"{start_day_fr} {start_date_year.day} {start_month_fr} {start_date_year.year}"
                end_date_year_fr = f"{end_day_fr} {end_date_year.day} {end_month_fr} {end_date_year.year}"
            
            # Affichage des informations sur l'année sélectionnée
            completeness = years_completeness[selected_year]
            status = "<span style='color: #27ae60; font-weight: bold;'>Complète</span>" if completeness >= 100 else "<span style='color: #ff9800; font-weight: bold;'>Incomplète</span>"
            
            # Informations sur la complétude de l'année sélectionnée
            st.markdown(f"""
            **Année sélectionnée:** {selected_year} ({completeness:.1f}% complète) - {status}
            """, unsafe_allow_html=True)
            
            # Affichage de la période réelle des données
            if not year_data.empty:
                st.markdown(f"""
                **Période des données analysées de votre fichier:**
                - Du {start_date_year_fr} au {end_date_year_fr}
                """)
            
            # Avertissement si les données sont incomplètes
            if completeness < 100:
                st.warning(f"⚠️ Cette année contient seulement {completeness:.1f}% des données. Les analyses pourraient être incomplètes.")
        else:
            # ================================================================
            # TRAITEMENT DU MODE "DONNÉES COMPLÈTES"
            # ================================================================
            # Gestion des cas mixtes : années complètes + années partielles
            
            # Classification des situations de données
            only_partial_years = len(complete_years) == 0 and len(years_in_data) >= 1
            mixed_years = len(complete_years) > 0 and len(complete_years) < len(years_in_data)
            
            # Affichage d'informations contextuelles selon la situation
            if only_partial_years:
                st.info("ℹ️ Votre fichier ne contient que des années avec des données partielles. L'option 'Inclure les années partielles' a été automatiquement activée.")
            elif mixed_years:
                if len(complete_years) == 1:
                    complete_year = complete_years[0]
                    st.info(f"ℹ️ Votre fichier contient **1 année complète** ({complete_year}) et {len(years_in_data) - len(complete_years)} année(s) partielle(s). **Par défaut, seule l'année {complete_year} est analysée.** Activez 'Inclure les années partielles' pour analyser toutes les données disponibles.")
                else:
                    st.info(f"ℹ️ Votre fichier contient **{len(complete_years)} années complètes** et {len(years_in_data) - len(complete_years)} année(s) partielle(s). **Par défaut, seules les années complètes sont analysées.** Activez 'Inclure les années partielles' pour analyser toutes les données disponibles.")
            else:
                # Toutes les années sont complètes - situation idéale
                if len(complete_years) == 1:
                    complete_year = complete_years[0]
                    st.success(f"✅ Votre fichier contient 1 année complète : {complete_year}")
                else:
                    st.success(f"✅ Votre fichier contient {len(complete_years)} années complètes")
            
            # Checkbox pour inclusion des années partielles
            show_all_years = st.checkbox(
                "Inclure les années partielles",
                value=st.session_state.get('show_all_years', False),
                help="Si activé, toutes les années disponibles seront incluses dans l'analyse, même celles avec des données incomplètes.",
                key="show_all_years_widget",
                disabled=only_partial_years  # Désactivée si uniquement des années partielles
            )
            
            # Mise à jour de l'état seulement en cas de changement (évite boucles infinies)
            if not only_partial_years and show_all_years != st.session_state.get('show_all_years', False):
                st.session_state['show_all_years'] = show_all_years
            # ============================================================
            # AFFICHAGE DE LA PÉRIODE ET DES STATISTIQUES DE DONNÉES
            # ============================================================
            
            # Calcul de la période globale des données pour résumé
            start_date = pdf.index.min()
            end_date = pdf.index.max()
            
            # Réutilisation des dictionnaires de traduction français (logique identique au mode année unique)
            jours_fr = {
                'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
                'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
            }
            mois_fr = {
                'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
                'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
                'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
            }
            
            # Formatage des dates extrêmes en français
            start_day_fr = jours_fr.get(start_date.strftime('%A'), start_date.strftime('%A'))
            end_day_fr = jours_fr.get(end_date.strftime('%A'), end_date.strftime('%A'))
            start_month_fr = mois_fr.get(start_date.strftime('%B'), start_date.strftime('%B'))
            end_month_fr = mois_fr.get(end_date.strftime('%B'), end_date.strftime('%B'))
            
            start_date_fr = f"{start_day_fr} {start_date.day} {start_month_fr} {start_date.year}"
            end_date_fr = f"{end_day_fr} {end_date.day} {end_month_fr} {end_date.year}"
            
            # Affichage de la période globale analysée
            st.markdown(f"""
            **Période des données analysées de votre fichier:**
            - Du {start_date_fr} au {end_date_fr}
            """)

            # Affichage détaillé de la complétude par année
            st.markdown("**Années disponibles:**")
            
            # Boucle d'affichage du statut de chaque année
            for year in years_in_data:
                completeness = years_completeness[year]
                is_complete = completeness >= 100
                status = "<span style='color: #27ae60; font-weight: bold;'>Complète</span>" if is_complete else "<span style='color: #ff9800; font-weight: bold;'>Incomplète</span>"
                
                st.markdown(f"• {year} ({completeness:.1f}%) - {status}", unsafe_allow_html=True)
            
    # ========================================================================
    # CONFIGURATION DES TARIFS ÉNERGÉTIQUES
    # ========================================================================
    # Interface pour configuration des prix de l'électricité
    # Supporte deux modes : Tarif Unique (Solo) et Tarif HP/HC (Modulo SIE SA)
    with st.sidebar.expander("💰 Configuration des tarifs", expanded=True):
        
        # Initialisation des variables tarifaires par défaut
        # Valeurs basées sur les tarifs SIE SA typiques (2024-2025)
        if 'tariff_type' not in st.session_state:
            st.session_state['tariff_type'] = "Tarif Unique"
        if 'tariff_unique_price' not in st.session_state:
            st.session_state['tariff_unique_price'] = 0.35          # Prix moyen CHF/kWh pour tarif unique
        if 'tariff_hp_price' not in st.session_state:
            st.session_state['tariff_hp_price'] = 0.40             # Prix heures pleines CHF/kWh
        if 'tariff_hc_price' not in st.session_state:
            st.session_state['tariff_hc_price'] = 0.27             # Prix heures creuses CHF/kWh
            
        # Horaires fixes SIE SA pour la tarification HP/HC
        # Ces horaires sont codés en dur et cohérents avec les autres modules
        if 'peak_start_hour' not in st.session_state:
            st.session_state['peak_start_hour'] = 6               # Début heures pleines : 06h00
        if 'peak_end_hour' not in st.session_state:
            st.session_state['peak_end_hour'] = 22                # Fin heures pleines : 22h00
        if 'peak_days' not in st.session_state:
            st.session_state['peak_days'] = [0, 1, 2, 3, 4, 5, 6] # Tous les jours (0=lundi, 6=dimanche)
        
        # Sélecteur de type de tarif
        tariff_options = ["Tarif Unique", "Tarif HP/HC"]
        try:
            default_tariff_index = tariff_options.index(st.session_state['tariff_type'])
        except (ValueError, KeyError):
            default_tariff_index = 0
            st.session_state['tariff_type'] = "Tarif Unique"
        
        # Widget de sélection du type de contrat
        tariff_type = st.selectbox(
            "Type de contrat :",
            options=tariff_options,
            index=default_tariff_index,
            help="Choisissez le type de tarif selon votre contrat d'électricité",
            key="tariff_type_widget"
        )
        
        # Gestion du changement de type de tarif avec rechargement
        if tariff_type != st.session_state.get('tariff_type'):
            st.session_state['tariff_type'] = tariff_type
            st.rerun()  # Rechargement nécessaire pour mise à jour de l'interface        # Configuration selon le mode tarifaire sélectionné
        if st.session_state.get('tariff_type') == "Tarif Unique":
            # ========================================================
            # MODE TARIF UNIQUE (SOLO)
            # ========================================================
            # Configuration simplifiée avec un prix unique pour toutes les heures
            unique_price = st.number_input(
                "Prix du kWh (CHF) :",
                min_value=0.05,                                    # Prix minimum réaliste
                max_value=1.0,                                     # Prix maximum réaliste  
                value=st.session_state['tariff_unique_price'],
                step=0.01,                                         # Précision au centime
                format="%.2f",
                help="Prix par kilowattheure selon votre contrat",
                key="unique_price_widget"
            )
            # Mise à jour immédiate des variables de session
            st.session_state['tariff_unique_price'] = unique_price
            st.session_state['price'] = unique_price              # Variable unifiée pour compatibilité
            
            # Affichage récapitulatif du tarif configuré
            st.markdown(f"""
            <div style="background-color: #e8f5e8; padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 0.9em;">
                <strong>Tarif :</strong> {unique_price:.2f} CHF/kWh (uniforme)
            </div>
            """, unsafe_allow_html=True)

        else:
            # ========================================================
            # MODE TARIF HP/HC (MODULO)
            # ========================================================
            # Configuration avec différenciation heures pleines/heures creuses
            # Horaires fixes basés sur la tarification SIE SA
            
            # Information sur les horaires SIE SA (non modifiables)
            st.markdown("""
            <div style="background-color: #f0f8ff; padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 0.85em;">
                📌 <strong>Horaires SIE SA :</strong><br>
                • Heures creuses : 22h00 - 06h00<br>
                • Heures pleines : 06h00 - 22h00
            </div>
            """, unsafe_allow_html=True)
            
            # Configuration des prix HP et HC en colonnes pour optimiser l'espace
            col_hp, col_hc = st.columns(2)
            
            with col_hp:
                hp_price = st.number_input(
                    "Prix HP (CHF/kWh) :",
                    min_value=0.05,
                    max_value=1.0,
                    value=st.session_state['tariff_hp_price'],
                    step=0.01,
                    format="%.2f",
                    key="hp_price_widget"
                )
                st.session_state['tariff_hp_price'] = hp_price
            
            with col_hc:
                hc_price = st.number_input(
                    "Prix HC (CHF/kWh) :",
                    min_value=0.05,
                    max_value=1.0,
                    value=st.session_state['tariff_hc_price'],
                    step=0.01,
                    format="%.2f",
                    key="hc_price_widget"
                )
                st.session_state['tariff_hc_price'] = hc_price
            
            # Calcul du prix moyen pondéré pour compatibilité avec les modules existants
            # Simplification : moyenne arithmétique (amélioration possible avec pondération réelle)
            avg_price = (hp_price + hc_price) / 2
            st.session_state['price'] = avg_price             # Variable unifiée pour compatibilité ascendante
            
            # Affichage récapitulatif des tarifs HP/HC
            st.markdown(f"""
            <div style="background-color: #e8f5e8; padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 0.9em;">
                <strong>HP :</strong> {hp_price:.2f} CHF/kWh (06h00-22h00)<br>
                <strong>HC :</strong> {hc_price:.2f} CHF/kWh (22h00-06h00)
            </div>
            """, unsafe_allow_html=True)    # ========================================================================
    # BARRE DE NAVIGATION DYNAMIQUE (SIDEBAR)
    # ========================================================================
    with st.sidebar:
        # Section de navigation pour l'onglet "Analyse Principale"
        # Navigation adaptative selon les données disponibles et le type d'utilisateur
        st.markdown("""
        <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px;'>
            <h3 style='text-align: center; color: #262730; margin-bottom: 10px; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px;'>Navigation - Analyse Principale</h3>
        """, unsafe_allow_html=True)
        
        # Construction dynamique des sections de navigation
        sections = []
        
        # Ajout conditionnel des sections selon les données disponibles
        if pdf is not None and not pdf.empty:
            # Section dashboard toujours présente si données chargées
            sections.append({"id": "dashboard", "name": "Tableau de bord"})
            
            # Section clustering uniquement pour les particuliers
            if user_type == "Particulier":
                sections.append({"id": "clustering-early", "name": "Votre profil"})
            
            # Sections d'analyse communes à tous les types d'utilisateurs
            sections.extend([
                {"id": "courbe-charge", "name": "Courbe de charge"},
                {"id": "indicateurs-consommation", "name": "Indicateurs clés"},
                {"id": "cout", "name": "Analyse des coûts"},
                {"id": "jour-nuit", "name": "Ratio Jour/Nuit"},
                {"id": "ratios", "name": "Ratio Semaine/Week-end"},
                {"id": "charge-base", "name": "Charge de base"}
            ])
        else:
            # Section upload si aucune donnée chargée
            sections.append({"id": "upload", "name": "📁 Charger vos données"})
            
        # Génération des liens de navigation HTML avec ancres
        links_html = ""
        for i, section in enumerate(sections):
            links_html += f"""
            <div style='margin-bottom: 8px; padding: 5px 10px; border-radius: 4px; transition: background-color 0.3s;' 
                 onmouseover="this.style.backgroundColor='#e8f4fd'" 
                 onmouseout="this.style.backgroundColor='transparent'">
                <a href='#{section["id"]}' style='text-decoration: none; color: #4F8BF9; font-size: 0.9em; font-weight: 500; display: block;'>
                    {section["name"]}
                </a>
            </div>
            """
            
        st.markdown(links_html + "</div>", unsafe_allow_html=True)

        # Affichage des informations additionnelles en bas de sidebar
        # Textes configurables via src/textual/text.py
        txt.side_info()
    # ========================================================================
    # SAUVEGARDE ET PRÉPARATION DES DONNÉES D'ANALYSE
    # ========================================================================
    # Stockage des métadonnées temporelles dans l'état de session pour réutilisation
    st.session_state['years_in_data'] = years_in_data              # Liste des années présentes
    st.session_state['complete_years'] = complete_years            # Liste des années complètes (100%)
    st.session_state['years_completeness'] = years_completeness    # Dict {année: pourcentage}
    st.session_state['num_complete_years'] = len(complete_years)   # Nombre d'années complètes
    st.session_state['num_years_in_data'] = len(years_in_data)     # Nombre total d'années
    
    # ========================================================================
    # FILTRAGE DES DONNÉES SELON LA SÉLECTION UTILISATEUR
    # ========================================================================
    # Détermine le sous-ensemble de données à analyser selon les choix utilisateur
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    if year_selection_mode == "Données complètes":
        # ================================================================
        # MODE DONNÉES COMPLÈTES
        # ================================================================
        # Logique de sélection des années à inclure dans l'analyse
        if len(complete_years) == 0:
            # Aucune année complète : forcer l'utilisation de toutes les années
            years_to_use = years_in_data
        else:
            # Choix utilisateur : années complètes uniquement ou toutes les années
            years_to_use = years_in_data if st.session_state.get('show_all_years', False) else complete_years
        
        # Configuration pour mode multi-années
        st.session_state['analysis_mode'] = 'multi_year'
        st.session_state['years_to_use'] = years_to_use
        
        # Filtrage du DataFrame selon les années sélectionnées
        pdf_filtered = pdf[pdf.index.year.isin(years_to_use)]
        
    else:
        # ================================================================
        # MODE ANNÉE SPÉCIFIQUE
        # ================================================================
        selected_year = st.session_state.get('selected_single_year')
        if selected_year:
            years_to_use = [selected_year]
            
            # Configuration pour mode année unique
            st.session_state['analysis_mode'] = 'single_year'
            st.session_state['years_to_use'] = years_to_use
            st.session_state['selected_analysis_year'] = selected_year
            
            # Filtrage pour l'année spécifique
            pdf_filtered = pdf[pdf.index.year == selected_year]
        else:
            # Fallback en cas d'erreur : retour au mode données complètes
            years_to_use = years_in_data if len(complete_years) == 0 else (
                years_in_data if st.session_state.get('show_all_years', False) else complete_years
            )
            st.session_state['analysis_mode'] = 'multi_year'
            st.session_state['years_to_use'] = years_to_use
            pdf_filtered = pdf[pdf.index.year.isin(years_to_use)]
    
    # Sauvegarde du DataFrame filtré pour utilisation dans les analyses
    st.session_state['pdf_filtered'] = pdf_filtered

# ============================================================================
# TRAITEMENT DES DONNÉES CHARGÉES ET DÉTECTION DES FONCTIONNALITÉS
# ============================================================================
if pdf is not None and not pdf.empty:

    # ========================================================================
    # DÉTECTION AUTOMATIQUE DES COLONNES SOLAIRES
    # ========================================================================
    # Analyse des colonnes pour détecter les données de production/autoconsommation solaire
    # Flag solar : 0=aucun, 1=excédent détecté, 2=autoconsommation détectée
    if 'flag_solar' not in st.session_state or st.session_state['flag_solar'] == 0:
        if 'Autoconsumption' in pdf.columns:
            st.session_state['flag_solar'] = 2              # Autoconsommation disponible
        elif 'Excedent' in pdf.columns:
            st.session_state['flag_solar'] = 1              # Excédent disponible
        else:
            st.session_state['flag_solar'] = 0              # Aucune donnée solaire

    # ========================================================================
    # PRÉ-CALCUL DES INDICATEURS PRINCIPAUX POUR LE DASHBOARD
    # ========================================================================
    # Calculs effectués en amont pour optimiser les performances d'affichage
    # Tous les indicateurs sont calculés sur le DataFrame filtré (pdf_for_analysis)
    
    # Récupération du DataFrame filtré selon la sélection utilisateur
    pdf_for_analysis = st.session_state.get('pdf_filtered', pdf)
    
    # Calcul du ratio jour/nuit (6h-22h vs 22h-6h)
    ratio_day_night_data = calculate_day_night_ratio(pdf_for_analysis)
    st.session_state['ratio_day_night_data'] = ratio_day_night_data
    st.session_state['ratio_day_night'] = ratio_day_night_data['overall_ratio']
    
    # Calcul du ratio semaine/week-end (comportement hebdomadaire)
    ratio_weekday_weekend_data = calculate_weekday_weekend_ratio(pdf_for_analysis)
    st.session_state['ratio_weekday_weekend_data'] = ratio_weekday_weekend_data
    st.session_state['ratio'] = ratio_weekday_weekend_data['overall_ratio']
    
    # Calcul de la charge de base (puissance minimale de veille)
    years, base_loads = calculate_base_load(pdf_for_analysis)
    st.session_state['years'] = years
    st.session_state['base_loads'] = base_loads
    
    # Calcul du prix moyen pour les analyses de coûts
    price = calculate_average_price()
    st.session_state['price'] = price
    
    # Calcul des données de consommation agrégées pour le dashboard
    consumption_data, consumption_years = calculate_dashboard_consumption_data(pdf_for_analysis)
    st.session_state['dashboard_consumption_data'] = consumption_data
    st.session_state['dashboard_consumption_years'] = consumption_years
    # ========================================================================
    # CALCUL DU CLUSTERING POUR UTILISATEURS PARTICULIERS
    # ========================================================================
    # Classification automatique du profil de consommation en 4 groupes typiques
    # Uniquement disponible pour les particuliers (analyse comportementale)
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier":
        # Vérification si le clustering n'a pas déjà été calculé (optimisation)
        if 'cluster_predicted' not in st.session_state or st.session_state['cluster_predicted'] is None:
            try:
                # Appel du module de prédiction de cluster
                # Utilise un modèle pré-entraîné avec 8 caractéristiques temporelles
                predicted_cluster, dist_fig, daily_fig, weekly_fig = predict_cluster_from_clean_dataset()
                
                # Stockage des résultats dans l'état de session
                if predicted_cluster is not None:
                    st.session_state['cluster_predicted'] = predicted_cluster      # Groupe prédit (0-3)
                    st.session_state['cluster_dist_fig'] = dist_fig               # Graphique de distribution
                    st.session_state['cluster_daily_fig'] = daily_fig             # Profil journalier moyen
                    st.session_state['cluster_weekly_fig'] = weekly_fig           # Profil hebdomadaire moyen
            except Exception as e:
                # Gestion d'erreur silencieuse : clustering optionnel
                st.session_state['cluster_predicted'] = None

    # ========================================================================
    # ANCRE DE NAVIGATION POUR LE DASHBOARD
    # ========================================================================
    # Point d'ancrage HTML pour la navigation interne vers le tableau de bord
    st.markdown("<a id='dashboard'></a>", unsafe_allow_html=True)
    # ========================================================================
    # SYSTÈME D'ONGLETS PRINCIPAUX DE L'APPLICATION
    # ========================================================================
    # Interface à trois onglets pour organiser les différentes analyses
    # 1. ANALYSE PRINCIPALE : Dashboard + indicateurs détaillés + clustering
    # 2. CARTOGRAPHIE : Heatmaps de consommation (calcul à la demande)
    # 3. ANALYSE PERSONNALISÉE : Formulaires + analyses spécialisées
    
    # Initialisation de l'onglet actif dans l'état de session
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 0                # Onglet "Analyse Principale" par défaut
    
    # Configuration des onglets avec noms explicites
    tab_names = ["**ANALYSE PRINCIPALE**", "**CARTOGRAPHIE**", "**ANALYSE PERSONNALISÉE**"]
    
    # Implémentation personnalisée avec colonnes (plus rapide que st.tabs natif)
    # Permet une meilleure gestion des événements et du state
    tab_cols = st.columns(3)
    
    # CSS personnalisé pour le styling des boutons d'onglets
    # Utilise les couleurs de la charte graphique SIE SA
    st.markdown("""
    <style>
    .stButton > button {
        color: #4a4a4a !important;
        font-weight: bold !important;
        background-color: #f5f5f5 !important;
        border: 2px solid #d9534f !important;
        border-radius: 8px !important;
    }
    
    .stButton > button:hover {
        background-color: #eeeeee !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Génération des boutons d'onglets avec gestion d'événements
    for i, (col, name) in enumerate(zip(tab_cols, tab_names)):
        with col:
            if st.button(name, key=f"tab_{i}", use_container_width=True):
                # Changement d'onglet SANS rechargement complet
                if st.session_state['active_tab'] != i:
                    st.session_state['active_tab'] = i
                    # Tracking Google Analytics du changement d'onglet
                    if ANALYTICS_CONFIG.get("enabled", True) and GOOGLE_ANALYTICS_ID != "G-XXXXXXXXXX":
                        tab_names_clean = ["analyse_principale", "cartographie", "analyse_personnalisee"]
                        track_user_interaction("tab_change", "navigation", tab_names_clean[i])
                    # Rechargement optimisé seulement si nécessaire
                    st.rerun()
    
    # Système d'indicateurs visuels pour l'onglet actif
    indicator_cols = st.columns(3)
    active_tab = st.session_state['active_tab']
    
    # Affichage des barres d'indication sous les boutons
    for i, col in enumerate(indicator_cols):
        with col:
            if i == active_tab:
                # Barre noire pour l'onglet actif
                st.markdown(f"""
                <div style="height: 3px; background-color: #000000; margin: -21px 10px 15px 10px; border-radius: 2px;"></div>
                """, unsafe_allow_html=True)
            else:
                # Espace vide pour les onglets inactifs
                st.markdown(f"""
                <div style="height: 3px; margin: -5px 10px 15px 10px;"></div>
                """, unsafe_allow_html=True)
    # ========================================================================
    # AFFICHAGE CONDITIONNEL DU CONTENU SELON L'ONGLET ACTIF
    # ========================================================================

    # ==================== ONGLET 1: ANALYSE PRINCIPALE ====================
    if active_tab == 0:
        # ====================================================================
        # SECTION TABLEAU DE BORD - VUE D'ENSEMBLE SYNTHÉTIQUE
        # ====================================================================
        txt.section_title("Votre tableau de bord")        # Titre de section standardisé
        create_dashboard()                                 # Génération du dashboard avec cartes d'indicateurs
        
        # Tracking de completion du dashboard pour analytics
        if ANALYTICS_CONFIG.get("enabled", True) and GOOGLE_ANALYTICS_ID != "G-XXXXXXXXXX":
            track_analysis_completion("dashboard", st.session_state.get('user_type', 'Unknown'))
        
        # Info-bulle explicative et message d'orientation
        tooltip_info("Information")
        st.info("Cliquez sur les liens sous les indicateurs afin d'aller sur les sections détaillées afin de comprendre vos données, les calculs et les interprétations de ces valeurs.")

        # ====================================================================
        # SECTION CLUSTERING - PROFIL DE CONSOMMATION (PARTICULIERS UNIQUEMENT)
        # ====================================================================
        user_type = st.session_state.get('user_type', "Particulier")
        if user_type == "Particulier":
            st.markdown("<a id='clustering-early'></a>", unsafe_allow_html=True)  # Ancre de navigation
            txt.section_title("Votre profil de consommation")

            # Exécution du clustering avec indicateur de progression
            with st.spinner("Analyse de votre profil de consommation en cours..."):
                # Vérification et calcul du clustering si nécessaire
                if 'cluster_predicted' not in st.session_state or st.session_state['cluster_predicted'] is None:
                    try:
                        # Validation des données avant clustering
                        if pdf is None or pdf.empty:
                            st.error("Aucune donnée disponible pour l'analyse de clustering. Veuillez charger un fichier valide.")
                        else:
                            # Exécution de la prédiction de cluster
                            # Utilise un modèle ML pré-entraîné avec 8 caractéristiques temporelles
                            # Voir Clustering_enhanced/predict_phase.py pour détails
                            predicted_cluster, dist_fig, daily_fig, weekly_fig = predict_cluster_from_clean_dataset()
                            
                            # Stockage des résultats avec validation
                            if predicted_cluster is not None:
                                st.session_state['cluster_predicted'] = predicted_cluster
                                st.session_state['cluster_dist_fig'] = dist_fig
                                st.session_state['cluster_daily_fig'] = daily_fig
                                st.session_state['cluster_weekly_fig'] = weekly_fig
                                
                                # Tracking de completion du clustering
                                if ANALYTICS_CONFIG.get("enabled", True) and GOOGLE_ANALYTICS_ID != "G-XXXXXXXXXX":
                                    track_analysis_completion("clustering", "Particulier")
                            else:
                                st.error("L'analyse de clustering n'a pas pu être effectuée. Vérifiez que votre fichier contient une série temporelle de consommation valide.")
                    except Exception as e:
                        st.error(f"Une erreur s'est produite pendant l'analyse de clustering: {str(e)}")
                        st.session_state['cluster_predicted'] = None

            # Afficher le résultat du clustering si disponible
            if 'cluster_predicted' in st.session_state and st.session_state['cluster_predicted'] is not None:
                predicted_cluster = st.session_state['cluster_predicted']

                # Description rapide par cluster (groupe) avec profil intégré
                cluster_quick_descriptions = {
                    0: "🎯 Votre profil correspond au **Groupe 0 - Ménage à consommation élevée** - Profil avec une consommation plus élevée que la moyenne et un schéma saisonnier marqué.",
                    1: "🎯 Votre profil correspond au **Groupe 1 - Ménage à consommmation régulière** - Profil avec une consommation relativement constante tout au long de l'année.",
                    2: "🎯 Votre profil correspond au **Groupe 2 - Ménage à faible consommation diurne** - Profil avec une faible consommation pendant la journée, typique des ménages équipés de panneaux solaires ou absents la journée.",
                    3: "🎯 Votre profil correspond au **Groupe 3 - Ménage avec activités professionnelles** - Profil similaire à celui d'une activité professionnelle à domicile."
                }
                
                if predicted_cluster in cluster_quick_descriptions:
                    st.success(cluster_quick_descriptions[predicted_cluster])
                
                
                # Récupérer les features depuis la session ou les calculer si nécessaire
                if 'user_features' in st.session_state:
                    user_features = st.session_state['user_features']
                else:
                    # Si les features ne sont pas disponibles, les recalculer (au cas où), un peu hard-codé mais facilement modifiable
                    def get_consumption_column(df):
                        """Retourne le nom de la colonne de consommation principale"""
                        possible_names = ['Consumption (kWh)', 'Consumption', 'consumption', 'kWh']
                        for name in possible_names:
                            if name in df.columns:
                                return name
                        return df.columns[0]  # Prendre la première colonne par défaut
                    
                    try:
                        from Clustering_enhanced.predict_phase import calculate_timeseries_features_8 as calculate_timeseries_features_8_to_compare
                        user_features = calculate_timeseries_features_8_to_compare(pdf[get_consumption_column(pdf)], pdf.index)
                        st.session_state['user_features'] = user_features
                    except Exception as e:
                        st.warning(f"Impossible de calculer les caractéristiques détaillées: {e}")
                        user_features = None
                    
                # Créer et afficher le graphique de comparaison des déciles
                if user_features is not None:
                    decile_chart = create_cluster_decile_comparison(user_features, predicted_cluster)
                    if decile_chart is not None:
                        st.plotly_chart(decile_chart, use_container_width=True)
                    
                    # Afficher le résumé rapide des indicateurs
                    # A REACTIVER ICI SI ON VEUT REMETTRE L'AFFICHAGE DES INDICATEURS DE MANIERE TEXTUELLE AU TOUT DEBUT 
                    #display_quick_indicators_summary(user_features, predicted_cluster)
                    
                    # Afficher l'explication du positionnement après le graphique
                    tooltip_info("Information")
                    display_cluster_positioning_explanation()

                    # Récupérer les recommandations basées sur les déciles, code géré dans src/indicators/cluster_indic.py
                    high_decile_recommendations, low_decile_remarks = generate_cluster_decile_recommendations(
                        user_features, predicted_cluster)
                    
                    # Afficher les recommandations et remarques
                    
                    # Si un grand décile est détécté 
                    if high_decile_recommendations:
                        st.markdown("""
                        <div style="background-color: #fff3f3; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 5px solid #e74c3c;">
                            <h4>Points d'amélioration identifiés</h4>
                        """, unsafe_allow_html=True)
                        for rec in high_decile_recommendations:
                            st.markdown(f"- {rec}", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

                    # Si un petit décile est détécté
                    if low_decile_remarks:
                        st.markdown("""
                        <div style="background-color: #e8f8f5; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 5px solid #2ecc71;">
                            <h4>Points forts de votre profil</h4>
                        """, unsafe_allow_html=True)
                        for remark in low_decile_remarks:
                            st.markdown(f"- {remark}", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                
                # GRAPHIQUES EN PLUS POUR L'UTILISATEUR, calculés dans le dossier Clustering_enhanced
                # Afficher les profils de consommation dans un expander. 
                # Voir le rapport Design Project pour plus d'informations sur la manière dont les groupes ont été calculés 
                # L'entrainement devra être refait pour plus de précisions et de cohérence avec les calculs d'indicateurs de la présente web app 
                # et pour créer plus de profils de comparaisons par la suite.  

                with st.expander("Voir les profils de consommation détaillés", expanded=False):
                    # Section 1: Profil journalier
                    st.warning("Votre courbe personnelle s'affiche en noire, des numéros ont été assignés aux groupes pour faciliter l'entrainement mais cette numérotation ne correspond à un classement (bon ou moins bon) entre groupes.")
                    
                    st.info("""
                    **Les 4 types de profils possibles sont :**
                    
                    • **Groupe 0** - Ménage à consommation élevée  
                    • **Groupe 1** - Ménage à consommation réguliere  
                    • **Groupe 2** - Ménage à faible consommation diurne  
                    • **Groupe 3** - Ménage avec activités professionnelles
                    """)
                    
                    st.subheader("Profil de consommation journalier")
                    st.markdown(f"""
                    Ce graphique compare votre profil de consommation journalier moyen avec celui des différents 
                    groupes. Votre profil est représenté par la ligne noire, tandis que le profil du 
                    groupe {predicted_cluster} (votre groupe) est mis en évidence.
                    """)
                    if 'cluster_daily_fig' in st.session_state and st.session_state['cluster_daily_fig'] is not None:
                        st.plotly_chart(st.session_state['cluster_daily_fig'], use_container_width=True)
                    
                    # Section 2: Profil hebdomadaire
                    st.subheader("Profil de consommation hebdomadaire")
                    st.markdown(f"""
                    Ce graphique montre comment votre consommation varie au cours de la semaine, comparée 
                    aux profils moyens des différents groupe.
                    """)
                    if 'cluster_weekly_fig' in st.session_state and st.session_state['cluster_weekly_fig'] is not None:
                        st.plotly_chart(st.session_state['cluster_weekly_fig'], use_container_width=True)
            else:
                st.info("L'analyse de votre profil de consommation sera disponible une fois vos données chargées.")
            
            # Affichage d'informations si seules des années partielles sont disponibles
            if (len(st.session_state.get('complete_years', [])) == 0 and 
                len(st.session_state.get('years_in_data', [])) >= 1):
                st.info("ℹ️ Votre fichier contient uniquement des années avec des données partielles. L'analyse s'adapte automatiquement à vos données disponibles.")

            # Bouton retour dashboard
            add_dashboard_return_button()

        # --- Section 1: Visualisations (Toujours affichées, commun aux Particuliers et aux Professionnels) ---
        st.markdown("<a id='courbe-charge'></a>", unsafe_allow_html=True)
        
        # Premier plot interactif avec vue "Année", "Saison", "Semaine" et "Jour"
        txt.section_title("Courbe de charge")
        display_interactive_plot(pdf_for_analysis)
        tooltip_info("Information")
        txt.load_curve()

        # Indicateurs de consommation
        st.markdown("<a id='indicateurs-consommation'></a>", unsafe_allow_html=True)
        display_key_indicators_standalone(pdf_for_analysis)
        
        # Comparaison avec le groupe de consommation pour les consommations hivernales et estivales
        display_user_group_comparison()

        # Bouton retour dashboard
        add_dashboard_return_button()

        # Analyse des coûts énergétiques
        st.markdown("<a id='cout'></a>", unsafe_allow_html=True)
        txt.section_title("Analyse des coûts énergétiques")
        # Réafficher l'analyse des coûts (maintenant avec l'affichage)
        price = display_cost_analysis(pdf_for_analysis)
        st.session_state['price'] = price

        # Bouton retour dashboard
        add_dashboard_return_button()

        # --- Affichage des sections détaillées (utilisant les calculs déjà effectués plus haut pour le dashboard) ---
        
        # Ratio Jour/Nuit
        st.markdown("<a id='jour-nuit'></a>", unsafe_allow_html=True)
        txt.section_title("Ratio Jour/Nuit")
        display_day_night_ratio(ratio_day_night_data, pdf_for_analysis)

        # Bouton retour dashboard
        add_dashboard_return_button()

        # Ratio Semaine/Week-end
        st.markdown("<a id='ratios'></a>", unsafe_allow_html=True)
        txt.section_title("Ratio Semaine/Week-end")
        display_weekday_weekend_ratio(ratio_weekday_weekend_data, pdf_for_analysis)

        # Bouton retour dashboard
        add_dashboard_return_button()

        # Charge de Base (avec charge nocturne et charge minimale)
        st.markdown("<a id='charge-base'></a>", unsafe_allow_html=True)
        txt.section_title("Charge de Base")
        display_base_load(years, base_loads)

        # Bouton retour dashboard
        add_dashboard_return_button()

        # Cette partie n'est plus utilisée car merge dans l'indicateur pour la charge de base 

        #st.markdown("<a id='tendances'></a>", unsafe_allow_html=True)
        #txt.section_title("Tendance de consommation")
        # Calculer et afficher la régression linéaire
        #trend_data = perform_linear_regression(pdf_for_analysis)
        #display_linear_regression_results(trend_data, pdf_for_analysis)


    # ========== ONGLET 2: CARTOGRAPHIE ========== 
    # Onglet créé pour les heatmaps de visualisation car demande un calcul plus long, le calcul 
    # se lance lorsque l'utilisateur clique sur l'onglet, ce qui permet d'accélérer l'affichage dans la 
    # page "Analyse Principale"
    elif active_tab == 1:
        
        st.markdown("<a id='heatmap'></a>", unsafe_allow_html=True)
        txt.section_title("Cartographie de consommation")
        
        # CACHE PLUS ROBUSTE basé sur les années analysées et le mode
        analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
        years_to_use = st.session_state.get('years_to_use', [])
        cache_key = f"heatmaps_{analysis_mode}_{'_'.join(map(str, sorted(years_to_use)))}"
        
        # Vérifier si les heatmaps sont déjà en cache
        if f"{cache_key}_calculated" not in st.session_state:
            # Première fois : calculer et mettre en cache
            with st.spinner("Chargement des cartes de consommation..."):
                # Créer un système d'onglets pour choisir entre les deux visualisations
                heatmap_tabs = st.tabs(["Cartographie hebdomadaire", "Cartographie annuelle"])
                
                # Onglet pour la cartographie hebdomadaire
                with heatmap_tabs[0]:
                    display_weekly_pattern_heatmap(pdf_for_analysis)
                
                # Onglet pour la cartographie annuelle
                with heatmap_tabs[1]:
                    display_heatmap(pdf_for_analysis)
                
                # Marquer comme calculé dans le cache
                st.session_state[f"{cache_key}_calculated"] = True
                
        else:
            # Réutiliser le cache : affichage direct sans recalcul
            heatmap_tabs = st.tabs(["🗓️ Cartographie hebdomadaire", "📅 Cartographie annuelle"])
            
            with heatmap_tabs[0]:
                # Afficher depuis le cache si disponible
                if f"{cache_key}_weekly" in st.session_state:
                    st.plotly_chart(st.session_state[f"{cache_key}_weekly"], use_container_width=True)
                else:
                    display_weekly_pattern_heatmap(pdf_for_analysis)
            
            with heatmap_tabs[1]:
                # Afficher depuis le cache si disponible  
                if f"{cache_key}_annual" in st.session_state:
                    st.plotly_chart(st.session_state[f"{cache_key}_annual"], use_container_width=True)
                else:
                    display_heatmap(pdf_for_analysis)
        
        # Expander d'information commun aux deux types de heatmap, plus simple ici d'en mettre un seul.   
        tooltip_info("Information")
        txt.heatmap_info()

    # ========== ONGLET 3: ANALYSE PERSONNALISÉE ==========
    elif active_tab == 2:  
        # L'utilisateur doit remplir un formulaire (qui s'adapte avec le choix fait dans la sidebar,  
        # pour les particuliers et les professionnels, afin qu'il ait plus d'infos sur sa courbe de charge).  
        tooltip_info("Information")
        st.info("💡 Complétez le formulaire ci-dessous pour obtenir des analyses et recommandations personnalisées basées sur vos données de consommation.")
        
        # --- Section 2: Analyse Détaillée (Conditionnelle au type d'utilisateur) ---
        user_type = st.session_state.get('user_type', "Particulier") # Récupérer depuis l'état


        # --- Logique de l'onglet pour Particulier (choix à faire dans la sidebar tout en haut) ---
        if user_type == "Particulier":
            # Afficher le formulaire
            list_info, flag_form = display_user_form()
            # Si le formulaire vient d'être soumis (ou mis à jour)
            if flag_form == 1:
                # Mettre à jour les données dans l'état de session SANS rerun
                st.session_state['form_data'] = list_info
                print("Formulaire Particulier soumis/mis à jour, données:", list_info) # Debug
                # Pas de st.rerun() ici pour éviter le rechargement

            # Afficher l'analyse détaillée si les données du formulaire existent dans l'état
            form_data = st.session_state.get('form_data') 
            
            # Debug 
            if form_data:
                print("Affichage analyse détaillée Particulier avec données:", form_data) # Debug
                #st.markdown("<hr style='margin: 30px 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)
                #st.markdown("<h3 style='text-align: center; color: #818081;'>Résultats de l'analyse détaillée</h3>", unsafe_allow_html=True)

                # --- Calculs et Affichages des Indicateurs ---

                # --- Consommation par surface (utilise la première entrée dans le formulaire form_data[0]) ---
                surface = form_data[0] 

                # Affiche l'indicateur de Consommation par Surface uniquement si la surface entrée est supérieure à 0 mètre carré.  
                # Fonction gérée dans src/indicators/personalized_analysis
                if surface > 0:
                    st.markdown("<a id='surface-personne'></a>", unsafe_allow_html=True)
                    txt.section_title("Consommation par Surface")

                    # Passer 'years' calculé précédemment et utiliser pdf_for_analysis
                    yearly_surface_consumption, surfc_list = display_surface_consumption(pdf_for_analysis, surface, st.session_state.get('years', []))
                    st.session_state['yearly_surface_consumption'] = yearly_surface_consumption
                    st.session_state['surfc_list'] = surfc_list
                else:
                    st.session_state['yearly_surface_consumption'] = None
                
                # Indicateur de Comparaison par aux standards suisses pour la consommation annuelle
                # utilise form_data[1], form_data[2], form_data[3], form_data[4] (4 entrées dans le formulaire)
                # Une logique est faite pour la comparaison avec les CSV disponibles dans le dossier src/database 
                # (valeurs_appartement.csv et valeurs_maison.csv), structure de CSV adapté des informations utilisées dans 
                # Calculowatt.  
                num_people = form_data[1]
                housing_type = form_data[2]  # Type de logement
                heating_type = form_data[3]  # Type de chauffage
                has_ecs = form_data[4]       # Type d'ECS
                
                # Condition pour faire apparaitre la comparaison uniquement s'il y a au moins une personne entrée dans le formulaire 
                # Fonction gérée dans src/indicators/personalized_analysis
                if num_people > 0:
                    txt.section_title("Comparaison aux standards suisses")
                    # Passer tous les paramètres à la fonction
                    daily_consumption_per_capita, yearly_consumption_per_capita = display_consumption(
                        pdf_for_analysis, num_people, housing_type, heating_type, has_ecs)
                    st.session_state['daily_consumption_per_capita'] = daily_consumption_per_capita
                    st.session_state['yearly_consumption_per_capita'] = yearly_consumption_per_capita
                else:
                    st.session_state['daily_consumption_per_capita'] = None

                # --- Analyse Solaire ---  
                # Comme vu plus haut, s'affiche uniquement si une colonne d'autoconsommation ou d'éxcédent est détéctée dans le fichier du user
                # Toujours en phase expérimental et de développement (un message y relatif s'affiche)
                if st.session_state.get('flag_solar', 0) > 0:
                    st.markdown("<a id='solaire'></a>", unsafe_allow_html=True)
                    txt.section_title("Analyse de production et consommation solaire")
                    tooltip_info("Visualisez votre production solaire et votre consommation")
                    display_solar_interactive_plot(pdf)

                # --- Synthèse et Recommandations ---
                #st.markdown("<a id='recommandations'></a>", unsafe_allow_html=True)
                #st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
                # Récupération des paramètres depuis l'état de session ou valeurs par défaut 

                # Récupère les valeurs calculées au fil du main. 
                base_load_rec = st.session_state.get('base_loads', [0])[-1] # Prend la dernière valeur (moyenne globale)
                ratio_rec = st.session_state.get('ratio', 2.5)
                ratio_day_night_rec = st.session_state.get('ratio_day_night', 2.0)
                slope_base_load_rec = st.session_state.get('slope_base_load', 0)
                yearly_surface_consumption_rec = st.session_state.get('yearly_surface_consumption', None)
                daily_consumption_per_capita_rec = st.session_state.get('daily_consumption_per_capita', None)
                has_solar_rec = st.session_state.get('flag_solar', 0) > 0
                predicted_cluster = st.session_state.get('cluster_predicted', None)

                # Fonction pour générer des recommandations personnalisées, gérer dans src/indicators/personalized_analysis
                recommendations = generate_personalized_recommendations(
                    base_load=base_load_rec,
                    ratio_weekday_weekend=ratio_rec,
                    ratio_day_night=ratio_day_night_rec,
                    slope_base_load=slope_base_load_rec,
                    yearly_surface_consumption=yearly_surface_consumption_rec,
                    daily_consumption_per_capita=daily_consumption_per_capita_rec,
                    has_solar=has_solar_rec
                )

                # Affichage recommandations détaillées, toujours en développement, apparait à la fin du troisième onglet,  
                # après validation du formulaire.  
                st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
                txt.section_title("Plan d'action détaillé")  
                st.markdown("""
                <div style="background-color: #ffebee; border: 1px solid #f44336; border-radius: 8px; padding: 15px; margin: 10px 0;">
                    <div style="color: #c62828; font-weight: bold; margin-bottom: 8px;">⚠️ Fonction expérimentale</div>
                    <div style="color: #d32f2f; font-size: 0.9em; line-height: 1.4;">
                        Il s'agit actuellement d'une fonction expérimentale vouée à être améliorée dans le temps. 
                        Il est donc normal que les conseils ne soient pas encore spécifiquement personnalisés.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                display_recommendations(recommendations)

            # Si le formulaire n'a pas encore été soumis (form_data est None)
            else:
                st.info("Cliquez sur [Valider les informations] pour accéder à des analyses personnalisées !")

        # --- Logique pour Professionnel ---  
        # Les fonctions qui s'affichent ici sont spécifiques aux utilisateurs professionnels, sauf pour la consommation par surface.
        elif user_type == "Professionnel":
            st.markdown("<hr style='margin: 30px 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color: #818081;'>Vos informations</h3>", unsafe_allow_html=True)
            # Afficher le formulaire
            list_info_c, flag_form_c = display_user_corp_form()

            # Si le formulaire vient d'être soumis (ou mis à jour)
            if flag_form_c == 1:
                # Mettre à jour les données dans l'état de session SANS rerun
                st.session_state['form_data_c'] = list_info_c
                print("Formulaire Pro soumis/mis à jour, données:", list_info_c) # Debug
                # Pas de st.rerun() ici

            # Afficher l'analyse détaillée si les données du formulaire existent dans l'état
            list_info_c = st.session_state.get('form_data_c')
            if list_info_c:
                print("Affichage analyse détaillée Pro avec données:", list_info_c) # Debug
                st.markdown("<hr style='margin: 30px 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)
                st.markdown("<h3 style='text-align: center; color: #818081;'>Résultats de l'analyse détaillée</h3>", unsafe_allow_html=True)

            # Indicateur de consommation par surface (comme pour les particuliers mais adapté à l'entrée du formulaire pour les Professionnels)
                surface = list_info_c[0]
                if surface > 0:
                    st.markdown("<a id='surface-pro'></a>", unsafe_allow_html=True)
                    txt.section_title("Consommation par Surface")
                    tooltip_info("Comparez votre consommation au m²")
                    
                    # Utiliser la même fonction que pour les particuliers avec pdf_for_analysis  
                    # La fonction issue de src/indicators/pro_indicators.py n'est plus utilisée
                    yearly_surface_consumption_c, surfc_list_c = display_surface_consumption(pdf_for_analysis, surface, st.session_state.get('years', []))
                    st.session_state['yearly_surface_consumption_c'] = yearly_surface_consumption_c
                    st.session_state['surfc_list_c'] = surfc_list_c
                else:
                    st.session_state['yearly_surface_consumption_c'] = None

                # Indicateur de consommations anormales : spécifique aux professionnels  
                # Code géré dans src/indicators/peak.py 
                st.markdown("<a id='anomalies'></a>", unsafe_allow_html=True)
                txt.section_title("Analyse des consommations anormales")  
                st.warning("Cette section est toujours en développement et n'est pas à jour avec le reste de l'application, attention à vos interprétations.")
                tooltip_info("Détectez les périodes de consommation inhabituelles")
                display_anomaly_analysis(pdf_for_analysis)  

                # Indicateur de Peak Shaving : spécifique aux professionnels  
                # Code géré dans src/indicators/peak.py
                st.markdown("<a id='peak-shaving'></a>", unsafe_allow_html=True)
                txt.section_title("Analyse de Peak Shaving")
                st.warning("Cette section est toujours en développement et n'est pas à jour avec le reste de l'application, attention à vos interprétations.")
                tooltip_info("Estimez les économies potentielles en réduisant vos pics de puissance")
                display_peak_shaving_analysis(pdf_for_analysis)

                # Section hôtel temporairement retirée de l'affichage
                # Code géré dans src/indicators/hotel.py
                # if list_info_c[2] == "Hôtel":
                #     st.markdown("<a id='analyse-pro'></a>", unsafe_allow_html=True)
                #     txt.section_title("Analyse spécifique pour hôtel")
                #     tooltip_info("Analyses et recommandations adaptées au secteur hôtelier")
                #     analyze_hotel_consumption(list_info_c[0], list_info_c[1], pdf)


                # Recommandations pour les professionnels toujours en développement 
                st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
                txt.section_title("Synthèse et Recommandations (Professionnel)")
                st.info("Des recommandations spécifiques pour les professionnels sont en cours de développement.")
            # Si le formulaire n'a pas encore été soumis (form_data_c est None)
            else:
                st.info("Cliquez sur [Valider les informations] pour accéder à des analyses personnalisées !")

###### ====================================================================
###### SECTION ACTEURS COMMUNAUX - FONCTIONNALITÉ DÉSACTIVÉE POUR LE MOMENT
###### ====================================================================
###### La logique complète pour les acteurs communaux (communes, collectivités)
###### était initialement prévue dans le Design Project mais a été retirée
###### de la version finale de l'application.
###### 
###### Le code pour les formulaires et analyses spécialisées reste disponible
###### dans les modules correspondants pour réactivation future :
###### - src/textual/user_form.py : display_user_am_form()
###### - Analyses spécialisées pour le secteur public/communal
######
###### Pour réactiver cette fonctionnalité :
###### 1. Ajouter "Acteur Communal" dans le sélecteur user_type (sidebar)
###### 2. Créer la section elif user_type == "Acteur Communal" 
###### 3. Implémenter les analyses spécialisées dans src/indicators/
######
###### Voir le rapport Design Project pour spécifications complètes.
######

else:
    # ========================================================================
    # ÉTAT INITIAL - AUCUNE DONNÉE CHARGÉE
    # ========================================================================
    # Message d'invitation à l'upload affiché si aucun fichier n'est encore chargé
    st.info("Veuillez déposer un fichier de courbe de charge pour commencer l'analyse. Attention, certains types de fichier ou formatage spécifique des colonnes ne pourront pas fonctionner. Contactez SIE SA en cas d'erreurs.")

# ============================================================================
# PIED DE PAGE DE L'APPLICATION
# ============================================================================
st.markdown("---")  # Ligne de séparation horizontale

# Signature et informations de développement
st.markdown("""
<div style="text-align: center; margin-top: 30px; padding: 15px; color: #818081; font-size: 0.8em;">
    <p>DataWatt © 2025 - SIE SA </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# FIN DU FICHIER PRINCIPAL - MAIN.PY
# ============================================================================