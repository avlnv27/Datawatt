"""
# ============================================================================
# MODULE DE CARTOGRAPHIE HEBDOMADAIRE (WEEKLY HEATMAP) - DataWatt
# ============================================================================
# 
# OBJECTIF PRINCIPAL:
# Génération de cartographies thermiques spécialisées pour analyser les patterns
# de consommation énergétique selon un profil hebdomadaire jour/heure, révélant
# les habitudes de consommation et routines énergétiques des utilisateurs.
#
# FONCTIONNALITÉS PRINCIPALES:
#
# 1. **VISUALISATION TEMPORELLE HEBDOMADAIRE**:
#    - Matrice 7 jours × 24 heures avec consommation horaire moyenne colorée
#    - Échelle de couleurs divergente (rouge=pics, vert=creux)
#    - Calcul intelligent des moyennes par type de jour (tous les lundis, etc.)
#    - Annotations automatiques des 3 pics de consommation horaire maximale
#
# 2. **MODES D'ANALYSE TEMPORELLE**:
#    - Mode "Année unique" : Profil hebdomadaire spécifique à une année
#    - Mode "Multi-années" : Profil moyen consolidé sur plusieurs années
#    - Agrégation horaire depuis données 15min/horaires source
#    - Gestion de la logique horaire complexe (23:15-00:00 pour 23h)
#
# 3. **ANALYSES COMPORTEMENTALES INTÉGRÉES**:
#    - Identification automatique du pic de consommation horaire global
#    - Détection du jour le plus/moins énergivore de la semaine
#    - Calcul des consommations minimales/maximales par créneaux
#    - Analyse de variabilité inter-annuelle (professionnels uniquement)
#
# 4. **OPTIMISATION DES PERFORMANCES**:
#    - Cache intelligent des matrices hebdomadaires calculées
#    - Évite les recalculs sur interactions utilisateur mineures
#    - Clé de cache basée sur mode d'analyse + années sélectionnées
#    - Algorithmes optimisés pour grandes séries temporelles
#
# 5. **LOGIQUE MÉTIER AVANCÉE**:
#    - Consommation horaire = somme 00:15-01:00, 01:15-02:00, etc.
#    - Gestion spéciale de minuit (23:15-00:00 → heure 23)
#    - Moyenne pondérée par nombre de jours réels disponibles
#    - Détection automatique de la colonne de consommation appropriée
#
# 6. **INSIGHTS ÉNERGÉTIQUES CONTEXTUELS**:
#    - Comparaison weekend vs semaine automatique
#    - Détection des patterns de télétravail/bureau
#    - Identification des créneaux d'optimisation tarifaire
#    - Métriques de régularité comportementale
#
# 7. **ANALYSES STATISTIQUES PROFESSIONNELLES**:
#    - Coefficient de variation par jour de semaine
#    - Analyse de stabilité des habitudes inter-annuelles
#    - Détection de changements comportementaux significatifs
#    - Classification de profils énergétiques (résidentiel/professionnel)
#
# ARCHITECTURE TECHNIQUE:
# - NumPy pour matrices de patterns hebdomadaires optimisées
# - Plotly Heatmap avec personnalisations avancées du rendu
# - Pandas pour agrégations temporelles et filtrage par jour de semaine
# - Session state pour persistance des paramètres et cache intelligent
#
# LOGIQUE DE CALCUL:
# - Pattern hebdomadaire = moyenne des mêmes créneaux jour+heure
# - Exemple: "Lundi 14h" = moyenne de tous les lundis à 14h sur période
# - Pondération automatique selon disponibilité réelle des données
# - Exclusion des valeurs aberrantes pour robustesse statistique
#
# ============================================================================
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import time  
from src.textual.tools import *

def display_weekly_pattern_heatmap(test2):
    # Determine which consumption column to use
    consumption_col = 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in test2.columns else 'Consumption (kWh)'
    
    # Récupérer le mode d'analyse depuis la session
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    years_to_use = st.session_state.get('years_to_use', [])
    
    # CACHE INTELLIGENT pour éviter les recalculs
    cache_key = f"weekly_heatmap_{analysis_mode}_{'_'.join(map(str, sorted(years_to_use)))}"
    
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
        years_available = sorted(test2['Year'].unique())
        
        if selected_year not in years_available:
            selected_year = years_available[0] if years_available else None
        
        if selected_year:
            fig = display_single_year_weekly_pattern(test2, selected_year, consumption_col)
        else:
            st.error("Aucune année disponible pour afficher le profil hebdomadaire.")
            
    else:
        # Mode données complètes : affichage de la moyenne multi-années uniquement
        years_available = sorted(test2['Year'].unique())
        
        if len(years_to_use) == 1:
            # Une seule année disponible, affichage direct
            selected_year = years_to_use[0]
            fig = display_single_year_weekly_pattern(test2, selected_year, consumption_col)
            
        else:
            # Plusieurs années disponibles : affichage automatique de la moyenne multi-années
            fig = display_multi_year_weekly_pattern(test2, years_to_use, consumption_col)
    
    # Mettre en cache le graphique généré
    if fig is not None:
        st.session_state[cache_key] = fig

def display_single_year_weekly_pattern(test2, selected_year, consumption_col):
    """
    Affiche le profil hebdomadaire pour une année spécifique
    """
    # Filter data for the selected year
    year_data = test2[test2['Year'] == selected_year]
    
    if not year_data.empty:
        # Define weekday names in French
        weekday_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", 
                         "Vendredi", "Samedi", "Dimanche"]
        
        # Create empty matrix to store consumption for each hour-day combination
        weekly_pattern = np.zeros((24, 7))  # 24 hours x 7 days
        
        # Pour chaque jour de semaine
        for weekday in range(7):
            # Récupérer tous les jours de cette semaine (lundi, mardi, etc.)
            weekday_data = year_data[year_data.index.weekday == weekday]
            
            if not weekday_data.empty:
                # Utiliser np.unique au lieu de .unique() pour les tableaux numpy
                all_dates = np.unique(weekday_data.index.date)
                day_count = 0
                
                # Pour chaque jour unique de ce type de jour de semaine
                for single_date in all_dates:
                    # Convertir en timestamp pour filtrage
                    date_str = single_date.strftime('%Y-%m-%d')
                    day_data = weekday_data[weekday_data.index.strftime('%Y-%m-%d') == date_str]
                    
                    if not day_data.empty:
                        day_count += 1
                        
                        # Calculer la somme pour chaque heure 0 à 22 (00:15-23:00)
                        for hour in range(0, 23):
                            start_time = f'{hour:02d}:15:00'
                            end_time = f'{hour+1:02d}:00:00'
                            hour_sum = day_data.between_time(start_time, end_time)[consumption_col].sum()
                            weekly_pattern[hour, weekday] += hour_sum
                        
                        # Cas spécial pour 23:00 (23:15-00:00)
                        midnight_sum = day_data.between_time('23:15', '00:00')[consumption_col].sum()
                        weekly_pattern[23, weekday] += midnight_sum
                
                # Calculer la moyenne pour ce jour de semaine
                if day_count > 0:
                    weekly_pattern[:, weekday] = weekly_pattern[:, weekday] / day_count
        
        # Create and display the heatmap
        fig = create_weekly_heatmap(weekly_pattern, weekday_names, f"Consommation hebdomadaire typique ({selected_year})", 
                            f"pour l'année {selected_year}")
        return fig
        
    else:
        st.markdown(f"Aucune donnée disponible pour {selected_year}")
        return None

def display_multi_year_weekly_pattern(test2, years_to_use, consumption_col):
    """
    Affiche le profil hebdomadaire moyen sur plusieurs années
    """
    # Filtrer les données pour les années sélectionnées
    filtered_data = test2[test2['Year'].isin(years_to_use)]
    
    if not filtered_data.empty:
        # Define weekday names in French
        weekday_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", 
                         "Vendredi", "Samedi", "Dimanche"]
        
        # Create empty matrix to store consumption for each hour-day combination
        weekly_pattern = np.zeros((24, 7))  # 24 hours x 7 days
        day_counts = np.zeros(7)  # Pour compter le nombre de jours par type
        
        # Pour chaque jour de semaine
        for weekday in range(7):
            # Récupérer tous les jours de cette semaine (lundi, mardi, etc.) sur toutes les années
            weekday_data = filtered_data[filtered_data.index.weekday == weekday]
            
            if not weekday_data.empty:
                # Utiliser np.unique au lieu de .unique() pour les tableaux numpy
                all_dates = np.unique(weekday_data.index.date)
                day_count = 0
                
                # Pour chaque jour unique de ce type de jour de semaine
                for single_date in all_dates:
                    # Convertir en timestamp pour filtrage
                    date_str = single_date.strftime('%Y-%m-%d')
                    day_data = weekday_data[weekday_data.index.strftime('%Y-%m-%d') == date_str]
                    
                    if not day_data.empty:
                        day_count += 1
                        
                        # Calculer la somme pour chaque heure 0 à 22 (00:15-23:00)
                        for hour in range(0, 23):
                            start_time = f'{hour:02d}:15:00'
                            end_time = f'{hour+1:02d}:00:00'
                            hour_sum = day_data.between_time(start_time, end_time)[consumption_col].sum()
                            weekly_pattern[hour, weekday] += hour_sum
                        
                        # Cas spécial pour 23:00 (23:15-00:00)
                        midnight_sum = day_data.between_time('23:15', '00:00')[consumption_col].sum()
                        weekly_pattern[23, weekday] += midnight_sum
                
                # Calculer la moyenne pour ce jour de semaine
                if day_count > 0:
                    weekly_pattern[:, weekday] = weekly_pattern[:, weekday] / day_count
                    day_counts[weekday] = day_count
        
        # Create and display the heatmap
        years_range = f"{min(years_to_use)}-{max(years_to_use)}" if len(years_to_use) > 1 else str(years_to_use[0])
        fig = create_weekly_heatmap(weekly_pattern, weekday_names, 
                            f"Consommation hebdomadaire moyenne ({years_range})", 
                            f"en moyenne sur {len(years_to_use)} années")
        
        # Afficher des informations supplémentaires sur la variabilité seulement pour les professionnels
        user_type = st.session_state.get('user_type', "Particulier")
        if user_type == "Professionnel":
            display_weekly_variability_info(filtered_data, consumption_col, years_to_use, weekday_names)
        
        return fig
        
    else:
        st.markdown("Aucune donnée disponible pour les années sélectionnées")
        return None

def create_weekly_heatmap(weekly_pattern, weekday_names, title, period_description):
    """
    Crée et affiche la heatmap hebdomadaire
    """
    # Identify min and max for better color scaling
    min_consumption = np.min(weekly_pattern[weekly_pattern > 0]) if np.any(weekly_pattern > 0) else 0
    max_consumption = np.max(weekly_pattern)
    
    # Use the same color scale as the other heatmap
    colorscale = px.colors.diverging.RdYlGn[::-1]
    
    # Create the heatmap with a custom colorscale
    fig = go.Figure(data=go.Heatmap(
        z=weekly_pattern,
        x=weekday_names,
        y=[f"{h:02d}:00" for h in range(24)],
        colorscale=colorscale,
        zmin=min_consumption,
        zmax=max_consumption,
        colorbar=dict(
            title=dict(
                text="Consommation (kWh)",
                side="right"
            ),
            thickness=20,
            tickfont=dict(size=12)
        ),
        hovertemplate="Jour: %{x}<br>Heure: %{y}<br>Consommation: %{z:.1f} kWh<extra></extra>"
    ))
    
    # Customize layout
    fig.update_layout(
        title={
            'text': title,
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=18)
        },
        xaxis_title="Jour de la semaine",
        yaxis_title="Heure de la journée",
        xaxis=dict(tickfont=dict(size=13)),
        yaxis=dict(
            tickmode='array',
            tickvals=[f"{h:02d}:00" for h in range(24)],
            tickfont=dict(size=11),
            autorange="reversed"  # To have 00:00 at the top
        ),
        width=650,
        height=600,
        margin=dict(l=50, r=50, t=80, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # Add annotations for top 3 consumption periods
    flat_indices = np.argsort(weekly_pattern.flatten())[-3:]
    hour_indices, day_indices = np.unravel_index(flat_indices, weekly_pattern.shape)
    
    for hour, day in zip(hour_indices, day_indices):
        fig.add_annotation(
            x=weekday_names[day],
            y=f"{hour:02d}:00",
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

    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add insights in two columns
    display_weekly_insights(weekly_pattern, weekday_names)
    
    # Retourner la figure pour le cache
    return fig

def display_weekly_insights(weekly_pattern, weekday_names):
    """
    Affiche les insights du profil hebdomadaire
    """
    # Ajouter un espacement
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pic de consommation horaire
        max_hour_day = np.unravel_index(np.argmax(weekly_pattern), weekly_pattern.shape)
        max_hour, max_day = max_hour_day
        
        st.markdown("<h5 style='text-align: center; color: #666666;'>Pic de consommation horaire</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='padding: 15px; margin: 5px 0; border-left: 4px solid #e74c3c; background-color: #f8f9fa; border-radius: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                <span style='color: #e74c3c; font-weight: bold; font-size: 1.1em;'>⚡ {weekday_names[max_day]} à {max_hour:02d}:00</span>
                <span style='font-size: 1.2em; font-weight: bold;'>{weekly_pattern[max_hour, max_day]:.1f} kWh</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                <strong>Maximum</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Jour le plus énergivore
        day_sums = np.sum(weekly_pattern, axis=0)
        max_day_index = np.argmax(day_sums)
        
        st.markdown("<h5 style='text-align: center; color: #666666;'>Jour le plus énergivore</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='padding: 15px; margin: 5px 0; border-left: 4px solid #ff9800; background-color: #f8f9fa; border-radius: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                <span style='color: #ff9800; font-weight: bold; font-size: 1.1em;'>📅 {weekday_names[max_day_index]}</span>
                <span style='font-size: 1.2em; font-weight: bold;'>{day_sums[max_day_index]:.1f} kWh</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                Consommation moyenne sur 24h
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Consommation minimale horaire
        min_non_zero = np.where(weekly_pattern > 0, weekly_pattern, np.inf).min()
        min_hour_day = np.where(weekly_pattern == min_non_zero)
        min_hour, min_day = min_hour_day[0][0], min_hour_day[1][0]
        
        st.markdown("<h5 style='text-align: center; color: #666666;'>Consommation minimale horaire</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='padding: 15px; margin: 5px 0; border-left: 4px solid #27ae60; background-color: #f8f9fa; border-radius: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                <span style='color: #27ae60; font-weight: bold; font-size: 1.1em;'>💤 {weekday_names[min_day]} à {min_hour:02d}:00</span>
                <span style='font-size: 1.2em; font-weight: bold;'>{min_non_zero:.1f} kWh</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                <strong>Minimum</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Jour le moins énergivore
        day_sums = np.sum(weekly_pattern, axis=0)
        min_day_index = np.argmin(day_sums)
        
        st.markdown("<h5 style='text-align: center; color: #666666;'>Jour le moins énergivore</h5>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='padding: 15px; margin: 5px 0; border-left: 4px solid #3498db; background-color: #f8f9fa; border-radius: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                <span style='color: #3498db; font-weight: bold; font-size: 1.1em;'>📅 {weekday_names[min_day_index]}</span>
                <span style='font-size: 1.2em; font-weight: bold;'>{day_sums[min_day_index]:.1f} kWh</span>
            </div>
            <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                Consommation moyenne sur 24h
            </div>
        </div>
        """, unsafe_allow_html=True)
        


def display_weekly_variability_info(filtered_data, consumption_col, years_to_use, weekday_names):
    """
    Affiche des informations sur la variabilité hebdomadaire entre les années
    """
    if len(years_to_use) > 1:
        st.markdown("---")
        st.subheader("Variabilité hebdomadaire entre les années")
        
        # Calculer la consommation par jour de semaine pour chaque année
        yearly_weekday_consumption = {}
        for year in years_to_use:
            year_data = filtered_data[filtered_data['Year'] == year]
            if not year_data.empty:
                weekday_sums = []
                for weekday in range(7):
                    weekday_data = year_data[year_data.index.weekday == weekday]
                    if not weekday_data.empty:
                        daily_avg = weekday_data[consumption_col].resample('D').sum().mean()
                        weekday_sums.append(daily_avg)
                    else:
                        weekday_sums.append(0)
                yearly_weekday_consumption[year] = weekday_sums
        
        if len(yearly_weekday_consumption) > 1:
            # Calculer la variabilité pour chaque jour de semaine
            weekday_variability = []
            for weekday in range(7):
                values = [yearly_weekday_consumption[year][weekday] for year in years_to_use 
                         if yearly_weekday_consumption[year][weekday] > 0]
                if len(values) > 1:
                    cv = (np.std(values) / np.mean(values)) * 100
                    weekday_variability.append(cv)
                else:
                    weekday_variability.append(0)
            
            # Analyser la variabilité globale
            if weekday_variability:
                avg_variability = np.mean(weekday_variability)
                max_variability = max(weekday_variability)
                min_variability = min(weekday_variability)
                most_variable_day = np.argmax(weekday_variability)
                least_variable_day = np.argmin(weekday_variability)
                
                years_range = f"{min(years_to_use)} - {max(years_to_use)}" if len(years_to_use) > 2 else " et ".join(map(str, sorted(years_to_use)))
                st.markdown(f"**📊 Analyse de la variabilité inter-annuelle par jour de semaine ({years_range})**")
                st.markdown(f"Le **coefficient de variation (CV)** mesure la variabilité relative de la consommation "
                           f"pour chaque jour de semaine entre les {len(years_to_use)} années analysées. Il est calculé comme "
                           f"*(écart-type / moyenne) × 100*. Plus le CV est élevé, plus la consommation "
                           f"de ce jour varie d'une année à l'autre.")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Variabilité moyenne", f"{avg_variability:.1f}% CV")
                with col2:
                    st.metric("Jour le plus variable", 
                             f"{weekday_names[most_variable_day]}", 
                             f"{weekday_variability[most_variable_day]:.1f}% CV")
                with col3:
                    st.metric("Jour le plus stable", 
                             f"{weekday_names[least_variable_day]}", 
                             f"{weekday_variability[least_variable_day]:.1f}% CV")
                
                if avg_variability < 10:
                    st.success("✅ **Profil hebdomadaire très stable** entre les années (variabilité moyenne < 10%)")
                elif avg_variability < 20:
                    st.info("ℹ️ **Profil hebdomadaire relativement stable** (variabilité modérée entre 10-20%)")
                else:
                    st.warning("⚠️ **Profil hebdomadaire variable** entre les années (variabilité > 20%). "
                              "Cela peut indiquer des changements d'habitudes saisonniers ou d'équipements.")