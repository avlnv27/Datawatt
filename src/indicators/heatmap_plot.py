"""
# ============================================================================
# MODULE DE CARTOGRAPHIE ANNUELLE (HEATMAP) - DataWatt
# ============================================================================
# 
# OBJECTIF PRINCIPAL:
# Génération de cartographies thermiques interactives pour visualiser les
# patterns de consommation énergétique selon un calendrier annuel jour/mois,
# permettant l'identification rapide des pics et périodes de faible consommation.
#
# FONCTIONNALITÉS PRINCIPALES:
#
# 1. **VISUALISATION CALENDAIRE**:
#    - Matrice 12 mois × 31 jours avec consommation journalière colorée
#    - Échelle de couleurs divergente (rouge=élevé, vert=faible)
#    - Gestion intelligente des jours inexistants (29 fév, 31 avril, etc.)
#    - Annotations automatiques des 3 pics de consommation maximale
#
# 2. **MODES D'AFFICHAGE ADAPTATIFS**:
#    - Mode "Année unique" : Consommation exacte jour par jour
#    - Mode "Multi-années" : Moyenne des consommations par jour calendaire
#    - Détection automatique des données insuffisantes (< 6 mois)
#    - Adaptation selon disponibilité des années complètes
#
# 3. **ANALYSES STATISTIQUES INTÉGRÉES**:
#    - Identification automatique des 3 pics maximaux avec annotations
#    - Calcul des 3 consommations minimales journalières
#    - Analyse de variabilité inter-annuelle (pour professionnels)
#    - Métriques de stabilité (coefficient de variation)
#
# 4. **OPTIMISATION DES PERFORMANCES**:
#    - Cache intelligent des graphiques générés par configuration
#    - Évite les recalculs sur changements mineurs d'interface
#    - Clé de cache basée sur mode d'analyse + années sélectionnées
#    - Gestion mémoire optimisée pour grandes séries temporelles
#
# 5. **GESTION AVANCÉE DES DONNÉES**:
#    - Détection automatique de la colonne de consommation appropriée
#    - Validation de suffisance des données (minimum 6 mois/an)
#    - Gestion des valeurs manquantes (NaN) dans la matrice
#    - Agrégation quotidienne automatique depuis données horaires
#
# ARCHITECTURE TECHNIQUE:
# - Plotly Heatmap avec personnalisation avancée du rendu
# - NumPy pour matrices de données optimisées
# - Pandas pour agrégations temporelles et resampling
# - Session state pour cache et persistance des paramètres
#
# LOGIQUE MÉTIER:
# - Consommation journalière = somme des données horaires/15min sur 24h
# - Moyenne multi-années = moyenne des mêmes jours calendaires
# - Seuils de validation = minimum 6 mois de données pour fiabilité
# - Échelle colorimétrique = adaptation automatique min/max des données
#
# ============================================================================
"""

import streamlit as st
import plotly.express as px
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.textual.tools import tooltip_info

def display_heatmap(test2):
    # Determine which consumption column to use
    consumption_col = 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in test2.columns else 'Consumption (kWh)'
    
    # Récupérer le mode d'analyse depuis la session
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    years_to_use = st.session_state.get('years_to_use', [])
    
    # CACHE INTELLIGENT pour éviter les recalculs
    cache_key = f"annual_heatmap_{analysis_mode}_{'_'.join(map(str, sorted(years_to_use)))}"
    
    # Vérifier si le graphique est déjà en cache
    if cache_key in st.session_state:
        # Afficher depuis le cache
        st.plotly_chart(st.session_state[cache_key], use_container_width=True)
        return
    
    # Sinon, calculer et mettre en cache
    fig = None
    
    # Affichage adapté selon le mode d'analyse
    if analysis_mode == 'single_year':
        # Mode année unique : afficher directement l'année sélectionnée
        selected_year = st.session_state.get('selected_analysis_year')
        years_available = sorted(test2.index.year.unique())
        
        if selected_year not in years_available:
            selected_year = years_available[0] if years_available else None
        
        if selected_year:
            fig = display_single_year_heatmap(test2, selected_year, consumption_col)
        else:
            st.error("Aucune année disponible pour afficher la heatmap.")
            
    else:
        # Mode données complètes : affichage de la moyenne multi-années uniquement
        years_available = sorted(test2.index.year.unique())
        
        if len(years_to_use) == 1:
            # Une seule année disponible, affichage direct
            selected_year = years_to_use[0]
            fig = display_single_year_heatmap(test2, selected_year, consumption_col)
            
        else:
            # Plusieurs années disponibles : affichage automatique de la moyenne multi-années
            # Vérifier si les données sont suffisamment complètes pour afficher une heatmap
            if is_data_sufficient_for_heatmap(test2, years_to_use, consumption_col):
                fig = display_multi_year_average_heatmap(test2, years_to_use, consumption_col)
            else:
                st.warning("⚠️ **Données insuffisantes** : Les données disponibles ne permettent pas de générer une cartographie annuelle fiable. "
                          "Il faut au minimum des données pour 6 mois de l'année sur au moins une des années sélectionnées.")
    
    # Mettre en cache le graphique généré
    if fig is not None:
        st.session_state[cache_key] = fig

def display_single_year_heatmap(test2, selected_year, consumption_col):
    """
    Affiche la heatmap pour une année spécifique avec la consommation journalière totale
    """

    # Filter data for the selected year
    year_data = test2[test2.index.year == selected_year]
    
    if not year_data.empty:
        # Calculer la consommation journalière totale (somme par jour)
        daily_consumption = year_data.resample('D')[consumption_col].sum()
        
        # Create a heatmap with missing values handled
        heatmap_data = np.full((12, 31), np.nan)  # Initialize with NaN for missing values
        
        # Remplir la matrice avec les consommations journalières
        for date, consumption in daily_consumption.items():
            if consumption > 0:  # Seulement si il y a une consommation
                month = date.month
                day = date.day
                heatmap_data[month-1, day-1] = consumption

        # Month names in French
        month_names = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                      "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        
        # Identify min and max for better color scaling
        valid_data = heatmap_data[~np.isnan(heatmap_data)]
        min_consumption = np.min(valid_data) if valid_data.size > 0 else 0
        max_consumption = np.max(valid_data) if valid_data.size > 0 else 1
        
        # Use the same color scale as the weekly cartography heatmap
        colorscale = px.colors.diverging.RdYlGn[::-1]
        
        # Create the heatmap with a custom colorscale
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=[str(i) for i in range(1, 32)],
            y=month_names,
            colorscale=colorscale,
            zmin=min_consumption,
            zmax=max_consumption,
            colorbar=dict(
                title=dict(
                    text="Consommation journalière (kWh)",
                    side="right"
                ),
                thickness=20,
                tickfont=dict(size=12)
            ),
            hovertemplate="Jour: %{x}<br>Mois: %{y}<br>Consommation journalière: %{z:.1f} kWh<extra></extra>",
            hoverongaps=False
        ))
        
        # Customize layout
        fig.update_layout(
            title={
                'text': f"Consommation journalière par mois ({selected_year})",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18)
            },
            xaxis_title="Jour du Mois",
            yaxis_title="Mois",
            xaxis=dict(
                tickmode='array',
                tickvals=[str(i) for i in range(1, 32, 2)],
                tickfont=dict(size=13)
            ),
            yaxis=dict(
                tickfont=dict(size=13),
                autorange="reversed"  # To have January at the top
            ),
            width=650,
            height=600,
            margin=dict(l=50, r=50, t=80, b=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add annotations for top 3 consumption periods
        add_peak_annotations(fig, heatmap_data, month_names)
        
        
        # Display the heatmap
        st.plotly_chart(fig, use_container_width=True)
        
        # Add insights
        display_heatmap_insights(heatmap_data, month_names, f"de {selected_year}")
    else:
        st.markdown(f"Aucune donnée disponible pour {selected_year}")

def display_multi_year_average_heatmap(test2, years_to_use, consumption_col):
    """
    Affiche la heatmap moyenne sur plusieurs années avec la consommation journalière moyenne
    """
    # Filtrer les données pour les années sélectionnées
    filtered_data = test2[test2.index.year.isin(years_to_use)]
    
    if not filtered_data.empty:
        # Calculer la consommation journalière pour chaque jour de chaque année
        daily_consumption_by_year = {}
        
        for year in years_to_use:
            year_data = filtered_data[filtered_data.index.year == year]
            if not year_data.empty:
                daily_consumption_by_year[year] = year_data.resample('D')[consumption_col].sum()
        
        # Create a heatmap with missing values handled
        heatmap_data = np.full((12, 31), np.nan)  # Initialize with NaN for missing values
        
        # Pour chaque jour de l'année, calculer la moyenne des consommations sur les années disponibles
        for month in range(1, 13):
            for day in range(1, 32):
                # Vérifier si ce jour existe (éviter les 30 février, etc.)
                try:
                    # Utiliser une année bissextile comme référence pour avoir tous les jours possibles
                    test_date = pd.Timestamp(2024, month, day)
                    
                    # Collecter les consommations pour ce jour sur toutes les années
                    day_consumptions = []
                    for year, daily_data in daily_consumption_by_year.items():
                        try:
                            date_to_check = pd.Timestamp(year, month, day)
                            if date_to_check in daily_data.index and daily_data[date_to_check] > 0:
                                day_consumptions.append(daily_data[date_to_check])
                        except:
                            # Le jour n'existe pas cette année (ex: 29 février sur année non bissextile)
                            continue
                    
                    # Si on a des données pour ce jour, calculer la moyenne
                    if day_consumptions:
                        heatmap_data[month-1, day-1] = np.mean(day_consumptions)
                        
                except:
                    # Le jour n'existe pas (ex: 31 avril)
                    continue

        # Month names in French
        month_names = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                      "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        
        # Identify min and max for better color scaling
        valid_data = heatmap_data[~np.isnan(heatmap_data)]
        min_consumption = np.min(valid_data) if valid_data.size > 0 else 0
        max_consumption = np.max(valid_data) if valid_data.size > 0 else 1
        
        # Use the same color scale as the weekly cartography heatmap
        colorscale = px.colors.diverging.RdYlGn[::-1]
        
        # Create the heatmap with a custom colorscale
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=[str(i) for i in range(1, 32)],
            y=month_names,
            colorscale=colorscale,
            zmin=min_consumption,
            zmax=max_consumption,
            colorbar=dict(
                title=dict(
                    text="Consommation journalière moyenne (kWh)",
                    side="right"
                ),
                thickness=20,
                tickfont=dict(size=12)
            ),
            hovertemplate="Jour: %{x}<br>Mois: %{y}<br>Consommation journalière moyenne: %{z:.1f} kWh<extra></extra>",
            hoverongaps=False
        ))
        
        # Customize layout
        years_range = f"{min(years_to_use)}-{max(years_to_use)}" if len(years_to_use) > 1 else str(years_to_use[0])
        fig.update_layout(
            title={
                'text': f"Consommation journalière moyenne par mois ({years_range})",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18)
            },
            xaxis_title="Jour du Mois",
            yaxis_title="Mois",
            xaxis=dict(
                tickmode='array',
                tickvals=[str(i) for i in range(1, 32, 2)],
                tickfont=dict(size=13)
            ),
            yaxis=dict(
                tickfont=dict(size=13),
                autorange="reversed"  # To have January at the top
            ),
            width=650,
            height=600,
            margin=dict(l=50, r=50, t=80, b=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        # Add annotations for top 3 consumption periods
        add_peak_annotations(fig, heatmap_data, month_names)
        
        
        # Display the heatmap
        st.plotly_chart(fig, use_container_width=True)
        
        # Add insights
        display_heatmap_insights(heatmap_data, month_names, f"en moyenne sur {len(years_to_use)} années")
        
        # Afficher des informations sur la variabilité entre années seulement pour les professionnels
        user_type = st.session_state.get('user_type', "Particulier")
        if user_type == "Professionnel":
            display_year_variability_info(filtered_data, consumption_col, years_to_use)
        
    else:
        st.markdown("Aucune donnée disponible pour les années sélectionnées")

def add_peak_annotations(fig, heatmap_data, month_names):
    """
    Ajoute les annotations pour les pics de consommation
    """
    # Add annotations for top 3 consumption periods
    # Get only valid data (non-NaN) to find the peaks
    valid_mask = ~np.isnan(heatmap_data)
    if np.any(valid_mask):
        # Create a masked array with only valid values
        masked_data = heatmap_data[valid_mask]
        if len(masked_data) >= 3:
            # Get indices of top 3 values
            flat_indices = np.argsort(masked_data)[-3:]
            # Convert flattened indices back to 2D indices in the masked array
            flat_positions = np.flatnonzero(valid_mask)
            top_positions = flat_positions[flat_indices]
            # Convert to month, day indices
            month_indices, day_indices = np.unravel_index(top_positions, heatmap_data.shape)
            
            for month_idx, day_idx in zip(month_indices, day_indices):
                fig.add_annotation(
                    x=str(day_idx + 1),  # +1 because days start at 0 but display at 1
                    y=month_names[month_idx],
                    text="Pic!",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="#ffffff",
                    font=dict(color="white", size=10),
                    bgcolor="rgba(0,0,0,0.7)",
                    bordercolor="white",
                    borderwidth=1,
                    borderpad=4,
                    opacity=0.8
                )

def display_heatmap_insights(heatmap_data, month_names, period_description):
    """
    Affiche les insights de la heatmap (min/max)
    """
    # Ajouter un espacement
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Find top 3 days with max consumption
        valid_data = heatmap_data[~np.isnan(heatmap_data)]
        if valid_data.size >= 3:
            # Get indices of top 3 values
            flat_data = heatmap_data.flatten()
            valid_indices = ~np.isnan(flat_data)
            valid_values = flat_data[valid_indices]
            top_3_indices = np.argsort(valid_values)[-3:][::-1]  # Reverse to get highest first
            
            # Convert back to 2D indices
            flat_positions = np.flatnonzero(valid_indices)
            top_positions = flat_positions[top_3_indices]
            top_coords = np.unravel_index(top_positions, heatmap_data.shape)
            
            st.markdown("<h5 style='text-align: center; color: #666666;'>Pics de consommation journalière (maximales)</h5>", unsafe_allow_html=True)
            
            for i, (month_idx, day_idx) in enumerate(zip(top_coords[0], top_coords[1])):
                value = heatmap_data[month_idx, day_idx]
                st.markdown(f"""
                <div style='padding: 12px; margin: 5px 0; border-left: 4px solid #e74c3c; background-color: #f8f9fa; border-radius: 8px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
                        <span style='color: #e74c3c; font-weight: bold; font-size: 1.0em;'>{day_idx+1} {month_names[month_idx]}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{value:.1f} kWh</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Fallback to single max if less than 3 values
            max_idx = np.nanargmax(heatmap_data)
            max_month, max_day = np.unravel_index(max_idx, heatmap_data.shape)
            max_value = heatmap_data[max_month, max_day]
            
            st.markdown("<h5 style='text-align: center; color: #666666;'>Pic de consommation journalière</h5>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style='padding: 15px; margin: 5px 0; border-left: 4px solid #e74c3c; background-color: #f8f9fa; border-radius: 8px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <span style='color: #e74c3c; font-weight: bold; font-size: 1.1em;'>⚡ {max_day+1} {month_names[max_month]}</span>
                    <span style='font-size: 1.2em; font-weight: bold;'>{max_value:.1f} kWh</span>
                </div>
                <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                    <strong>Maximum</strong> {period_description}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Find top 3 days with min consumption (excluding zeros)
        valid_data = heatmap_data[~np.isnan(heatmap_data) & (heatmap_data > 0)]
        if valid_data.size >= 3:
            # Get indices of bottom 3 values (minimum)
            flat_data = heatmap_data.flatten()
            valid_indices = ~np.isnan(flat_data) & (flat_data > 0)
            valid_values = flat_data[valid_indices]
            bottom_3_indices = np.argsort(valid_values)[:3]  # Get 3 smallest
            
            # Convert back to 2D indices
            flat_positions = np.flatnonzero(valid_indices)
            bottom_positions = flat_positions[bottom_3_indices]
            bottom_coords = np.unravel_index(bottom_positions, heatmap_data.shape)
            
            st.markdown("<h5 style='text-align: center; color: #666666;'>Consommations journalières minimales</h5>", unsafe_allow_html=True)
            
            for i, (month_idx, day_idx) in enumerate(zip(bottom_coords[0], bottom_coords[1])):
                value = heatmap_data[month_idx, day_idx]
                st.markdown(f"""
                <div style='padding: 12px; margin: 5px 0; border-left: 4px solid #27ae60; background-color: #f8f9fa; border-radius: 8px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
                        <span style='color: #27ae60; font-weight: bold; font-size: 1.0em;'>{day_idx+1} {month_names[month_idx]}</span>
                        <span style='font-size: 1.1em; font-weight: bold;'>{value:.1f} kWh</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        elif valid_data.size > 0:
            # Fallback to single min if less than 3 values
            min_value = np.min(valid_data)
            min_idx = np.where((heatmap_data == min_value) & (heatmap_data > 0))
            min_month, min_day = min_idx[0][0], min_idx[1][0]
            
            st.markdown("<h5 style='text-align: center; color: #666666;'>Consommation journalière minimale</h5>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style='padding: 15px; margin: 5px 0; border-left: 4px solid #27ae60; background-color: #f8f9fa; border-radius: 8px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                    <span style='color: #27ae60; font-weight: bold; font-size: 1.1em;'>💤 {min_day+1} {month_names[min_month]}</span>
                    <span style='font-size: 1.2em; font-weight: bold;'>{min_value:.1f} kWh</span>
                </div>
                <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                    <strong>Minimum</strong> {period_description}
                </div>
            </div>
            """, unsafe_allow_html=True)

def display_year_variability_info(filtered_data, consumption_col, years_to_use):
    """
    Affiche des informations sur la variabilité entre les années
    """
    if len(years_to_use) > 1:
        # Calculer la consommation annuelle pour chaque année
        annual_consumption = {}
        for year in years_to_use:
            year_data = filtered_data[filtered_data.index.year == year]
            if not year_data.empty:
                annual_consumption[year] = year_data[consumption_col].sum()
        
        if len(annual_consumption) > 1:
            values = list(annual_consumption.values())
            avg_consumption = np.mean(values)
            std_consumption = np.std(values)
            cv = (std_consumption / avg_consumption) * 100  # Coefficient de variation
            
            st.markdown("---")
            st.subheader("Variabilité entre les années")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Consommation moyenne", f"{avg_consumption:.0f} kWh/an")
            
            with col2:
                st.metric("Écart-type", f"{std_consumption:.0f} kWh")
            
            with col3:
                st.metric("Variabilité", f"{cv:.1f}%")
            
            # Interprétation de la variabilité
            if cv < 5:
                st.success("✅ **Consommation très stable** entre les années (variabilité < 5%)")
            elif cv < 15:
                st.info("ℹ️ **Consommation relativement stable** (variabilité modérée)")
            else:
                st.warning("⚠️ **Consommation variable** entre les années (variabilité > 15%). "
                          "Cela peut indiquer des changements d'habitudes ou d'équipements.")

def is_data_sufficient_for_heatmap(test2, years_to_use, consumption_col):
    """
    Vérifie si les données sont suffisantes pour générer une heatmap annuelle fiable
    
    Args:
        test2: DataFrame avec les données
        years_to_use: Liste des années à analyser
        consumption_col: Nom de la colonne de consommation
        
    Returns:
        bool: True si les données sont suffisantes, False sinon
    """
    # Filtrer les données pour les années sélectionnées
    filtered_data = test2[test2.index.year.isin(years_to_use)]
    
    if filtered_data.empty:
        return False
    
    # Vérifier qu'il y a au moins une année avec des données pour au moins 6 mois
    for year in years_to_use:
        year_data = filtered_data[filtered_data.index.year == year]
        if not year_data.empty:
            # Compter le nombre de mois avec des données
            months_with_data = len(year_data.index.month.unique())
            if months_with_data >= 6:  # Au moins 6 mois de données
                return True
    
    return False