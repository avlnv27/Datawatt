"""
# ============================================================================
# MODULE D'ANALYSE DU RATIO JOUR/NUIT - DataWatt
# ============================================================================
# MODULE ACTIF - Fonctionnalité clé de l'analyse comportementale énergétique
#
# OBJECTIF PRINCIPAL:
# Ce module analyse la répartition temporelle de la consommation électrique entre
# les périodes de jour (6h-22h) et de nuit (22h-6h), fournissant des insights
# sur les habitudes de consommation et les opportunités d'optimisation.
#
# FONCTIONNALITÉS CLÉS:
# 1. **Calcul du ratio jour/nuit** - Métrique comportementale fondamentale
# 2. **Analyse temporelle** - Classification automatique jour/nuit
# 3. **Détection de tendances** - Évolution du ratio entre années complètes
# 4. **Positionnement groupe** - Comparaison avec profils similaires (clustering)
# 5. **Visualisations adaptatives** - Interface selon modes d'analyse
#
# LOGIQUE MÉTIER:
# - **Jour**: 6h00-22h00 (16h) - Période d'activité standard
# - **Nuit**: 22h00-6h00 (8h) - Période de repos/veille
# - **Ratio optimal**: ~2.0 (équilibré résidentiel standard)
# - **Seuils d'alerte**: <1.7 (nuit élevée) / >2.3 (jour très élevé)
#
# INTÉGRATIONS ÉCOSYSTÈME:
# - Dashboard principal: Métriques comportementales
# - Module clustering: Positionnement dans groupes homogènes
# - Analyse personnalisée: Recommandations d'optimisation
# - Base de charge: Corrélation avec consommation nocturne minimum
#
# ARCHITECTURE TECHNIQUE:
# - Calculs sur DataFrame pré-filtré (évite duplications de filtrage)
# - Support modes année unique/multi-années
# - Gestion robuste des années partielles/complètes
# - Formatage numérique suisse (apostrophes)
# - Interface responsive avec tooltip contextuel
#
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
    
    Cette fonction respecte les conventions de formatage numérique suisses
    où l'apostrophe (') sert de séparateur de milliers au lieu de l'espace.
    
    EXEMPLES D'USAGE:
    - 1234567.89 -> "1'234'567.89" (avec décimales)
    - 1234567 -> "1'234'567" (sans décimales)
    - 5432.1 -> "5'432.1" (une décimale)
    
    Args:
        number (float): Nombre à formater
        decimal_places (int): Nombre de décimales à afficher (défaut: 0)
        
    Returns:
        str: Nombre formaté avec apostrophes comme séparateurs
        
    Note:
        Gère les cas None en retournant "0" pour éviter les erreurs d'affichage
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
    Détermine automatiquement la colonne de consommation à utiliser selon le DataFrame
    
    LOGIQUE DE DÉTECTION:
    - Priorité 1: 'Total Consumption (kWh)' (données agrégées/traitées)
    - Priorité 2: 'Consumption (kWh)' (données brutes standard)
    
    Cette approche garantit la compatibilité avec différents formats de données
    tout en privilégiant les colonnes totalisées quand elles sont disponibles.
    
    Args:
        df (pandas.DataFrame): DataFrame contenant les données de consommation
        
    Returns:
        str: Nom de la colonne de consommation détectée
        
    Note:
        Fonction critique pour la robustesse - évite les erreurs KeyError
        lors du traitement de DataFrames aux structures variées
    """
    return 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in df.columns else 'Consumption (kWh)'

# ============================================================================
# FONCTION PRINCIPALE DE CALCUL DU RATIO JOUR/NUIT
# ============================================================================

def calculate_day_night_ratio(df):
    """
    Calcule le ratio de consommation électrique jour/nuit avec analyse temporelle complète
    
    Cette fonction constitue le cœur analytique du module. Elle traite les données
    de consommation pré-filtrées pour extraire les métriques comportementales
    fondamentales liées à la répartition temporelle de l'usage énergétique.
    
    ARCHITECTURE DE CALCUL:
    1. **Détection automatique** de la colonne de consommation
    2. **Classification temporelle** : jour (6h-22h) vs nuit (22h-6h)
    3. **Calcul du ratio global** sur l'ensemble des données filtrées
    4. **Analyse annuelle** avec ratios par année pour détection de tendances
    5. **Filtrage intelligent** des années complètes pour tendances fiables
    6. **Agrégation des métriques** pour retour vers interface utilisateur
    
    LOGIQUE TEMPORELLE STANDARD:
    - **Période JOUR**: 6h00 à 22h00 (16 heures d'activité)
    - **Période NUIT**: 22h00 à 6h00 (8 heures de repos/veille)
    - **Ratio = Consommation Jour ÷ Consommation Nuit**
    
    STRATÉGIE DE TENDANCE:
    - Utilise uniquement les années avec complétude ≥100% (fiables)
    - Prend les 2 années complètes les plus récentes pour éviter le bruit
    - Cohérence avec la logique du module base_load (standards DataWatt)
    
    ROBUSTESSE:
    - Gestion des divisions par zéro (nuit_consumption = 0)
    - Support des DataFrames partiels/filtrés
    - Compatibilité avec modes année unique/multi-années
    
    Args:
        df (pandas.DataFrame): DataFrame avec index datetime et colonnes de consommation
                              ⚠️ DOIT ÊTRE PRÉ-FILTRÉ selon la sélection utilisateur
        
    Returns:
        dict: Dictionnaire complet contenant :
            - overall_ratio (float): Ratio global sur toutes les données filtrées
            - yearly_ratios (dict): Ratios par année {année: ratio}
            - yearly_data (dict): Données détaillées par année {année: {jour, nuit}}
            - years (list): Liste des années pour analyse de tendance
            - ratios_list (list): Ratios correspondants pour tendance
            - total_day_consumption (float): Somme totale jour (toutes années)
            - total_night_consumption (float): Somme totale nuit (toutes années)
            
    Note Importante:
        Cette fonction NE DOIT PAS refiltrer les données - elle travaille sur
        le DataFrame déjà filtré selon les choix utilisateur (années, mode, etc.)
        pour éviter les incohérences avec l'interface.
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
    
    # ÉTAPE 3: CLASSIFICATION TEMPORELLE JOUR/NUIT
    # ============================================
    # Création des masques booléens pour séparation temporelle standardisée
    # Jour: 6h-22h (16h d'activité) / Nuit: 22h-6h (8h repos/veille)
    day_mask = df.index.hour.isin(range(6, 22))
    night_mask = ~day_mask
    
    # ÉTAPE 4: CALCUL DU RATIO GLOBAL SUR LES DONNÉES FILTRÉES
    # ========================================================
    # Sommes totales sur l'ensemble du DataFrame pré-filtré (toutes années confondues)
    day_consumption = df.loc[day_mask, consumption_col].sum()
    night_consumption = df.loc[night_mask, consumption_col].sum()
    # Protection contre division par zéro avec gestion d'infini
    overall_ratio = day_consumption / night_consumption if night_consumption != 0 else float('inf')
    
    # ÉTAPE 5: ANALYSE ANNUELLE POUR DÉTECTION DE TENDANCES
    # =====================================================
    # Calcul des ratios par année pour identifier les évolutions comportementales
    yearly_ratios = {}
    yearly_data = {}
    years_list = []
    ratios_list = []
    
    # === BOUCLE DE CALCUL PAR ANNÉE ===
    # Traitement individuel de chaque année présente dans les données filtrées
    for year in years_to_use:
        year_data = df[df.index.year == year]
        if not year_data.empty:
            # Classification temporelle pour cette année spécifique
            year_day_mask = year_data.index.hour.isin(range(6, 22))
            year_night_mask = ~year_day_mask
            
            # Calculs de consommation annuelle par période
            year_day_consumption = year_data.loc[year_day_mask, consumption_col].sum()
            year_night_consumption = year_data.loc[year_night_mask, consumption_col].sum()
            
            # Calcul du ratio annuel avec protection division par zéro
            if year_night_consumption != 0:
                year_ratio = year_day_consumption / year_night_consumption
                yearly_ratios[year] = year_ratio
                yearly_data[year] = {
                    'day_consumption': year_day_consumption,
                    'night_consumption': year_night_consumption
                }
    
    # ÉTAPE 6: FILTRAGE INTELLIGENT POUR ANALYSE DE TENDANCE FIABLE
    # =============================================================
    # Application de la même logique que base_load: années complètes seulement
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
        ratios_list.append(yearly_ratios[year])
    
    return {
        'overall_ratio': overall_ratio,
        'yearly_ratios': yearly_ratios,
        'yearly_data': yearly_data,
        'years': years_list,
        'ratios_list': ratios_list,
        'total_day_consumption': day_consumption,    # AJOUT : sommes totales du DataFrame filtré
        'total_night_consumption': night_consumption  # AJOUT : sommes totales du DataFrame filtré
    }

def _display_day_night_ratio_explanation():
    """
    Affiche l'expander avec les explications sur le ratio jour/nuit
    """
    tooltip_info("Information")
    with st.expander("Comment interpréter votre ratio jour/nuit ?"):
        st.markdown(""" 
                    
        ### Qu'est-ce que le ratio jour/nuit ?  
                    
        Ce ratio compare votre consommation électrique moyenne durant le jour (entre 6h et 22h) à votre consommation électrique moyenne de nuit (entre 22h et 6h).

        ### Seuils d'interprétation et couleurs
        
        - 🟢 **Ratio équilibré (1.7 - 2.3)** : Répartition standard pour un foyer résidentiel
        - 🟡 **Ratio élevé (> 2.3)** : Votre consommation est significativement plus élevée la journée que la nuit
        - 🔴 **Ratio faible (< 1.7)** : Votre consommation est significativement plus élevée la nuit que la journée
        
        ### Qu'est-ce que cela signifie ?  
                    
        Voici quelques interprétations possibles de votre ratio de consommation. Il s'agit de propositions non exhaustives, il reste cependant à examiner si ce ratio semble correspondre à vos habitudes de consommations : 
        
        Un **Ratio équilibré** indique que votre consommation suit un rythme standard avec plus d'activité électrique le jour.

        Un **Ratio élevé** peut indiquer : 
        - Une très faible consommation nocturne (excellent contrôle des veilles)  
        - Une utilisation intensive d'appareils électriques en journée  
        - Peu d'appareils fonctionnant la nuit
        
        Un **Ratio faible** peut indiquer :
        - Beaucoup d'appareils qui restent en veille
        - Du chauffage électrique avec programmation nocturne
        - Beaucoup d'appareils énergivores en fonction la nuit (congélateurs, systèmes de surveillance, etc.)
        """)

# ============================================================================
# FONCTION PRINCIPALE D'AFFICHAGE ET ORCHESTRATION
# ============================================================================

def display_day_night_ratio(ratio_data, df=None):
    """
    Orchestre l'affichage du rapport jour/nuit selon les modes d'analyse configurés
    
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
    - Privilégie les données issues de calculate_day_night_ratio()
    - Évite les recalculs pour maintenir la cohérence
    - Gère les différences entre années partielles/complètes
    - Support de l'inclusion/exclusion des années partielles
    
    LOGIQUE DE TENDANCE:
    - Affichage conditionnel selon disponibilité des années complètes
    - Calcul de variation pourcentuelle entre première/dernière année
    - Seuils de signification: ±10% pour stabilité
    - Codes couleur: vert (baisse), bleu (stable), rouge (hausse)
    
    Args:
        ratio_data (dict): Données pré-calculées par calculate_day_night_ratio()
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
        yearly_data = ratio_data.get('yearly_data', {})
        
        if selected_year and selected_year in yearly_ratios:
            # Cas optimal: données disponibles pour l'année demandée
            year_ratio = yearly_ratios[selected_year]
            year_data = yearly_data.get(selected_year, {})
            day_consumption = year_data.get('day_consumption', 0)
            night_consumption = year_data.get('night_consumption', 0)
            _display_single_year_ratio(year_ratio, selected_year, day_consumption, night_consumption)
        else:
            # Cas de fallback: année non disponible, utiliser ratio global
            overall_ratio = ratio_data.get('overall_ratio', 0)
            _display_single_year_ratio(overall_ratio, selected_year, 0, 0)
    else:
        # === MODE DONNÉES COMPLÈTES : Vue globale et tendances ===
        # Extraction de toutes les données pour analyse complète
        years = ratio_data.get('years', [])
        ratios_list = ratio_data.get('ratios_list', [])
        overall_ratio = ratio_data.get('overall_ratio', 0)
        yearly_data = ratio_data.get('yearly_data', {})
        yearly_ratios = ratio_data.get('yearly_ratios', {})
        
        # PHASE 2: ANALYSE DE LA DISPONIBILITÉ DES DONNÉES MULTI-ANNÉES
        # =============================================================
        # Vérification du mode d'inclusion des années partielles configuré par l'utilisateur
        include_partial_years = st.session_state.get('include_partial_years', False)
        years_completeness = st.session_state.get('years_completeness', {})
        
        # === LOGIQUE DE DÉTERMINATION : ANNÉES MULTIPLES OU UNIQUE ===
        # Stratégie adaptative selon le mode d'inclusion des années partielles
        if include_partial_years:
            # Mode "inclure années partielles" : utiliser TOUTES les années disponibles
            available_years = list(yearly_data.keys()) if yearly_data else []
            has_multiple_years = len(available_years) >= 2
        else:
            # Mode "années complètes seulement" : appliquer le filtrage de complétude
            has_multiple_years = len(years) >= 2
        
        if has_multiple_years:
            # === CAS MULTI-ANNÉES : Affichage global avec tendances conditionnelles ===
            
            # UTILISATION DU RATIO GLOBAL (sommes totales) au lieu de moyenne
            # Plus représentatif car pondéré par les volumes réels de consommation
            overall_ratio_to_display = overall_ratio
            
            # === LOGIQUE DE CALCUL DE TENDANCE ===
            # Dépend du mode d'inclusion configuré par l'utilisateur
            if include_partial_years:
                # Mode années partielles : utiliser toutes les années du DataFrame
                valid_years_for_trend = years
            else:
                # Mode années complètes : filtrage strict par complétude ≥100%
                valid_years_for_trend = []
                for year in years:
                    if year in years_completeness and years_completeness[year] >= 100:
                        valid_years_for_trend.append(year)
            
            # === VALIDATION DE LA POSSIBILITÉ D'AFFICHER UNE TENDANCE ===
            # Nécessite au minimum 2 années valides selon les critères choisis
            show_trend = len(valid_years_for_trend) >= 2
            if show_trend:
                # Calcul de la variation entre première et dernière année valide
                if include_partial_years:
                    # Mode années partielles : utiliser toutes les années disponibles
                    years_for_trend = sorted(valid_years_for_trend)
                    first_year = years_for_trend[0]
                    last_year = years_for_trend[-1]
                    first_ratio = yearly_ratios.get(first_year, 0)
                    last_ratio = yearly_ratios.get(last_year, 0)
                else:
                    # Mode années complètes : utiliser les ratios pré-filtrés
                    first_ratio = ratios_list[0] if ratios_list else 0
                    last_ratio = ratios_list[-1] if ratios_list else 0
                
                # === CALCUL DE LA VARIATION POURCENTUELLE ===
                ratio_change_percent = ((last_ratio - first_ratio) / first_ratio) * 100 if first_ratio != 0 else 0
                
                # === CLASSIFICATION DE LA TENDANCE AVEC SEUILS ===
                # Seuil de 10% pour distinguer stabilité vs variation significative
                if abs(ratio_change_percent) < 10:
                    trend_color = "#3498db"  # Bleu - Stable
                    trend_icon = "➡️"
                    trend_text = "stable"
                elif ratio_change_percent > 0:
                    trend_color = "#e74c3c"  # Rouge - Augmentation
                    trend_icon = "📈"
                    trend_text = "en augmentation"
                else:
                    trend_color = "#27ae60"  # Vert - Diminution
                    trend_icon = "📉"
                    trend_text = "en diminution"
            else:
                # === CAS SANS TENDANCE : Données insuffisantes ===
                trend_color = None
                trend_icon = None
                trend_text = None
                ratio_change_percent = 0
            
            # Préparer les données annuelles pour l'affichage - utiliser TOUTES les années du ratio_data
            years_data = []
            for year in years:
                if year in yearly_data:
                    year_info = yearly_data[year]
                    years_data.append({
                        'year': year,
                        'day_consumption': year_info.get('day_consumption', 0),
                        'night_consumption': year_info.get('night_consumption', 0),
                        'ratio': yearly_ratios.get(year, 0)
                    })
            
            # Afficher le ratio overall avec tendance conditionnelle et données détaillées
            _display_mean_ratio_with_trend(overall_ratio_to_display, trend_icon, trend_text, trend_color, ratio_change_percent, years, years_data, ratio_data)
        else:
            # CORRECTION : Gérer le cas selon le mode d'inclusion des années partielles
            if include_partial_years:
                # Mode "inclure années partielles" : afficher le ratio global même avec une seule année complète
                # car on peut avoir plusieurs années partielles au total
                available_years = list(yearly_data.keys()) if yearly_data else []
                if len(available_years) == 1:
                    # Une seule année au total
                    year = available_years[0]
                    year_data = yearly_data.get(year, {})
                    day_consumption = year_data.get('day_consumption', 0)
                    night_consumption = year_data.get('night_consumption', 0)
                    year_ratio = yearly_ratios.get(year, overall_ratio)
                    _display_single_year_ratio(year_ratio, year, day_consumption, night_consumption)
                else:
                    # Plusieurs années : afficher en mode données complètes sans tendance
                    _display_mean_ratio_with_trend(overall_ratio, None, None, None, 0, available_years, None, ratio_data)
            else:
                # Mode "années complètes seulement" : EN MODE DONNÉES COMPLÈTES, afficher toujours le mode consolidé
                # même s'il n'y a qu'une seule année complète (car l'utilisateur a choisi "Données complètes")
                available_years = list(yearly_data.keys()) if yearly_data else []
                if len(available_years) >= 2:
                    # Plusieurs années : afficher en mode données complètes sans tendance  
                    _display_mean_ratio_with_trend(overall_ratio, None, None, None, 0, available_years, None, ratio_data)
                elif len(available_years) == 1:
                    # Une seule année AU TOTAL : alors oui, afficher en mode année unique
                    year = available_years[0]
                    year_data = yearly_data.get(year, {})
                    day_consumption = year_data.get('day_consumption', 0)
                    night_consumption = year_data.get('night_consumption', 0)
                    year_ratio = yearly_ratios.get(year, overall_ratio)
                    _display_single_year_ratio(year_ratio, year, day_consumption, night_consumption)
                else:
                    # Aucune année (cas d'erreur)
                    _display_fallback_ratio(overall_ratio)
    


def _display_mean_ratio_with_trend(overall_ratio, trend_icon, trend_text, trend_color, ratio_change_percent, years, years_data=None, ratio_data=None):
    """
    Affiche le ratio overall avec la tendance conditionnelle pour le mode données complètes
    """
    
    # Interprétation du ratio overall avec les mêmes seuils que pour une année unique
    if abs(overall_ratio - 2.0) < 0.3:
        interpretation = "Votre répartition jour/nuit est équilibrée."
        ratio_color = "#28a745"  # Vert
    elif overall_ratio > 2.0:
        interpretation = "Votre consommation est plus importante durant la journée."
        ratio_color = "#ffc107"  # Jaune
    else:
        interpretation = "Votre consommation nocturne est relativement élevée."
        ratio_color = "#dc3545"  # Rouge
    
    # === Note : La barre visuelle sera créée après le calcul du ratio ajusté selon le mode d'inclusion ===
    
    # Tableau des métriques avec sommes totales - utiliser les sommes calculées dans calculate_day_night_ratio
    total_day_consumption = ratio_data.get('total_day_consumption', 0)
    total_night_consumption = ratio_data.get('total_night_consumption', 0)
    yearly_data_all = ratio_data.get('yearly_data', {})
    yearly_ratios_all = ratio_data.get('yearly_ratios', {})
    
    # Vérifier le mode d'inclusion des années partielles
    include_partial_years = st.session_state.get('include_partial_years', False)
    years_completeness = st.session_state.get('years_completeness', {})
    
    if total_day_consumption > 0 or total_night_consumption > 0:
        # CORRECTION : Utiliser directement les sommes calculées dans calculate_day_night_ratio
        # Ces sommes correspondent exactement au DataFrame filtré utilisé pour le overall_ratio
        
        # CORRECTION : Utiliser le overall_ratio qui est déjà correct (calculé sur TOUTES les données filtrées)
        # Ne pas recalculer car overall_ratio provient du DataFrame déjà filtré selon le mode d'inclusion
        adjusted_ratio = overall_ratio
        
        # Recalculer les pourcentages avec le ratio overall correct
        day_percentage_adjusted = (adjusted_ratio / (adjusted_ratio + 1)) * 100
        night_percentage_adjusted = 100 - day_percentage_adjusted
        
        # Barre visuelle avec les pourcentages ajustés
        st.markdown(f"""
        <div style="display: flex; height: 40px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
            <div style="width: {day_percentage_adjusted:.1f}%; background: linear-gradient(135deg, #FFD700, #FFA500); display: flex; align-items: center; justify-content: center;">
                <span style="color: #333; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); font-family: 'Source Sans Pro', sans-serif;">☀️ {day_percentage_adjusted:.1f}%</span>
            </div>
            <div style="width: {night_percentage_adjusted:.1f}%; background: linear-gradient(135deg, #191970, #000080); display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">🌙 {night_percentage_adjusted:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">☀️ Consommation de jour de 06h00 à 22h00 (total)</th>
                        <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">📊 Ratio Jour/Nuit</th>
                        <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">🌙 Consommation de nuit de 22h00 à 06h00 (total)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 15px; text-align: center; color: #333;">
                            <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(total_day_consumption)} kWh</div>
                            <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{day_percentage_adjusted:.1f}%</div>
                        </td>
                        <td style="padding: 15px; text-align: center; color: #333;">
                            <div style="font-size: 1.4em; font-weight: bold; color: {ratio_color};">{adjusted_ratio:.2f}</div>
                        </td>
                        <td style="padding: 15px; text-align: center; color: #333;">
                            <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(total_night_consumption)} kWh</div>
                            <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{night_percentage_adjusted:.1f}%</div>
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
                    <strong style="color: #333;">Tendance globale de votre ratio jour/nuit : <span style="color: {trend_color}; font-weight: bold;">{trend_icon} {trend_text.title()}</span></strong>
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
    _display_day_night_ratio_explanation()

    # Afficher la position par rapport au groupe si disponible et si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier" and get_user_feature_position is not None:
        position_data = get_user_feature_position('ratio_day_night')
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
                    description = "Votre ratio jour/nuit est proche de la médiane du groupe (similaire)"
                elif abs_percentile <= 30:
                    emoji = "🟡"
                    status = "Ratio légèrement différent de la médiane"
                    color = "#f39c12"
                    bg_color = "#fef9e7"
                    border_color = "#f39c12"
                    description = "Votre ratio jour/nuit est légèrement différent de la médiane du groupe"
                else:  # > 30%
                    emoji = "🔴"
                    status = "Ratio très différent de la médiane"
                    color = "#e74c3c"
                    bg_color = "#fdf2f2"
                    border_color = "#e74c3c"
                    description = "Votre ratio jour/nuit est très différent de la médiane du groupe"
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
                    <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} Ratio jour/nuit</span>
                    <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{position_percentile:+.0f}%</span>
                </div>
                <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                    {description}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Expander explicatif pour les seuils de position dans le groupe
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


def _display_year_bars_comparison(years_data):
    """
    Affiche des barres séparées pour chaque année avec les données de consommation
    """
    for i, data in enumerate(years_data):
        year = data['year']
        day_consumption = data['day_consumption']
        night_consumption = data['night_consumption']
        ratio = data['ratio']
        
        # Calcul des pourcentages
        total_consumption = day_consumption + night_consumption
        day_percentage = (day_consumption / total_consumption) * 100 if total_consumption > 0 else 0
        night_percentage = 100 - day_percentage
        
        # Affichage de l'année et du total simplifié
        st.markdown(f"**{year}** - {format_number_with_apostrophe(total_consumption)} kWh")
        
        # Barre visuelle pour cette année
        st.markdown(f"""
        <div style="display: flex; height: 40px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
            <div style="width: {day_percentage:.1f}%; background: linear-gradient(135deg, #FFD700, #FFA500); display: flex; align-items: center; justify-content: center;">
                <span style="color: #333; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); font-family: 'Source Sans Pro', sans-serif;">☀️ {day_percentage:.1f}%</span>
            </div>
            <div style="width: {night_percentage:.1f}%; background: linear-gradient(135deg, #191970, #000080); display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">🌙 {night_percentage:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Ajouter un séparateur sauf pour la dernière année
        if i < len(years_data) - 1:
            st.markdown("---")

def _display_single_year_ratio(ratio, year, day_consumption, night_consumption):
    """
    Affiche le ratio jour/nuit pour une seule année avec les consommations totales
    """
    # Calcul des pourcentages pour la barre visuelle
    total_consumption = day_consumption + night_consumption
    day_percentage = (day_consumption / total_consumption) * 100 if total_consumption > 0 else 0
    night_percentage = 100 - day_percentage
    
    # Interprétation du ratio
    if abs(ratio - 2.0) < 0.3:
        interpretation = "Votre répartition jour/nuit est équilibrée."
        ratio_color = "#28a745"  # Vert
    elif ratio > 2.0:
        interpretation = "Votre consommation est plus importante durant la journée."
        ratio_color = "#ffc107"  # Jaune
    else:
        interpretation = "Votre consommation nocturne est relativement élevée."
        ratio_color = "#dc3545"  # Rouge

    
    # Barre visuelle pour l'année sélectionnée
    #st.markdown(f"**{year}** - {format_number_with_apostrophe(total_consumption)} kWh")
    
    # Barre visuelle pour cette année
    st.markdown(f"""
    <div style="display: flex; height: 40px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
        <div style="width: {day_percentage:.1f}%; background: linear-gradient(135deg, #FFD700, #FFA500); display: flex; align-items: center; justify-content: center;">
            <span style="color: #333; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); font-family: 'Source Sans Pro', sans-serif;">☀️ {day_percentage:.1f}%</span>
        </div>
        <div style="width: {night_percentage:.1f}%; background: linear-gradient(135deg, #191970, #000080); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">🌙 {night_percentage:.1f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tableau des métriques détaillées
    st.markdown(f"""
    <div style="margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">☀️ Consommation de jour de 06h00 à 22h00</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">📊 Ratio Jour/Nuit</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">🌙 Consommation de nuit de 22h00 à 06h00</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(day_consumption)} kWh</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{day_percentage:.1f}%</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: {ratio_color};">{ratio:.2f}</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{format_number_with_apostrophe(night_consumption)} kWh</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 2px;">{night_percentage:.1f}%</div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


    # Expander avec les seuils d'interprétation
    _display_day_night_ratio_explanation()

    # Afficher la position par rapport au groupe si disponible et si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier" and get_user_feature_position is not None:
        position_data = get_user_feature_position('ratio_day_night')
        if position_data is not None:
            position_percentile, user_value, cluster_id = position_data
            
            # Fonction pour déterminer l'emoji, statut et couleur
            def get_status_info(percentile):
                # Pour les ratios : nouvelle logique basée sur la distance absolue à la médiane
                abs_percentile = abs(percentile)  # Valeur absolue par rapport à la médiane
                if abs_percentile <= 10:
                    emoji = "🟢"
                    status = "Ratio proche de la médiane"
                    color = "#27ae60"
                    bg_color = "#d5f4e6"
                    border_color = "#27ae60"
                    description = "Votre ratio jour/nuit est proche de la médiane du groupe (similaire)"
                elif abs_percentile <= 30:
                    emoji = "🟡"
                    status = "Ratio légèrement différent de la médiane"
                    color = "#f39c12"
                    bg_color = "#fef9e7"
                    border_color = "#f39c12"
                    description = "Votre ratio jour/nuit est légèrement différent de la médiane du groupe"
                else:  # > 30%
                    emoji = "🔴"
                    status = "Ratio très différent de la médiane"
                    color = "#e74c3c"
                    bg_color = "#fdf2f2"
                    border_color = "#e74c3c"
                    description = "Votre ratio jour/nuit est très différent de la médiane du groupe"
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
                    <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} Ratio jour/nuit</span>
                    <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{position_percentile:+.0f}%</span>
                </div>
                <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                    {description}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Expander explicatif pour les seuils de position dans le groupe
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

def _display_two_years_comparison(years_data):
    """
    Cette fonction n'est plus utilisée dans le nouveau design simplifié
    """
    pass

def _display_fallback_ratio(ratio):
    """
    Affichage de fallback pour le ratio jour/nuit avec tableau
    """
    # Interprétation du ratio
    if abs(ratio - 2.0) < 0.3:
        interpretation = "Votre répartition jour/nuit est équilibrée."
        ratio_color = "#28a745"  # Vert
    elif ratio > 2.0:
        interpretation = "Votre consommation est plus importante durant la journée."
        ratio_color = "#ffc107"  # Jaune
    else:
        interpretation = "Votre consommation nocturne est relativement élevée."
        ratio_color = "#dc3545"  # Rouge
    
    # Calcul des pourcentages pour la barre visuelle
    day_percentage = (ratio / (ratio + 1)) * 100 if ratio > 0 else 50
    night_percentage = 100 - day_percentage
    
    st.markdown("### Rapport Jour/Nuit")
    
    # Barre visuelle générale
    st.markdown(f"""
    <div style="display: flex; height: 40px; border-radius: 20px; overflow: hidden; border: 2px solid #ddd; margin: 10px 0;">
        <div style="width: {day_percentage:.1f}%; background: linear-gradient(135deg, #FFD700, #FFA500); display: flex; align-items: center; justify-content: center;">
            <span style="color: #333; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(255,255,255,0.8); font-family: 'Source Sans Pro', sans-serif;">☀️ {day_percentage:.1f}%</span>
        </div>
        <div style="width: {night_percentage:.1f}%; background: linear-gradient(135deg, #191970, #000080); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); font-family: 'Source Sans Pro', sans-serif;">🌙 {night_percentage:.1f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tableau des métriques
    st.markdown(f"""
    <div style="margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">☀️ Jour (06h00-22h00)</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">📊 Ratio Jour/Nuit</th>
                    <th style="padding: 12px; text-align: center; color: #495057; font-weight: bold; border-bottom: 2px solid #ffffff;">🌙 Nuit (22h00-06h00)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{day_percentage:.1f}%</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: {ratio_color};">{ratio:.2f}</div>
                    </td>
                    <td style="padding: 15px; text-align: center; color: #333;">
                        <div style="font-size: 1.4em; font-weight: bold; color: #333;">{night_percentage:.1f}%</div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


    # Expander avec les seuils d'interprétation
    _display_day_night_ratio_explanation()

    # Afficher la position par rapport au groupe si disponible et si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier" and get_user_feature_position is not None:
        position_data = get_user_feature_position('ratio_day_night')
        if position_data is not None:
            position_percentile, user_value, cluster_id = position_data
            
            # Fonction pour déterminer l'emoji, statut et couleur
            def get_status_info(percentile):
                # Pour les ratios : nouvelle logique basée sur la distance absolue à la médiane
                abs_percentile = abs(percentile)  # Valeur absolue par rapport à la médiane
                if abs_percentile <= 10:
                    emoji = "🟢"
                    status = "Ratio proche de la médiane"
                    color = "#27ae60"
                    bg_color = "#d5f4e6"
                    border_color = "#27ae60"
                    description = "Votre ratio jour/nuit est proche de la médiane du groupe (similaire)"
                elif abs_percentile <= 30:
                    emoji = "🟡"
                    status = "Ratio légèrement différent de la médiane"
                    color = "#f39c12"
                    bg_color = "#fef9e7"
                    border_color = "#f39c12"
                    description = "Votre ratio jour/nuit est légèrement différent de la médiane du groupe"
                else:  # > 30%
                    emoji = "🔴"
                    status = "Ratio très différent de la médiane"
                    color = "#e74c3c"
                    bg_color = "#fdf2f2"
                    border_color = "#e74c3c"
                    description = "Votre ratio jour/nuit est très différent de la médiane du groupe"
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
                    <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} Ratio jour/nuit</span>
                    <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{position_percentile:+.0f}%</span>
                </div>
                <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                    {description}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Expander explicatif pour les seuils de position dans le groupe
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

# ============================================================================
# NOTES D'INTÉGRATION ET MAINTENANCE - Module day_night_ratio
# ============================================================================
#
# 1. **Cohérence avec base_load**: 
#    - Utilise la même logique de filtrage des années complètes
#    - Même stratégie de calcul de tendances (2 années récentes max)
#    - Cohérence des seuils de complétude (≥100%)
#
# 2. **Gestion des données pré-filtrées**:
#    - NE JAMAIS refiltrer dans les fonctions de calcul
#    - Toujours utiliser le DataFrame passé en paramètre
#    - Éviter les références à st.session_state['years_to_use']
#
# 3. **Performance et cache**:
#    - calculate_day_night_ratio() fait les calculs lourds UNE fois
#    - display_day_night_ratio() orchestre sans recalculer
#    - Données partagées via dictionnaire ratio_data
#
# 4. **Extensibilité clustering**:
#    - Import conditionnel de get_user_feature_position
#    - Gestion élégante si module clustering absent
#    - Interface standardisée pour comparaison groupe
#
# 5. **Standards DataWatt**:
#    - Formatage numérique suisse (apostrophes)
#    - Palette de couleurs cohérente avec écosystème
#    - Documentation utilisateur intégrée (expanders)
#    - Responsive design pour différentes tailles d'écran
#
# ÉVOLUTIONS POSSIBLES:
# - Seuils personnalisables jour/nuit (actuellement fixes 6h-22h)
# - Analyse saisonnière des variations de ratio
# - Comparaisons avec standards régionaux/nationaux
# - Intégration avec module tarification HP/HC
# - Alertes automatiques sur ratios atypiques
#
# ============================================================================