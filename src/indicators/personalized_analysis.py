# ============================================================================
# MODULE D'ANALYSE PERSONNALISÉE - DataWatt
# ============================================================================
# 
# OBJECTIF PRINCIPAL:
# Module central pour l'onglet "ANALYSE PERSONNALISÉE" de l'application web
# DataWatt, fournissant des analyses énergétiques contextuelles adaptées au
# profil spécifique de chaque utilisateur (surface, nombre de personnes, 
# équipements énergétiques).
#
# CONTEXTE D'UTILISATION:
# Ces fonctions s'affichent dans l'onglet dédié "ANALYSE PERSONNALISÉE" après 
# que l'utilisateur ait rempli le formulaire de configuration avec ses 
# informations personnelles (surface du logement, composition du ménage, 
# type de chauffage, etc.).
#
# FONCTIONNALITÉS PRINCIPALES:
#
# 1. **ANALYSE PAR SURFACE (display_surface_consumption)**:
#    • Calcul de consommation par m² avec comparaisons intelligentes
#    • Standards Minergie classiques (33/56 kWh/m²/an) pour chauffage non-électrique
#    • Références personnalisées selon profil énergétique :
#      - Chauffage électrique + ECS électrique : 100 kWh/m²/an
#      - Chauffage électrique OU ECS électrique : 80 kWh/m²/an
#    • Visualisations en barres comparatives avec échelle adaptative
#    • Analyse de tendance entre années complètes (si données multi-années)
#    • Messages d'avertissement pour comparaisons désagrégées vs Minergie
#
# 2. **ANALYSE PAR MÉNAGE (display_consumption)**:
#    • Comparaison avec références OFEN segmentées par profil exact
#    • Bases de données CSV spécialisées (appartements vs maisons)
#    • Matrice de références croisant :
#      - Type logement (Appartement/Maison)
#      - Type chauffage (Électrique/Non électrique/PAC)
#      - Type ECS (Électrique/Non électrique)
#      - Nombre de personnes (1-6+, extrapolation au-delà)
#    • Validation sur années complètes uniquement pour comparaisons fiables
#    • Calculs de consommation par habitant avec retour de métriques
#
# 3. **SYSTÈME DE RECOMMANDATIONS (generate_personalized_recommendations) A METTRE A JOUR**:
#    • Algorithme d'analyse croisée des indicateurs énergétiques
#    • Classification par priorité (Haute/Moyenne/Basse)
#    • Calcul d'économies potentielles en % et CHF
#    • Recommandations basées sur :
#      - Charge de base nocturne
#      - Ratios temporels (jour/nuit, semaine/weekend)
#      - Tendances de consommation
#      - Comparaisons aux standards nationaux
#      - Présence/absence d'installation solaire
#
# 4. **LOGIQUES MÉTIER AVANCÉES**:
#    • Détection automatique des années complètes vs partielles
#    • Adaptation des analyses selon mode (année unique vs multi-années)
#    • Gestion intelligente des références selon équipements déclarés
#    • Extrapolation pour ménages >6 personnes (base OFEN limitée)
#    • Validation de cohérence des données avant analyses
#
# 5. **INTERFACE UTILISATEUR OPTIMISÉE**:
#    • Barres de progression visuelles avec valeurs intégrées
#    • Codes couleur adaptatifs (vert=bon, orange=moyen, rouge=élevé)
#    • Liens contextuels vers documentation officielle (Minergie, OFEN)
#    • Expandeurs détaillés pour explications méthodologiques
#    • Messages d'alerte pour données insuffisantes ou incohérentes
#
# ARCHITECTURE TECHNIQUE:
# - Intégration avec session state Streamlit pour persistance des paramètres
# - Lecture de bases de données CSV OFEN pour références nationales
# - Calculs statistiques robustes avec gestion des cas limites
# - Formatage HTML/CSS intégré pour rendu visuel optimal
# - Gestion d'erreurs gracieuse avec fallback sur valeurs par défaut
#
# SOURCES DE DONNÉES:
# - Fichiers CSV OFEN : valeurs_appartements.csv, valeurs_maison.csv
# - Standards Minergie officiels pour comparaisons énergétiques
# - Références littérature pour bâtiments administratifs (comparaisons désagrégées)
# - Session state utilisateur pour paramètres personnels et données de consommation
#
# ============================================================================

# IMPORTS AU CAS OÙ

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

### ANALYSE PERSONNALISEE DU USER, DANS UN NOUVEL ONGLET

def get_consumption_column(df):
    """Determine which consumption column to use"""
    return 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in df.columns else 'Consumption (kWh)'


def display_surface_consumption(df, surface, years):
    """
    Calcule et affiche la consommation par surface de manière stylisée avec comparaison aux standards Minergie
    """
    # Determine which consumption column to use
    consumption_col = get_consumption_column(df)
      
    # Déterminer le mode d'analyse selon la sélection d'années
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    years_to_use = st.session_state.get('years_to_use', [])
    available_years = sorted([year for year in df.index.year.unique() if year in years_to_use])
    
    # Calculer les valeurs annuelles pour toutes les années disponibles
    yearly_values = {}
    for year in available_years:
        year_data = df[df.index.year == year]
        total_year = year_data[consumption_col].sum()
        yearly_values[year] = total_year / surface
    
    # Créer la liste pour la tendance
    surfc_list = [yearly_values[year] for year in available_years]
    
    if year_selection_mode != "Données complètes":
        # Mode année unique - afficher seulement la valeur pour l'année sélectionnée
        selected_year = st.session_state.get('selected_single_year', available_years[0] if available_years else None)
        if selected_year and selected_year in yearly_values:
            yearly_surface_consumption = yearly_values[selected_year]
            period_text = f"({selected_year})"
        else:
            yearly_surface_consumption = 0
            period_text = "(Aucune donnée)"
        show_trend = False  # Pas de tendance en mode année unique
    else:
        # Mode données complètes - calculer sur toute la période disponible
        if available_years:
            # Calculer la consommation totale sur toute la période
            total_consumption_all_period = df[consumption_col].sum()
            # Calculer le nombre total de jours dans les données
            total_days = (df.index.max() - df.index.min()).days + 1
            # Calculer la consommation annuelle équivalente (365 jours)
            yearly_surface_consumption = (total_consumption_all_period * 365 / total_days) / surface
            period_text = f"({min(available_years)}-{max(available_years)})"
            
            # Vérifier les années complètes pour la tendance
            years_completeness = st.session_state.get('years_completeness', {})
            complete_years = [year for year in available_years 
                            if year in years_completeness and years_completeness[year] >= 100]
            # Prendre les deux années complètes les plus récentes pour la tendance
            recent_complete_years = sorted(complete_years)[-2:] if len(complete_years) >= 2 else []
            show_trend = len(recent_complete_years) >= 2
        else:
            yearly_surface_consumption = 0
            period_text = "(Aucune donnée)"
            show_trend = False
    
    # Récupérer les informations de chauffage et ECS depuis le formulaire
    heating_type = st.session_state.get('heating_type', 'Non électrique')
    has_ecs = st.session_state.get('has_ecs', 'Non électrique')
    
    # Déterminer la référence de comparaison selon le profil énergétique
    if heating_type == "Électrique" and has_ecs == "Électrique":
        # Chauffage électrique + ECS électrique : référence à 100 kWh/m²/an
        reference_consumption = 100
        efficiency_message = "Cette comparaison inclut chauffage et eau chaude électriques"
        show_minergie_warning = False
        use_custom_comparison = True
    elif (heating_type == "Électrique" and has_ecs == "Non électrique") or (heating_type == "Non électrique" and has_ecs == "Électrique"):
        # Chauffage électrique seul OU ECS électrique seule : référence à 80 kWh/m²/an
        reference_consumption = 80
        efficiency_message = "Comparaison désagrégée par rapport aux standards Minergie complets"
        show_minergie_warning = True
        use_custom_comparison = True
    else:
        # Pas de chauffage ni ECS électrique : utiliser les standards Minergie classiques
        reference_consumption = None
        efficiency_message = ""
        show_minergie_warning = False
        use_custom_comparison = False
    
    # Déterminer l'efficacité selon le type de comparaison
    if use_custom_comparison:
        # Comparaison personnalisée selon le profil énergétique
        if yearly_surface_consumption < reference_consumption * 0.7:  # 70% de la référence
            efficiency = f"excellente (bien en-dessous de {reference_consumption} kWh/m²/an)"
            efficiency_color = "#228B22"  # Forest green
        elif yearly_surface_consumption < reference_consumption:
            efficiency = f"bonne (en-dessous de {reference_consumption} kWh/m²/an)"
            efficiency_color = "#FFA500"  # Orange
        else:
            efficiency = f"élevée (au-dessus de {reference_consumption} kWh/m²/an)"
            efficiency_color = "#DC143C"  # Crimson
        
        # Message de comparaison personnalisé
        if yearly_surface_consumption < reference_consumption:
            minergie_comparison = f"Votre consommation est en-dessous de la référence pour votre profil énergétique ({reference_consumption} kWh/m²/an)."
        else:
            minergie_comparison = f"Votre consommation dépasse la référence pour votre profil énergétique ({reference_consumption} kWh/m²/an)."
    else:
        # Comparaison Minergie classique (logique originale)
        if yearly_surface_consumption < 33:
            efficiency = "conforme au standard Minergie pour nouvelles constructions"
            efficiency_color = "#228B22"  # Forest green
        elif yearly_surface_consumption < 56:
            efficiency = "conforme au standard Minergie pour rénovations"
            efficiency_color = "#FFA500"  # Orange
        else:
            efficiency = "au-dessus des standards Minergie"
            efficiency_color = "#DC143C"  # Crimson
        
        # Compare to Minergie standards
        if yearly_surface_consumption < 33:
            minergie_comparison = "Votre consommation est inférieure au standard Minergie pour les nouvelles constructions (33 kWh/m²/an)."
        elif yearly_surface_consumption < 56:
            minergie_comparison = "Votre consommation est inférieure au standard Minergie pour les rénovations (56 kWh/m²/an), mais supérieure à celui des nouvelles constructions (33 kWh/m²/an)."
        else:
            minergie_comparison = "Votre consommation dépasse les standards Minergie recommandés (33-56 kWh/m²/an)."
    
    
    # Stylish display
    if yearly_surface_consumption > 0:
        st.markdown(f"""
        <div style='padding: 15px; margin: 10px 0; border-left: 4px solid #ff1100; background-color: #f8f9fa; border-radius: 5px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='color: #333; font-weight: bold;'>Total {period_text}</span>
                <span style='font-size: 1.2em; font-weight: bold; color: #333;'>{yearly_surface_consumption:.0f} kWh/m²/an</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 8px;'>Consommation {efficiency}</div>
            <div style='font-size: 0.85em; color: #888; margin-top: 4px; font-style: italic;'>{efficiency_message}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Analyse de tendance si multiple années et mode données complètes
        if show_trend and year_selection_mode == "Données complètes" and len(recent_complete_years) >= 2:
            # Calculer la tendance entre les deux années complètes les plus récentes
            first_year = recent_complete_years[0]
            last_year = recent_complete_years[-1]
            first_year_value = yearly_values[first_year]
            last_year_value = yearly_values[last_year]
            
            # Calcul de la variation
            change_absolute = last_year_value - first_year_value
            change_percent = ((last_year_value - first_year_value) / first_year_value) * 100 if first_year_value != 0 else 0
            
            # Détermination de la tendance selon les mêmes seuils que dans indic_func
            if abs(change_percent) < 10:
                trend_icon = "➡️"
                trend_text = "stable"
                trend_color = "#3498db"
            elif change_percent > 0:
                trend_icon = "⬆️"
                trend_text = "en augmentation"
                trend_color = "#e74c3c"
            else:
                trend_icon = "⬇️" 
                trend_text = "en diminution"
                trend_color = "#27ae60"
            
            # Affichage de la tendance
            st.markdown(f"""
            <div style='padding: 15px; margin: 10px 0; border-left: 4px solid {trend_color}; background-color: #f8f9fa; border-radius: 5px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <span style='color: {trend_color}; font-weight: bold;'>Tendance par m² : {trend_text.title()}</span>
                    <span style='color: {trend_color}; font-weight: bold; margin-left: 10px;'>{trend_icon} {change_percent:+.1f}% vs {first_year}</span>
                </div>
                <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                    {change_absolute:+.1f} kWh/m²/an entre {first_year} et {last_year} (années complètes)
                </div>
            </div>
            """, unsafe_allow_html=True)  

        value_length_bar = 120 if use_custom_comparison and reference_consumption == 100 else 80

        # Display comparison visual selon le type de référence
        if use_custom_comparison:
            # Comparaison personnalisée
            st.markdown(f"""
                <div style="margin: 10px 0 8px 0; text-align: center;">
                <h5 style="color: #333; font-weight: bold; font-size: 0.9em; margin: 0; letter-spacing: 1px; text-transform: uppercase;">
                Votre position par rapport à votre profil énergétique
                </h5>
                </div>
                """, unsafe_allow_html=True)
            
            # Votre consommation
            bar_width_percent = min(yearly_surface_consumption/value_length_bar*100, 100)
            text_position = "left: 10px;" if bar_width_percent < 25 else "right: 10px;"
            
            st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="width: 180px; font-size: 0.9em;">Votre consommation</span>
                        <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: visible; position: relative;">
                            <div style="width: {bar_width_percent}%; background-color: #ff1100; height: 100%; position: relative;">
                            </div>
                            <span style="position: absolute; {text_position} top: 50%; transform: translateY(-50%); color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; white-space: nowrap;">{yearly_surface_consumption:.1f} kWh/m²</span>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
            
            # Référence selon le profil
            ref_color = "#4CAF50" if reference_consumption == 80 else "#2196F3"
            ref_label = f"Référence profil énergétique"
            
            st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="width: 180px; font-size: 0.9em;">{ref_label}</span>
                        <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: hidden;">
                            <div style="width: {reference_consumption/value_length_bar*100}%; background-color: {ref_color}; height: 100%; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px;">
                                <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;">{reference_consumption} kWh/m²</span>
                            </div>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
                
        else:
            # Comparaison Minergie classique (logique originale)
            st.markdown("""
                <div style="margin: 10px 0 8px 0; text-align: center;">
                <h5 style="color: #333; font-weight: bold; font-size: 0.9em; margin: 0; letter-spacing: 1px; text-transform: uppercase;">
                Votre position par rapport aux standards Minergie
                </h5>
                </div>
                """, unsafe_allow_html=True)
            
            # Votre consommation - avec valeur à l'intérieur et bordure noire
            bar_width_percent = min(yearly_surface_consumption/value_length_bar*100, 100)
            # Si la barre est trop petite (moins de 25%), on met le texte à gauche
            text_position = "left: 10px;" if bar_width_percent < 25 else "right: 10px;"
            
            st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="width: 180px; font-size: 0.9em;">Votre consommation</span>
                        <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: visible; position: relative;">
                            <div style="width: {bar_width_percent}%; background-color: #ff1100; height: 100%; position: relative;">
                            </div>
                            <span style="position: absolute; {text_position} top: 50%; transform: translateY(-50%); color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; white-space: nowrap;">{yearly_surface_consumption:.1f} kWh/m²</span>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
            # Minergie (neuf) - avec valeur à l'intérieur et bordure noire
            st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="width: 180px; font-size: 0.9em;">Minergie (neuf)</span>
                        <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: hidden;">
                            <div style="width: {33/value_length_bar*100}%; background-color: #4CAF50; height: 100%; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px;">
                                <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;">33 kWh/m²</span>
                            </div>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
            
            # Minergie (rénové) - avec valeur à l'intérieur et bordure noire
            st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="width: 180px; font-size: 0.9em;">Minergie (rénové)</span>
                        <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: hidden;">
                            <div style="width: {56/value_length_bar*100}%; background-color: #2196F3; height: 100%; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px;">
                                <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;">56 kWh/m²</span>
                            </div>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
            
            # Construction standard - avec valeur à l'intérieur et bordure noire
            st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="width: 180px; font-size: 0.9em;">Construction standard</span>
                        <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: hidden;">
                            <div style="width: {42/value_length_bar*100}%; background-color: #FFC107; height: 100%; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px;">
                                <span style="color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;">42 kWh/m²</span>
                            </div>
                        </div>
                    </div>
            """, unsafe_allow_html=True)
        
        # Afficher l'avertissement après les barres si nécessaire
        if show_minergie_warning:
            st.markdown(f"""
            <div style='padding: 12px; margin: 10px 0; border-left: 4px solid #FFA500; background-color: #fff8e1; border-radius: 5px;'>
                <div style='font-size: 0.9em; color: #e65100; font-weight: bold;'>⚠️ Note importante</div>
                <div style='font-size: 0.85em; color: #bf360c; margin-top: 4px;'>
                    Cette comparaison est désagrégée par rapport à la documentation Minergie officielle et peut manquer de précision. 
                    Les standards Minergie incluent généralement l'ensemble des consommations énergétiques du bâtiment.
                </div>
            </div>
            """, unsafe_allow_html=True)
    
        # Lien vers Minergie
        st.markdown("""
                <div style="text-align: center; margin-top: 15px;">
                    <a href="https://www.minergie.ch/fr/" target="_blank" style="display: inline-block; text-decoration: none; color: #1E88E5; font-weight: bold; padding: 8px 15px; border: 1px solid #1E88E5; border-radius: 5px;">Découvrir les standards Minergie →</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    tooltip_info("Information")
    
    # Expander with detailed explanation
    with st.expander("À propos de la consommation par m² et des standards Minergie"):
        if use_custom_comparison:
            st.markdown(f"""
            ### Qu'est-ce que la consommation par m² ?
            
            Cet indicateur mesure votre consommation électrique annuelle par mètre carré de surface. C'est un standard couramment utilisé pour comparer l'efficacité énergétique entre différents bâtiments. Ici les références utilisent des valeurs de la littérature pour un bâtiment admnistratif, donc attention à l'interprétation de la comparaison qui peut être faussée. Contactez SIE SA en cas de doutes.
            
            ### Votre profil énergétique
            
            Selon votre configuration (Chauffage : {heating_type}, ECS : {has_ecs}), nous utilisons une référence adaptée :
            
            - **Référence pour votre profil** : {reference_consumption} kWh/m²/an
            
            {'⚠️ **Note importante** : Cette comparaison est désagrégée par rapport à la documentation Minergie officielle car elle ne prend en compte que les équipements électriques que vous avez spécifiés. Les standards Minergie incluent généralement l\'ensemble des consommations énergétiques du bâtiment (chauffage, eau chaude, ventilation, etc.).' if show_minergie_warning else ''}
            
            ### Pourquoi cette approche ?
            
            Les standards Minergie officiels concernent l'énergie totale d'un bâtiment (chauffage, eau chaude, ventilation, etc.). Lorsque votre installation inclut des équipements électriques spécifiques, nous adaptons la comparaison pour une évaluation plus pertinente de votre consommation électrique.
            
            Vous trouverez plus de détails sur le site Minergie ou en contactant SIE SA afin de mieux comprendre votre consommation ou si vous notez une anomalie.
            """)
        else:
            st.markdown("""
            ### Qu'est-ce que la consommation par m² ?
            
            Cet indicateur mesure votre consommation électrique annuelle par mètre carré de surface. C'est un standard couramment utilisé pour comparer l'efficacité énergétique entre différents bâtiments et par rapport à des standards tel que le Minergie.
            
            ### Standards Minergie (kWh/m²/an)
            
            - **Nouvelle construction Minergie** : max. 33 kWh/m²/an
            - **Rénovation Minergie** : max. 56 kWh/m²/an
            - **Nouvelle construction standard** : environ 42 kWh/m²/an
            - **Bâtiment non rénové** : souvent 4 fois plus (>170 kWh/m²/an)
            
            Les standards Minergie-P et Minergie-A imposent des valeurs encore plus basses.
                    
            Les standards Minergie concernent en général l'énergie totale (chauffage, eau chaude, ventilation, etc.). Ici, selon vos choix dans le formulaire les valeurs qui apparaissent prennent en compte ou non le chauffage. Vous trouverez plus de détails sur le site Minergie ou en contactant SIE SA afin de mieux comprendre votre consommation ou si vous notez une anomalie.
            """)
    
    
    return yearly_surface_consumption, surfc_list

def display_consumption(df, num_people, housing_type=None, heating_type=None, has_ecs=None):
    """
    Affiche une comparaison simple entre la consommation du ménage et la référence suisse selon le profil
    Affiche uniquement si au moins une année complète est disponible.
    
    Args:
        df: DataFrame with consumption data
        num_people: Number of people in the household
        housing_type: Type of housing ("Appartement" or "Maison")
        heating_type: Type of heating ("Électrique", "Non électrique", "PAC")
        has_ecs: Type of water heating ("Électrique", "Non électrique")
    """
    # Determine which consumption column to use
    consumption_col = get_consumption_column(df)

    # Vérifier les années complètes disponibles
    complete_years = st.session_state.get('complete_years', [])
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    years_completeness = st.session_state.get('years_completeness', {})
    
    # Déterminer quelle année utiliser selon le mode
    year_to_use = None
    
    if year_selection_mode != "Données complètes":
        # Mode année unique - vérifier si l'année sélectionnée est complète
        selected_year = st.session_state.get('selected_single_year')
        if selected_year and years_completeness.get(selected_year, 0) >= 100:
            year_to_use = selected_year
    else:
        # Mode données complètes - utiliser l'année complète la plus récente
        if complete_years:
            year_to_use = max(complete_years)
    
    # Si aucune année complète disponible, afficher un message d'information
    if year_to_use is None:
        st.info("⚠️ Cette analyse nécessite au moins une année complète de données. " +
                "Les comparaisons avec les références suisses ne sont disponibles qu'avec des données annuelles complètes.")
        
        # Retourner des valeurs par défaut
        return 0, 0

    # Charger les données de référence appropriées selon le type de logement
    try:
        if housing_type == "Appartement":
            reference_df = pd.read_csv('src/database/valeurs_appartements.csv')
        else:  # Maison
            reference_df = pd.read_csv('src/database/valeurs_maison.csv')
    except FileNotFoundError:
        st.error("Fichiers de référence non trouvés. Utilisation de valeurs par défaut.")
        # Valeurs par défaut si les fichiers ne sont pas trouvés
        if housing_type == "Appartement":
            swiss_avg_consumption = 2200 * (num_people / 2)
        else:
            swiss_avg_consumption = 3000 * (num_people / 2)
    else:
        # Déterminer la colonne appropriée selon le type de chauffage et ECS
        # Ligne 1 : Chauffage (Electrique, Electrique, Non electrique, Non electrique, PAC, PAC)
        # Ligne 2 : ECS (Electrique, Non electrique, Electrique, Non electrique, Electrique, Non electrique)
        
        column_index = None
        
        # Trouver la bonne colonne selon le profil chauffage + ECS
        if heating_type == "Électrique" and has_ecs == "Électrique":
            column_index = 1  # Colonne "Electrique" avec ECS "Electrique"
        elif heating_type == "Électrique" and has_ecs == "Non électrique":
            column_index = 2  # Colonne "Electrique" avec ECS "Non electrique"
        elif heating_type == "Non électrique" and has_ecs == "Électrique":
            column_index = 3  # Colonne "Non electrique" avec ECS "Electrique"
        elif heating_type == "Non électrique" and has_ecs == "Non électrique":
            column_index = 4  # Colonne "Non electrique" avec ECS "Non electrique"
        elif heating_type == "PAC" and has_ecs == "Électrique":
            column_index = 5  # Colonne "PAC" avec ECS "Electrique"
        elif heating_type == "PAC" and has_ecs == "Non électrique":
            column_index = 6  # Colonne "PAC" avec ECS "Non electrique"
        
        # Récupérer la valeur pour le nombre de personnes
        try:
            if column_index is not None:
                # Structure CSV: ligne 0=headers chauffage, ligne 1=headers ECS, ligne 2=1 personne, etc.
                row_index = num_people # + 1
                
                # Vérifier que l'index est dans les limites (max 6 personnes dans le CSV = ligne 7)
                if row_index <= 7 and row_index < len(reference_df) and column_index < len(reference_df.columns):
                    # Récupérer la valeur et la convertir (enlever la virgule et convertir en float)
                    swiss_value_str = str(reference_df.iloc[row_index, column_index])
                    swiss_avg_consumption = float(swiss_value_str.replace(',', '.').replace('"', '')) * 1000  # Convertir en kWh
                else:
                    # Si le nombre de personnes dépasse 6, extrapoler à partir de la valeur pour 6 personnes
                    last_row_index = 7  # Ligne 7 = 6 personnes
                    if last_row_index < len(reference_df) and column_index < len(reference_df.columns):
                        swiss_value_str = str(reference_df.iloc[last_row_index, column_index])
                        base_value = float(swiss_value_str.replace(',', '.').replace('"', '')) * 1000
                        # Extrapolation linéaire simple (ajouter ~500 kWh par personne supplémentaire)
                        swiss_avg_consumption = base_value + (num_people - 6) * 500
                    else:
                        # Valeur par défaut si même la ligne 6 personnes n'existe pas
                        if housing_type == "Appartement":
                            swiss_avg_consumption = 2200 * (num_people / 2)
                        else:
                            swiss_avg_consumption = 3000 * (num_people / 2)
            else:
                # Valeur par défaut si profil non trouvé
                if housing_type == "Appartement":
                    swiss_avg_consumption = 2200 * (num_people / 2)
                else:
                    swiss_avg_consumption = 3000 * (num_people / 2)
        except Exception as e:
            st.warning(f"Erreur lors de la lecture des données de référence: {e}")
            # Valeurs par défaut
            if housing_type == "Appartement":
                swiss_avg_consumption = 2200 * (num_people / 2)
            else:
                swiss_avg_consumption = 3000 * (num_people / 2)
    
    # Utiliser l'année complète sélectionnée
    year_data = df[df.index.year == year_to_use]
    total_year = year_data[consumption_col].sum()
    period_text = f"({year_to_use})"
    
    # Calculer les valeurs par personne pour retour de fonction
    daily_consumption_per_capita = (total_year / 365) / num_people if num_people > 0 else 0
    yearly_consumption_per_capita = total_year / num_people if num_people > 0 else 0
    
    # Titre de la section de comparaison avec le profil spécifique
    st.markdown(f"""
            <div style="margin: 10px 0 8px 0; text-align: center;">
            <h5 style="color: #333; font-weight: bold; font-size: 0.9em; margin: 0; letter-spacing: 1px; text-transform: uppercase;">
            Comparaison avec un {housing_type.lower()} suisse de votre profil
            </h5>
            </div>
            """, unsafe_allow_html=True)
    
    # Informations sur le profil de référence et l'année utilisée
    st.markdown(f"""
    <p style='text-align: center; color: #888; font-size: 0.9em; margin-bottom: 20px;'>
        Profil de référence : {housing_type} • {heating_type} • ECS {has_ecs} • {num_people} personne{'s' if num_people > 1 else ''}<br>
        <span style='color: #2e7d32; font-weight: bold;'>Données {year_to_use} (année complète)</span>
    </p>
    """, unsafe_allow_html=True)
    
    # Calculer les dimensions des barres avec gestion améliorée des petites valeurs
    max_value = max(total_year, swiss_avg_consumption) * 1.2  # Pour dimensionner les barres
    
    # Votre ménage - avec valeur à l'intérieur et gestion des petites barres
    user_bar_width_percent = min(total_year/max_value*100, 100)
    # Si la barre est trop petite (moins de 25%), on met le texte à gauche
    user_text_position = "left: 10px;" if user_bar_width_percent < 25 else "right: 10px;"
    
    st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <span style="width: 180px; font-size: 0.9em;">Votre ménage {period_text}</span>
                <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: visible; position: relative;">
                    <div style="width: {user_bar_width_percent}%; background-color: #ff1100; height: 100%; position: relative;">
                    </div>
                    <span style="position: absolute; {user_text_position} top: 50%; transform: translateY(-50%); color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; white-space: nowrap;">{total_year:.0f} kWh</span>
                </div>
            </div>
    """, unsafe_allow_html=True)
    
    # Référence suisse - avec valeur à l'intérieur et gestion des petites barres
    swiss_bar_width_percent = min(swiss_avg_consumption/max_value*100, 100)
    swiss_text_position = "left: 10px;" if swiss_bar_width_percent < 25 else "right: 10px;"
    
    st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <span style="width: 180px; font-size: 0.9em;">Référence suisse</span>
                <div style="flex-grow: 1; height: 30px; background-color: #E0E0E0; border-radius: 5px; overflow: visible; position: relative;">
                    <div style="width: {swiss_bar_width_percent}%; background-color: #1976D2; height: 100%; position: relative;">
                    </div>
                    <span style="position: absolute; {swiss_text_position} top: 50%; transform: translateY(-50%); color: white; font-weight: bold; font-size: 0.9em; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; white-space: nowrap;">{swiss_avg_consumption:.0f} kWh</span>
                </div>
            </div>
    """, unsafe_allow_html=True)
    
    # Comparer avec la référence spécifique
    if swiss_avg_consumption > 0:
        percent_diff = ((total_year - swiss_avg_consumption) / swiss_avg_consumption) * 100
        if percent_diff > 0:
            comparison_text = f"{percent_diff:.1f}% au-dessus"
            comparison_color = "#DC143C"  # Crimson for higher consumption
        elif percent_diff < 0:
            comparison_text = f"{abs(percent_diff):.1f}% en dessous"
            comparison_color = "#228B22"  # Forest green for lower consumption
        else:
            comparison_text = "équivalente"
            comparison_color = "#FFA500"  # Orange for equivalent
    else:
        comparison_text = "non disponible"
        comparison_color = "#666666"
    
    # Note de bas avec lien vers étude OFEN
    st.markdown(f"""
            <p style="font-size: 1.0em; color: #555; margin-top: 20px; font-style: italic; text-align: center; line-height: 1.5;">
                La référence suisse pour votre profil ({housing_type.lower()}, {heating_type.lower()}, ECS {has_ecs.lower()}, {num_people} personne{'s' if num_people > 1 else ''}) est de {swiss_avg_consumption:.0f} kWh/an.
                <br>Votre consommation est <span style="color: {comparison_color}; font-weight: bold;">{comparison_text}</span> de cette référence.
            </p>
            <div style="text-align: center; margin-top: 15px;">
                <a href="https://pubdb.bfe.admin.ch/fr/publication/download/10559" target="_blank" style="display: inline-block; text-decoration: none; color: #1E88E5; font-weight: bold; padding: 8px 15px; border: 1px solid #1E88E5; border-radius: 5px;">
                    Consultez l'étude de l'OFEN sur les ménages →
                </a>
            </div>
    """, unsafe_allow_html=True)
    
    tooltip_info("Information")
    
    # Expander with detailed explanation
    with st.expander("À propos de la comparaison aux standards suisses"):
        st.markdown(f"""
        ### Qu'est-ce que la comparaison personnalisée aux standards suisses ?  

        Cet indicateur vous permet de comparer la consommation annuelle de votre ménage par rapport à un ménage Suisse similaire à votre situation. 
        
        ### Selon votre profil : 
        Cette comparaison utilise des données spécifiques de l'Office fédéral de l'énergie (OFEN) pour votre profil exact :
        
        - **Type de logement** : {housing_type}
        - **Type de chauffage** : {heating_type}
        - **Eau chaude sanitaire** : {has_ecs}
        - **Nombre de personnes** : {num_people}
        - **Année analysée** : {year_to_use} (La plus récente et complète si le mode "Données complètes" est sélectionné dans la sidebar)
        - **Consommation de référence** : {swiss_avg_consumption:.0f} kWh/an pour votre profil.  

        ### Ce que permet cette approche :  
        
        Cette approche permet une comparaison plus précise que les moyennes nationales générales, car elle tient compte de vos équipements et de votre situation spécifique.
        
        Les données de référence proviennent des études de consommation des ménages suisses et sont segmentées selon le type d'équipement énergétique.
        
        **Note importante** : Cette analyse utilise uniquement les années avec des données complètes pour garantir une comparaison fiable avec les références nationales.
        
        ### Plus d'exemples entre les profils suisses :  
        [Consultez l'étude de l'OFEN sur la consommation des ménages](https://pubdb.bfe.admin.ch/fr/publication/download/10559)
        """)
    
    return daily_consumption_per_capita, yearly_consumption_per_capita


## Recommandations ## SECTION NON MISE A JOUR POUR LE MOMENT  

def generate_personalized_recommendations(base_load, ratio_weekday_weekend, ratio_day_night, 
                                          slope_base_load=0, yearly_surface_consumption=None, 
                                          daily_consumption_per_capita=None, has_solar=False):
    """
    Génère des recommandations personnalisées pour l'économie d'énergie
    basées sur l'analyse des différents indicateurs
    
    Args:
        base_load: Charge de base moyenne en kW
        ratio_weekday_weekend: Ratio de consommation semaine/weekend
        ratio_day_night: Ratio de consommation jour/nuit
        slope_base_load: Tendance de la charge de base (pente de régression)
        yearly_surface_consumption: Consommation annuelle par m² (None si non disponible)
        daily_consumption_per_capita: Consommation quotidienne par personne (None si non disponible)
        has_solar: Indique si l'utilisateur a déjà une installation solaire
    
    Returns:
        recommendations: Liste des recommandations personnalisées
    """
    recommendations = {
        "high_priority": [],
        "medium_priority": [],
        "low_priority": []
    }
    
    # --- Recommandations basées sur la charge de base ---
    if base_load > 0.3:
        if base_load > 0.5:
            recommendations["high_priority"].append({
                "title": "Réduisez votre charge de base",
                "description": "Votre charge de base est significativement élevée. Vérifiez les appareils en veille et les équipements fonctionnant la nuit.",
                "actions": [
                    "Utilisez des prises multiples avec interrupteur pour couper complètement l'alimentation",
                    "Vérifiez si des serveurs, NAS ou ordinateurs fonctionnent 24h/24",
                    "Remplacez les appareils anciens par des modèles plus économes"
                ],
                "savings": "5-15%"
            })
        else:
            recommendations["medium_priority"].append({
                "title": "Optimisez votre charge de base",
                "description": "Votre charge de base pourrait être optimisée pour économiser de l'énergie.",
                "actions": [
                    "Identifiez les appareils en veille consommant le plus",
                    "Programmez l'extinction automatique des équipements non essentiels la nuit"
                ],
                "savings": "3-8%"
            })  
    
    # --- Recommandations basées sur la consommation par personne ---
    if daily_consumption_per_capita:
        yearly_consumption_per_capita = daily_consumption_per_capita * 365
        
        if yearly_consumption_per_capita > 2000:
            recommendations["high_priority"].append({
                "title": "Réduisez votre empreinte énergétique personnelle",
                "description": "Votre consommation par personne est significativement supérieure à la moyenne suisse.",
                "actions": [
                    "Adoptez des comportements plus économes au quotidien",
                    "Remplacez les appareils énergivores par des modèles plus efficaces",
                    "Sensibilisez tous les membres du foyer aux économies d'énergie"
                ],
                "savings": "10-20%"
            })
        elif yearly_consumption_per_capita > 1500:
            recommendations["medium_priority"].append({
                "title": "Optimisez votre consommation individuelle",
                "description": "Votre consommation par personne est légèrement supérieure à la moyenne d'une maison suisse.",
                "actions": [
                    "Identifiez vos principaux postes de consommation",
                    "Adoptez des gestes simples d'économie d'énergie au quotidien"
                ],
                "savings": "5-15%"
            })
        elif yearly_consumption_per_capita > 1100:
            recommendations["low_priority"].append({
                "title": "Affinez votre efficacité énergétique",
                "description": "Votre consommation par personne est proche de la moyenne d'un appartement suisse.",
                "actions": [
                    "Optimisez l'utilisation de vos appareils électroménagers",
                    "Considérez des technologies plus efficaces lors du remplacement d'équipements"
                ],
                "savings": "3-8%"
            })
        
    # --- Recommandations basées sur la tendance de consommation ---
    if slope_base_load > 0.05:
        recommendations["medium_priority"].append({
            "title": "Inversez la tendance d'augmentation de consommation",
            "description": f"Votre consommation de base augmente de manière significative ({slope_base_load:.1f}W par an).",
            "actions": [
                "Faites un audit des nouveaux appareils ajoutés ces dernières années",
                "Comparez la consommation avant/après pour identifier les changements"
            ],
            "savings": "Variable"
        })
    
    # --- Recommandations basées sur le ratio semaine/weekend ---
    if abs(ratio_weekday_weekend - 2.5) > 0.5:
        if ratio_weekday_weekend > 3.5:
            recommendations["medium_priority"].append({
                "title": "Équilibrez votre consommation semaine/weekend",
                "description": "Votre consommation est beaucoup plus élevée en semaine qu'en weekend.",
                "actions": [
                    "Programmez l'extinction des équipements professionnels en votre absence",
                    "Vérifiez les systèmes de chauffage/climatisation pendant les heures de bureau"
                ],
                "savings": "5-10%"
            })
        elif ratio_weekday_weekend < 1.5:
            recommendations["medium_priority"].append({
                "title": "Optimisez votre consommation du weekend",
                "description": "Votre consommation est anormalement élevée le weekend par rapport à la semaine.",
                "actions": [
                    "Regroupez les tâches énergivores (lessives, cuisine, etc.)",
                    "Profitez des heures creuses pour les activités à forte consommation"
                ],
                "savings": "3-8%"
            })
    
    # --- Recommandations basées sur le ratio jour/nuit ---
    if ratio_day_night < 1.5:
        recommendations["medium_priority"].append({
            "title": "Réduisez votre consommation nocturne",
            "description": "Votre consommation nocturne est relativement élevée.",
            "actions": [
                "Vérifiez quels appareils fonctionnent la nuit",
                "Utilisez des minuteries pour les systèmes de chauffage ou climatisation",
                "Évitez de laisser des appareils en fonctionnement durant la nuit"
            ],
            "savings": "3-7%"
        })
    elif ratio_day_night > 2.5:
        recommendations["low_priority"].append({
            "title": "Lissez votre consommation sur la journée",
            "description": "Votre consommation est fortement concentrée pendant la journée.",
            "actions": [
                "Déplacez certaines tâches énergivores vers les heures creuses (soir)",
                "Profitez des tarifs heures creuses si vous en disposez"
            ],
            "savings": "2-5% sur votre facture"
        })
    
    # --- Recommandations basées sur la consommation par surface ---
    if yearly_surface_consumption:
        if yearly_surface_consumption > 56:
            recommendations["high_priority"].append({
                "title": "Améliorez l'efficacité énergétique de votre bâtiment",
                "description": "Votre consommation par m² dépasse les standards Minergie.",
                "actions": [
                    "Améliorez l'isolation de votre bâtiment",
                    "Remplacez les équipements de chauffage/climatisation",
                    "Envisagez un audit énergétique complet"
                ],
                "savings": "10-30%"
            })
        elif yearly_surface_consumption > 33:
            recommendations["medium_priority"].append({
                "title": "Optimisez l'efficacité de votre bâtiment",
                "description": "Votre consommation par m² est acceptable mais pourrait être améliorée.",
                "actions": [
                    "Vérifiez l'isolation des fenêtres et portes",
                    "Optimisez la gestion du chauffage avec des thermostats intelligents"
                ],
                "savings": "5-15%"
            })
    
    # --- Recommandations basées sur la consommation par personne ---
    if daily_consumption_per_capita:
        if daily_consumption_per_capita > 5:
            recommendations["high_priority"].append({
                "title": "Réduisez votre empreinte énergétique personnelle",
                "description": "Votre consommation par personne est significativement supérieure à la moyenne suisse.",
                "actions": [
                    "Adoptez des comportements plus économes au quotidien",
                    "Remplacez les appareils énergivores par des modèles plus efficaces",
                    "Sensibilisez tous les membres du foyer aux économies d'énergie"
                ],
                "savings": "10-20%"
            })
        elif daily_consumption_per_capita > 4:
            recommendations["medium_priority"].append({
                "title": "Optimisez votre consommation individuelle",
                "description": "Votre consommation par personne est légèrement supérieure à la moyenne suisse.",
                "actions": [
                    "Identifiez vos principaux postes de consommation",
                    "Adoptez des gestes simples d'économie d'énergie au quotidien"
                ],
                "savings": "5-15%"
            })
    
    # --- Recommandation sur le solaire si non encore installé ---
    if not has_solar:
        recommendations["medium_priority"].append({
            "title": "Envisagez l'autoconsommation solaire",
            "description": "L'installation de panneaux photovoltaïques pourrait réduire votre dépendance au réseau.",
            "actions": [
                "Réalisez une étude de faisabilité pour une installation solaire",
                "Renseignez-vous sur les subventions disponibles dans votre canton",
                "Explorez les options de communautés énergétiques locales"
            ],
            "savings": "30-60% sur votre facture à long terme"
        })
    
    # --- Recommandations générales toujours pertinentes ---
    recommendations["low_priority"].append({
        "title": "Optez pour l'éclairage intelligent",
        "description": "L'optimisation de votre éclairage peut générer des économies significatives.",
        "actions": [
            "Remplacez toutes les ampoules par des LED",
            "Installez des détecteurs de présence dans les zones de passage",
            "Exploitez au maximum la lumière naturelle"
        ],
        "savings": "2-5%"
    })
    
    # Assurez-vous qu'il y a toujours au moins une recommandation de chaque priorité
    if not recommendations["high_priority"]:
        recommendations["high_priority"].append({
            "title": "Surveillez régulièrement votre consommation",
            "description": "Même si votre consommation est relativement bonne, un suivi régulier vous permettra de maintenir cette performance.",
            "actions": [
                "Mettez en place un suivi mensuel de votre consommation",
                "Vérifiez l'impact de vos habitudes sur votre consommation"
            ],
            "savings": "3-8% par une meilleure conscience énergétique"
        })
    
    return recommendations

def display_recommendations(recommendations):
    """
    Affiche les recommandations personnalisées de manière visuelle et attractive
    avec indication des économies en pourcentage et en CHF
    """
    # Récupérer le prix par kWh et la consommation annuelle totale
    price_per_kwh = st.session_state.get('price', 0.35)  # Prix par défaut si non disponible
    
    # Calculer la consommation annuelle totale (en kWh)
    consumption_column = get_consumption_column(st.session_state.get('pdf', pd.DataFrame()))
    if not st.session_state.get('pdf', pd.DataFrame()).empty:
        yearly_consumption = st.session_state.get('pdf', pd.DataFrame())[consumption_column].sum()
    else:
        yearly_consumption = 0
    
    # Calculer le coût annuel total
    annual_cost = yearly_consumption * price_per_kwh
    
    # Affichage des recommandations à haute priorité
    if recommendations["high_priority"]:
        st.markdown("<h4 style='color: #666666;'>Actions prioritaires</h4>", unsafe_allow_html=True)
        for rec in recommendations["high_priority"]:
            # Extraire les valeurs min et max du pourcentage d'économies
            savings_text = rec['savings']
            try:
                if '-' in savings_text:
                    min_pct, max_pct = map(float, savings_text.strip('%').split('-'))
                else:
                    min_pct = max_pct = float(savings_text.strip('%'))
                
                # Calculer les économies en CHF
                min_savings_chf = (min_pct / 100) * annual_cost
                max_savings_chf = (max_pct / 100) * annual_cost
                
                if min_pct == max_pct:
                    savings_chf_text = f"{min_savings_chf:.0f} CHF/an"
                else:
                    savings_chf_text = f"{min_savings_chf:.0f} - {max_savings_chf:.0f} CHF/an"
                
                # Format complet avec pourcentage et CHF
                savings_display = f"{savings_text} ({savings_chf_text})"
            except:
                # En cas d'erreur, afficher seulement le pourcentage
                savings_display = savings_text
            
            st.markdown(f"""
            <div style="border-left: 5px solid #DC143C; background-color: #fff; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h5 style="color: #333; margin-top: 0;">{rec['title']}</h5>
                <p style="color: #555;">{rec['description']}</p>
                <ul style="margin-bottom: 10px; padding-left: 20px;">
                    {''.join([f"<li>{action}</li>" for action in rec['actions']])}
                </ul>
                <p style="margin: 0; color: #DC143C; font-weight: bold;">Économies potentielles: {savings_display}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Affichage des recommandations à priorité moyenne
    if recommendations["medium_priority"]:
        st.markdown("<h4 style='color: #666666;'>Actions recommandées</h4>", unsafe_allow_html=True)
        for rec in recommendations["medium_priority"]:
            # Extraire les valeurs min et max du pourcentage d'économies
            savings_text = rec['savings']
            try:
                if '-' in savings_text:
                    min_pct, max_pct = map(float, savings_text.strip('%').split('-'))
                else:
                    min_pct = max_pct = float(savings_text.strip('%'))
                
                # Calculer les économies en CHF
                min_savings_chf = (min_pct / 100) * annual_cost
                max_savings_chf = (max_pct / 100) * annual_cost
                
                if min_pct == max_pct:
                    savings_chf_text = f"{min_savings_chf:.0f} CHF/an"
                else:
                    savings_chf_text = f"{min_savings_chf:.0f} - {max_savings_chf:.0f} CHF/an"
                
                # Format complet avec pourcentage et CHF
                savings_display = f"{savings_text} ({savings_chf_text})"
            except:
                # En cas d'erreur, afficher seulement le pourcentage
                savings_display = savings_text
            
            st.markdown(f"""
            <div style="border-left: 5px solid #FFA500; background-color: #fff; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h5 style="color: #333; margin-top: 0;">{rec['title']}</h5>
                <p style="color: #555;">{rec['description']}</p>
                <ul style="margin-bottom: 10px; padding-left: 20px;">
                    {''.join([f"<li>{action}</li>" for action in rec['actions']])}
                </ul>
                <p style="margin: 0; color: #FF8C00; font-weight: bold;">Économies potentielles: {savings_display}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Affichage des recommandations à basse priorité
    if recommendations["low_priority"]:
        st.markdown("<h4 style='color: #666666;'>Actions complémentaires</h4>", unsafe_allow_html=True)
        for rec in recommendations["low_priority"]:
            # Extraire les valeurs min et max du pourcentage d'économies
            savings_text = rec['savings']
            try:
                if '-' in savings_text:
                    min_pct, max_pct = map(float, savings_text.strip('%').split('-'))
                else:
                    min_pct = max_pct = float(savings_text.strip('%').strip())
                
                # Calculer les économies en CHF
                min_savings_chf = (min_pct / 100) * annual_cost
                max_savings_chf = (max_pct / 100) * annual_cost
                
                if min_pct == max_pct:
                    savings_chf_text = f"{min_savings_chf:.0f} CHF/an"
                else:
                    savings_chf_text = f"{min_savings_chf:.0f} - {max_savings_chf:.0f} CHF/an"
                
                # Format complet avec pourcentage et CHF
                savings_display = f"{savings_text} ({savings_chf_text})"
            except:
                # En cas d'erreur, afficher seulement le pourcentage
                savings_display = savings_text
            
            st.markdown(f"""
            <div style="border-left: 5px solid #228B22; background-color: #fff; padding: 15px; margin-bottom: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h5 style="color: #333; margin-top: 0;">{rec['title']}</h5>
                <p style="color: #555;">{rec['description']}</p>
                <ul style="margin-bottom: 10px; padding-left: 20px;">
                    {''.join([f"<li>{action}</li>" for action in rec['actions']])}
                </ul>
                <p style="margin: 0; color: #228B22; font-weight: bold;">Économies potentielles: {savings_display}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Message final
    st.markdown(f"""
    <div style="max-width: 800px; margin: 20px auto; padding: 15px; text-align: center; background-color: #f8f9fa; border-radius: 10px;">
        <p style="margin: 0; font-style: italic;">La mise en œuvre de ces recommandations pourrait vous permettre d'économiser 10 à 30% sur votre facture d'électricité, soit environ {annual_cost * 0.1:.0f} à {annual_cost * 0.3:.0f} CHF par an.</p>
    </div>
    """, unsafe_allow_html=True)