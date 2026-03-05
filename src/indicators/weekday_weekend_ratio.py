"""
# ============================================================================
# MODULE D'ANALYSE DU RATIO SEMAINE/WEEKEND - DataWatt
# ============================================================================
# MODULE ACTIF - Analyse comportementale des habitudes de consommation temporelle
#
# OBJECTIF PRINCIPAL:
# Ce module analyse la répartition de la consommation électrique entre les jours
# de semaine (lundi-vendredi) et les weekends (samedi-dimanche), révélant les
# patterns d'usage liés aux rythmes de vie et habitudes professionnelles.
#
# FONCTIONNALITÉS CLÉS:
# 1. **Calcul du ratio semaine/weekend** - Métrique comportementale fondamentale
# 2. **Classification temporelle** - Séparation automatique jours ouvrables/repos
# 3. **Détection de tendances** - Évolution des habitudes entre années complètes
# 4. **Positionnement groupe** - Comparaison avec profils similaires (clustering)
# 5. **Visualisations adaptatives** - Interface selon modes d'analyse
#
# LOGIQUE MÉTIER:
# - **Semaine**: Lundi à Vendredi (5 jours ouvrables)
# - **Weekend**: Samedi et Dimanche (2 jours de repos)
# - **Ratio optimal**: ~2.5 (répartition proportionnelle 5j/2j)
# - **Seuils d'interprétation**: 2.2-2.8 (équilibré), >2.8 (semaine intense), <2.2 (weekend élevé)
#
# INSIGHTS COMPORTEMENTAUX:
# - **Télétravail/activité à domicile** : Ratio élevé (>2.8)
# - **Habitudes équilibrées** : Ratio proche de 2.5
# - **Vie concentrée weekend** : Ratio faible (<2.2)
# - **Saisonnalité** : Variations selon chauffage/climatisation
#
# INTÉGRATIONS ÉCOSYSTÈME:
# - Dashboard principal: Métriques de rythme de vie
# - Module clustering: Variable discriminante pour profils
# - Analyse personnalisée: Recommandations d'optimisation temporelle
# - Corrélation day_night_ratio: Compréhension globale des habitudes
#
# ARCHITECTURE TECHNIQUE:
# - Calculs sur DataFrame pré-filtré (cohérence avec autres modules)
# - Support modes année unique/multi-années
# - Gestion robuste des années partielles/complètes
# - Classification automatique jours de la semaine
# - Interface responsive avec documentation intégrée
# ============================================================================
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import streamlit as st
from src.textual.tools import tooltip_info  
import src.textual.text as txt   
try:
    from src.indicators.cluster_indic import get_user_feature_position
except ImportError:
    get_user_feature_position = None   

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================  

def format_number_with_apostrophe(number, decimal_places=0):
    """
    Formate un nombre avec des apostrophes comme séparateurs de milliers (standard suisse)
    
    Fonction utilitaire pour respecter les conventions de formatage numérique suisses
    dans toutes les interfaces DataWatt, assurant une cohérence visuelle.
    
    EXEMPLES D'USAGE:
    - 1234567.89 -> "1'234'567.89" (avec décimales)
    - 1234567 -> "1'234'567" (sans décimales)
    - 5432.1 -> "5'432.1" (une décimale)
    
    Args:
        number (float): Nombre à formater (peut être None)
        decimal_places (int): Nombre de décimales à afficher (défaut: 0)
        
    Returns:
        str: Nombre formaté avec apostrophes comme séparateurs
        
    Note:
        Identique aux autres modules DataWatt pour cohérence de l'écosystème
    """
    if number is None:
        return "0"
    
    # Arrondir selon le nombre de décimales souhaité
    if decimal_places == 0:
        formatted = f"{number:.0f}"
    elif decimal_places == 1:
        formatted = f"{number:.1f}"
    elif decimal_places == 2:
        formatted = f"{number:.2f}"
    else:
        formatted = f"{number:.{decimal_places}f}"
    
    # Séparer la partie entière et décimale
    if '.' in formatted:
        integer_part, decimal_part = formatted.split('.')
        formatted_with_apostrophe = f"{int(integer_part):_}".replace('_', "'")
        return f"{formatted_with_apostrophe}.{decimal_part}"
    else:
        return f"{int(formatted):_}".replace('_', "'")

def get_consumption_column(df):
    """
    Détermine automatiquement la colonne de consommation selon le type de données
    
    LOGIQUE DE DÉTECTION:
    - Priorité 1: 'Total Consumption (kWh)' (installations avec solaire)
    - Priorité 2: 'Consumption (kWh)' (installations standard réseau)
    
    Cette fonction garantit la compatibilité avec tous les formats de données
    DataWatt, qu'ils incluent ou non de l'autoconsommation solaire.
    
    Args:
        df (pandas.DataFrame): DataFrame contenant les données de consommation
        
    Returns:
        str: Nom de la colonne de consommation détectée
        
    Note:
        Fonction critique pour la robustesse du module - évite les erreurs
        lors du traitement de différents types d'installations énergétiques
    """
    return 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in df.columns else 'Consumption (kWh)'

# ============================================================================
# FONCTION PRINCIPALE DE CALCUL DU RATIO SEMAINE/WEEKEND
# ============================================================================

def calculate_weekday_weekend_ratio(df):
    """
    Calcule le ratio de consommation semaine/weekend avec analyse temporelle complète
    
    Cette fonction constitue le cœur analytique du module, traitant les données
    de consommation pré-filtrées pour extraire les métriques comportementales
    liées aux rythmes de vie hebdomadaires et habitudes professionnelles.
    
    ARCHITECTURE DE CALCUL:
    1. **Détection automatique** de la colonne de consommation
    2. **Classification temporelle** : semaine (lun-ven) vs weekend (sam-dim)
    3. **Calcul du ratio global** sur l'ensemble des données filtrées
    4. **Analyse annuelle** avec ratios par année pour détection de tendances
    5. **Filtrage intelligent** des années complètes pour tendances fiables
    6. **Agrégation des métriques** pour retour vers interface utilisateur
    
    LOGIQUE TEMPORELLE STANDARD:
    - **Période SEMAINE**: Lundi à Vendredi (5 jours ouvrables)
    - **Période WEEKEND**: Samedi et Dimanche (2 jours de repos)
    - **Ratio = Consommation Semaine ÷ Consommation Weekend**
    - **Ratio théorique**: 2.5 (répartition proportionnelle 5j/2j)
    
    STRATÉGIE DE CLASSIFICATION:
    - Utilise pandas.dayofweek (0=lundi, 6=dimanche)
    - Semaine: dayofweek < 5 (lundi à vendredi)
    - Weekend: dayofweek >= 5 (samedi et dimanche)
    
    STRATÉGIE DE TENDANCE:
    - Utilise uniquement les années avec complétude ≥100% (fiables)
    - Prend les 2 années complètes les plus récentes pour éviter le bruit
    - Cohérence avec la logique des modules base_load et day_night_ratio
    
    ROBUSTESSE:
    - Gestion des divisions par zéro (weekend_consumption = 0)
    - Support des DataFrames partiels/filtrés
    - Compatibilité avec modes année unique/multi-années
    
    Args:
        df (pandas.DataFrame): DataFrame avec index datetime et colonnes de consommation
                              ⚠️ DOIT ÊTRE PRÉ-FILTRÉ selon la sélection utilisateur
        
    Returns:
        dict: Dictionnaire complet contenant :
            - overall_ratio (float): Ratio global sur toutes les données filtrées
            - weekday_consumption (float): Somme totale semaine (toutes années)
            - weekend_consumption (float): Somme totale weekend (toutes années)
            - yearly_ratios (dict): Ratios détaillés par année
            - years (list): Liste des années pour analyse de tendance
            - ratios_list (list): Ratios correspondants pour tendance
            
    Note Importante:
        Cette fonction NE DOIT PAS refiltrer les données - elle travaille sur
        le DataFrame déjà filtré selon les choix utilisateur pour maintenir
        la cohérence avec l'interface et éviter les incohérences.
    """
    # ÉTAPE 1: DÉTECTION AUTOMATIQUE DE LA COLONNE DE CONSOMMATION
    # =============================================================
    # Garantit la compatibilité avec différents formats de DataFrames DataWatt
    consumption_col = get_consumption_column(df)
    
    # ÉTAPE 2: EXTRACTION DES ANNÉES DISPONIBLES DANS LE DATAFRAME PRÉ-FILTRÉ
    # =======================================================================
    # IMPORTANT: Utilise DIRECTEMENT les années présentes dans le DataFrame
    # Ne dépend plus de st.session_state['years_to_use'] qui peut être incohérent
    # Cette approche garantit la cohérence avec les données réellement affichées
    years_to_use = sorted(df.index.year.unique().tolist())
    
    # ÉTAPE 3: CLASSIFICATION TEMPORELLE SEMAINE/WEEKEND
    # =================================================
    # Création des masques booléens pour séparation temporelle standardisée
    # Semaine: Lun-Ven (5 jours ouvrables) / Weekend: Sam-Dim (2 jours repos)
    # dayofweek: 0=Lundi, 1=Mardi, ..., 4=Vendredi, 5=Samedi, 6=Dimanche
    weekday_mask = df.index.dayofweek < 5
    weekend_mask = df.index.dayofweek >= 5
    
    # ÉTAPE 4: CALCUL DU RATIO GLOBAL SUR LES DONNÉES FILTRÉES
    # ========================================================
    # Sommes totales sur l'ensemble du DataFrame pré-filtré (toutes années confondues)
    weekday_consumption = df.loc[weekday_mask, consumption_col].sum()
    weekend_consumption = df.loc[weekend_mask, consumption_col].sum()
    # Protection contre division par zéro avec gestion d'infini
    overall_ratio = weekday_consumption / weekend_consumption if weekend_consumption != 0 else float('inf')
    
    # ÉTAPE 5: ANALYSE ANNUELLE POUR DÉTECTION DE TENDANCES
    # =====================================================
    # Calcul des ratios par année pour identifier les évolutions comportementales
    yearly_ratios = {}
    years_list = []
    ratios_list = []
    
    # === BOUCLE DE CALCUL PAR ANNÉE ===
    # Traitement individuel de chaque année présente dans les données filtrées
    for year in years_to_use:
        year_data = df[df.index.year == year]
        if not year_data.empty:
            # Classification temporelle pour cette année spécifique
            year_weekday_consumption = year_data.loc[year_data.index.dayofweek < 5, consumption_col].sum()
            year_weekend_consumption = year_data.loc[year_data.index.dayofweek >= 5, consumption_col].sum()
            
            # Calcul du ratio annuel avec protection division par zéro
            if year_weekend_consumption > 0:
                year_ratio = year_weekday_consumption / year_weekend_consumption
                yearly_ratios[year] = {
                    'ratio': year_ratio,
                    'weekday_consumption': year_weekday_consumption,
                    'weekend_consumption': year_weekend_consumption
                }
    
    # ÉTAPE 6: FILTRAGE INTELLIGENT POUR ANALYSE DE TENDANCE FIABLE
    # =============================================================
    # Application de la même logique que base_load et day_night_ratio
    # Évite les biais dus aux données partielles dans l'analyse de tendance
    years_completeness = st.session_state.get('years_completeness', {})
    complete_years = [year for year in years_to_use 
                     if year in years_completeness and years_completeness[year] >= 100 and year in yearly_ratios]
    
    # === SÉLECTION DES ANNÉES POUR TENDANCE ===
    # Stratégie: 2 années complètes les plus récentes pour éviter le bruit
    # Compromis entre robustesse statistique et pertinence temporelle
    recent_complete_years = sorted(complete_years)[-2:] if len(complete_years) >= 2 else complete_years
    
    # === CONSTRUCTION DES LISTES POUR CALCUL DE TENDANCE ===
    # Seulement les années validées comme complètes et récentes
    for year in recent_complete_years:
        years_list.append(year)
        ratios_list.append(yearly_ratios[year]['ratio'])
    
    # ÉTAPE 7: RETOUR DES MÉTRIQUES COMPLÈTES
    # =======================================
    # Dictionnaire structuré pour interface utilisateur avec toutes les données nécessaires
    return {
        'overall_ratio': overall_ratio,                # Ratio global (sommes totales)
        'weekday_consumption': weekday_consumption,    # Somme totale semaine (toutes années)
        'weekend_consumption': weekend_consumption,    # Somme totale weekend (toutes années)
        'yearly_ratios': yearly_ratios,               # Données détaillées par année
        'years': years_list,                          # Années pour tendance (complètes seulement)
        'ratios_list': ratios_list                    # Ratios correspondants pour tendance
    }

def _display_weekday_weekend_ratio_explanation():
    """
    Affiche l'expander avec les explications sur le ratio semaine/weekend
    """  
    tooltip_info("Information")
    with st.expander("Comment interpréter votre ratio semaine/weekend ?"):
        st.markdown("""
        ### Qu'est-ce que le rapport semaine/weekend ?
        
        Ce rapport compare votre consommation électrique moyenne durant les jours de semaine (lundi à vendredi) à votre consommation électrique moyenne du weekend (samedi et dimanche).         


        ### Seuils d'interprétation et couleurs
        
        - 🟢 **Ratio équilibré (2.2 - 2.8)** : Répartition standard pour un foyer résidentiel
        - 🔵 **Ratio élevé (> 2.8)** : Votre consommation est significativement plus élevée la semaine par rapport au weekend
        - 🟠 **Ratio faible (< 2.2)** : Votre consommation est significativement plus élevée le weekend par rapport à la semaine
        
        
        
        ### Qu'est-ce que cela signifie ?  
        Voici quelques interprétations possibles de votre ratio de consommation. Il s'agit de propositions non exhaustives, il reste cependant à examiner si ce ratio semble correspondre à vos habitudes de consommations :  
        
        **Ratio équilibré :** Votre consommation suit la répartition standard 5 jours vs 2 jours (ratio autour de 2.5).
        
        Un **Ratio élevé** peut indiquer :  
        - Du télétravail ou une activité professionnelle à domicile
        - Une utilisation intensive d'appareils électriques en journée de semaine
        - Une réduction volontaire des activités électriques le weekend
        - Des habitudes de vie différenciées selon les jours
        
        Un **Ratio faible** peut indiquer : 
        - Plus de temps passé à domicile le weekend
        - Des loisirs domestiques énergivores (bricolage, cuisine, etc.)
        - Une utilisation accrue du chauffage/climatisation le weekend
        - Des habitudes de vie concentrées sur les weekends
        
        """)

# ============================================================================
# FONCTION PRINCIPALE D'AFFICHAGE ET ORCHESTRATION
# ============================================================================

def display_weekday_weekend_ratio(ratio_data, df=None):
    """
    Orchestre l'affichage du rapport semaine/weekend selon les modes d'analyse configurés
    
    Cette fonction constitue le point d'entrée principal pour l'interface utilisateur.
    Elle analyse les paramètres de configuration pour déterminer le mode d'affichage
    optimal et route vers les fonctions de rendu appropriées.
    
    MODES D'AFFICHAGE SUPPORTÉS:
    1. **Mode année unique** : Focus sur une année spécifique sélectionnée
    2. **Mode données complètes** : Vue globale avec agrégations et tendances
    
    ARCHITECTURE ADAPTIVE:
    - **Détection automatique** du mode via st.session_state
    - **Routage intelligent** vers les fonctions d'affichage spécialisées
    - **Utilisation exclusive** des données pré-calculées (évite recalculs)
    - **Gestion robuste** des cas de fallback et données manquantes
    
    STRATÉGIE DE DONNÉES:
    - Privilégie les données issues de calculate_weekday_weekend_ratio()
    - Évite les recalculs pour maintenir la cohérence
    - Gère les différences entre années partielles/complètes
    - Support de l'inclusion/exclusion des années partielles
    
    LOGIQUE DE TENDANCE:
    - Affichage conditionnel selon disponibilité des années complètes
    - Calcul de variation pourcentuelle entre première/dernière année
    - Seuils de signification: ±10% pour stabilité
    - Codes couleur: vert (baisse), bleu (stable), rouge (hausse)
    
    Args:
        ratio_data (dict): Données pré-calculées par calculate_weekday_weekend_ratio()
        df (pandas.DataFrame, optional): DataFrame original pour compatibilité
                                        (généralement non utilisé)
        
    Note Performance:
        Cette fonction ne recalcule jamais les ratios - elle se contente
        d'orchestrer l'affichage basé sur les données pré-calculées,
        garantissant cohérence et performance optimale.
    """
    # PHASE 1: DÉTECTION DU MODE D'ANALYSE CONFIGURÉ
    # ==============================================
    # Lecture de la configuration utilisateur pour adapter l'interface
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    if year_selection_mode != "Données complètes":
        # === MODE ANNÉE UNIQUE : Focus sur une année spécifique ===
        # Extraction des données pré-calculées pour l'année sélectionnée
        selected_year = st.session_state.get('selected_single_year')
        yearly_ratios = ratio_data.get('yearly_ratios', {})
        
        if selected_year and selected_year in yearly_ratios:
            # Utiliser les données déjà calculées pour l'année sélectionnée
            year_data = yearly_ratios[selected_year]
            _display_single_year_weekday_weekend_ratio(
                year_data['ratio'], 
                selected_year, 
                year_data['weekday_consumption'], 
                year_data['weekend_consumption']
            )
        else:
            # Fallback sur les données globales
            _display_fallback_weekday_weekend_ratio(ratio_data)
    else:
        # Mode données complètes - utiliser les données de ratio_data
        years = ratio_data.get('years', [])
        ratios_list = ratio_data.get('ratios_list', [])
        yearly_ratios = ratio_data.get('yearly_ratios', {})
        overall_ratio = ratio_data.get('overall_ratio', 0)
        
        if len(years) >= 2:
            # Utiliser le ratio overall (somme totale) au lieu de la moyenne
            overall_ratio_to_display = overall_ratio
            
            # Vérifier si on a au moins 2 années complètes dans la liste retournée (même logique que base_load)
            years_completeness = st.session_state.get('years_completeness', {})
            valid_years_for_trend = []
            
            for year in years:
                if year in years_completeness and years_completeness[year] >= 100:
                    valid_years_for_trend.append(year)
            
            # Afficher la tendance seulement si on a exactement 2+ années complètes dans la liste retournée
            show_trend = len(valid_years_for_trend) >= 2
            if show_trend:
                # Calculer la tendance entre les années complètes
                ratio_change = ratios_list[-1] - ratios_list[0]
                ratio_change_percent = (ratio_change / ratios_list[0]) * 100 if ratios_list[0] != 0 else 0
                
                # Détermination de la tendance
                if abs(ratio_change_percent) < 10:
                    trend_icon = "➡️"
                    trend_text = "stable"
                    trend_color = "#3498db"
                elif ratio_change_percent > 0:
                    trend_icon = "📈"
                    trend_text = "en hausse"
                    trend_color = "#e74c3c"
                else:
                    trend_icon = "📉"
                    trend_text = "en baisse"
                    trend_color = "#27ae60"
            else:
                # Pas de tendance à afficher
                trend_color = None
                trend_icon = None
                trend_text = None
                ratio_change_percent = 0
            
            # Préparer les données par année pour l'affichage (utiliser les données déjà calculées)
            years_data = []
            for year in years:
                if year in yearly_ratios:
                    year_info = yearly_ratios[year]
                    years_data.append({
                        'year': year,
                        'ratio': year_info['ratio'],
                        'weekday_consumption': year_info['weekday_consumption'],
                        'weekend_consumption': year_info['weekend_consumption']
                    })
            
            _display_mean_weekday_weekend_ratio_with_trend(
                overall_ratio_to_display, trend_icon, trend_text, trend_color, 
                ratio_change_percent, years, years_data, ratio_data
            )
        else:
            # Une seule année ou données insuffisantes
            _display_fallback_weekday_weekend_ratio(ratio_data)

def _display_mean_weekday_weekend_ratio_with_trend(overall_ratio, trend_icon, trend_text, trend_color, ratio_change_percent, years, years_data=None, ratio_data=None):
    """
    Affiche le ratio overall avec la tendance conditionnelle pour le mode données complètes
    """
    
    # Interprétation du ratio overall avec les mêmes seuils que pour une année unique
    if abs(overall_ratio - 2.5) < 0.3:
        interpretation = "Votre consommation semaine/weekend est équilibrée."
        ratio_color = "#27ae60"
    elif overall_ratio > 2.5:
        interpretation = "Votre consommation en semaine est proportionnellement plus élevée."
        ratio_color = "#3498db"
    else:
        interpretation = "Votre consommation en weekend est relativement élevée."
        ratio_color = "#f39c12"

    # Calculer les pourcentages pour la barre unique
    weekday_percentage_avg = (overall_ratio / (overall_ratio + 1)) * 100
    weekend_percentage_avg = 100 - weekday_percentage_avg
    
    
    # Barre visuelle
    st.markdown(f"""
    <div style="display: flex; height: 40px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
        <div style="width: {weekday_percentage_avg:.1f}%; background: linear-gradient(135deg, #2980b9, #3498db); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">📅 {weekday_percentage_avg:.1f}%</span>
        </div>
        <div style="width: {weekend_percentage_avg:.1f}%; background: linear-gradient(135deg, #7f8c8d, #95a5a6); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">🏠 {weekend_percentage_avg:.1f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tableau des métriques avec sommes totales - utiliser TOUTES les données yearly_ratios, pas seulement years_data (années complètes)
    yearly_ratios_all = ratio_data.get('yearly_ratios', {}) if ratio_data else {}
    
    if yearly_ratios_all:
        # Calculer les sommes totales de consommation sur TOUTES les années disponibles  
        total_weekday_consumption = sum(year_info.get('weekday_consumption', 0) for year_info in yearly_ratios_all.values())
        total_weekend_consumption = sum(year_info.get('weekend_consumption', 0) for year_info in yearly_ratios_all.values())
        
        st.markdown(f"""
        <div style="margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">📅 Consommation Semaine (Lundi-Vendredi) (total)</th>
                        <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">📊 Ratio Semaine/Weekend</th>
                        <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">🏠 Consommation Weekend (Samedi-Dimanche) (total)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 15px; text-align: center; color: #333;">
                            <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(total_weekday_consumption)} kWh</div>
                            <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{weekday_percentage_avg:.1f}%</div>
                        </td>
                        <td style="padding: 15px; text-align: center; color: #333;">
                            <div style="font-size: 1.4em; font-weight: bold; color: {ratio_color};">{overall_ratio:.2f}</div>
                        </td>
                        <td style="padding: 15px; text-align: center; color: #333;">
                            <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(total_weekend_consumption)} kWh</div>
                            <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{weekend_percentage_avg:.1f}%</div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        # Afficher la tendance seulement si on a les données de tendance
        if trend_icon is not None and trend_text is not None and trend_color is not None:
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="margin-bottom: 10px;">
                    <strong style="color: #333;">Tendance globale de votre ratio semaine/weekend : <span style="color: {trend_color}; font-weight: bold;">{trend_icon} {trend_text.title()}</span></strong>
                    <br>
                    <span style="font-size: 0.9em; color: #666;">
                        {abs(ratio_change_percent):.1f}% entre {years[0]} et {years[-1]}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Pas de tendance à afficher (années incomplètes)
            st.markdown("""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #e0e0e0;">
                <div style="text-align: center; color: #666; font-style: italic;">
                    ℹ️ La tendance d'évolution n'est disponible qu'avec au moins 2 années complètes de données
                </div>
            </div>
            """, unsafe_allow_html=True)
    

    # Expander avec les seuils d'interprétation
    _display_weekday_weekend_ratio_explanation()

    # Afficher la position par rapport au groupe si disponible et si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier" and get_user_feature_position is not None:
        position_data = get_user_feature_position('ratio_weekday_weekend')
        if position_data is not None:
            position_percentile, user_value, cluster_id = position_data
            
            # Fonction pour déterminer l'emoji, statut et couleur selon les mêmes critères que cluster_indic
            def get_status_info(percentile):
                # Pour les ratios : nouvelle logique basée sur la distance absolue à la médiane
                abs_percentile = abs(percentile)  # Valeur absolue par rapport à la médiane
                if abs_percentile <= 10:
                    emoji = "🟢"
                    status = "Ratio proche de la médiane"
                    color = "#27ae60"
                    bg_color = "#d5f4e6"
                    border_color = "#27ae60"
                    description = "Votre ratio semaine/weekend est proche de la médiane du groupe (similaire)"
                elif abs_percentile <= 30:
                    emoji = "🟡"
                    status = "Ratio légèrement différent de la médiane"
                    color = "#f39c12"
                    bg_color = "#fef9e7"
                    border_color = "#f39c12"
                    description = "Votre ratio semaine/weekend est légèrement différent de la médiane du groupe"
                else:  # > 30%
                    emoji = "🔴"
                    status = "Ratio très différent de la médiane"
                    color = "#e74c3c"
                    bg_color = "#fdf2f2"
                    border_color = "#e74c3c"
                    description = "Votre ratio semaine/weekend est très différent de la médiane du groupe"
                return emoji, status, color, bg_color, border_color, description
            
            emoji, status, color, bg_color, border_color, description = get_status_info(position_percentile)
            
            st.markdown("""
            <div style="margin: 10px 0 8px 0; text-align: center;">
            <h5 style="color: #333; font-weight: bold; font-size: 0.9em; margin: 0; letter-spacing: 1px; text-transform: uppercase;">
            Votre position dans votre groupe
            </h5>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 12px 0; border: 2px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} Ratio semaine/weekend</span>
                    <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{position_percentile:+.0f}%</span>
                </div>
                <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                    {description}
                </div>
            </div>
            """, unsafe_allow_html=True)


            tooltip_info("Information")
            with st.expander("Comment interpréter ma position dans le groupe ?"):
                st.markdown("""
                ### Seuils d'évaluation pour votre position
                
                **🟢 <10% d'écart (positif ou négatif)** par rapport à la médiane de votre groupe. Cela indique un profil de consommation typique et équilibré par rapport aux autres utilisateurs ayant des caractéristiques similaires.  
                
                **🟡 Entre 10 et 30% d'écart (positif ou négatif)** par rapport à la médiane de votre groupe. Cette diﬀérence peut s'expliquer par des habitudes de vie légèrement diﬀérentes, mais reste dans une plage normale de variation. 
                
                **🔴 >30% d'écart (positif ou négatif)** par rapport à la médiane de votre groupe. Cela peut indiquer des habitudes de consommation particulières ou des opportunités d'optimisation énergétique. Une analyse plus approfondie de vos usages pourrait être bénéfique.
                
                ### Pourquoi cette comparaison ?
                
                Cette comparaison vous permet de situer votre consommation par rapport à des utilisateurs ayant un profil similaire au vôtre. C'est un indicateur utile pour identifier si vos habitudes de consommation sont typiques ou si elles présentent des particularités.
                
                💡 **Conseil** : Une position différente n'est pas nécessairement négative - elle peut simplement refléter des besoins ou des habitudes spécifiques à votre situation.
                """)

def _display_single_year_weekday_weekend_ratio(ratio, year, weekday_consumption, weekend_consumption):
    """
    Affiche le ratio semaine/weekend pour une seule année avec les consommations totales
    """
    # Calcul des pourcentages pour la barre visuelle
    total_consumption = weekday_consumption + weekend_consumption
    weekday_percentage = (weekday_consumption / total_consumption) * 100 if total_consumption > 0 else 0
    weekend_percentage = 100 - weekday_percentage
    
    # Interprétation du ratio
    if abs(ratio - 2.5) < 0.3:
        interpretation = "Votre consommation semaine/weekend est équilibrée."
        ratio_color = "#27ae60"
    elif ratio > 2.5:
        interpretation = "Votre consommation en semaine est proportionnellement plus élevée."
        ratio_color = "#3498db"
    else:
        interpretation = "Votre consommation en weekend est relativement élevée."
        ratio_color = "#f39c12"
    
    
    # Barre visuelle pour l'année sélectionnée
    #st.markdown(f"**{year}** - {format_number_with_apostrophe(total_consumption)} kWh")
    
    # Barre visuelle pour cette année
    st.markdown(f"""
    <div style="display: flex; height: 50px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
        <div style="width: {weekday_percentage:.1f}%; background: linear-gradient(135deg, #2980b9, #3498db); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
            <span style="color: white; font-weight: bold; font-size: 0.85em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif; line-height: 1.1;">📅 {weekday_percentage:.1f}%</span>
            <span style="color: white; font-weight: bold; font-size: 0.75em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">{format_number_with_apostrophe(weekday_consumption)} kWh</span>
        </div>
        <div style="width: {weekend_percentage:.1f}%; background: linear-gradient(135deg, #7f8c8d, #95a5a6); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
            <span style="color: white; font-weight: bold; font-size: 0.85em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif; line-height: 1.1;">🏠 {weekend_percentage:.1f}%</span>
            <span style="color: white; font-weight: bold; font-size: 0.75em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">{format_number_with_apostrophe(weekend_consumption)} kWh</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tableau des métriques détaillées
    st.markdown(f"""
    <div style="margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">📅 Consommation Semaine (Lundi-Vendredi)</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">📊 Ratio Semaine/Weekend</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">🏠 Consommation Weekend (Samedi-Dimanche)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(weekday_consumption)} kWh</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{weekday_percentage:.1f}%</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: {ratio_color};">{ratio:.2f}</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(weekend_consumption)} kWh</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{weekend_percentage:.1f}%</div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    
    # Expander avec les seuils d'interprétation
    _display_weekday_weekend_ratio_explanation()

    # Afficher la position par rapport au groupe si disponible et si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier" and get_user_feature_position is not None:
        position_data = get_user_feature_position('ratio_weekday_weekend')
        if position_data is not None:
            position_percentile, user_value, cluster_id = position_data
            
            # Fonction pour déterminer l'emoji, statut et couleur selon les mêmes critères que cluster_indic
            def get_status_info(percentile):
                # Pour les ratios : nouvelle logique basée sur la distance absolue à la médiane
                abs_percentile = abs(percentile)  # Valeur absolue par rapport à la médiane
                if abs_percentile <= 10:
                    emoji = "🟢"
                    status = "Ratio proche de la médiane"
                    color = "#27ae60"
                    bg_color = "#d5f4e6"
                    border_color = "#27ae60"
                    description = "Votre ratio semaine/weekend est proche de la médiane du groupe (similaire)"
                elif abs_percentile <= 30:
                    emoji = "🟡"
                    status = "Ratio légèrement différent de la médiane"
                    color = "#f39c12"
                    bg_color = "#fef9e7"
                    border_color = "#f39c12"
                    description = "Votre ratio semaine/weekend est légèrement différent de la médiane du groupe"
                else:  # > 30%
                    emoji = "🔴"
                    status = "Ratio très différent de la médiane"
                    color = "#e74c3c"
                    bg_color = "#fdf2f2"
                    border_color = "#e74c3c"
                    description = "Votre ratio semaine/weekend est très différent de la médiane du groupe"
                return emoji, status, color, bg_color, border_color, description
            
            emoji, status, color, bg_color, border_color, description = get_status_info(position_percentile)

            st.markdown("""
            <div style="margin: 10px 0 8px 0; text-align: center;">
            <h5 style="color: #333; font-weight: bold; font-size: 0.9em; margin: 0; letter-spacing: 1px; text-transform: uppercase;">
            Votre position dans votre groupe
            </h5>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 12px 0; border: 2px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} Ratio semaine/weekend</span>
                    <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{position_percentile:+.0f}%</span>
                </div>
                <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                    {description}
                </div>
            </div> 
            """, unsafe_allow_html=True)

            tooltip_info("Information")
            with st.expander("Comment interpréter ma position dans le groupe ?"):
                st.markdown("""
                ### Seuils d'évaluation pour votre position
                
                **🟢 <10% d'écart (positif ou négatif)** par rapport à la médiane de votre groupe. Cela indique un profil de consommation typique et équilibré par rapport aux autres utilisateurs ayant des caractéristiques similaires.  
                
                **🟡 Entre 10 et 30% d'écart (positif ou négatif)** par rapport à la médiane de votre groupe. Cette diﬀérence peut s'expliquer par des habitudes de vie légèrement diﬀérentes, mais reste dans une plage normale de variation. 
                
                **🔴 >30% d'écart (positif ou négatif)** par rapport à la médiane de votre groupe. Cela peut indiquer des habitudes de consommation particulières ou des opportunités d'optimisation énergétique. Une analyse plus approfondie de vos usages pourrait être bénéfique.
                
                ### Pourquoi cette comparaison ?
                
                Cette comparaison vous permet de situer votre consommation par rapport à des utilisateurs ayant un profil similaire au vôtre. C'est un indicateur utile pour identifier si vos habitudes de consommation sont typiques ou si elles présentent des particularités.
                
                💡 **Conseil** : Une position différente n'est pas nécessairement négative - elle peut simplement refléter des besoins ou des habitudes spécifiques à votre situation.
                """)

def _display_fallback_weekday_weekend_ratio(ratio_data):
    """
    Affichage de fallback pour le ratio semaine/weekend
    """
    # Extraire les données du dictionnaire
    ratio = ratio_data['overall_ratio']
    weekday_consumption = ratio_data.get('weekday_consumption', 0)
    weekend_consumption = ratio_data.get('weekend_consumption', 0)
    
    # Interprétation du ratio
    if abs(ratio - 2.5) < 0.3:
        interpretation = "Votre consommation semaine/weekend est équilibrée."
        ratio_color = "#27ae60"
        weekday_percentage = 71.4  # 5/7 * 100
        weekend_percentage = 28.6  # 2/7 * 100
    elif ratio > 2.5:
        interpretation = "Votre consommation en semaine est proportionnellement plus élevée."
        ratio_color = "#3498db"
        weekday_percentage = (ratio / (ratio + 1)) * 100
        weekend_percentage = 100 - weekday_percentage
    else:
        interpretation = "Votre consommation en weekend est relativement élevée."
        ratio_color = "#f39c12"
        weekday_percentage = (ratio / (ratio + 1)) * 100
        weekend_percentage = 100 - weekday_percentage
    
    st.markdown(f"""
    <div style="display: flex; height: 40px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
        <div style="width: {weekday_percentage:.1f}%; background: linear-gradient(135deg, #2980b9, #3498db); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">📅 {weekday_percentage:.1f}%</span>
        </div>
        <div style="width: {weekend_percentage:.1f}%; background: linear-gradient(135deg, #7f8c8d, #95a5a6); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">🏠 {weekend_percentage:.1f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tableau des métriques globales (avec valeurs absolues si disponibles)
    st.markdown(f"""
    <div style="margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">📅 Consommation Semaine (Lundi-Vendredi)</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">📊 Ratio Semaine/Weekend</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #dee2e6;">🏠 Consommation Weekend (Samedi-Dimanche)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(weekday_consumption)} kWh</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{weekday_percentage:.1f}%</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: {ratio_color};">{ratio:.2f}</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(weekend_consumption)} kWh</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{weekend_percentage:.1f}%</div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    
    # Expander avec les seuils d'interprétation
    _display_weekday_weekend_ratio_explanation()

# ============================================================================
# NOTES D'INTÉGRATION ET MAINTENANCE - Module weekday_weekend_ratio
# ============================================================================
#
# 1. **Cohérence avec autres modules ratio**: 
#    - Utilise la même logique de filtrage des années complètes que base_load et day_night_ratio
#    - Même stratégie de calcul de tendances (2 années récentes max)
#    - Cohérence des seuils de complétude (≥100%)
#
# 2. **Gestion des données pré-filtrées**:
#    - NE JAMAIS refiltrer dans les fonctions de calcul
#    - Toujours utiliser le DataFrame passé en paramètre
#    - Éviter les références à st.session_state['years_to_use']
#
# 3. **Performance et cache**:
#    - calculate_weekday_weekend_ratio() fait les calculs lourds UNE fois
#    - display_weekday_weekend_ratio() orchestre sans recalculer
#    - Données partagées via dictionnaire ratio_data
#
# 4. **Classification temporelle spécifique**:
#    - Utilise pandas.dayofweek (0=lundi, 6=dimanche)
#    - Semaine: dayofweek < 5 (lundi à vendredi)
#    - Weekend: dayofweek >= 5 (samedi et dimanche)
#
# 5. **Seuils d'interprétation métier**:
#    - Ratio optimal: ~2.5 (proportionnalité théorique 5j/2j)
#    - Équilibré: 2.2-2.8 (variation normale)
#    - Élevé: >2.8 (télétravail, activité intense semaine)
#    - Faible: <2.2 (vie concentrée weekend, loisirs domestiques)
#
# 6. **Extensibilité clustering**:
#    - Import conditionnel de get_user_feature_position
#    - Gestion élégante si module clustering absent
#    - Interface standardisée pour comparaison groupe
#
# 7. **Standards DataWatt**:
#    - Formatage numérique suisse (apostrophes)
#    - Palette de couleurs cohérente avec écosystème
#    - Documentation utilisateur intégrée (expanders)
#    - Responsive design pour différentes tailles d'écran
#
# ÉVOLUTIONS POSSIBLES:
# - Analyse saisonnière des variations semaine/weekend (été vs hiver)
# - Détection automatique de patterns télétravail/activité professionnelle
# - Corrélation avec données météorologiques (impact chauffage/climatisation)
# - Intégration avec calendrier des jours fériés (redéfinition weekend élargi)
# - Recommandations personnalisées d'optimisation temporelle
# - Comparaisons avec standards sectoriels (résidentiel, commercial, industriel)
#
# INSIGHTS MÉTIER POTENTIELS:
# - Détection de changements d'habitudes (déménagement, retraite, télétravail)
# - Identification d'opportunités d'optimisation tarifaire (HP/HC)
# - Évaluation de l'impact des équipements selon usage temporel
# - Analyse de cohérence avec déclarations utilisateur (profil d'usage)
#
# ============================================================================