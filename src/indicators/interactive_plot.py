# ============================================================================
# MODULE DE GRAPHIQUES INTERACTIFS - DataWatt
# ============================================================================
# 
# OBJECTIF PRINCIPAL:
# Module central pour l'affichage de graphiques interactifs multi-temporels
# permettant l'exploration des données de consommation énergétique selon
# différentes granularités temporelles et modes d'analyse.
#
# FONCTIONNALITÉS PRINCIPALES:
#
# 1. **VUES TEMPORELLES MULTIPLES**:
#    - Vue Année : Consommation journalière avec zoom interactif
#    - Vue Saison : Comparaison trimestrielle (Hiver/Printemps/Été/Automne)
#    - Vue Semaine : Profil hebdomadaire heure par heure
#    - Vue Jour : Analyse horaire ou par quart d'heure
#
# 2. **MODES D'ANALYSE**:
#    - Mode "Année unique" : Focus sur une année spécifique
#    - Mode "Données complètes" : Comparaison multi-années (max 3 simultanées)
#
# 3. **CALCULS DE TENDANCES**:
#    - Analyse automatique sur les 2 années complètes les plus récentes
#    - Classification : Stable (-10% à +10%), Augmentation (>10%), Diminution (<-10%)
#    - Détection des points de consommation maximale avec navigation interactive
#
# 4. **GESTION AVANCÉE DES DONNÉES**:
#    - Détection automatique des années complètes vs partielles
#    - Adaptation des vues selon la disponibilité des données
#    - Timeline continue pour années non-consécutives
#    - Cache intelligent des palettes de couleurs par année
#
# 5. **INTÉGRATIONS**:
#    - Calculs de coûts avec tarifs HP/HC ou unique
#    - Comparaison avec groupes de consommation (clustering)
#    - Indicateurs clés : consommation journalière et annuelle
#    - Alertes sur données partielles et années incomplètes
#
# 6. **NAVIGATION INTERACTIVE**:
#    - Zoom et curseur sur vue annuelle
#    - Boutons de navigation vers points maximaux
#    - Synchronisation entre vues temporelles
#    - Persistence des sélections utilisateur
#
# ARCHITECTURE TECHNIQUE:
# - Plotly pour graphiques interactifs avec hover personnalisé
# - Session state Streamlit pour persistence des paramètres
# - Gestion des couleurs cohérente par année
# - Optimisation des re-rendus avec callbacks
#
# ============================================================================

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import meteostat as mstat  
import plotly.graph_objects as go
from datetime import timedelta, datetime  
import src.textual.text as txt 
from src.textual.tools import *
from src.textual.format_number import format_number_with_apostrophe
try:
    from src.indicators.cluster_indic import load_user_cluster_positions
except ImportError:
    load_user_cluster_positions = None

def display_partial_year_warning(selected_years, time_range):
    """
    Affiche un avertissement si l'utilisateur travaille avec des années partielles
    
    Args:
        selected_years (list): Liste des années sélectionnées
        time_range (str): Type de vue actuelle
    """
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    years_completeness = st.session_state.get('years_completeness', {})
    
    # Message d'erreur sur les années partielles si une année est sélectionnée et que cette dernière est incomplète
    if analysis_mode == 'single_year':
        # Mode année unique : vérifier si l'année sélectionnée est partielle
        selected_year = st.session_state.get('selected_analysis_year')
        if selected_year and selected_year in years_completeness:
            completeness = years_completeness[selected_year]
            if completeness < 100:  # Année considérée comme partielle si < 100%
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 12px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #e74c3c;">
                    <p style="margin: 0; color: #d32f2f; font-weight: 500;">
                        ⚠️ <strong>Attention :</strong> L'année sélectionnée ({selected_year}) est partielle ({completeness:.1f}% des données). 
                        Les analyses peuvent être incomplètes.
                    </p>
                </div>
                """, unsafe_allow_html=True)

    # Message d'erreur si l'utilisateur a sélectionné les "Données complètes" mais qu'il y a quand même des données partielles dans la data
    else:
        # Mode données complètes : vérifier s'il y a des années partielles dans la sélection
        partial_years = []
        for year in selected_years:
            if year in years_completeness and years_completeness[year] < 100:
                partial_years.append(year)
        
        if partial_years:
            years_text = ", ".join(map(str, partial_years))
            st.markdown(f"""
            <div style="background-color: #fff3e0; padding: 12px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ff9800;">
                <p style="margin: 0; color: #f57c00; font-weight: 500;">
                    ⚠️ <strong>Information :</strong> Attention vous analysez des années avec des données partielles !
                </p>
            </div>
            """, unsafe_allow_html=True)

def display_trend_arrows(df, years_to_use):
    """
    Affiche des flèches de tendance pour montrer l'évolution entre les années
    Utilise la même logique que les autres indicateurs : tendance uniquement sur deux années complètes les plus récentes
    
    Args:
        df (pandas.DataFrame): DataFrame contenant les données
        years_to_use (list): Liste des années à analyser
    """
    # Vérifier si on a au moins 2 années complètes dans la liste retournée (même logique que base_load)
    years_completeness = st.session_state.get('years_completeness', {})
    valid_years_for_trend = []
    
    # Créer une liste des années valides pour la tendance (années complètes uniquement)
    for year in sorted(years_to_use):
        if year in years_completeness and years_completeness[year] >= 100:
            valid_years_for_trend.append(year)
    
    # Garder seulement les 2 années complètes les plus récentes
    recent_complete_years = sorted(valid_years_for_trend)[-2:]
    
    # Vérifier si on a au moins 2 années complètes
    if len(recent_complete_years) < 2:
        st.markdown(f"""
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ff9800;">
            <strong style="color: #f57c00;">ℹ️ Analyse de tendance</strong><br>
            <span style="color: #666;">
                La tendance nécessite au moins 2 années complètes. Actuellement : {len(recent_complete_years)} année(s) complète(s) disponible(s).
            </span>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Déterminer la colonne de consommation
    consumption_column = None
    for col in ['Consumption (kWh)', 'Consumption', 'kWh']:
        if col in df.columns:
            consumption_column = col
            break
    
    if consumption_column is None:
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            consumption_column = numeric_cols[0]
        else:
            return
    
    # Calculer la consommation annuelle pour les années complètes seulement
    annual_consumption = {}
    for year in recent_complete_years:
        year_data = df[df['Year'] == year]
        if not year_data.empty:
            annual_consumption[year] = year_data[consumption_column].sum()
    
    if len(annual_consumption) < 2:
        st.markdown(f"""
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ff9800;">
            <strong style="color: #f57c00;">ℹ️ Analyse de tendance</strong><br>
            <span style="color: #666;">
                Données insuffisantes pour calculer une tendance sur les années complètes.
            </span>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Calculer les tendances sur les 2 années complètes les plus récentes
    years_list = sorted(annual_consumption.keys())
    consumption_values = [annual_consumption[year] for year in years_list]
    
    # Calculer le pourcentage de changement total
    first_year_consumption = consumption_values[0]
    last_year_consumption = consumption_values[-1]
    total_change_percent = ((last_year_consumption - first_year_consumption) / first_year_consumption) * 100
    
    # Déterminer la couleur de la tendance selon les nouveaux seuils
    if total_change_percent > 10:
        trend_color = "#e74c3c"  # Rouge pour augmentation > 10%
        trend_text = "Augmentation"
    elif total_change_percent < -10:
        trend_color = "#27ae60"  # Vert pour diminution < -10%
        trend_text = "Diminution"
    else:
        trend_color = "#3498db"  # Bleu pour stable (-10% à +10%)
        trend_text = "Stable"
    
    # Afficher la tendance globale avec fond blanc
    st.markdown(f"""
    <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="margin-bottom: 10px;">
            <strong style="color: #333;">Tendance sur années complètes : <span style="color: {trend_color}; font-weight: bold;">{trend_text}</span></strong>
            <br>
            <span style="font-size: 0.9em; color: #666;">
                {total_change_percent:+.1f}% entre {years_list[0]} et {years_list[-1]}
            </span>
            <br>
            <span style="font-size: 0.8em; color: #888; font-style: italic;">
                Calculé sur les 2 années complètes les plus récentes
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def format_date_french(date):
    """Formate une date en français"""
    months_fr = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril", 
        5: "mai", 6: "juin", 7: "juillet", 8: "août",
        9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    day = date.day
    month_fr = months_fr[date.month]
    return f"{day} {month_fr}"

def get_month_abbr_french(date):
    """Retourne l'abréviation du mois en français"""
    months_abbr_fr = {
        1: "jan", 2: "fév", 3: "mar", 4: "avr", 
        5: "mai", 6: "jun", 7: "jul", 8: "aoû",
        9: "sep", 10: "oct", 11: "nov", 12: "déc"
    }
    return months_abbr_fr[date.month]

def display_user_group_comparison():
    """
    Affiche la position de l'utilisateur par rapport à son groupe de consommation
    basé sur les données de clustering sauvegardées
    """
    # Vérifier si l'utilisateur est un particulier
    user_type = st.session_state.get('user_type', "Particulier")
    if user_type != "Particulier":
        return  # Ne pas afficher pour les professionnels
    
    if load_user_cluster_positions is None:
        return
    
    # Charger les données de position de l'utilisateur
    positions_df = load_user_cluster_positions()
    
    if positions_df is None or positions_df.empty:
        return  # Pas de données disponibles, on ne fait rien
    
    # Récupérer le cluster ID
    cluster_id = positions_df['cluster_id'].iloc[0]
    
    # Définir les seuils et couleurs pour la nouvelle échelle (-50% à +50%)
    def get_status_info(percentile):
        if percentile < 0:
            return "🟢", "Très bon", "#27ae60", f"Votre consommation est {abs(percentile):.0f}% plus faible que la médiane de votre groupe"
        elif percentile < 20:
            return "🟡", "Modéré", "#f39c12", f"Votre consommation est {percentile:.0f}% plus élevée que la médiane de votre groupe"
        else:
            return "🔴", "Élevé", "#e74c3c", f"Votre consommation est {percentile:.0f}% plus élevée que la médiane de votre groupe"
    
    # Récupérer les données clés - uniquement consommations hivernales et estivales pour l'instant
    consumption_features = ['mean_consumption_winter', 'mean_consumption_summer']
    
    # Filtrer les données disponibles
    available_consumption = positions_df[positions_df['feature'].isin(consumption_features)]
    
    if available_consumption.empty:
        return  # Pas de données de consommation disponibles
    
    st.markdown("""
    <div style="margin: 10px 0 8px 0; text-align: center;">
        <h5 style="color: #333; font-weight: bold; font-size: 0.9em; margin: 0; letter-spacing: 1px; text-transform: uppercase;">
            Votre position dans votre groupe
        </h5>
    </div>
    """, unsafe_allow_html=True)
    
    # Afficher les consommations
    for _, row in available_consumption.iterrows():
        emoji, status, color, description = get_status_info(row['position_percentile'])
        
        feature_display = {
            'mean_consumption_winter': 'Consommation hivernale (Déc-Fév)',
            'mean_consumption_summer': 'Consommation estivale (Jun-Aoû)'
        }
        
        feature_name = feature_display.get(row['feature'], row['feature_name_fr'])
        
        # Créer une couleur de fond plus claire basée sur la couleur principale
        if color == "#27ae60":  # Vert
            bg_color = "#e8f5e8"
            border_color = "#27ae60"
        elif color == "#f39c12":  # Orange/Jaune
            bg_color = "#fff8e1"
            border_color = "#f39c12"
        else:  # Rouge
            bg_color = "#ffebee"
            border_color = "#e74c3c"
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 12px 0; border: 2px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 1.1em; color: #333;">{emoji} {feature_name}</span>
                <span style="color: {color}; font-weight: bold; font-size: 1.2em; background-color: white; padding: 4px 8px; border-radius: 6px; border: 1px solid {color};">{row['position_percentile']:+.0f}%</span>
            </div>
            <div style="font-size: 0.9em; color: #555; font-weight: 500;">
                {description}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recommandations retirées sous l'encart.  
    
    # Explication des percentiles
    tooltip_info("Information")
    with st.expander("Comment interpréter ces pourcentages ?", expanded=False):
        st.markdown("""
        **Échelle par rapport à la médiane :**
        
        **🟢 -50% à 0%** : Votre consommation est inférieure à la médiane  
        **🟡 0% à +20%** : Votre consommation est légèrement supérieure à la médiane  
        **🔴 +20% à +50%** : Votre consommation est nettement supérieure à la médiane (à optimiser)  
        """)

def display_key_indicators_standalone(pdf):
    """
    Affiche les indicateurs clés de consommation selon le mode d'analyse sélectionné.
    Version adaptée au nouveau système de sélection d'années.
    
    Args:
        pdf (pandas.DataFrame): DataFrame contenant les données (déjà filtrées selon la sélection)
    """
    # Créer une copie du DataFrame et ajouter les colonnes d'année et de semaine si nécessaire
    df = pdf.copy()
    if 'Year' not in df.columns:
        df['Year'] = df.index.year
    if 'Week' not in df.columns:
        df['Week'] = df.index.isocalendar().week
    
    # Récupérer le mode d'analyse
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    # Définir une palette de couleurs extensible pour toutes les années
    default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
    
    # Générer automatiquement le color_map pour toutes les années présentes
    color_map = {}
    unique_years = sorted(df['Year'].unique())
    for i, year in enumerate(unique_years):
        color_map[year] = default_colors[i % len(default_colors)]
    
    txt.section_title("Indicateurs de consommation")
    
    # Ajouter un espacement
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    # Afficher les informations sur le tarif utilisé (depuis la barre latérale)
    tariff_type = st.session_state.get('tariff_type', 'Tarif Unique')
    if tariff_type == "Tarif Unique":
        price_per_kwh = st.session_state.get('tariff_unique_price', 0.35)
        st.markdown(f"""
        <div style='background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;'>
            <p style='margin: 0;'><strong>💰 Tarif utilisé :</strong> {price_per_kwh:.2f} CHF/kWh (tarif unique, appliqué à toutes les années)</p>
            <p style='margin: 5px 0 0 0; font-size: 0.9em; color: #666;'>Modifiable dans la barre latérale ← "Configuration des tarifs"</p>
        </div>
        """, unsafe_allow_html=True)
        # Mettre à jour le prix dans l'état de session pour compatibilité (tarif unique)
        st.session_state['price'] = price_per_kwh
    else:
        hp_price = st.session_state.get('tariff_hp_price', 0.40)
        hc_price = st.session_state.get('tariff_hc_price', 0.27)
        # Calculer un prix moyen pour compatibilité avec d'autres fonctions
        average_price = (hp_price + hc_price) / 2
        st.markdown(f"""
        <div style='background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;'>
            <p style='margin: 0;'><strong>💰 Tarif utilisé :</strong> HP {hp_price:.2f} CHF/kWh | HC {hc_price:.2f} CHF/kWh (appliqué à toutes les années)</p>
            <p style='margin: 5px 0 0 0; font-size: 0.9em; color: #666;'>Modifiable dans la barre latérale ← "Configuration des tarifs"</p>
        </div>
        """, unsafe_allow_html=True)
        # Mettre à jour le prix dans l'état de session pour compatibilité (prix moyen HP/HC)
        st.session_state['price'] = average_price
    
    # Ajouter un espacement
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    # Adaptation selon le mode d'analyse
    if analysis_mode == 'single_year':
        # Mode année unique : affichage simplifié
        selected_year = st.session_state.get('selected_analysis_year')
        display_single_year_indicators(df, selected_year, color_map)
    else:
        # Mode données complètes : onglets avec évolution
        display_multi_year_indicators(df, color_map)

def display_single_year_indicators(df, selected_year, color_map):
    """
    Affiche les indicateurs pour une année unique
    """
    available_years = sorted(df['Year'].unique())
    
    if not available_years:
        st.error("Aucune donnée disponible pour l'affichage des indicateurs.")
        return
    
    # Utiliser l'année sélectionnée ou la première disponible
    display_year = selected_year if selected_year in available_years else available_years[0]
    
    # Calculer les métriques pour l'année sélectionnée
    year_data = df[df['Year'] == display_year]
    
    # Déterminer la colonne de consommation à utiliser
    consumption_column = None
    for col in ['Consumption (kWh)', 'Consumption', 'kWh']:
        if col in df.columns:
            consumption_column = col
            break
    
    if consumption_column is None:
        # Si aucune colonne spécifique n'est trouvée, prendre la première colonne numérique
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            consumption_column = numeric_cols[0]
        else:
            st.error("Aucune colonne de consommation valide trouvée dans les données.")
            return
    
    daily_avg = year_data[consumption_column].resample('D').sum().mean()
    total_year = year_data[consumption_column].sum()
    
    # === CALCULS DE COÛT SELON LE TYPE DE TARIF ===
    tariff_type = st.session_state.get('tariff_type', 'Tarif Unique')
    
    if tariff_type == "Tarif Unique":
        # Tarif unique : multiplication simple
        price_per_kwh = st.session_state.get('tariff_unique_price', 0.35)
        daily_cost = daily_avg * price_per_kwh
        total_cost = total_year * price_per_kwh
    else:  # Tarif HP/HC
        # === RÉCUPÉRATION DES PARAMÈTRES HP/HC ===
        hp_price = st.session_state.get('tariff_hp_price', 0.40)
        hc_price = st.session_state.get('tariff_hc_price', 0.27)
        peak_start = st.session_state.get('peak_start_hour', 6)
        peak_end = st.session_state.get('peak_end_hour', 22)
        peak_days = st.session_state.get('peak_days', [0, 1, 2, 3, 4])
        
        # === IMPORTATION DE LA FONCTION is_peak_hour ===
        from src.indicators.cost_analysis import is_peak_hour
        
        # === CALCUL DU COÛT TOTAL AVEC TARIFICATION HP/HC ===
        # Déterminer si chaque point de données est en HP ou HC
        year_data_copy = year_data.copy()
        year_data_copy['is_peak'] = year_data_copy.index.map(
            lambda timestamp: is_peak_hour(timestamp, peak_start, peak_end, peak_days)
        )
        
        # Calculer les consommations HP et HC
        consumption_hp = year_data_copy[year_data_copy['is_peak']][consumption_column].sum()
        consumption_hc = year_data_copy[~year_data_copy['is_peak']][consumption_column].sum()
        
        # Calculer le coût total avec tarification différenciée
        total_cost = (consumption_hp * hp_price) + (consumption_hc * hc_price)
        
        # Pour le coût journalier, calculer les moyennes HP/HC par jour
        year_data_hp = year_data_copy[year_data_copy['is_peak']]
        year_data_hc = year_data_copy[~year_data_copy['is_peak']]
        
        daily_hp = year_data_hp[consumption_column].resample('D').sum().mean()
        daily_hc = year_data_hc[consumption_column].resample('D').sum().mean()
        daily_cost = (daily_hp * hp_price) + (daily_hc * hc_price)
    
    # Utiliser la couleur correspondant à l'année sélectionnée
    year_color = color_map.get(display_year, '#42A5F5')
    
    # Ajouter un espacement après le sélecteur
    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
    
    # Affichage des indicateurs avec le même design que l'affichage multi-années
    st.markdown(f"<h4 style='text-align: center; color: #666666; margin-bottom: 20px;'>Indicateurs pour {display_year}</h4>", unsafe_allow_html=True)
    
    # Créer deux colonnes pour organiser l'affichage
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h5 style='text-align: center; color: #666666;'>Consommation moyenne par jour</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {year_color}; background-color: #f8f9fa; border-radius: 5px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='color: {year_color}; font-weight: bold;'>{display_year}</span>
                <span style='font-size: 1.1em; font-weight: bold;'>{daily_avg:.1f} kWh</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>Coût: {daily_cost:.2f} CHF/jour</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h5 style='text-align: center; color: #666666;'>Consommation totale annuelle</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {year_color}; background-color: #f8f9fa; border-radius: 5px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='color: {year_color}; font-weight: bold;'>{display_year}</span>
                <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(total_year)} kWh</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>Coût: {total_cost:.2f} CHF/an</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Ajouter un espacement avant l'info-bulle
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # Information sur l'année analysée
    tooltip_info("Information")
    st.info(f"Les indicateurs ci-dessus sont calculés uniquement pour l'année {display_year}.")

def display_multi_year_indicators(df, color_map):
    """
    Affiche les indicateurs pour plusieurs années
    """
    # Déterminer la colonne de consommation à utiliser
    consumption_column = None
    for col in ['Consumption (kWh)', 'Consumption', 'kWh']:
        if col in df.columns:
            consumption_column = col
            break
    
    if consumption_column is None:
        # Si aucune colonne spécifique n'est trouvée, prendre la première colonne numérique
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            consumption_column = numeric_cols[0]
        else:
            st.error("Aucune colonne de consommation valide trouvée dans les données.")
            return
    
    available_years = sorted(df['Year'].unique())
    
    if not available_years:
        st.error("Aucune donnée disponible pour l'affichage des indicateurs.")
        return
    
    # === RÉCUPÉRATION DES PARAMÈTRES DE TARIFICATION ===
    tariff_type = st.session_state.get('tariff_type', 'Tarif Unique')
    
    # Calculer les métriques pour toutes les années
    yearly_data = {}
    for year in available_years:
        year_data = df[df['Year'] == year]
        daily_avg = year_data[consumption_column].resample('D').sum().mean()
        total_year = year_data[consumption_column].sum()
        
        # === CALCULS DE COÛT SELON LE TYPE DE TARIF ===
        if tariff_type == "Tarif Unique":
            # Tarif unique : multiplication simple
            price_per_kwh = st.session_state.get('tariff_unique_price', 0.35)
            daily_cost = daily_avg * price_per_kwh
            total_cost = total_year * price_per_kwh
        else:  # Tarif HP/HC
            # === RÉCUPÉRATION DES PARAMÈTRES HP/HC ===
            hp_price = st.session_state.get('tariff_hp_price', 0.40)
            hc_price = st.session_state.get('tariff_hc_price', 0.27)
            peak_start = st.session_state.get('peak_start_hour', 6)
            peak_end = st.session_state.get('peak_end_hour', 22)
            peak_days = st.session_state.get('peak_days', [0, 1, 2, 3, 4])
            
            # === IMPORTATION DE LA FONCTION is_peak_hour ===
            from src.indicators.cost_analysis import is_peak_hour
            
            # === CALCUL DU COÛT TOTAL AVEC TARIFICATION HP/HC ===
            # Déterminer si chaque point de données est en HP ou HC
            year_data_copy = year_data.copy()
            year_data_copy['is_peak'] = year_data_copy.index.map(
                lambda timestamp: is_peak_hour(timestamp, peak_start, peak_end, peak_days)
            )
            
            # Calculer les consommations HP et HC
            consumption_hp = year_data_copy[year_data_copy['is_peak']][consumption_column].sum()
            consumption_hc = year_data_copy[~year_data_copy['is_peak']][consumption_column].sum()
            
            # Calculer le coût total avec tarification différenciée
            total_cost = (consumption_hp * hp_price) + (consumption_hc * hc_price)
            
            # Pour le coût journalier, calculer les moyennes HP/HC par jour
            year_data_hp = year_data_copy[year_data_copy['is_peak']]
            year_data_hc = year_data_copy[~year_data_copy['is_peak']]
            
            daily_hp = year_data_hp[consumption_column].resample('D').sum().mean()
            daily_hc = year_data_hc[consumption_column].resample('D').sum().mean()
            daily_cost = (daily_hp * hp_price) + (daily_hc * hc_price)
        
        yearly_data[year] = {
            'daily_avg': daily_avg,
            'total_year': total_year,
            'daily_cost': daily_cost,
            'total_cost': total_cost
        }
    
    # Affichage des indicateurs
    
    # Créer deux colonnes pour organiser l'affichage
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h5 style='text-align: center; color: #666666;'>Consommation moyenne par jour</h5>", unsafe_allow_html=True)
        for i, year in enumerate(available_years):
            data = yearly_data[year]
            year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
            
            st.markdown(f"""
            <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {year_color}; background-color: #f8f9fa; border-radius: 5px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <span style='color: {year_color}; font-weight: bold;'>{year}</span>
                    <span style='font-size: 1.1em; font-weight: bold;'>{data['daily_avg']:.1f} kWh</span>
                </div>
                <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>Coût: {data['daily_cost']:.2f} CHF/jour</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h5 style='text-align: center; color: #666666;'>Consommation totale annuelle</h5>", unsafe_allow_html=True)
        for i, year in enumerate(available_years):
            data = yearly_data[year]
            year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
            
            st.markdown(f"""
            <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {year_color}; background-color: #f8f9fa; border-radius: 5px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <span style='color: {year_color}; font-weight: bold;'>{year}</span>
                    <span style='font-size: 1.1em; font-weight: bold;'>{format_number_with_apostrophe(data["total_year"])} kWh</span>
                </div>
                <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>Coût: {data['total_cost']:.2f} CHF/an</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Ajouter un espacement avant l'info-bulle
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # Avertissement sur les données incomplètes - uniquement si années partielles
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    if year_selection_mode != "Données complètes":
        tooltip_info("Information")
        st.info("Attention : Les valeurs de consommation sont calculées uniquement à partir des données disponibles pour les années sélectionnées et ne représentent pas des années complètes.")

def display_date_range(df):
    """
    Affiche la plage de dates disponibles dans le DataFrame.
    
    Args:
        df (pandas.DataFrame): DataFrame contenant les données avec un index temporel
    """
    if df is not None and not df.empty:
        # Dictionnaires de traduction pour les jours et mois en français
        jours_fr = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        
        mois_fr = {
            'January': 'janvier',
            'February': 'février',
            'March': 'mars',
            'April': 'avril',
            'May': 'mai',
            'June': 'juin',
            'July': 'juillet',
            'August': 'août',
            'September': 'septembre',
            'October': 'octobre',
            'November': 'novembre',
            'December': 'décembre'
        }
        
        start_date = df.index.min()
        end_date = df.index.max()
        
        # Récupération des noms en anglais
        start_day_en = start_date.strftime('%A')
        end_day_en = end_date.strftime('%A')
        start_month_en = start_date.strftime('%B')
        end_month_en = end_date.strftime('%B')
        
        # Traduction en français
        start_day_fr = jours_fr.get(start_day_en, start_day_en)
        end_day_fr = jours_fr.get(end_day_en, end_day_en)
        start_month_fr = mois_fr.get(start_month_en, start_month_en)
        end_month_fr = mois_fr.get(end_month_en, end_month_en)
        
        # Création des chaînes de date en français
        start_date_fr = f"{start_day_fr} {start_date.day} {start_month_fr} {start_date.year}"
        end_date_fr = f"{end_day_fr} {end_date.day} {end_month_fr} {end_date.year}"
        
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
            <p style="margin: 0;"><strong>Période des données disponibles dans votre fichier :</strong> Du {start_date_fr} au {end_date_fr}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Aucune donnée disponible pour afficher la période.")

def display_interactive_plot(test2):    
    # Plot the data using Plotly
    # display_date_range(test2)  # Retiré car maintenant affiché dans la sidebar

    # Display the start date and end date
    start_date = test2.index.min().strftime('%Y-%m-%d')
    end_date = test2.index.max().strftime('%Y-%m-%d')
    
    # Vérifier si une navigation vers courbe-charge est nécessaire
    if st.session_state.get('navigate_to_courbe_charge', False):
        st.markdown("""
        <script>
        setTimeout(function() {
            document.getElementById('courbe-charge').scrollIntoView({behavior: 'smooth'});
        }, 100);
        </script>
        """, unsafe_allow_html=True)
        # Réinitialiser le flag pour éviter de répéter la navigation
        st.session_state.navigate_to_courbe_charge = False
    
    # Récupérer le mode d'analyse depuis la session
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")

    # Initialisation des paramètres de session pour le suivi de la sélection (UNE SEULE FOIS)
    session_defaults = {
        'selected_month': "01 - Janvier",
        'selected_day': "01",
        'click_detected': False,
        'day_resolution': "Horaire",
        'current_view': "Year",
        'last_max_point': None,
        'selected_week_value': 1
    }
    
    # Initialiser seulement les clés manquantes
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Fonction pour réinitialiser l'état de navigation entre points max
    def reset_max_point_navigation():
        st.session_state.last_max_point = None
        st.session_state.click_detected = False

    # Définition des couleurs distinctes mais neutres pour chaque année (cache)
    if 'color_map_cache' not in st.session_state:
        # Palette de couleurs extensible pour toutes les années
        default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
        
        # Générer automatiquement le color_map pour toutes les années présentes
        color_map = {}
        unique_years = sorted(test2['Year'].unique())
        for i, year in enumerate(unique_years):
            color_map[year] = default_colors[i % len(default_colors)]
        
        st.session_state.color_map_cache = color_map
        st.session_state.cached_years = set(unique_years)
    else:
        # Vérifier si de nouvelles années sont présentes dans les données
        current_years = set(test2['Year'].unique())
        cached_years = st.session_state.get('cached_years', set())
        
        if current_years != cached_years:
            # Régénérer le color_map si les années ont changé
            default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
            color_map = {}
            unique_years = sorted(test2['Year'].unique())
            for i, year in enumerate(unique_years):
                color_map[year] = default_colors[i % len(default_colors)]
            
            st.session_state.color_map_cache = color_map
            st.session_state.cached_years = current_years
        else:
            color_map = st.session_state.color_map_cache

    fig = go.Figure()

    # Si un clic est détecté, définir la vue sur "Day"
    if st.session_state.click_detected:
        st.session_state.current_view = "Day"
        st.session_state.click_detected = False

    # Déterminer l'index à utiliser pour le bouton radio
    # Vérifier si des années complètes sont disponibles
    complete_years = st.session_state.get('complete_years', [])
    has_complete_years = len(complete_years) > 0
    
    # Définir les options disponibles selon la disponibilité des années complètes
    if has_complete_years:
        time_range_options = ("Année", "Saison", "Semaine", "Jour")
    else:
        time_range_options = ("Année", "Saison", "Jour")
        # Si la vue actuelle est "Semaine" mais qu'aucune année complète n'est disponible, basculer sur "Année"
        if st.session_state.current_view == "Week":
            st.session_state.current_view = "Year"
    
    time_range_mapping = {"Year": "Année", "Season": "Saison", "Week": "Semaine", "Day": "Jour"}
    reverse_mapping = {"Année": "Year", "Saison": "Season", "Semaine": "Week", "Jour": "Day"}
    
    current_view_fr = time_range_mapping.get(st.session_state.current_view, "Année")
    
    # S'assurer que la vue actuelle est dans les options disponibles
    if current_view_fr not in time_range_options:
        current_view_fr = "Année"
        st.session_state.current_view = "Year"
    
    time_range_index = time_range_options.index(current_view_fr)

    # Fonction de callback pour le radio
    def on_time_range_change():
        # Mettre à jour immédiatement la vue actuelle
        new_time_range_fr = st.session_state.time_range_interactive
        new_time_range = reverse_mapping[new_time_range_fr]
        
        # Si la vue change, réinitialiser les navigations
        if new_time_range != st.session_state.current_view:
            reset_max_point_navigation()
            st.session_state.current_view = new_time_range

    # Main page for user input en utilisant la vue actuelle avec callback
    time_range_fr = st.radio("Choisissez entre :", time_range_options, 
                         index=time_range_index,
                         key="time_range_interactive", 
                         horizontal=True,
                         on_change=on_time_range_change)
    
    # Afficher un message informatif si la vue hebdomadaire n'est pas disponible
    if not has_complete_years:
        st.info("ℹ️ La vue hebdomadaire n'est pas disponible car aucune année complète (100% des données) n'a été détectée dans vos données.")
    
    # Convertir la sélection française vers l'anglais interne
    time_range = reverse_mapping[time_range_fr]
    
    # S'assurer que la vue actuelle est synchronisée
    st.session_state.current_view = time_range

    # User input for selecting the specific date or week
    selected_date = None
    selected_week = None
    selected_season = None
    
    # Gestion de la sélection d'années selon le mode d'analyse
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    
    if analysis_mode == 'single_year':
        # Mode année unique : afficher seulement l'année sélectionnée
        selected_year = st.session_state.get('selected_analysis_year')
        available_years = [selected_year] if selected_year else test2['Year'].unique()
        selected_years = available_years
        
    else:
        # Mode données complètes : permettre la sélection multiple limitée à 3 années
        years_to_use = st.session_state.get('years_to_use', test2['Year'].unique())
        
        # Limiter l'affichage et proposer les 3 années les plus récentes par défaut
        available_years_sorted = sorted(years_to_use, reverse=True)  # Trier du plus récent au plus ancien
        
        # Définir les années par défaut (3 plus récentes ou toutes si moins de 3)
        default_years = available_years_sorted[:3] if len(available_years_sorted) >= 3 else available_years_sorted
        
        # Interface de sélection avec limitation
        if len(years_to_use) > 3:
            st.markdown("**📊 Sélection des années à analyser :**")
            st.info("💡 Pour une meilleure lisibilité, vous pouvez sélectionner jusqu'à 3 années simultanément.")
            
            selected_years = st.multiselect(
                "Choisissez jusqu'à 3 années à comparer", 
                options=sorted(years_to_use, reverse=True),  # Afficher du plus récent au plus ancien
                default=default_years,
                help="Sélectionnez un maximum de 3 années pour optimiser la lisibilité des graphiques",
                max_selections=3
            )
            
            # Si plus de 3 années sélectionnées (ne devrait pas arriver avec max_selections mais sécurité)
            if len(selected_years) > 3:
                st.warning("⚠️ Seules les 3 premières années sélectionnées seront utilisées.")
                selected_years = selected_years[:3]
        else:
            # Si 3 années ou moins disponibles, les afficher toutes
            selected_years = years_to_use

    # Optimisation des sélecteurs conditionnels pour éviter les re-rendus
    if time_range == "Day":
        # Mois en français
        months = [f"{i:02d} - {month}" for i, month in enumerate(["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"], 1)]
        days = [f"{i:02d}" for i in range(1, 32)]
        
        # Initialiser les valeurs de session si nécessaire pour le mois et jour
        if 'selected_week_value' not in st.session_state:
            st.session_state.selected_week_value = 1
        
        col1, col2 = st.columns(2)
        with col1:
            current_month_index = months.index(st.session_state.selected_month) if st.session_state.selected_month in months else 0
            selected_month = st.selectbox("Sélectionner un mois", months, 
                                         index=current_month_index, 
                                         key="month_select_interactive")
        with col2:
            current_day_index = days.index(st.session_state.selected_day) if st.session_state.selected_day in days else 0
            selected_day = st.selectbox("Sélectionner un jour", days, 
                                       index=current_day_index, 
                                       key="day_select_interactive")
        
        # Fonction de callback pour préserver la vue Day lors du changement de résolution
        def on_resolution_change():
            st.session_state.current_view = "Day"
        
        # Ajouter l'option pour choisir entre vue horaire et quart d'heure avec callback
        resolution = st.radio("Résolution temporelle :", ("Horaire", "Quart d'heure"), 
                             key="day_resolution", horizontal=True,
                             on_change=on_resolution_change)
        
        selected_month_number = selected_month.split(" - ")[0]
        selected_date = pd.Timestamp(f"1900-{selected_month_number}-{selected_day}")
        
        # Mettre à jour les variables de session seulement si elles ont changé
        if st.session_state.selected_month != selected_month:
            st.session_state.selected_month = selected_month
        if st.session_state.selected_day != selected_day:
            st.session_state.selected_day = selected_day
        
    elif time_range == "Week":
        # Déterminer les semaines disponibles selon le mode d'analyse
        analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
        
        # Vérifier si on doit adapter le slider (mode année unique OU une seule année sélectionnée)
        should_adapt_slider = False
        target_year = None
        
        if analysis_mode == 'single_year':
            # Mode année unique : adapter le slider aux semaines réellement disponibles
            target_year = st.session_state.get('selected_analysis_year')
            should_adapt_slider = True
        elif len(selected_years) == 1:
            # Mode données complètes mais une seule année sélectionnée : même comportement
            target_year = selected_years[0]
            should_adapt_slider = True
        
        if should_adapt_slider and target_year and target_year in test2['Year'].values:
            year_data = test2[test2['Year'] == target_year]
            available_weeks = sorted(year_data['Week'].unique())
            
            if available_weeks:
                min_week = min(available_weeks)
                max_week = max(available_weeks)
                
                # Utiliser la valeur de session persistante pour la semaine, mais l'adapter aux limites
                if 'selected_week_value' not in st.session_state:
                    st.session_state.selected_week_value = min_week
                
                # S'assurer que la valeur actuelle est dans la plage disponible
                current_week = st.session_state.selected_week_value
                if current_week < min_week or current_week > max_week:
                    st.session_state.selected_week_value = min_week
                    current_week = min_week
                
                # Afficher des informations sur la plage de semaines disponibles
                if min_week != 1 or max_week != 52:
                    st.markdown(f"""
                    <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #4361ee;">
                        <p style="margin: 0;"><strong>📅 Semaines disponibles pour {target_year} :</strong> Semaines {min_week} à {max_week}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                selected_week = st.slider("Sélectionner une semaine", 
                                         min_value=min_week, max_value=max_week, 
                                         value=current_week, 
                                         key="week_slider_interactive")
            else:
                st.warning(f"Aucune donnée de semaine disponible pour l'année {target_year}")
                selected_week = 1
        else:
            # Mode données complètes avec plusieurs années : garder le comportement original (1-52)
            if 'selected_week_value' not in st.session_state:
                st.session_state.selected_week_value = 1
            
            selected_week = st.slider("Sélectionner une semaine", 
                                     min_value=1, max_value=52, 
                                     value=st.session_state.selected_week_value, 
                                     key="week_slider_interactive")
        
        # Mettre à jour la valeur de session si elle a changé
        if st.session_state.selected_week_value != selected_week:
            st.session_state.selected_week_value = selected_week
            
    elif time_range == "Season":
        # Toutes les saisons sont affichées automatiquement sur le graphique
        pass

    if time_range == "Year":
        # Réinitialiser pour permettre une nouvelle sélection de point maximal
        if time_range != "Day":
            st.session_state.last_max_point = None
            
        # Stockage pour les dates des points maximaux
        max_point_dates = []
        
        # Filtrer les données uniquement pour les années sélectionnées
        filtered_years_data = test2[test2['Year'].isin(selected_years)]
        
        if filtered_years_data.empty:
            st.warning("Aucune donnée pour les années sélectionnées.")
            return
        
        # Trier les années sélectionnées 
        selected_years_sorted = sorted(selected_years)
        
        # Dictionnaire pour stocker les données journalières de chaque année
        year_data_dict = {}
        
        # Récupérer les données pour chaque année sélectionnée avec granularité journalière
        for year in selected_years_sorted:
            year_data = test2[test2['Year'] == year]
            if not year_data.empty:
                year_data_dict[year] = year_data.resample('D').sum(numeric_only=True)
        
        # Créer une timeline continue sans gap entre années non consécutives
        continuous_data = {}  # Pour stocker les données avec dates transformées
        shifted_dates_map = {}  # Mapper les dates transformées aux dates originales
        
        for i, year in enumerate(selected_years_sorted):
            if year in year_data_dict:
                year_df = year_data_dict[year]
                
                # Pour la première année, utiliser les dates telles quelles
                if i == 0:
                    continuous_data[year] = year_df
                    for date in year_df.index:
                        shifted_dates_map[date] = date
                else:
                    # Pour les années suivantes, créer des dates adjacentes à la précédente
                    prev_year = selected_years_sorted[i-1]
                    last_date_prev_year = max(continuous_data[prev_year].index)
                    
                    # Calculer les dates transformées pour cette année
                    transformed_dates = []
                    real_dates = []
                    
                    for idx, date in enumerate(year_df.index):
                        day_of_year = (date - pd.Timestamp(f"{year}-01-01")).days + 1
                        new_date = last_date_prev_year + pd.Timedelta(days=day_of_year)
                        
                        transformed_dates.append(new_date)
                        real_dates.append(date)
                        shifted_dates_map[new_date] = date
                    
                    transformed_df = pd.DataFrame(
                        index=transformed_dates, 
                        data=year_df.values, 
                        columns=year_df.columns
                    )
                    continuous_data[year] = transformed_df
        
        # Tracer les données avec les dates transformées
        for i, year in enumerate(selected_years_sorted):
            if year in continuous_data:
                df = continuous_data[year]
                
                # Préparer les données pour le hover (dates réelles)
                hover_dates = [shifted_dates_map.get(date, date) for date in df.index]
                hover_text = [d.strftime('%Y-%m-%d') for d in hover_dates]
                hover_template = '%{text}<br>Consommation: %{y:.1f} kWh<extra></extra>'
                
                # Tracer la courbe
                year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['Consumption (kWh)'],
                    mode='lines',
                    name=str(year),
                    line=dict(color=year_color, width=2.5),
                    hovertemplate=hover_template,
                    text=hover_text
                ))
                
                # Trouver les 3 points avec la consommation la plus élevée pour cette année  
                df['Consumption (kWh)'] = pd.to_numeric(df['Consumption (kWh)'], errors='coerce')
                top_points = df.nlargest(3, 'Consumption (kWh)')
                
                # Préparer les dates réelles et les textes pour le hover
                top_hover_dates = [shifted_dates_map.get(date, date) for date in top_points.index]
                top_hover_text = [d.strftime('%Y-%m-%d') for d in top_hover_dates]
                
                # Stocker les dates réelles des points maximaux pour cette année avec les valeurs de consommation
                for idx, date in enumerate(top_hover_dates):
                    consumption_value = top_points.iloc[idx]['Consumption (kWh)']
                    max_point_dates.append((year, date.strftime('%m'), date.strftime('%d'), date.strftime('%m-%d'), date.strftime('%Y-%m-%d'), consumption_value))
                
                # Ajouter des points rouges pour les 3 consommations les plus élevées
                fig.add_trace(go.Scatter(
                    x=top_points.index,
                    y=top_points['Consumption (kWh)'],
                    mode='markers',
                    marker=dict(
                        color='red',
                        size=10,
                        symbol='circle',
                        line=dict(
                            color='white',
                            width=1
                        )
                    ),
                    name=f'Top 3 - {year}',
                    showlegend=False,  # MODIFICATION 1: Masquer dans la légende
                    hovertemplate='Date: %{text}<br>Consommation: %{y:.1f} kWh<br><b>Cliquez pour voir ce jour en détail</b><extra>Point maximal</extra>',
                    text=top_hover_text
                ))
                
                # Si ce n'est pas la première année, ajouter une connexion
                if i > 0:
                    prev_year = selected_years_sorted[i-1]
                    prev_df = continuous_data[prev_year]
                    
                    # Connecter le dernier point de l'année précédente au premier point de l'année courante
                    last_idx_prev = prev_df.index[-1]
                    first_idx_curr = df.index[0]
                    
                    # Valeurs de consommation pour ces points
                    last_val_prev = prev_df['Consumption (kWh)'].iloc[-1]
                    first_val_curr = df['Consumption (kWh)'].iloc[0]
                    
                    # Tracer la connexion
                    prev_year_color = color_map.get(prev_year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
                    fig.add_trace(go.Scatter(
                        x=[last_idx_prev, first_idx_curr],
                        y=[last_val_prev, first_val_curr],
                        mode='lines',
                        line=dict(color=prev_year_color, width=2.5),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
        
        # Déterminer la plage de dates pour le graphique
        all_dates = []
        for year in selected_years_sorted:
            if year in continuous_data:
                all_dates.extend(continuous_data[year].index)
        
        date_min = min(all_dates)
        date_max = max(all_dates)
        total_days = (date_max - date_min).days
        
        # Créer des ticks personnalisés pour montrer correctement les années
        custom_ticks = []
        custom_tick_labels = []
        
        # Optimiser les ticks pour la vue journalière
        if total_days <= 14:
            tick_interval = 1  # Quotidien
        elif total_days <= 60:
            tick_interval = 5  # Tous les 5 jours
        elif total_days <= 120:
            tick_interval = 10  # Tous les 10 jours
        else:
            tick_interval = 30  # Mensuel
        
        current_date = date_min
        while current_date <= date_max:
            custom_ticks.append(current_date)
            real_date = shifted_dates_map.get(current_date, current_date)
            
            if total_days <= 60:
                custom_tick_labels.append(f"{real_date.day} {get_month_abbr_french(real_date)}")
            else:
                custom_tick_labels.append(f"{get_month_abbr_french(real_date)} {real_date.year}")
            
            current_date += pd.Timedelta(days=tick_interval)
        
        # Préparer le titre dynamique pour la vue annuelle
        if len(selected_years) == 1:
            year_title = f"Consommation journalière pour {selected_years[0]}"
        else:
            years_sorted = sorted(selected_years)
            if len(years_sorted) == 2:
                year_title = f"Consommation journalière pour {years_sorted[0]} et {years_sorted[1]}"
            else:
                year_title = f"Consommation journalière pour {min(years_sorted)} - {max(years_sorted)}"
        
        # Configuration pour la vue Year avec le curseur interactif
        fig.update_layout(
            title=year_title, 
            xaxis_title='Date', 
            yaxis_title='Consommation (kWh)',
            height=600, 
            xaxis=dict(
                rangeslider=dict(
                    visible=True,
                    thickness=0.18,
                    bgcolor='rgba(13, 71, 161, 0.2)'
                ),
                type="date",
                tickvals=custom_ticks,
                ticktext=custom_tick_labels,
                tickmode='array',
                range=[date_min, date_max]
            ),
            margin=dict(l=50, r=50, t=60, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode='closest',
            uirevision="Don't change zoom on update"
        )
        
        # Configurer les boutons Réinitialiser Zoom et Afficher Top 3
        fig.update_layout(
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                x=0.8,      # Position à droite
                y=1.0,      # Position basse (0 est en bas, 1 est en haut)
                xanchor="left",  # Aligné à droite
                yanchor="bottom",  
                bgcolor="rgba(240, 240, 240, 0.8)",  # Fond grisâtre semi-transparent
                bordercolor="rgba(0, 0, 0, 0.3)",
                buttons=[
                    dict(
                        label="Réinitialiser",
                        method="relayout",
                        args=[{"xaxis.range": [date_min, date_max]}]
                    )
                ]
            )]
        )
        
        # Afficher le graphique avec curseur interactif sans barre d'outils
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Afficher l'avertissement pour les années partielles
        display_partial_year_warning(selected_years, time_range)
        
        # Bulle d'info pour guider l'utilisation du Zoom
        tooltip_info("Information")
        st.info("""
            **Utilisation du zoom:**
            - Sélectionnez une zone sur le graphique pour zoomer
            - Utilisez le curseur en bas pour naviguer dans les données
            - **Points rouges** : Les trois points de consommation journalière les plus élevés pour chaque année sélectionnée
            - Pour revenir à la vue complète, cliquez sur "Réinitialiser" en haut à droite du graphique
        """)
        
        # Afficher la tendance globale après le plot pour le mode données complètes
        if analysis_mode != 'single_year':
            display_trend_arrows(test2, selected_years)
        
        # Création des boutons pour accéder aux dates des points maximaux dans un expander
        with st.expander("Voir les jours avec consommation maximale", expanded=False):
            st.markdown("Cliquez sur un jour pour voir sa consommation détaillée :")
            
            # Organiser les boutons par année
            max_dates_by_year = {}
            for year, month, day, date_str, full_date, consumption in max_point_dates:
                if year not in max_dates_by_year:
                    max_dates_by_year[year] = []
                max_dates_by_year[year].append((month, day, date_str, full_date, consumption))
            
            # Créer des colonnes pour chaque année
            if max_dates_by_year:
                num_years = len(max_dates_by_year)
                cols = st.columns(num_years)
                
                # Afficher les boutons dans chaque colonne
                for i, (year, dates) in enumerate(max_dates_by_year.items()):
                    with cols[i]:
                        st.subheader(f"Année {year}")
                        for month, day, date_str, full_date, consumption in dates:
                            # Créer un identifiant unique pour chaque bouton
                            button_id = f"max_day_{year}_{date_str}"
                            
                            # Adapter l'affichage selon le nombre d'années
                            if num_years >= 3:
                                # Avec 3 années, placer le bouton sous les infos pour plus d'espace
                                st.markdown(f"""
                                <div style="margin-bottom: 8px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                    <span style="color: #333; font-weight: normal;">{day}/{month} ({full_date})</span><br>
                                    <span style="color: red; font-weight: bold; font-size: 0.9em;">{consumption:.1f} kWh</span>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Bouton en pleine largeur sous les infos
                                if st.button(f"Voir le détail", key=button_id, use_container_width=True):
                                    # Convertir le mois en format français pour la session
                                    month_names_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                                                    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
                                    month_name_fr = month_names_fr[int(month) - 1]
                                    
                                    # Mettre à jour les variables de session pour la redirection
                                    st.session_state.selected_month = f"{month} - {month_name_fr}"
                                    st.session_state.selected_day = day
                                    st.session_state.click_detected = True
                                    st.session_state.last_max_point = button_id
                                    # Réinitialiser la résolution temporelle à "Horaire"
                                    st.session_state.day_resolution = "Horaire"
                                    # Forcer explicitement la vue Day
                                    st.session_state.current_view = "Day"
                                    # Marquer qu'une navigation est nécessaire
                                    st.session_state.navigate_to_courbe_charge = True
                                    
                                    # Recharger la page pour appliquer la redirection et aller vers courbe-charge
                                    st.rerun()
                            else:
                                # Avec 1-2 années, garder l'affichage côte à côte
                                info_col, button_col = st.columns([3, 1])
                                
                                with info_col:
                                    # Afficher la date et la consommation avec styling
                                    st.markdown(f"""
                                    <div style="margin-bottom: 8px; padding-top: 8px;">
                                        <span style="color: #333; font-weight: normal;">{day}/{month} ({full_date})</span><br>
                                        <span style="color: red; font-weight: bold; font-size: 0.9em;">{consumption:.1f} kWh</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with button_col:
                                    # Créer un bouton pour chaque date maximale
                                    if st.button(f"Voir le détail", key=button_id):
                                        # Convertir le mois en format français pour la session
                                        month_names_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                                                        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
                                        month_name_fr = month_names_fr[int(month) - 1]
                                        
                                        # Mettre à jour les variables de session pour la redirection
                                        st.session_state.selected_month = f"{month} - {month_name_fr}"
                                        st.session_state.selected_day = day
                                        st.session_state.click_detected = True
                                        st.session_state.last_max_point = button_id
                                        # Réinitialiser la résolution temporelle à "Horaire"
                                        st.session_state.day_resolution = "Horaire"
                                        # Forcer explicitement la vue Day
                                        st.session_state.current_view = "Day"
                                        # Marquer qu'une navigation est nécessaire
                                        st.session_state.navigate_to_courbe_charge = True
                                        
                                        # Recharger la page pour appliquer la redirection et aller vers courbe-charge
                                        st.rerun()
        
        
        
    elif time_range == "Season":
        # Réinitialiser pour permettre une nouvelle sélection de point maximal
        reset_max_point_navigation()
        
        season_months = {
            "Hiver (Jan-Mar)": [1, 2, 3],
            "Printemps (Avr-Juin)": [4, 5, 6],
            "Été (Juil-Sept)": [7, 8, 9],
            "Automne (Oct-Déc)": [10, 11, 12]
        }
        for year in selected_years:
            year_data = test2[test2['Year'] == year]
            season_sums = []
            for season, months in season_months.items():
                season_data = year_data[year_data.index.month.isin(months)]
                if not season_data.empty:
                    season_data = season_data.resample('D').sum(numeric_only=True)
                    season_sum = season_data['Consumption (kWh)'].sum()
                    season_sums.append(season_sum)
            year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
            fig.add_trace(go.Bar(x=list(season_months.keys()), y=season_sums, name=str(year), marker_color=year_color))
        
        # Préparer le titre dynamique pour la vue saisonnière
        if len(selected_years) == 1:
            season_title = f"Consommation saisonnière pour {selected_years[0]}"
        else:
            years_sorted = sorted(selected_years)
            if len(years_sorted) == 2:
                season_title = f"Consommation saisonnière pour {years_sorted[0]} et {years_sorted[1]}"
            else:
                season_title = f"Consommation saisonnière pour {min(years_sorted)} - {max(years_sorted)}"
        
        fig.update_layout(barmode='group', title=season_title, xaxis_title='Saison', yaxis_title='Consommation (kWh)')
        st.plotly_chart(fig)
        
        # Afficher l'avertissement pour les années partielles
        display_partial_year_warning(selected_years, time_range)
        
    elif time_range == "Week":
        # Réinitialiser pour permettre une nouvelle sélection de point maximal
        reset_max_point_navigation()
        
        # Dictionnaire pour mapper les numéros de jour aux noms en français
        weekday_names = {
            0: "Lundi",
            1: "Mardi", 
            2: "Mercredi",
            3: "Jeudi",
            4: "Vendredi",
            5: "Samedi",
            6: "Dimanche"
        }
        
        # Créer des positions de ticks pour le milieu de chaque jour
        tick_positions = [i * 24 + 12 for i in range(7)]  # Position à midi pour chaque jour
        tick_labels = [weekday_names[i] for i in range(7)]
        
        # Informations sur l'alignement des semaines pour le mode données complètes
        if analysis_mode != 'single_year' and len(selected_years) > 1:
            # Calculer les dates de début pour chaque année/semaine pour vérifier l'alignement
            week_alignment_info = []
            for year in sorted(selected_years):
                try:
                    # Calculer la date du lundi de cette semaine pour cette année
                    jan_1 = pd.Timestamp(f"{year}-01-01")
                    # Trouver le premier lundi de l'année
                    days_to_monday = (7 - jan_1.weekday()) % 7
                    if days_to_monday == 0 and jan_1.weekday() != 0:  # Si c'est dimanche
                        days_to_monday = 1
                    elif jan_1.weekday() == 0:  # Si c'est déjà lundi
                        days_to_monday = 0
                    else:
                        days_to_monday = (7 - jan_1.weekday()) % 7
                    
                    # Calculer la date du lundi de la semaine sélectionnée
                    week_start = jan_1 + pd.Timedelta(days=days_to_monday + (selected_week - 1) * 7)
                    week_start_monday = week_start - pd.Timedelta(days=week_start.weekday())
                    
                    week_alignment_info.append((year, week_start_monday.strftime('%d/%m/%Y')))
                except:
                    week_alignment_info.append((year, "Date invalide"))
            
            # Afficher l'information d'alignement
            alignment_text = " | ".join([f"{year}: Lundi {date}" for year, date in week_alignment_info])
            st.markdown(f"""
            <div style="background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;">
                <p style="margin: 0; font-size: 0.9em;"><strong>📅 Alignement des semaines :</strong></p>
                <p style="margin: 5px 0 0 0; font-size: 0.8em; color: #666;">{alignment_text}</p>
                <p style="margin: 5px 0 0 0; font-size: 0.8em; color: #888; font-style: italic;">
                    ⚠️ Les semaines ISO peuvent ne pas s'aligner parfaitement entre années (années bissextiles, décalages de calendrier)
                </p>
            </div>
            """, unsafe_allow_html=True)

        for year in selected_years:
            year_data = test2[test2['Year'] == year]
            week_data = year_data[year_data['Week'] == selected_week]
            if not week_data.empty:
                week_data = week_data.groupby([week_data.index.weekday, week_data.index.hour]).mean(numeric_only=True)
                
                # Préparer les données pour le hover avec information sur l'année
                hover_text = []
                for day, hour in week_data.index:
                    hover_text.append(f"{weekday_names[day]}, {hour}:00 ({year})")
                
                year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
                fig.add_trace(go.Scatter(
                    x=week_data.index.get_level_values(0) * 24 + week_data.index.get_level_values(1), 
                    y=week_data['Consumption (kWh)'], 
                    mode='lines', 
                    name=str(year), 
                    line=dict(color=year_color),
                    hovertemplate="Jour-Heure: %{text}<br>Consommation: %{y:.1f} kWh<extra></extra>",
                    text=hover_text
                ))
        
        # Afficher la date calendaire pour une seule année
        if len(selected_years) == 1:
            target_year = selected_years[0]
            try:
                # Calculer la date du lundi de la semaine sélectionnée pour cette année
                # Utiliser la méthode ISO pour obtenir le premier jour (lundi) de la semaine
                from datetime import datetime, timedelta
                
                # Créer une date pour le 4 janvier de l'année (toujours dans la semaine 1)
                jan_4 = datetime(target_year, 1, 4)
                
                # Trouver le lundi de la semaine 1
                monday_week_1 = jan_4 - timedelta(days=jan_4.weekday())
                
                # Calculer le lundi de la semaine sélectionnée
                monday_selected_week = monday_week_1 + timedelta(weeks=selected_week - 1)
                dimanche_selected_week = monday_selected_week + timedelta(days=6)
                
                # Formater les dates en français
                def format_date_fr(date):
                    months_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
                               "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                    return f"{date.day} {months_fr[date.month - 1]}"
                
                monday_str = format_date_fr(monday_selected_week)
                sunday_str = format_date_fr(dimanche_selected_week)
                
                st.markdown(f"""
                <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #4361ee;">
                    <p style="margin: 0; font-size: 0.9em;"><strong>📅 Semaine {selected_week} de {target_year} :</strong></p>
                    <p style="margin: 5px 0 0 0; font-size: 0.85em; color: #666;">Du lundi {monday_str} au dimanche {sunday_str}</p>
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                # En cas d'erreur dans le calcul, afficher juste le numéro de semaine
                st.markdown(f"""
                <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #4361ee;">
                    <p style="margin: 0; font-size: 0.9em;"><strong>📅 Semaine {selected_week} de {target_year}</strong></p>
                </div>
                """, unsafe_allow_html=True)
        
        fig.update_layout(
            title=f'Consommation énergétique pour la semaine {selected_week} pour les années sélectionnées', 
            xaxis_title='Jour de la semaine', 
            yaxis_title='Consommation (kWh)',
            xaxis=dict(
                tickvals=tick_positions,
                ticktext=tick_labels,
                tickmode='array'
            )
        )
        st.plotly_chart(fig)
        
        # Afficher l'avertissement pour les années partielles
        display_partial_year_warning(selected_years, time_range)
        
    elif time_range == "Day":
        for year in selected_years:
            year_data = test2[test2['Year'] == year]
            day_data = year_data[year_data.index.strftime('%m-%d') == selected_date.strftime('%m-%d')]
            
            if not day_data.empty:
                if resolution == "Horaire":
                    # Vue horaire (ancienne vue)
                    # Resample to 15 minutes
                    day_data_resampled = day_data.resample('15T').sum(numeric_only=True)
                    
                    # Create a new DataFrame to store hourly sums
                    hourly_data = pd.DataFrame(index=range(0, 24), columns=['Consumption (kWh)'])
                    hourly_data.index.name = 'Hour'
                    
                    # Calculate sums for each hour from 0 to 22 (00:15-23:00)
                    for hour in range(0, 23):
                        start_time = f'{hour:02d}:15:00'
                        end_time = f'{hour+1:02d}:00:00'
                        hourly_data.loc[hour, 'Consumption (kWh)'] = day_data_resampled.between_time(start_time, end_time)['Consumption (kWh)'].sum()
                    
                    # Special case for hour 23 (23:15-00:00)
                    midnight_data = day_data_resampled.between_time('23:15', '00:00').sum(numeric_only=True)
                    hourly_data.loc[23, 'Consumption (kWh)'] = midnight_data['Consumption (kWh)']
                    
                    year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
                    fig.add_trace(go.Scatter(
                        x=hourly_data.index, 
                        y=hourly_data['Consumption (kWh)'], 
                        mode='lines', 
                        name=str(year), 
                        line=dict(color=year_color),
                        hovertemplate="Heure: %{x}:00<br>Consommation: %{y:.1f} kWh<extra></extra>"
                    ))
                    
                    # Configuration pour la vue horaire
                    fig.update_layout(
                        title=f'Consommation énergétique du {format_date_french(selected_date)} par heure pour les années sélectionnées',
                        xaxis_title='Heure de la journée',
                        yaxis_title='Consommation (kWh)',
                        xaxis=dict(
                            tickmode='array',
                            tickvals=list(range(0, 24)),
                            ticktext=[f"{h:02d}:00" for h in range(0, 24)]
                        )
                    )
                    
                else:  # "Quart d'heure"
                    # Vue par quart d'heure (nouvelle vue)
                    # Resample au quart d'heure et formater les données pour affichage
                    quarter_data = day_data.resample('15T').sum(numeric_only=True)
                    
                    # Simplifier : utiliser l'index temporel directement
                    time_range_15min = pd.date_range(
                        start=quarter_data.index.min().replace(hour=0, minute=0),
                        end=quarter_data.index.min().replace(hour=23, minute=45),
                        freq='15T'
                    )
                    
                    # Reindexer pour avoir toutes les périodes de 15 minutes
                    quarter_data_complete = quarter_data.reindex(time_range_15min, fill_value=0)
                    
                    # Préparer les données pour l'affichage
                    quarter_values = quarter_data_complete['Consumption (kWh)'].values
                    hover_texts = [t.strftime('%H:%M') for t in quarter_data_complete.index]
                    quarter_index = list(range(len(quarter_values)))
                    
                    # Tracer les données
                    year_color = color_map.get(year, '#42A5F5')  # Couleur par défaut si l'année n'est pas trouvée
                    fig.add_trace(go.Scatter(
                        x=quarter_index,
                        y=quarter_values,
                        mode='lines',
                        name=str(year),
                        line=dict(color=year_color),
                        hovertemplate="Heure: %{text}<br>Consommation: %{y:.1f} kWh<extra></extra>",
                        text=hover_texts
                    ))
                    
                    # Configuration pour la vue quart d'heure
                    # Montrer uniquement les heures complètes pour éviter l'encombrement
                    tick_positions = []
                    tick_labels = []
                    # Position des ticks pour chaque heure
                    for i in range(0, len(quarter_index), 4):  # Tous les 4 quarts d'heure = 1 heure
                        if i < len(quarter_index):
                            tick_positions.append(i)
                            hour = i // 4
                            tick_labels.append(f"{hour:02d}:00")
                    
                    fig.update_layout(
                        title=f'Consommation énergétique du {format_date_french(selected_date)} par quart d\'heure pour les années sélectionnées',
                        xaxis_title='Heure de la journée',
                        yaxis_title='Consommation (kWh)',
                        xaxis=dict(
                            tickmode='array',
                            tickvals=tick_positions,
                            ticktext=tick_labels,
                            range=[0, len(quarter_index)-1]
                        )
                    )
        
        # Afficher le graphique
        st.plotly_chart(fig)
        
        # Afficher l'avertissement pour les années partielles
        display_partial_year_warning(selected_years, time_range)
        
        # Afficher une note explicative adaptée à la résolution sélectionnée
        if resolution == "Horaire":
            st.info("Note : Les consommations par heure correspondent à la somme de quatre quart d'heure")
        else:
            st.info("Note : Les données par quart d'heure montrent la consommation détaillée pour chaque période de 15 minutes.")
    

    # Function to filter data based on the selected time range
    def filter_data(df, time_range, selected_date, selected_week, selected_season):
        season_months = {
            "Hiver (Jan-Mar)": [1, 2, 3],
            "Printemps (Avr-Juin)": [4, 5, 6],
            "Été (Juil-Sept)": [7, 8, 9],
            "Automne (Oct-Déc)": [10, 11, 12]
        }
        if time_range == "Day":
            filtered_data = df[df.index.strftime('%m-%d') == selected_date.strftime('%m-%d')]
            # Utiliser st.session_state.day_resolution pour déterminer la résolution
            if st.session_state.day_resolution == "Horaire":
                filtered_data = filtered_data.resample('H', closed='right', label='right').sum(numeric_only=True)
                filtered_data = filtered_data.shift(-1, freq='15T')
            else:  # "Quart d'heure"
                filtered_data = filtered_data.resample('15T').sum(numeric_only=True)
        elif time_range == "Week":
            filtered_data = df[df['Week'] == selected_week]
            filtered_data = filtered_data.groupby([filtered_data.index.weekday, filtered_data.index.hour]).mean(numeric_only=True)
        elif time_range == "Year":
            # Filtrer d'abord par années sélectionnées
            filtered_data = df[df['Year'].isin(selected_years)]
            filtered_data = filtered_data.resample('D').sum(numeric_only=True)
        elif time_range == "Season":
            # En mode Saison, on retourne toutes les données (toutes les saisons sont affichées)
            filtered_data = df.resample('D').sum(numeric_only=True)
        return filtered_data

    # Filter the data based on the selected time range
    filtered_data = filter_data(test2, time_range, selected_date, selected_week, selected_season)

    incomplete_seasons = []
    season_months = {
        "Hiver (Jan-Mar)": [1, 2, 3],
        "Printemps (Avr-Juin)": [4, 5, 6],
        "Été (Juil-Sept)": [7, 8, 9],
        "Automne (Oct-Déc)": [10, 11, 12]
    }
    for season, months in season_months.items():
        if not all(month in test2.index.month for month in months):
            incomplete_seasons.append(season)
    if incomplete_seasons:
        st.markdown(f"**Saisons incomplètes:** {', '.join(incomplete_seasons)}")


# ============================================================================
# PISTES D'AMÉLIORATION DU MODULE INTERACTIVE_PLOT
# ============================================================================
#
# 1. **OPTIMISATION DES PERFORMANCES**:
#    - Mise en cache des calculs de tendance pour éviter recalculs répétés
#    - Lazy loading des données pour grandes séries temporelles
#    - Compression des données affichées selon le niveau de zoom
#    - Streaming des données pour fichiers très volumineux. 
# 
# 2. LAISSER LE CHOIX A L'UTILISATEUR DES COULEURS QU'IL SOUHAITE SUR L'APP POUR CHAQUE ANNEE DISPO (A APPLIQUER PARTOUT)
#
# Ces améliorations permettraient de faire évoluer le module vers une solution
# d'analyse énergétique de niveau professionnel tout en conservant la simplicité
# d'usage pour les particuliers.
#
# ============================================================================