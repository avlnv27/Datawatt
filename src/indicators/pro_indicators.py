"""
MODULE D'INDICATEURS PROFESSIONNELS POUR ÉTABLISSEMENTS SCOLAIRES - NON UTILISÉ EN L'ÉTAT

Ce module contient des fonctions d'analyse spécialisées pour les établissements professionnels et scolaires,
en particulier les collèges, mais n'est actuellement pas intégré dans l'application web principale.

FONCTIONNALITÉS DISPONIBLES:
- display_surface_consumption_c() : Calcul et affichage de la consommation par surface (version collège)
- display_surface_consumption_am() : Calcul et affichage de la consommation par surface (version administration)
- display_college_comparison() : Comparaison détaillée avec les données de référence des collèges

ANALYSE DE RÉFÉRENCE COLLÈGES:
Le module inclut une fonction sophistiquée de comparaison avec une base de données de référence
de collèges (daily_period_stats_overall.csv) permettant:
- Normalisation par surface pour comparaison équitable
- Analyse par périodes (nuit, matin, après-midi, soirée)
- Visualisation avec percentiles (25ème-75ème) pour contextualiser les performances
- Recommandations automatiques basées sur les écarts observés
- Identification des opportunités d'optimisation énergétique

ARCHITECTURE TECHNIQUE:
- Interface Streamlit avec composants interactifs
- Graphiques Plotly pour visualisations comparatives
- Gestion intelligente des colonnes de consommation
- Calculs surfaciques avec métriques kWh/m²/jour et kWh/m²/an
- Système de recommandations basé sur les écarts statistiques

ÉTAT ACTUEL: Module développé mais non déployé
UTILISATION: Prêt pour intégration future dans l'onglet d'analyse comparative ou module spécialisé
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from pathlib import Path
import os
from src.textual.format_number import get_consumption_column


def display_surface_consumption_c(df, surface, years):
    """
    Calcule et affiche la consommation par surface de manière stylisée avec comparaison aux standards Minergie
    """
    # Determine which consumption column to use
    consumption_col = get_consumption_column(df)
    
    # Expander with detailed explanation
    with st.expander("À propos de la consommation par m² et standards Minergie"):
        st.markdown("""
        ### Qu'est-ce que la consommation par m² ?
        
        Cet indicateur mesure votre consommation électrique quotidienne et annuelle par mètre carré de surface. 
    """)
    
    # Get list of available years
    years_to_use = st.session_state.get('years_to_use', [])
    available_years = sorted([year for year in df.index.year.unique() if year in years_to_use])
    
    # Year selection
    if available_years:
        default_year_index = 0
        selected_year = st.selectbox("Sélectionnez une année ici", 
                            options=available_years, 
                            index=default_year_index,
                            key="surface_year_select")
        
        # Get data for selected year only
        year_data = df[df.index.year == selected_year]
        
        # Calculate daily average consumption for selected year
        daily_avg = year_data[consumption_col].resample('D').sum().mean()
        
        # Calculate surface values
        surface_daily_consumption = daily_avg / surface
        
        # Calculate total consumption for selected year
        total_year = year_data[consumption_col].sum()
        yearly_surface_consumption = total_year / surface
        
        # Calculate yearly values for comparison across years
        yearly_values = {}
        for year in available_years:
            year_data = df[df.index.year == year]
            total_consumption = year_data[consumption_col].sum()
            yearly_values[year] = total_consumption / surface
            
        # Create list of yearly values for display
        surfc_list = [yearly_values[year] for year in available_years]
    else:
        # Fallback if no years are available
        surface_daily_consumption = 0
        yearly_surface_consumption = 0
        selected_year = "N/A"
        surfc_list = []

        # Stylish display
    st.markdown(f"""
    <div style="max-width: 500px; margin: 20px auto; text-align: center;">
        <div style="border: 2px solid #ff1100; border-radius: 15px; padding: 25px; background-color: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="color: #666666; margin-bottom: 15px;">Consommation par surface</h3>
            <div style="display: flex; justify-content: space-around; margin: 20px 0;">
                <div>
                    <p style="font-size: 0.9em; color: #666;">Par jour ({selected_year})</p>
                    <p style="font-size: 2em; font-weight: bold; color: #ff1100;">{surface_daily_consumption:.2f}</p>
                    <p style="font-size: 0.9em; color: #666;">kWh/m²/jour</p>
                </div>
                <div>
                    <p style="font-size: 0.9em; color: #666;">Total ({selected_year})</p>
                    <p style="font-size: 2em; font-weight: bold; color: #ff1100;">{yearly_surface_consumption:.2f}</p>
                    <p style="font-size: 0.9em; color: #666;">kWh/m²/an</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    return surface_daily_consumption, yearly_surface_consumption, surfc_list


def display_surface_consumption_am(df, surface, years):
    """
    Calcule et affiche la consommation par surface de manière stylisée avec comparaison aux standards Minergie
    """
    # Determine which consumption column to use
    consumption_col = get_consumption_column(df)
    
    # Expander with detailed explanation
    with st.expander("À propos de la consommation par m² et standards Minergie"):
        st.markdown("""
        ### Qu'est-ce que la consommation par m² ?
        
        Cet indicateur mesure votre consommation électrique quotidienne et annuelle par mètre carré de surface. 
    """)
    
    # Get list of available years
    years_to_use = st.session_state.get('years_to_use', [])
    available_years = sorted([year for year in df.index.year.unique() if year in years_to_use])
    
    # Year selection
    if available_years:
        default_year_index = 0
        selected_year = st.selectbox("Sélectionnez une année ici", 
                            options=available_years, 
                            index=default_year_index,
                            key="surface_year_select")
        
        # Get data for selected year only
        year_data = df[df.index.year == selected_year]
        
        # Calculate daily average consumption for selected year
        daily_avg = year_data[consumption_col].resample('D').sum().mean()
        
        # Calculate surface values
        surface_daily_consumption = daily_avg / surface
        
        # Calculate total consumption for selected year
        total_year = year_data[consumption_col].sum()
        yearly_surface_consumption = total_year / surface
        
        # Calculate yearly values for comparison across years
        yearly_values = {}
        for year in available_years:
            year_data = df[df.index.year == year]
            total_consumption = year_data[consumption_col].sum()
            yearly_values[year] = total_consumption / surface
            
        # Create list of yearly values for display
        surfc_list = [yearly_values[year] for year in available_years]
    else:
        # Fallback if no years are available
        surface_daily_consumption = 0
        yearly_surface_consumption = 0
        selected_year = "N/A"
        surfc_list = []

        # Stylish display
    st.markdown(f"""
    <div style="max-width: 500px; margin: 20px auto; text-align: center;">
        <div style="border: 2px solid #ff1100; border-radius: 15px; padding: 25px; background-color: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="color: #666666; margin-bottom: 15px;">Consommation par surface</h3>
            <div style="display: flex; justify-content: space-around; margin: 20px 0;">
                <div>
                    <p style="font-size: 0.9em; color: #666;">Par jour ({selected_year})</p>
                    <p style="font-size: 2em; font-weight: bold; color: #ff1100;">{surface_daily_consumption:.2f}</p>
                    <p style="font-size: 0.9em; color: #666;">kWh/m²/jour</p>
                </div>
                <div>
                    <p style="font-size: 0.9em; color: #666;">Total ({selected_year})</p>
                    <p style="font-size: 2em; font-weight: bold; color: #ff1100;">{yearly_surface_consumption:.2f}</p>
                    <p style="font-size: 0.9em; color: #666;">kWh/m²/an</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    return surface_daily_consumption, yearly_surface_consumption, surfc_list




def display_college_comparison(user_data):
    """
    Display comparison between user's data and college reference data.
    
    Parameters:
    -----------
    user_data : DataFrame
        User's electricity consumption data
    """
    # Load college reference data
    try:
        csv_path = Path(os.path.join("data", "csv_college", "daily_period_stats_overall.csv"))
        if not csv_path.exists():
            st.error("Les données de référence des collèges n'ont pas été trouvées.")
            return
            
        college_data = pd.read_csv(csv_path)
        
        # Process user data - calculate hourly averages
        user_data['Hour'] = user_data.index.hour
        
        # Determine which column to use for consumption
        # This handles different possible column names in user data
        if 'Consumption' in user_data.columns:
            consumption_col = 'Consumption'
        elif 'Consumption (kWh)' in user_data.columns:
            consumption_col = 'Consumption (kWh)'
        else:
            # Try to find the first numeric column that's not Hour, Year, Month, etc.
            numeric_cols = [col for col in user_data.columns 
                           if col not in ['Hour', 'Year', 'Month', 'Day', 'Weekday'] 
                           and pd.api.types.is_numeric_dtype(user_data[col])]
            
            if numeric_cols:
                consumption_col = numeric_cols[0]
            else:
                st.error("Aucune colonne de consommation détectée dans vos données.")
                return
        
        # Get building surface area from session state
        user_surface = st.session_state.get('surface_am', 100)  # Default to 100 m² if not provided
        
        # Calculate hourly averages and normalize by surface area
        hourly_avg = user_data.groupby('Hour')[consumption_col].mean()*4 / user_surface
        
        # Create period averages from user data to match college periods
        night_avg = hourly_avg[0:6].mean()
        morning_avg = hourly_avg[6:12].mean()
        afternoon_avg = hourly_avg[12:18].mean()
        evening_avg = hourly_avg[18:24].mean()
        overall_avg = hourly_avg.mean()
        
        user_periods = {
            'Nuit (0h-6h)': night_avg,
            'Matin (6h-12h)': morning_avg,
            'Après-midi (12h-18h)': afternoon_avg,
            'Soirée (18h-24h)': evening_avg,
            'Journée entière': overall_avg
        }
        
        # Get periods excluding "Journée entière" for the line chart
        periods = college_data['period'].tolist()
        daily_periods = [p for p in periods if p != 'Journée entière']
        
        # Display information about the normalization
        st.info(f"Vos données de consommation ont été normalisées par la surface de {user_surface} m² pour permettre une comparaison équitable avec les références des collèges.")
        
        # GRAPH 1: Line chart for periods
        fig1 = go.Figure()
        
        # Add college reference data as a solid line
        fig1.add_trace(go.Scatter(
            x=daily_periods,
            y=college_data.loc[college_data['period'].isin(daily_periods), 'mean_power'],
            mode='lines+markers',
            name='Moyenne des collèges',
            line=dict(color='#1f77b4', width=3)
        ))
        
        # Add 25th percentile as a dotted line
        fig1.add_trace(go.Scatter(
            x=daily_periods,
            y=college_data.loc[college_data['period'].isin(daily_periods), '25th_percentile'],
            mode='lines',
            line=dict(color='#1f77b4', width=2, dash='dot'),
            name='25ème percentile'
        ))
        
        # Add 75th percentile as a dotted line
        fig1.add_trace(go.Scatter(
            x=daily_periods,
            y=college_data.loc[college_data['period'].isin(daily_periods), '75th_percentile'],
            mode='lines',
            line=dict(color='#1f77b4', width=2, dash='dot'),
            name='75ème percentile'
        ))
        
        # Add user data as a line
        user_values_daily = [user_periods[p] for p in daily_periods]
        fig1.add_trace(go.Scatter(
            x=daily_periods,
            y=user_values_daily,
            mode='lines+markers',
            name='Votre établissement',
            line=dict(color='#ff7f0e', width=3)
        ))
        
        # Customize layout
        fig1.update_layout(
            title='Consommation surfacique par période de la journée',
            xaxis_title='Période de la journée',
            yaxis_title='Consommation moyenne par m² (kWh/m²)',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # Provide insights
        st.subheader("Analyse comparative")
        
        # Calculate percentage differences
        differences = []
        for period in periods:
            college_value = college_data.loc[college_data['period'] == period, 'mean_power'].values[0]
            user_value = user_periods[period]
            pct_diff = ((user_value - college_value) / college_value) * 100
            differences.append((period, pct_diff))
        
        # Display insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Points clés")
            st.markdown("- Comparaison de votre consommation surfacique (kWh/m²) avec les moyennes de référence des collèges")
            st.markdown("- Les lignes pointillées représentent où se situent 50% des collèges (entre le 25ème et 75ème percentile)")
            st.markdown("- Analyse par périodes pour identifier les opportunités d'optimisation énergétique rapportée à la surface")
            st.markdown("- La normalisation par surface permet une comparaison équitable entre bâtiments de tailles différentes")
        
        with col2:
            st.markdown("#### Différences notables")
            for period, diff in differences:
                if abs(diff) > 15:  # Only highlight significant differences
                    if diff > 0:
                        st.markdown(f"- **{period}**: +{diff:.1f}% par rapport à la consommation surfacique moyenne des collèges 📈")
                    else:
                        st.markdown(f"- **{period}**: {diff:.1f}% par rapport à la consommation surfacique moyenne des collèges 📉")
        
        # Recommendations based on the comparison
        st.subheader("Recommandations")
        
        # Find the period with the highest consumption compared to reference
        highest_diff_period = max(differences, key=lambda x: x[1])
        
        if highest_diff_period[1] > 20:
            st.markdown(f"""
            💡 **Optimisation prioritaire**: Votre consommation surfacique durant la période **{highest_diff_period[0]}** est 
            significativement plus élevée que la moyenne des collèges ({highest_diff_period[1]:.1f}% supérieure). 
            Nous recommandons de:
            - Vérifier les équipements actifs durant cette période et leur efficacité énergétique
            - Évaluer la possibilité de programmer certains équipements en dehors de cette période
            - Examiner l'isolation et les systèmes de chauffage/climatisation si cette période correspond aux heures de chauffage/refroidissement
            """)
        
        # Look for opportunities in night consumption
        night_diff = next((diff for period, diff in differences if period == "Nuit (0h-6h)"), 0)
        if night_diff > 10:
            st.markdown("""
            💡 **Consommation nocturne par m²**: Votre consommation surfacique nocturne est supérieure à la moyenne des collèges. 
            Vérifiez:
            - Les systèmes qui restent actifs la nuit (serveurs, éclairage, chauffage)
            - La présence de minuteries ou de détecteurs de présence
            - La possibilité de mettre en veille plus d'équipements
            - L'isolation du bâtiment qui peut impacter les besoins en chauffage/climatisation nocturnes
            """)
            
        # Check overall consumption
        overall_diff = next((diff for period, diff in differences if period == "Journée entière"), 0)
        if overall_diff < -10:
            st.markdown("""
            ✅ **Bonne performance globale**: Votre consommation surfacique globale est inférieure à la moyenne des collèges.
            Continuez vos efforts d'efficacité énergétique par unité de surface!
            """)
        elif overall_diff > 10:
            st.markdown("""
            ⚠️ **Opportunité d'amélioration globale**: Votre consommation énergétique par m² est supérieure à la moyenne.
            Envisagez un audit énergétique complet pour identifier les principaux postes de consommation et leur efficacité.
            """)
            
    except Exception as e:
        st.error(f"Erreur lors de la comparaison avec les données de collège: {str(e)}")
        st.exception(e)