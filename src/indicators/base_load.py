"""
=====================================================================================
                      ANALYSE DE LA CHARGE DE BASE ÉNERGÉTIQUE 
=====================================================================================
[MODULE ACTIF - FONCTIONNALITÉ PRINCIPALE DE DATAWATT]

Ce module implémente l'analyse complète de la charge de base (charge nocturne) et du talon 
de consommation, deux indicateurs clés pour comprendre les habitudes énergétiques et 
détecter les consommations de veille ou les anomalies.

FONCTIONNALITÉS PRINCIPALES:
1. **Calcul de la charge nocturne** : Analyse de la consommation entre 1h-5h du matin
2. **Calcul du talon de consommation** : Moyenne des minimums quotidiens 
3. **Analyse des tendances** : Évolution temporelle avec seuils de variation
4. **Équivalences d'appareils** : Conversion en équipements domestiques de référence
5. **Positionnement utilisateur** : Comparaison avec les groupes de référence
6. **Interface adaptative** : Affichage selon le mode de sélection des années

LOGIQUE MÉTIER - CHARGE NOCTURNE:
La période 1h-5h du matin est choisie car elle représente le moment où :
- L'activité humaine est au minimum (sommeil)
- Les appareils de confort sont éteints (éclairage, électroménager actif)
- Seuls fonctionnent les équipements essentiels (réfrigérateur, veilles, systèmes techniques)
- Les variations météorologiques ont moins d'impact (pas de climatisation/chauffage actif)

MÉTHODE DE CALCUL TECHNIQUE:
1. **Filtrage temporel** : Sélection des créneaux 1h-5h (4 heures × 4 quarts d'heure = 16 mesures/jour)
2. **Sommation énergétique** : Total des consommations sur la période (kWh)
3. **Conversion puissance** : Division par 16 pour obtenir la puissance moyenne (kW)
4. **Normalisation temporelle** : Division par le nombre de jours pour la moyenne quotidienne

LOGIQUE MÉTIER - TALON DE CONSOMMATION:
Le talon représente la consommation minimale absolue et permet de :
- Identifier les consommations incompressibles (veilles, équipements techniques)
- Détecter les anomalies (défauts de mesure, coupures, équipements défaillants)
- Calculer le potentiel d'économies sur les consommations de base

GESTION DES MODES D'ANALYSE:
- **Mode année unique** : Analyse ciblée sur une année spécifique pour diagnostic précis
- **Mode données complètes** : Vue d'ensemble avec tendances sur années complètes uniquement
- **Filtrage de qualité** : Exclusion automatique des années partielles pour les tendances

INTÉGRATION AVEC LE CLUSTERING:
- Positionnement de l'utilisateur par rapport à son groupe de référence
- Percentiles calculés sur la charge nocturne comme variable discriminante
- Recommandations personnalisées basées sur la position relative

AUTEURS: Équipe DataWatt - SIE SA & EPFL
DATE: Développement continu 2025 - Module actif en production
=====================================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import streamlit as st
from src.textual.tools import tooltip_info  
import src.textual.text as txt   

# Import conditionnel du module de clustering pour positionnement utilisateur
try:
    from src.indicators.cluster_indic import get_user_feature_position
except ImportError:
    get_user_feature_position = None   

# ============================================================================
# FONCTIONS UTILITAIRES POUR LE FORMATAGE ET L'AFFICHAGE
# ============================================================================

def format_number_with_apostrophe(number, decimal_places=0):
    """
    Formate un nombre selon la norme suisse avec apostrophes comme séparateurs de milliers
    
    Cette fonction applique la convention typographique suisse pour les grands nombres,
    facilitant la lecture des valeurs énergétiques dans l'interface utilisateur.
    
    Args:
        number (float): Nombre à formater (peut être None)
        decimal_places (int): Nombre de décimales à afficher (0, 1, 2, ou plus)
        
    Returns:
        str: Nombre formaté avec apostrophes ou "0" si number est None
        
    Exemples:
        format_number_with_apostrophe(1234567.89, 2) → "1'234'567.89"
        format_number_with_apostrophe(1234567.89, 0) → "1'234'568"
        format_number_with_apostrophe(1234, 1) → "1'234.0"
        format_number_with_apostrophe(None, 0) → "0"
    """
    # Gestion des valeurs nulles pour éviter les erreurs d'affichage
    if number is None:
        return "0"
    
    # === FORMATAGE SELON LE NOMBRE DE DÉCIMALES SOUHAITÉ ===
    # Application de la précision demandée avec arrondi automatique
    if decimal_places == 0:
        formatted = f"{number:.0f}"
    elif decimal_places == 1:
        formatted = f"{number:.1f}"
    elif decimal_places == 2:
        formatted = f"{number:.2f}"
    else:
        formatted = f"{number:.{decimal_places}f}"
    
    # === SÉPARATION ET INSERTION DES APOSTROPHES ===
    # Traitement différentiel selon la présence de décimales
    if '.' in formatted:
        integer_part, decimal_part = formatted.split('.')
        # Formatage de la partie entière avec apostrophes
        formatted_with_apostrophe = f"{int(integer_part):_}".replace('_', "'")
        return f"{formatted_with_apostrophe}.{decimal_part}"
    else:
        # Nombre entier : formatage direct avec apostrophes
        return f"{int(formatted):_}".replace('_', "'")

def get_consumption_column(df):
    """
    Détermine automatiquement la colonne de consommation à utiliser selon le type de données
    
    Cette fonction gère la compatibilité avec différents formats de fichiers d'entrée :
    - Fichiers avec données solaires : 'Total Consumption (kWh)' (somme autoconso + réseau)
    - Fichiers standards : 'Consumption (kWh)' (consommation directe du réseau)
    
    Args:
        df (DataFrame): DataFrame contenant les données de consommation
        
    Returns:
        str: Nom de la colonne de consommation à utiliser pour les calculs
        
    Logique de sélection:
        1. Priorité à 'Total Consumption (kWh)' si disponible (inclut l'autoconsommation solaire)
        2. Fallback sur 'Consumption (kWh)' pour les installations sans solaire
        3. Cette logique assure une analyse cohérente quel que soit le type d'installation
    """
    return 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in df.columns else 'Consumption (kWh)'

# ============================================================================
# FONCTION PRINCIPALE DE CALCUL DE LA CHARGE NOCTURNE
# ============================================================================

def calculate_base_load(df):
    """
    Calcule la charge de base (charge nocturne) selon le mode de sélection d'années utilisateur
    
    Cette fonction implémente la logique métier principale pour l'analyse de la charge nocturne.
    Elle s'adapte automatiquement au mode de sélection choisi par l'utilisateur dans l'interface.
    
    LOGIQUE MÉTIER:
    La charge nocturne est calculée sur la période 1h-5h du matin car :
    - Activité humaine minimale (période de sommeil)
    - Appareils de confort éteints (éclairage, électroménager actif)
    - Fonctionnement uniquement des équipements essentiels (réfrigération, veilles)
    - Impact météorologique réduit (pas de chauffage/climatisation actifs)
    
    MÉTHODE DE CALCUL:
    1. Filtrage temporel : Sélection des créneaux 1h-5h (16 quarts d'heure/jour)
    2. Sommation énergétique : Total des consommations sur la période (kWh)  
    3. Conversion puissance : Division par 16 pour obtenir la puissance moyenne (kW)
    4. Normalisation temporelle : Division par le nombre de jours (kW moyen/jour)
    
    GESTION DES MODES:
    - Mode année unique : Calcul ciblé sur l'année sélectionnée
    - Mode données complètes : Calcul global + tendance si ≥2 années complètes
    
    Args:
        df (DataFrame): DataFrame avec index temporel et colonnes de consommation
        
    Returns:
        tuple: (years_list, base_loads_list)
            - years_list (list): Liste des années analysées 
            - base_loads_list (list): Valeurs de charge nocturne en kW
            
    Modes de retour:
    - Année unique : ([année], [charge_année])
    - Données complètes avec tendance : ([année1, année2], [charge1, charge2, charge_globale])
    - Données complètes sans tendance : ([], [charge_globale])
    """
    # === DÉTERMINATION DE LA COLONNE DE CONSOMMATION ===
    # Sélection automatique selon le type de données (avec/sans solaire)
    consumption_col = get_consumption_column(df)
    
    # === RÉCUPÉRATION DU MODE D'ANALYSE DEPUIS L'INTERFACE UTILISATEUR ===
    # Mode défini dans la sidebar de main.py selon les choix utilisateur
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    # ========================================================================
    # BRANCHE 1: MODE ANNÉE UNIQUE - ANALYSE CIBLÉE SUR UNE ANNÉE SPÉCIFIQUE
    # ========================================================================

    if year_selection_mode != "Données complètes":
        # === RÉCUPÉRATION DE L'ANNÉE SÉLECTIONNÉE ===
        # Année choisie par l'utilisateur dans le selectbox de la sidebar
        selected_year = st.session_state.get('selected_single_year')
        
        if selected_year:
            # === FILTRAGE DES DONNÉES POUR L'ANNÉE CIBLE ===
            year_data = df[df.index.year == selected_year]
            
            if not year_data.empty:
                # === FILTRAGE TEMPOREL: SÉLECTION DES HEURES NOCTURNES (1h-5h) ===
                # Deux méthodes selon le type d'index pour compatibilité maximale
                if hasattr(year_data.index, 'hour'):
                    # Méthode directe si l'index a un attribut 'hour'
                    base_load_mask = year_data.index.hour.isin([1, 2, 3, 4])
                    base_load_data = year_data[base_load_mask]
                else:
                    # Méthode alternative avec between_time (plus robuste)
                    base_load_data = year_data.between_time('01:00', '05:00')
                
                # === GESTION DES CAS SANS DONNÉES NOCTURNES ===
                # Fallback vers toutes les données si pas de mesures nocturnes
                if base_load_data.empty:
                    st.warning("Aucune donnée disponible entre 1h et 5h du matin. Calcul de la charge de base approximatif.")
                    base_load_data = year_data.copy()
                
                # === SÉLECTION DES COLONNES NUMÉRIQUES UNIQUEMENT ===
                # Évite les erreurs sur les colonnes texte ou catégorielles
                numeric_base_load_data = base_load_data.select_dtypes(include=[np.number])
                
                if consumption_col in numeric_base_load_data.columns:
                    # === CALCUL DE LA CHARGE NOCTURNE POUR L'ANNÉE ===
                    # Application de la méthode de calcul standardisée
                    
                    # 1. Sommation de toutes les consommations nocturnes (kWh)
                    total_night_consumption = numeric_base_load_data[consumption_col].sum()
                    
                    # 2. Conversion en puissance équivalente (kWh → kW)
                    # Division par 16 = (4 quarts d'heure/heure × 4 heures de période)
                    power_equivalent = total_night_consumption / 16
                    
                    # 3. Normalisation par le nombre de jours pour obtenir la moyenne quotidienne
                    unique_days = len(set(base_load_data.index.date))
                    year_base_load = power_equivalent / unique_days if unique_days > 0 else 0
                    
                    # === RETOUR DES RÉSULTATS POUR MODE ANNÉE UNIQUE ===
                    return [selected_year], [year_base_load]
                else:
                    st.error(f"Colonne de consommation '{consumption_col}' non trouvée.")
                    return [], [0]
            else:
                st.error(f"Aucune donnée disponible pour l'année {selected_year}")
                return [], [0]
        else:
            st.error("Aucune année sélectionnée")
            return [], [0]
    
    # ========================================================================
    # BRANCHE 2: MODE DONNÉES COMPLÈTES - ANALYSE GLOBALE AVEC TENDANCES
    # ========================================================================
    else:
        # === IDENTIFICATION DES ANNÉES DISPONIBLES DANS LE DATASET ===
        available_years = sorted(df.index.year.unique().tolist())
        
        if not available_years:
            return [], [0]
        
        # === FILTRAGE TEMPOREL GLOBAL: TOUTES LES HEURES NOCTURNES ===
        # Application du même filtrage que le mode année unique mais sur tout le dataset
        if hasattr(df.index, 'hour'):
            base_load_mask = df.index.hour.isin([1, 2, 3, 4])
            base_load_data = df[base_load_mask]
        else:
            # Méthode alternative pour compatibilité avec différents types d'index
            base_load_data = df.between_time('01:00', '05:00')
        
        # === GESTION DES CAS SANS DONNÉES NOCTURNES GLOBALES ===
        if base_load_data.empty:
            st.warning("Aucune donnée disponible entre 1h et 5h du matin. Calcul de la charge de base approximatif.")
            base_load_data = df.copy()
        
        # === SÉLECTION DES COLONNES NUMÉRIQUES POUR CALCULS ===
        numeric_base_load_data = base_load_data.select_dtypes(include=[np.number])
        
        # === VÉRIFICATION DE LA DISPONIBILITÉ DE LA COLONNE DE CONSOMMATION ===
        if consumption_col not in numeric_base_load_data.columns:
            st.error(f"Colonne de consommation '{consumption_col}' non trouvée.")
            return [], [0]
        
        try:
            # === CALCUL DE LA CHARGE NOCTURNE GLOBALE ===
            # Application de la même méthode que le mode année unique sur tout le dataset
            
            # 1. Sommation de toutes les consommations nocturnes sur la période complète
            total_night_consumption_all = numeric_base_load_data[consumption_col].sum()
            
            # 2. Conversion en puissance équivalente globale  
            power_equivalent_all = total_night_consumption_all / 16
            
            # 3. Normalisation par le nombre total de jours uniques
            unique_days_all = len(set(base_load_data.index.date))
            overall_base_load = power_equivalent_all / unique_days_all if unique_days_all > 0 else 0
            
            # === CALCUL PAR ANNÉE POUR L'ANALYSE DE TENDANCE ===
            # Nécessaire pour identifier les variations temporelles
            yearly_base_loads_all = {}
            
            # Calcul individuel pour chaque année disponible
            for year in available_years:
                year_data = numeric_base_load_data[numeric_base_load_data.index.year == year]
                if not year_data.empty:
                    # Application de la même méthode de calcul par année
                    total_night_consumption_year = year_data[consumption_col].sum()
                    power_equivalent_year = total_night_consumption_year / 16
                    unique_days_year = len(set(year_data.index.date))
                    year_base_load = power_equivalent_year / unique_days_year if unique_days_year > 0 else 0
                    yearly_base_loads_all[year] = year_base_load
            
            # === FILTRAGE DES ANNÉES COMPLÈTES POUR ANALYSE DE TENDANCE ===
            # Cohérence avec la logique appliquée dans day_night_ratio.py
            years_completeness = st.session_state.get('years_completeness', {})
            complete_years = [year for year in available_years 
                             if year in years_completeness and years_completeness[year] >= 100 and year in yearly_base_loads_all]
            
            # === SÉLECTION DES ANNÉES POUR TENDANCE ===
            # Prise des deux années complètes les plus récentes pour tendance robuste
            recent_complete_years = sorted(complete_years)[-2:] if len(complete_years) >= 2 else complete_years
            
            # === CONSTRUCTION DES LISTES DE RETOUR ===
            # Préparation des données selon le nombre d'années complètes disponibles
            yearly_base_loads = []
            years_list = []
            for year in recent_complete_years:
                years_list.append(year)
                yearly_base_loads.append(yearly_base_loads_all[year])
            
            # === LOGIQUE DE RETOUR SELON LA DISPONIBILITÉ DES DONNÉES ===
            if len(years_list) >= 2:
                # Cas optimal : ≥2 années complètes → Analyse de tendance possible
                # Retourne : [année1, année2], [charge1, charge2, charge_globale]
                base_load_list = yearly_base_loads + [overall_base_load]
                return years_list, base_load_list
            elif len(years_list) == 1:
                # Cas intermédiaire : 1 année complète → Pas de tendance mais données fiables
                # Retourne : [année], [charge_année, charge_globale]
                base_load_list = yearly_base_loads + [overall_base_load]
                return years_list, base_load_list
            else:
                # Cas minimal : 0 année complète → Charge globale uniquement
                # Retourne : [], [charge_globale]
                return [], [overall_base_load]
                
        except Exception as e:
            st.error(f"Erreur lors du calcul de la charge de base: {e}")
            return [], [0]

# ============================================================================
# FONCTION DE CALCUL DU TALON DE CONSOMMATION (MINIMUM QUOTIDIEN MOYEN)
# ============================================================================

def calculate_minimum_consumption(df):
    """
    Calcule le talon de consommation selon le mode de sélection d'années utilisateur
    
    Le talon de consommation représente la consommation minimale moyenne et permet de :
    - Identifier les consommations incompressibles (équipements en veille permanente)
    - Détecter les anomalies de mesure (valeurs aberrantes, coupures réseau)
    - Évaluer le potentiel d'optimisation des consommations de base
    
    LOGIQUE MÉTIER:
    Calcul de la moyenne des minimums quotidiens plutôt que du minimum absolu pour :
    - Éviter l'impact des anomalies ponctuelles (coupures, défauts de mesure)
    - Obtenir une valeur représentative du fonctionnement normal
    - Permettre une comparaison fiable entre périodes ou utilisateurs
    
    MÉTHODE DE CALCUL:
    1. Identification des minimums quotidiens (plus petit quart d'heure de chaque jour)
    2. Calcul de la moyenne de ces minimums sur la période sélectionnée
    3. Détection du minimum absolu pour diagnostic (affiché séparément)
    4. Vérification de cohérence (alerte si valeurs suspectes)
    
    Args:
        df (DataFrame): DataFrame avec index temporel et colonnes de consommation (PRÉ-FILTRÉ)
        
    Returns:
        tuple: (avg_daily_min, is_partial_data, min_datetime, min_value)
            - avg_daily_min (float): Moyenne des minimums quotidiens en kWh
            - is_partial_data (bool): True si données incomplètes détectées
            - min_datetime (datetime): Date/heure du minimum absolu
            - min_value (float): Valeur du minimum absolu en kWh
            
    Note:
        Le DataFrame d'entrée est déjà filtré selon les paramètres utilisateur 
        (année unique ou période complète) par les fonctions appelantes.
    """
    # Determine which consumption column to use
    consumption_col = get_consumption_column(df)
    
    # Vérifications de base
    if df is None or df.empty:
        return 0, False, None, 0  # Return 0 and False for partial data indicator, None for datetime, 0 for min value
    
    # Déterminer le mode d'analyse selon la sélection de l'utilisateur
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    if year_selection_mode != "Données complètes":
        # Mode année unique - calculer la moyenne des minimums quotidiens pour l'année sélectionnée
        selected_year = st.session_state.get('selected_single_year')
        if selected_year:
            # Filtrer les données pour l'année sélectionnée
            year_data = df[df.index.year == selected_year]
            
            # Vérifier que nous avons des données et que la colonne existe
            if not year_data.empty:
                if consumption_col in year_data.columns:
                    # Vérifier qu'il y a des valeurs non-nulles dans la colonne
                    valid_data = year_data[consumption_col].dropna()
                    if not valid_data.empty:
                        # Trouver le minimum absolu et sa date/heure
                        min_value = valid_data.min()
                        min_datetime = valid_data.idxmin()
                        
                        # Calculer les minimums quotidiens
                        daily_minimums = []
                        
                        # Grouper par jour et calculer le minimum de chaque jour
                        for date, day_group in valid_data.groupby(valid_data.index.date):
                            if not day_group.empty:
                                daily_min = day_group.min()
                                daily_minimums.append(daily_min)
                        
                        if daily_minimums:
                            # Calculer la moyenne des minimums quotidiens
                            avg_daily_min = sum(daily_minimums) / len(daily_minimums)
                            
                            # Vérifier si l'année est complète (au moins 365 jours de données)
                            is_partial_year = len(daily_minimums) < 365
                            
                            return avg_daily_min, is_partial_year, min_datetime, min_value
                        else:
                            return 0, False, None, 0
                    else:
                        # Pas de données valides dans la colonne de consommation
                        return 0, False, None, 0
                else:
                    # La colonne de consommation n'existe pas
                    return 0, False, None, 0
            else:
                # Aucune donnée pour cette année
                return 0, False, None, 0
        else:
            return 0, False, None, 0
    else:
        # Mode données complètes - calculer directement la moyenne de tous les minimums quotidiens
        # sur toute la période pour éviter de donner un poids disproportionné aux années partielles
        available_years = sorted(df.index.year.unique().tolist())
        
        # Calculer directement tous les minimums quotidiens sur toute la période
        if consumption_col in df.columns:
            # Vérifier qu'il y a des valeurs non-nulles dans la colonne
            valid_data = df[consumption_col].dropna()
            if not valid_data.empty:
                # Trouver le minimum absolu et sa date/heure sur toute la période
                min_value = valid_data.min()
                min_datetime = valid_data.idxmin()
                
                # Calculer tous les minimums quotidiens sur toute la période
                all_daily_minimums = []
                
                # Grouper par jour et calculer le minimum de chaque jour
                for date, day_group in valid_data.groupby(valid_data.index.date):
                    if not day_group.empty:
                        daily_min = day_group.min()
                        all_daily_minimums.append(daily_min)
                
                if all_daily_minimums:
                    # Moyenne directe de tous les minimums quotidiens
                    overall_avg_minimum = sum(all_daily_minimums) / len(all_daily_minimums)
                    
                    # Vérifier s'il y a des années partielles pour l'avertissement
                    has_partial_years = False
                    for year in available_years:
                        year_data = df[df.index.year == year]
                        year_daily_count = len([date for date in year_data.index.date])
                        unique_days_in_year = len(set(year_data.index.date))
                        if unique_days_in_year < 365:
                            has_partial_years = True
                            break
                    
                    return overall_avg_minimum, has_partial_years, min_datetime, min_value
                else:
                    return 0, False, None, 0
            else:
                return 0, False, None, 0
        else:
            return 0, False, None, 0

# ============================================================================
# FONCTION D'ÉQUIVALENCE EN ÉQUIPEMENTS DOMESTIQUES
# ============================================================================

def get_equipment_equivalence(base_load_w):
    """
    Convertit une puissance en équivalents d'équipements domestiques de référence
    
    Cette fonction traduit les valeurs techniques en comparaisons concrètes pour faciliter
    la compréhension utilisateur et permettre une évaluation intuitive des consommations.
    
    ÉQUIPEMENTS DE RÉFÉRENCE (choisis pour leur universalité):
    - Box wifi : 10W (équipement omniprésent, consommation constante bien connue)
    - Réfrigérateur : 150W (électroménager essentiel, référence de puissance moyenne)
    
    LOGIQUE DE PRÉSENTATION:
    - Priorité au réfrigérateur si puissance ≥ 150W (référence plus parlante)
    - Combinaison réfrigérateur + box wifi pour valeurs intermédiaires
    - Expression en box wifi uniquement pour petites puissances
    - Gestion des décimales selon la grandeur pour lisibilité optimale
    
    Args:
        base_load_w (float): Puissance de charge de base en Watts
        
    Returns:
        str: Texte descriptif de l'équivalence avec exemples concrets
        
    Exemples de sortie:
        50W → "Soit l'équivalent de 5 box wifi de 10W de puissance"
        150W → "Soit l'équivalent de 1 réfrigérateur de 150W de puissance"  
        200W → "Soit l'équivalent de 1 réfrigérateur de 150W + 5 box wifi de 10W"
        250W → "Soit l'équivalent de 1.7 réfrigérateurs de 150W ou 25 box wifi de 10W"
    """
    # === DÉFINITION DES PUISSANCES DE RÉFÉRENCE ===
    # Valeurs choisies pour leur représentativité et reconnaissance universelle
    box_wifi_w = 10      # Watts - Équipement omniprésent, consommation stable
    refrigerator_w = 150 # Watts - Électroménager essentiel, puissance moyenne typique
    
    # === CALCUL DES ÉQUIVALENTS NUMÉRIQUES ===
    nb_box_wifi = base_load_w / box_wifi_w
    nb_refrigerators = base_load_w / refrigerator_w
    
    # === LOGIQUE DE FORMATAGE SELON LA PUISSANCE ===
    # Adaptation du message selon la grandeur pour optimiser la compréhension
    if base_load_w >= refrigerator_w:
        # Cas 1: Puissance ≥ 150W → Référence principale = réfrigérateur
        if nb_refrigerators >= 1.5:
            # Puissance élevée : double affichage pour donner l'ordre de grandeur
            nb_refrigerators_rounded = round(nb_refrigerators)
            nb_box_wifi_rounded = round(nb_box_wifi)
            return f"Soit l'équivalent d'environ {nb_refrigerators_rounded} réfrigérateurs de 150W ou {nb_box_wifi_rounded} box wifi de 10W"
        else:
            # Puissance modérée : réfrigérateur + complément en box wifi
            remaining_boxes = round((base_load_w - refrigerator_w) / box_wifi_w)
            if remaining_boxes > 0:
                return f"Soit l'équivalent de 1 réfrigérateur de 150W + environ {remaining_boxes} box wifi de 10W"
            else:
                # Exactement 150W ou légèrement moins
                return f"Soit l'équivalent de 1 réfrigérateur de 150W de puissance"
    else:
        # Cas 2: Puissance < 150W → Référence principale = box wifi
        nb_box_wifi_rounded = round(nb_box_wifi)
        if nb_box_wifi_rounded >= 2:
            # Valeur entière pour simplifier la lecture
            return f"Soit l'équivalent d'environ {nb_box_wifi_rounded} box wifi de 10W de puissance"
        else:
            # Petite puissance : utiliser "environ 1" plutôt que des décimales
            if nb_box_wifi_rounded == 0:
                return f"Soit l'équivalent de moins d'1 box wifi de 10W de puissance"
            else:
                return f"Soit l'équivalent d'environ {nb_box_wifi_rounded} box wifi de 10W de puissance"

# ============================================================================
# FONCTION PRINCIPALE D'AFFICHAGE DE L'INTERFACE CHARGE DE BASE
# ============================================================================

def display_base_load(years, base_loads):
    """
    Affiche l'interface complète d'analyse de la charge de base et du talon de consommation
    
    Cette fonction orchestre l'affichage de tous les éléments de l'analyse :
    - Cartes de charge nocturne et charge minimale côte à côte
    - Calcul et affichage des tendances (si données suffisantes)
    - Équivalences d'équipements pour faciliter l'interprétation
    - Positionnement utilisateur par rapport aux groupes de référence
    - Documentation explicative interactive
    
    ARCHITECTURE D'AFFICHAGE:
    - Layout en 2 colonnes : Charge nocturne (gauche) | Charge minimale (droite)
    - Section tendance centrée sous les cartes (si applicable)
    - Expander d'aide avec documentation complète
    - Carte de positionnement pour utilisateurs particuliers avec clustering
    
    ADAPTATION AU MODE DE SÉLECTION:
    - Mode année unique : Affichage simple avec couleurs spécifiques à l'année
    - Mode données complètes : Affichage global avec tendances si ≥2 années complètes
    
    LOGIQUE DES COULEURS:
    - Cohérence avec interactive_plot.py via palette commune
    - Mode année unique : Couleur spécifique à l'année sélectionnée
    - Mode données complètes : Couleur neutre (#333333) pour vision d'ensemble
    - Différenciation charge nocturne/charge minimale via palette décalée
    
    CALCULS INTÉGRÉS:
    - Récupération automatique du talon depuis pdf_filtered
    - Gestion des cas d'erreur et données manquantes
    - Vérifications de cohérence avec alertes utilisateur
    
    Args:
        years (list): Liste des années pour l'analyse de tendance
        base_loads (list): Valeurs de charge nocturne correspondantes
        
    Note:
        Cette fonction accède à st.session_state pour :
        - pdf_filtered : DataFrame pré-filtré selon les choix utilisateur
        - year_selection_mode : Mode de sélection des années
        - years_completeness : Données de qualité des années
        - Paramètres de clustering pour positionnement (si disponible)
    """
    # === CALCUL DU TALON DE CONSOMMATION ===
    # Utilisation du DataFrame pré-filtré selon les choix utilisateur
    pdf_for_analysis = st.session_state.get('pdf_filtered')
    minimum_consumption = 0
    is_partial_data = False
    min_datetime = None
    min_value = 0
    
    # Calcul uniquement si des données sont disponibles
    if pdf_for_analysis is not None:
        minimum_consumption, is_partial_data, min_datetime, min_value = calculate_minimum_consumption(pdf_for_analysis)
    
    # === RÉCUPÉRATION DES PARAMÈTRES D'AFFICHAGE ===
    # Mode déterminé par les choix utilisateur dans la sidebar
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    # === DÉFINITION DE LA PALETTE DE COULEURS ===
    # Cohérence avec interactive_plot.py pour harmonie visuelle de l'application
    default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
    
    # === FONCTION UTILITAIRE DE SÉLECTION DES COULEURS ===
    def get_year_color(year, is_multi_year_mode=False):
        """
        Détermine la couleur d'affichage selon le mode et l'année
        
        Args:
            year (int): Année pour laquelle obtenir la couleur
            is_multi_year_mode (bool): True si mode données complètes
            
        Returns:
            str: Code couleur hexadécimal
            
        Logique:
            - Mode données complètes : Couleur neutre (noir) pour vision globale
            - Mode année unique : Couleur spécifique basée sur l'index dans la palette
        """
        if is_multi_year_mode:
            return "#333333"  # Couleur neutre pour le mode données complètes
        else:
            # Attribution d'une couleur spécifique selon la position dans la liste des années
            year_index = 0
            if pdf_for_analysis is not None:
                unique_years = sorted(pdf_for_analysis.index.year.unique())
                if year in unique_years:
                    year_index = unique_years.index(year)
            return default_colors[year_index % len(default_colors)]
    
    # === CRÉATION DU LAYOUT EN DEUX COLONNES ===
    # Structure : Charge nocturne (gauche) | Charge minimale (droite)
    col1, col2 = st.columns(2)
    
    # ========================================================================
    # COLONNE 1: AFFICHAGE DE LA CHARGE NOCTURNE
    # ========================================================================
    
    with col1:
        if year_selection_mode != "Données complètes":
            # Mode année unique - afficher seulement la valeur de l'année sélectionnée
            if years and len(years) >= 1:
                selected_year = years[0]
                year_base_load = base_loads[0] if len(base_loads) > 0 else 0
                
                # Obtenir la couleur appropriée pour l'année
                year_color = get_year_color(selected_year, is_multi_year_mode=False)
                
                # Affichage simple pour l'année sélectionnée
                equipment_text = get_equipment_equivalence(year_base_load * 1000)
                st.markdown("<h5 style='text-align: center; color: #666666;'>Charge nocturne (moyenne)</h5>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {year_color}; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: {year_color}; font-weight: bold;'>{selected_year}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(year_base_load*1000, 1)} W</span>
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>{equipment_text}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Aucune donnée disponible pour l'année sélectionnée")
        else:
            # Mode données complètes - calculer et afficher la charge nocturne globale + tendance conditionnelle
            if len(years) >= 2 and len(base_loads) >= 3:
                # Affichage de la charge de base globale
                overall_base_load = base_loads[-1]
                equipment_text = get_equipment_equivalence(overall_base_load * 1000)
                
                # Utiliser la couleur noire pour le mode données complètes
                base_color = get_year_color(years[0], is_multi_year_mode=True)
                
                # Vérifier que les années dans la liste sont bien complètes (double vérification)
                complete_years_count = 0
                years_completeness = st.session_state.get('years_completeness', {})
                valid_years_for_trend = []
                
                for year in years:
                    if year in years_completeness and years_completeness[year] >= 100:
                        complete_years_count += 1
                        valid_years_for_trend.append(year)
                
                # La tendance sera affichée séparément en bas de la section
                
                # Déterminer la période selon les années disponibles
                if pdf_for_analysis is not None:
                    all_available_years = sorted(pdf_for_analysis.index.year.unique().tolist())
                    if len(all_available_years) >= 2:
                        period_text = f"{all_available_years[0]}-{all_available_years[-1]}"
                    elif len(all_available_years) == 1:
                        period_text = f"{all_available_years[0]}"
                    else:
                        period_text = f"{years[0]}-{years[-1]}"
                else:
                    period_text = f"{years[0]}-{years[-1]}"
                
                st.markdown("<h5 style='text-align: center; color: #666666;'>Charge nocturne</h5>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {base_color}; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: {base_color}; font-weight: bold;'>{period_text}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(overall_base_load*1000, 1)} W</span>
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>{equipment_text}</div>
                </div>
                """, unsafe_allow_html=True)
            elif len(years) == 1:
                # Une seule année disponible - afficher la charge pour cette année
                year_base_load = base_loads[0] if len(base_loads) > 0 else 0
                year = years[0]
                equipment_text = get_equipment_equivalence(year_base_load * 1000)
                
                # Utiliser la couleur de l'année spécifique
                year_color = get_year_color(year, is_multi_year_mode=False)
                
                st.markdown("<h5 style='text-align: center; color: #666666;'>Charge nocturne</h5>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {year_color}; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: {year_color}; font-weight: bold;'>{year}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(year_base_load*1000, 1)} W</span>
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>{equipment_text}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.info("Analyse de tendance nécessite au moins deux années de données.")
            elif len(base_loads) == 1:
                # Cas où on a seulement la charge globale (sans années spécifiques)
                overall_base_load = base_loads[0]
                equipment_text = get_equipment_equivalence(overall_base_load * 1000)
                
                # Couleur neutre pour les données globales
                base_color = "#333333"
                
                # Déterminer la période selon les données disponibles
                if pdf_for_analysis is not None:
                    all_available_years = sorted(pdf_for_analysis.index.year.unique().tolist())
                    if len(all_available_years) >= 2:
                        period_text = f"{all_available_years[0]}-{all_available_years[-1]}"
                    elif len(all_available_years) == 1:
                        period_text = f"{all_available_years[0]}"
                    else:
                        period_text = "Moyenne"
                else:
                    period_text = "Moyenne"
                
                st.markdown("<h5 style='text-align: center; color: #666666;'>Charge nocturne</h5>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {base_color}; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: {base_color}; font-weight: bold;'>{period_text}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(overall_base_load*1000, 1)} W</span>
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>{equipment_text}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Données insuffisantes pour afficher la charge de base")
    
    with col2:
        # Affichage du talon de consommation
        if minimum_consumption is not None and minimum_consumption >= 0:
            # Déterminer la période selon le mode de sélection
            if year_selection_mode != "Données complètes":
                selected_year = st.session_state.get('selected_single_year', "N/A")
                period_text = f"{selected_year}"
                
                # Obtenir la couleur appropriée pour l'année (différente de la charge nocturne)
                if pdf_for_analysis is not None:
                    unique_years = sorted(pdf_for_analysis.index.year.unique())
                    if selected_year in unique_years:
                        year_index = unique_years.index(selected_year)
                        # Utiliser la couleur suivante dans la palette pour différencier
                        talon_color = default_colors[(year_index + 1) % len(default_colors)]
                    else:
                        talon_color = default_colors[1]
                else:
                    talon_color = default_colors[1]
                
                # Équivalent en appareils pour le talon
                talon_equipment_text = get_equipment_equivalence(minimum_consumption * 1000)
                
                # Formatage de la date/heure du minimum absolu si disponible
                min_datetime_text = ""
                if min_datetime is not None:
                    # Formater la date et l'heure en français
                    date_str = min_datetime.strftime("%d/%m/%Y")
                    hour_str = min_datetime.strftime("%H:%M")
                    min_datetime_text = f"<div style='font-size: 0.8em; color: #999; margin-top: 8px; font-style: italic;'>Minimum absolu de consommation : {min_value:.3f} kWh le {date_str} à {hour_str}</div>"
                
                st.markdown("<h5 style='text-align: center; color: #666666;'>Charge minimale (moyenne)</h5>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {talon_color}; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: {talon_color}; font-weight: bold;'>{period_text}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(minimum_consumption*1000, 1)} W</span>
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>{talon_equipment_text}</div>
                    {min_datetime_text}
                </div>
                """, unsafe_allow_html=True)
                
                # Avertissement spécifique pour le mode année unique
                if min_datetime is not None:
                    st.warning("⚠️ **Note :** Ce minimum absolu peut être lié à un défaut temporaire de votre équipement de mesure ou à une coupure ponctuelle. Vérifiez si cette valeur semble cohérente avec votre installation.")
                
                # Vérifier si la charge minimale est de 0 et afficher un avertissement
                if minimum_consumption == 0:
                    st.error("⚠️ **Attention :** Une charge minimale de 0W détectée ! Cela peut indiquer une incohérence dans votre fichier de données ou une erreur de mesure de votre compteur. Veuillez vérifier vos données d'origine.")
                
            else:
                # Mode données complètes - afficher simplement la période couverte
                if pdf_for_analysis is not None:
                    # Obtenir TOUTES les années disponibles dans le fichier
                    available_years = sorted(pdf_for_analysis.index.year.unique().tolist())
                    
                    # Déterminer la période selon les années disponibles
                    if len(available_years) >= 2:
                        period_text = f"{available_years[0]}-{available_years[-1]}"
                    elif len(available_years) == 1:
                        period_text = f"{available_years[0]}"
                    else:
                        period_text = "Moyenne"
                else:
                    period_text = "Moyenne"
                
                # Équivalent en appareils pour le talon
                talon_equipment_text = get_equipment_equivalence(minimum_consumption * 1000)
                
                # Formatage de la date/heure du minimum absolu si disponible
                min_datetime_text = ""
                if min_datetime is not None:
                    # Formater la date et l'heure en français
                    date_str = min_datetime.strftime("%d/%m/%Y")
                    hour_str = min_datetime.strftime("%H:%M")
                    min_datetime_text = f"<div style='font-size: 0.8em; color: #999; margin-top: 8px; font-style: italic;'>Minimum absolu de consommation : {min_value:.3f} kWh le {date_str} à {hour_str}</div>"
                
                st.markdown("<h5 style='text-align: center; color: #666666;'>Charge minimale</h5>", unsafe_allow_html=True)
                
                # Affichage sans tendance
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; border-left: 4px solid #E91E63; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: #E91E63; font-weight: bold;'>{period_text}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(minimum_consumption*1000, 1)} W</span>
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>{talon_equipment_text}</div>
                    {min_datetime_text}
                </div>
                """, unsafe_allow_html=True)
                
                # Avertissement spécifique pour le mode données complètes
                if min_datetime is not None:
                    st.warning("⚠️ **Note :** Ce minimum absolu peut être lié à un défaut temporaire de votre équipement de mesure ou à une coupure ponctuelle. Vérifiez si cette valeur semble cohérente avec votre installation.")
                
                # Vérifier si la charge minimale est de 0 et afficher un avertissement (mode données complètes)
                if minimum_consumption == 0:
                    st.error("⚠️ **Attention :** Une charge minimale de 0W détectée ! Cela peut indiquer une incohérence dans votre fichier de données ou une erreur de mesure de votre compteur. Veuillez vérifier vos données d'origine.")
                
        else:
            # Afficher un message d'erreur seulement si les données ne sont pas disponibles
            if pdf_for_analysis is None:
                st.error("Aucune donnée disponible pour calculer le talon de consommation")
            else:
                st.error("Impossible de calculer le talon de consommation - données invalides")
    
    # Afficher la tendance (sous les deux cartes) - SEULEMENT si 2+ années complètes disponibles
    # La logique de filtrage des années complètes est maintenant faite dans calculate_base_load()
    if len(years) >= 2 and len(base_loads) >= 2:
        # Les années dans years sont déjà filtrées pour être complètes et récentes
        first_year_for_trend = years[0]
        last_year_for_trend = years[-1]
        
        # Les valeurs correspondantes sont dans base_loads (sans la moyenne globale à la fin)
        first_year_value = base_loads[0]
        last_year_value = base_loads[-1] if len(base_loads) == len(years) else base_loads[-2]
        
        # Calcul de la variation
        change_w = (last_year_value - first_year_value) * 1000  # Conversion en W
        change_percent = ((last_year_value - first_year_value) / first_year_value) * 100 if first_year_value != 0 else 0
        
        # Détermination de la tendance
        if abs(change_percent) < 10:
            trend_icon = "➡️"
            trend_text = "stable"
            trend_color = "#3498db"
        elif change_percent > 0:
            trend_icon = "📈"
            trend_text = "en augmentation"
            trend_color = "#e74c3c"
        else:
            trend_icon = "📉" 
            trend_text = "en diminution"
            trend_color = "#27ae60"
        
        # Affichage de la tendance avec fond blanc
        st.markdown(f"""
        <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="margin-bottom: 10px;">
                <strong style="color: #333;">Tendance globale de votre charge nocturne : <span style="color: {trend_color}; font-weight: bold;">{trend_icon} {trend_text.title()}</span></strong>
                <br>
                <span style="font-size: 0.9em; color: #666;">
                    {change_w:+.1f} W ({change_percent:+.1f}%) entre {first_year_for_trend} et {last_year_for_trend}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Pas assez d'années complètes - afficher un message informatif
        st.markdown("""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #e0e0e0;">
            <div style="text-align: center; color: #666; font-style: italic;">
                ℹ️ La tendance d'évolution n'est disponible qu'avec au moins 2 années complètes de données
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Expander avec les détails sur la charge de base et les couleurs des tendances
    tooltip_info("Information")
    with st.expander("Comment interpréter votre charge nocturne et votre charge minimale ?"):
        st.markdown("""
        ### Qu'est-ce que la charge nocturne ?  
                    
        Il s'agit de la consommation moyenne durant les heures nocturnes (1h à 5h du matin), calculée en puissance (Watts).  
        
        La charge nocturne représente la consommation électrique minimale de votre foyer ou entreprise, même lorsque la plupart des appareils sont éteints. 
        
        **Pourquoi cette période ?** Il s'agit de la consommation mesurée entre 1h et 5h du matin. En effet, pendant cette période nos activités sont en principe au minimum, ce qui permet d'isoler la consommation des appareils qui fonctionnent en permanence (réfrigérateurs, congélateurs, appareils en veille, etc.) ou bien détecter des anomalies !
        
        ### Méthode de calcul exacte de la charge nocturne
        
        **Mode année unique :** 
        1. Somme de tous les quarts d'heure de consommation entre 1h et 5h du matin sur l'année sélectionnée
        2. Division par 16 (4 quarts d'heure × 4 heures) pour obtenir la puissance moyenne horaire équivalente
        3. Division par le nombre de jours pour obtenir la moyenne quotidienne
        
        **Mode données complètes :** 
        1. Somme de tous les quarts d'heure de consommation entre 1h et 5h du matin sur toute la période sélectionnée
        2. Division par 16 (4 quarts d'heure × 4 heures) pour obtenir la puissance moyenne horaire équivalente
        3. Division par le nombre total de jours pour obtenir la moyenne globale
        4. Affichage de la tendance uniquement si au moins 2 années complètes sont détectées (comparaison entre les deux années complètes les plus récentes)
        
        ### Qu'est-ce que la charge minimale (talon de consommation) ? 
        
        Le talon de consommation correspond à la **moyenne des quarts d'heure minimums quotidiens** sur la période analysée. C'est le minimum moyen de votre consommation électrique.  
        
        ### Méthode de calcul exacte de la charge minimale
        
        **Mode année unique :** Calcul de la moyenne de tous les minimums quotidiens (quart d'heure le plus faible de chaque jour) sur l'année sélectionnée.
        
        **Mode données complètes :** Calcul direct de la moyenne de tous les minimums quotidiens sur l'ensemble de la période disponible.
                            
        **Différence avec la charge nocturne :** Alors que la charge nocturne est une moyenne sur une période spécifique (1h-5h), la charge minimale représente votre niveau de consommation le plus bas en moyenne quotidienne. C'est ce que consomme votre ménage au minimum en tout temps.  
                
        ### Comment interpréter ces valeurs ?
        
        - Une charge de base élevée peut indiquer des appareils en veille consommant beaucoup d'énergie
        - Une augmentation de la charge de base au fil des ans peut signaler l'ajout d'appareils électriques toujours alimentés
        - Une charge minimale stable et basse indique une bonne maîtrise des consommations de veille
        - Un écart important entre charge de base et charge minimale peut révéler des variations dans le fonctionnement des appareils
        - Réduire votre charge de base est un moyen efficace d'économiser de l'énergie
        - **Un talon très bas peut indiquer une bonne maîtrise des consommations de veille et à l'inverse, un talon élevé mérite de réaliser un audit plus spécifique, contactez un expert SIE SA afin d'en savoir plus !**
        
        ### Exemples d'équipements pour vous positionner
        
        **Appareils de référence :**
        - **Box wifi** : environ 10W de consommation continue
        - **Réfrigérateur** : environ 150W de consommation continue
        
        **Exemples concrets :**
        - **50W** → Équivalent à 5 box wifi
        - **150W** → Équivalent à 1 réfrigérateur standard
        - **200W** → Équivalent à 1 réfrigérateur + 5 box wifi
        
        💡 **Info :** Une charge de base entre 50W et 150W est généralement considérée comme normale pour un foyer.
        
        ### Interprétation des tendances et couleurs
        
        - 🟢 **Tendance en diminution (vert)** : Votre charge de base diminue, c'est bon signe ! Cela peut indiquer une meilleure gestion des appareils en veille ou des équipements plus efficaces
        - 🔵 **Tendance stable (bleu)** : Votre charge de base reste constante, votre consommation de base est maîtrisée
        - 🔴 **Tendance en augmentation (rouge)** : Votre charge de base augmente, cela peut signaler l'ajout d'appareils, une dégradation de l'efficacité énergétique, ou un équipement déréglé qui nécessite de la maintenance
        """)
    
    # Afficher la position par rapport au groupe si disponible et si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type == "Particulier" and get_user_feature_position is not None:
        position_data = get_user_feature_position('base_load')
        if position_data is not None:
            position_percentile, user_value, cluster_id = position_data
            
            # Fonction pour déterminer l'emoji, statut et couleur selon les mêmes critères que les ratios
            def get_status_info(percentile):
                if percentile < 0:
                    emoji = "🟢"
                    status = "Charge de base plus faible que la médiane"
                    color = "#27ae60"
                    bg_color = "#d5f4e6"
                    border_color = "#27ae60"
                    description = "Votre charge nocturne est plus faible que la médiane de votre groupe"
                elif percentile < 20:
                    emoji = "🟡"
                    status = "Charge de base modérément plus élevée"
                    color = "#f39c12"
                    bg_color = "#fef9e7"
                    border_color = "#f39c12"
                    description = "Votre charge nocturne est modérément plus élevée que la médiane de votre groupe"
                else:
                    emoji = "🔴"
                    status = "Charge de base plus élevée que la médiane"
                    color = "#e74c3c"
                    bg_color = "#fdf2f2"
                    border_color = "#e74c3c"
                    description = "Votre charge nocturne est nettement plus élevée que la médiane de votre groupe"
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
                    <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} Charge nocturne</span>
                    <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{position_percentile:+.0f}%</span>
                </div>
                <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                    {description}
                </div>
            </div>
            """, unsafe_allow_html=True)

            tooltip_info("Information")
            with st.expander("Comment interpréter ces pourcentages ?", expanded=False):
                st.markdown("""
                    **Échelle par rapport à la médiane :**
        
                    **🟢 -50% à 0%** : Votre consommation est inférieure à la médiane  
                    **🟡 0% à +20%** : Votre consommation est légèrement supérieure à la médiane  
                    **🔴 +20% à +50%** : Votre consommation est nettement supérieure à la médiane (à optimiser)  
                    """)

# ============================================================================
# FIN DU MODULE BASE_LOAD - ANALYSE DE LA CHARGE NOCTURNE ET TALON
# ============================================================================
# 
# Ce module constitue l'un des piliers de l'analyse énergétique DataWatt,
# fournissant des indicateurs clés pour :
# - Le diagnostic des consommations de veille
# - L'identification d'anomalies de fonctionnement
# - L'évaluation du potentiel d'économies d'énergie
# - Le positionnement par rapport aux groupes de référence
#
# Intégration avec DataWatt :
# - Dashboard principal : Cartes synthétiques de charge nocturne
# - Clustering : Variable discriminante pour classification des profils
# - Analyses personnalisées : Base pour recommandations d'optimisation
# - Interface utilisateur : Adaptation automatique selon les modes de sélection
#
# Évolutions futures possibles :
# - Détection automatique d'anomalies avec alertes intelligentes
# - Intégration de données météorologiques pour affiner l'analyse
# - Prédiction de la charge de base selon les équipements déclarés
# - Recommandations automatisées d'optimisation par IA
# ============================================================================