"""
MODULE D'ANALYSE DES PICS ET ANOMALIES ÉNERGÉTIQUES - PHASE EXPÉRIMENTALE

Ce module implémente des fonctionnalités avancées d'analyse énergétique destinées aux utilisateurs professionnels
dans l'onglet "ANALYSE PERSONNALISÉE" de l'application web DataWatt. Ces fonctionnalités sont actuellement
en phase expérimentale et font l'objet de tests et d'améliorations continues.

FONCTIONNALITÉS PRINCIPALES:

1. DÉTECTION D'ANOMALIES DE CONSOMMATION:
   - Analyse sophistiquée par quart d'heure pour identifier les pics anormaux
   - Calcul de seuils statistiques adaptatifs (95ème percentile + distance médiane)
   - Classification en anomalies "extrêmes" vs "significatives" 
   - Traitement mensuel pour tenir compte des variations saisonnières
   - Visualisation interactive avec Plotly pour exploration détaillée des anomalies

2. PEAK SHAVING (ÉCRÊTAGE DES PICS):
   - Simulation d'écrêtage des pics de puissance avec pourcentage paramétrable
   - Calcul automatique des économies financières (6.19 CHF/kW/mois)
   - Analyse comparative avant/après écrêtage avec visualisation des gains
   - Vue annuelle et mensuelle pour analyse granulaire des bénéfices
   - Identification optimisée des pics journaliers pour performance graphique

ARCHITECTURE TECHNIQUE:
- Interface Streamlit avec composants interactifs avancés (sliders, sélecteurs)
- Graphiques Plotly avec optimisations pour gros volumes de données
- Algorithmes statistiques robustes pour détection d'anomalies
- Calculs financiers basés sur tarifs suisses de puissance
- Gestion intelligente des séries temporelles quart-horaires

INTÉGRATION WEB APP:
- Apparaît dans l'onglet "ANALYSE PERSONNALISÉE" pour les utilisateurs professionnels
- Deux visualisations principales: graphique d'anomalies + graphique de peak shaving
- Interface utilisateur avec onglets (vue annuelle/mensuelle) et contrôles interactifs
- Explications détaillées des méthodes dans des expanders pour contexte utilisateur

STATUT: EXPÉRIMENTAL - En cours de validation et d'optimisation pour déploiement production
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calendar

def detect_monthly_anomalies(df):
    """
    Détecte les anomalies significatives dans les données de consommation mensuelles,
    en calculant les seuils par quart d'heure.
    """
    # Assurez-vous que le dataframe a un index temporel
    if not isinstance(df.index, pd.DatetimeIndex):
        st.warning("Le dataframe doit avoir un index temporel.")
        raise ValueError("Le dataframe doit avoir un index DatetimeIndex.")
    
    # Créer une copie du dataframe pour éviter de modifier l'original
    df_copy = df.copy()
    
    # Identifier la colonne de consommation et s'assurer qu'elle est numérique
    if 'Consumption (kWh)' not in df_copy.columns:
        st.warning("La colonne 'Consumption (kWh)' n'existe pas. Utilisation de la première colonne.")
        # Si pas de colonne 'Consumption', utiliser la première colonne
        if len(df_copy.columns) > 0:
            consumption_col = df_copy.columns[0]
            df_copy['Consumption (kWh)'] = pd.to_numeric(df_copy[consumption_col], errors='coerce')
        else:
            st.warning("Le dataframe ne contient pas de colonnes.")
            raise ValueError("Le dataframe ne contient pas de colonnes.")
    else:
        # Convertir la colonne existante en numérique
        df_copy['Consumption (kWh)'] = pd.to_numeric(df_copy['Consumption (kWh)'], errors='coerce')
    
    # Supprimer les valeurs NaN qui peuvent résulter de la conversion
    df_copy = df_copy.dropna(subset=['Consumption (kWh)'])
    
    # Ajouter des colonnes pour le mois et l'année
    df_copy['month'] = df_copy.index.month
    df_copy['year'] = df_copy.index.year
    df_copy['month_year'] = df_copy['year'].astype(str) + '-' + df_copy['month'].astype(str).str.zfill(2)
    
    # Ajouter l'heure du jour (pour l'analyse par heure)
    df_copy['hour'] = df_copy.index.hour
    df_copy['minute'] = df_copy.index.minute
    df_copy['hour_minute'] = df_copy['hour'].astype(str).str.zfill(2) + 'h' + df_copy['minute'].astype(str).str.zfill(2)
    
    # Initialiser les dictionnaires pour stocker les résultats
    anomalies = {}
    stats = {}
    
    # Traiter chaque mois séparément
    for month_year, month_group in df_copy.groupby('month_year'):
        # Vérifier si le groupe contient des données
        if len(month_group) < 96:  # Au moins 1 jour de données (24h * 4 quarts d'heure)
            continue
        
        # Calculer le 75e percentile sur l'ensemble du mois
        p75_month = np.percentile(month_group['Consumption (kWh)'], 75) ### seuil à modifier pour reduire les anomalies significatives
        
        # Initialiser les dictionnaires pour ce mois
        hourly_stats = {}
        monthly_anomalies = {
            'extreme_values': pd.DataFrame(),
            'significant_anomalies': pd.DataFrame()
        }
        
        # Pour chaque quart d'heure, calculer les statistiques
        for hour_minute, hour_group in month_group.groupby('hour_minute'):
            if len(hour_group) < 3:  # Au moins 3 points de données pour ce créneau horaire
                continue
                
            # Calculer les statistiques pour ce créneau horaire
            p95 = np.percentile(hour_group['Consumption (kWh)'], 95)
            median = np.median(hour_group['Consumption (kWh)'])
            threshold = p95 + (p95 - median) / 3  # Seuil d'anomalie significative
            
            # Stocker les statistiques pour ce créneau horaire
            hourly_stats[hour_minute] = {
                'p95': p95,
                'median': median,
                'threshold': threshold,
                'p75_month': p75_month  # Ajouter le 75e percentile du mois entier
            }
            
            # Identifier les valeurs extrêmes
            extreme_values = hour_group[hour_group['Consumption (kWh)'] > p95]
            
            # Identifier les anomalies significatives avec la double condition:
            # 1. Dépasser le seuil calculé par quart d'heure
            # 2. Dépasser le 75e percentile du mois entier
            potential_anomalies = hour_group[hour_group['Consumption (kWh)'] > threshold]
            significant_anomalies = potential_anomalies[potential_anomalies['Consumption (kWh)'] > p75_month]
            
            # Ajouter aux dataframes d'anomalies du mois
            monthly_anomalies['extreme_values'] = pd.concat([monthly_anomalies['extreme_values'], extreme_values])
            monthly_anomalies['significant_anomalies'] = pd.concat([monthly_anomalies['significant_anomalies'], significant_anomalies])
        
        # Stocker les résultats pour ce mois
        anomalies[month_year] = monthly_anomalies
        stats[month_year] = hourly_stats
    
    return anomalies, stats

def plot_monthly_anomalies(df, month_year, anomalies, stats):
    """
    Crée un graphique pour visualiser les anomalies pour un mois donné, avec des seuils par quart d'heure.
    """
    # Filtrer les données pour le mois sélectionné
    df_copy = df.copy()
    df_copy['month'] = df_copy.index.month
    df_copy['year'] = df_copy.index.year
    df_copy['month_year'] = df_copy['year'].astype(str) + '-' + df_copy['month'].astype(str).str.zfill(2)
    df_copy['hour'] = df_copy.index.hour
    df_copy['minute'] = df_copy.index.minute
    df_copy['hour_minute'] = df_copy['hour'].astype(str).str.zfill(2) + 'h' + df_copy['minute'].astype(str).str.zfill(2)
    
    month_data = df_copy[df_copy['month_year'] == month_year]
    
    # Extraire les anomalies pour le mois sélectionné
    if month_year in anomalies and month_year in stats:
        hourly_stats = stats[month_year]
        extreme_values = anomalies[month_year]['extreme_values']
        significant_anomalies = anomalies[month_year]['significant_anomalies']
    else:
        return go.Figure()
    
    # Créer le graphique
    fig = go.Figure()
    
    # Préparer les données pour les courbes de médiane, p95 et seuil
    hour_minutes = sorted(hourly_stats.keys())
    medians = [hourly_stats[hm]['median'] for hm in hour_minutes]
    p95s = [hourly_stats[hm]['p95'] for hm in hour_minutes]
    thresholds = [hourly_stats[hm]['threshold'] for hm in hour_minutes]
    
    # Ajouter les données de consommation (points uniquement)
    fig.add_trace(go.Scatter(
        x=month_data['hour_minute'],
        y=month_data['Consumption (kWh)'],
        mode='markers',
        name='Consommation',
        marker=dict(color='#2C82C9', size=6, opacity=0.5),
        line=dict(width=0),
        connectgaps=False
    ))

    # Ajouter les valeurs extrêmes (mais pas significatives)
    non_significant = extreme_values[~extreme_values.index.isin(significant_anomalies.index)]
    if not non_significant.empty:
        fig.add_trace(go.Scatter(
            x=non_significant['hour_minute'],
            y=non_significant['Consumption (kWh)'],
            mode='markers',
            name='Valeurs extrêmes',
            marker=dict(color='#ED7F09', size=8),
            line=dict(width=0),
            connectgaps=False
        ))

    # Ajouter les anomalies significatives
    if not significant_anomalies.empty:
        fig.add_trace(go.Scatter(
            x=significant_anomalies['hour_minute'],
            y=significant_anomalies['Consumption (kWh)'],
            mode='markers',
            name='Anomalies significatives',
            marker=dict(color='#ff1100', size=10),
            line=dict(width=0),
            connectgaps=False
        ))
    
    # Configurer le layout
    year, month = month_year.split('-')
    month_name = calendar.month_name[int(month)]
    
    fig.update_layout(
        title=f'Analyse des anomalies de consommation - {month_name} {year}',
        xaxis_title='Heure de la journée',
        yaxis_title='Consommation (kWh)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600,
        xaxis=dict(
            tickmode='array',
            tickvals=['00h00', '03h00', '06h00', '09h00', '12h00', '15h00', '18h00', '21h00'],
            ticktext=['00h00', '03h00', '06h00', '09h00', '12h00', '15h00', '18h00', '21h00'],
            categoryorder='array',
            categoryarray=hour_minutes  # Assure que l'ordre des heures est correct
        )
    )
    
    return fig

def display_anomaly_analysis(df):
    """
    Affiche l'analyse des anomalies dans une application Streamlit.
    """
    st.subheader("Analyse des anomalies de consommation")
    
    # Renommer la colonne si nécessaire
    if 'Consumption (kWh)' not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: 'Consumption (kWh)'})
    
    # Détecter les anomalies
    anomalies, stats = detect_monthly_anomalies(df)
    
    # Créer une liste de mois disponibles
    available_months = sorted(list(anomalies.keys()))
    
    if not available_months:
        st.warning("Aucune données mensuelles disponibles pour l'analyse.")
        return
    
    # Afficher le sélecteur de mois
    selected_month = st.select_slider(
        "Sélectionnez un mois pour visualiser les anomalies:",
        options=available_months,
        value=available_months[0]
    )
    
    # Afficher les statistiques pour le mois sélectionné
    if selected_month in stats:
        st.write(f"**Statistiques pour {selected_month}:**")
        
        # Nombre d'anomalies
        extreme_count = len(anomalies[selected_month]['extreme_values'])
        significant_count = len(anomalies[selected_month]['significant_anomalies'])


        # Créer la colonne month_year dans le df pour le comptage
        df_month = df.copy()
        df_month['month'] = df_month.index.month
        df_month['year'] = df_month.index.year
        df_month['month_year'] = df_month['year'].astype(str) + '-' + df_month['month'].astype(str).str.zfill(2)
        
        # Total des points de données pour le mois
        total_points = len(df_month[df_month['month_year'] == selected_month])

        # Calculer les pourcentages
        extreme_percentage = (extreme_count / total_points) * 100
        significant_percentage = (significant_count / total_points) * 100
        
        # Déterminer la couleur selon les seuils
        def get_extreme_color(value):
            if value <= 5: return "#16A085"  # Vert
            elif value <= 7.5: return "#2C82C9"  # Bleu
            elif value <= 10: return "#8E44AD"  # Violet
            else: return "#ff1100"  # Rouge
          
        def get_significant_color(value):
            if value <= 2: return "#16A085"  # Vert
            elif value <= 3.5: return "#2C82C9"  # Bleu
            elif value <= 5: return "#8E44AD"  # Violet
            else: return "#ff1100"  # Rouge
          
        # Obtenir les évaluations textuelles
        def get_extreme_text(value):
            if value <= 5: return "Bon"
            elif value <= 7.5: return "Moyen"
            elif value <= 10: return "Médiocre"
            else: return "Mauvais"

        def get_significant_text(value):
            if value <= 2: return "Bon"
            elif value <= 3.5: return "Moyen"
            elif value <= 5: return "Médiocre"
            else: return "Mauvais"

        col1, col2 = st.columns(2)
        
        # Utiliser un HTML personnalisé pour colorer directement le pourcentage avec un style plus flashy
        col1.markdown(
            f"""
            <div style="padding: 20px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 10px 0;">
                <p style="font-size: 1.1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Valeurs extrêmes détectées</p>
                <p style="font-size: 1.8rem; font-weight: bold; color: {get_extreme_color(extreme_percentage)}; text-shadow: 1px 1px 1px rgba(0,0,0,0.3); margin: 0; padding: 5px 0;">
                    {extreme_percentage:.2f}% <span style="font-size: 1rem; background-color: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px; margin-left: 5px;">({get_extreme_text(extreme_percentage)})</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        col2.markdown(
            f"""
            <div style="padding: 20px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 10px 0;">
                <p style="font-size: 1.1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Anomalies significatives</p>
                <p style="font-size: 1.8rem; font-weight: bold; color: {get_significant_color(significant_percentage)}; text-shadow: 1px 1px 1px rgba(0,0,0,0.3); margin: 0; padding: 5px 0;">
                    {significant_percentage:.2f}% <span style="font-size: 1rem; background-color: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px; margin-left: 5px;">({get_significant_text(significant_percentage)})</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.write("Les seuils d'anomalie sont calculés pour chaque quart d'heure dans la journée.")
    
    # Afficher le graphique
    fig = plot_monthly_anomalies(df, selected_month, anomalies, stats)
    st.plotly_chart(fig, use_container_width=True)
    
    # Explication de la méthode
    with st.expander("À propos de la méthode de détection des anomalies"):
        st.markdown("""
        ### Méthode de détection des anomalies
        
        La méthode utilisée pour détecter les anomalies dans la consommation électrique se base sur les principes suivants :
        
        1. **Analyse par quart d'heure** : Pour chaque quart d'heure de la journée (00h00, 00h15, etc.), les statistiques sont calculées séparément.
        
        2. **Identification des valeurs extrêmes** : Pour chaque créneau horaire, les valeurs dépassant le 95e percentile sont considérées comme extrêmes.
        
        3. **Distinction entre anomalies mineures et significatives** : Pour différencier les anomalies significatives des anomalies mineures, 
        on utilise un seuil basé sur la distance entre la médiane et le 95e percentile.
        
        4. **Calcul du seuil d'anomalie significative** : Le seuil est fixé au 95e percentile plus un tiers de la distance entre 
        le 95e percentile et la médiane, calculé pour chaque créneau horaire.
        
        5. **Traitement mensuel** : L'analyse est effectuée indépendamment pour chaque mois afin de tenir compte des variations saisonnières.
        
        Cette approche permet d'identifier les anomalies en tenant compte de la cartographie de consommation propre à chaque moment de la journée.
        """)

def perform_peak_shaving(df, shaving_percentage):
    """
    Performs peak shaving on monthly peak power data (quarter-hourly data).
    Reduces only the peak power value for each month.
    
    Args:
        df: DataFrame with consumption data
        shaving_percentage: Percentage by which to reduce the peaks (0-100%)
    
    Returns:
        DataFrame with original and shaved power values
    """
    # Make a copy to avoid modifying the original dataframe
    df_copy = df.copy()
    
    # Ensure we're working with the right column
    if 'Consumption (kWh)' not in df_copy.columns and len(df_copy.columns) > 0:
        df_copy = df_copy.rename(columns={df_copy.columns[0]: 'Consumption (kWh)'})
    
    # Convert consumption (kWh) to power (kW) if needed
    # For 15-minute data, multiply by 4 to get kW
    time_diff = (df_copy.index[1] - df_copy.index[0]).total_seconds() / 3600
    power_factor = 1 / time_diff if time_diff < 1 else 1
    
    df_copy['Power (kW)'] = df_copy['Consumption (kWh)'] * power_factor
    df_copy['Shaved Power (kW)'] = df_copy['Power (kW)'].copy()
    
    # Add month-year column for grouping
    df_copy['month'] = df_copy.index.month
    df_copy['year'] = df_copy.index.year
    df_copy['month_year'] = df_copy['year'].astype(str) + '-' + df_copy['month'].astype(str).str.zfill(2)
    
    # Power cost in CHF/kW/month
    power_cost_rate = 6.19
    
    # Initialize dictionary to store monthly peak powers and savings
    monthly_peaks = {}
    
    # Apply peak shaving for each month
    for month_year, month_data in df_copy.groupby('month_year'):
        # Find the peak power for this month
        peak_power = month_data['Power (kW)'].max()
        
        # Calculate the new peak limit after shaving
        new_peak_limit = peak_power * (1 - shaving_percentage / 100)
        
        # Identify the peak value(s) for the month
        peak_indices = month_data.index[month_data['Power (kW)'] >= peak_power * 0.9]
        
        # Apply shaving only to peak values and those within 10% of the peak
        # This ensures we only reduce the actual peaks, not all values above the new limit
        for idx in peak_indices:
            if df_copy.loc[idx, 'Power (kW)'] > new_peak_limit:
                df_copy.loc[idx, 'Shaved Power (kW)'] = new_peak_limit
        
        # Store original and shaved peak for this month
        shaved_peak = df_copy.loc[month_data.index, 'Shaved Power (kW)'].max()
        monthly_peaks[month_year] = {
            'original_peak': peak_power,
            'shaved_peak': shaved_peak,
            'peak_reduction': peak_power - shaved_peak,
            'financial_savings': (peak_power - shaved_peak) * power_cost_rate
        }
    
    # Calculate saved energy
    df_copy['Saved Energy (kWh)'] = (df_copy['Power (kW)'] - df_copy['Shaved Power (kW)']) * time_diff
    
    # Add monthly peaks and savings information to the dataframe as attributes
    df_copy.monthly_peaks = monthly_peaks
    df_copy.power_cost_rate = power_cost_rate
    
    return df_copy

def plot_peak_shaving(df_shaved, show_full_year=True, selected_month=None):
    """
    Version améliorée qui affiche uniquement les pics de puissance journaliers
    plutôt que toutes les valeurs quart-horaires.
    """
    fig = go.Figure()
    
    # Filter data if showing a specific month
    if not show_full_year and selected_month:
        plot_data = df_shaved[df_shaved['month_year'] == selected_month].copy()
    else:
        plot_data = df_shaved.copy()
    
    # Créer un DataFrame avec les pics journaliers
    daily_peaks = plot_data.groupby(pd.Grouper(freq='D')).agg({
        'Power (kW)': 'max',
        'Shaved Power (kW)': 'max',
        'month': 'first',
        'year': 'first',
        'month_year': 'first'
    })
    
    # Add month boundaries for background shading
    if show_full_year:
        # Méthode plus efficace pour identifier les transitions de mois
        month_changes = daily_peaks['month'] != daily_peaks['month'].shift(1)
        month_transitions = daily_peaks.index[month_changes].tolist()
        
        # Add last date to close the last month's area
        if len(daily_peaks) > 0:
            month_transitions.append(daily_peaks.index[-1])
        
        # Add alternating background for months
        for i in range(len(month_transitions)-1):
            color = "rgba(230, 230, 230, 0.3)" if i % 2 == 0 else "rgba(255, 255, 255, 0)"
            fig.add_vrect(
                x0=month_transitions[i],
                x1=month_transitions[i+1],
                fillcolor=color,
                line_width=0,
                layer="below"
            )
    
    # Calculate epsilon - minimum difference to consider as shaved
    epsilon = 0.001  # Small value to avoid floating point comparison issues
    
    # Add the original power peaks (blue points)
    fig.add_trace(go.Scatter(
        x=daily_peaks.index,
        y=daily_peaks['Power (kW)'],
        mode='markers',
        marker=dict(color='#2C82C9', size=6),
        name='Pic de puissance original'
    ))
    
    # Add shaved power peaks where reduction occurred
    shaved_days = daily_peaks[daily_peaks['Power (kW)'] - daily_peaks['Shaved Power (kW)'] > epsilon]
    
    if not shaved_days.empty:
        # Add the shaved power points
        fig.add_trace(go.Scatter(
            x=shaved_days.index,
            y=shaved_days['Shaved Power (kW)'],
            mode='markers',
            marker=dict(color='#16A085', size=6),
            name='Pic de puissance après shaving'
        ))
        
        # Optimisation des lignes rouges - créer un seul objet Scatter au lieu de multiples shapes
        x_values = []
        y_values = []
        
        for idx, row in shaved_days.iterrows():
            # Pour chaque jour écrêté, ajouter 2 points + un None pour séparer les lignes
            x_values.extend([idx, idx, None])
            y_values.extend([row['Shaved Power (kW)'], row['Power (kW)'], None])
        
        # Ajouter toutes les lignes dans une seule trace
        if x_values:  # S'assurer qu'il y a des valeurs à ajouter
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines',
                line=dict(color='#ff1100', width=2),
                name='Portion écrêtée',
                hoverinfo='none'  # Désactiver les infobulles pour ces lignes
            ))
    
    # Update layout
    title = 'Peak Shaving (Ecrêtage des pics) - Pics de puissance journaliers (Année complète)'
    if not show_full_year and selected_month:
        year, month = selected_month.split('-')
        month_name = calendar.month_name[int(month)]
        title = f'Peak Shaving (Ecrêtage des pics) - Pics de puissance journaliers ({month_name} {year})'
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Puissance (kW)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        )
    )
    
    return fig

def display_peak_shaving_analysis(df):
    """
    Displays the peak shaving analysis in a Streamlit application.
    """
    st.subheader("Analyse de Peak Shaving (Ecrêtage des pics)")
    
    st.write("""
    Le peak shaving (écrêtage des pics) permet de réduire les pics de puissance, ce qui peut 
    entraîner des économies importantes sur les factures d'électricité, notamment pour les 
    clients professionnels qui paient des frais basés sur leur puissance maximale.
    """)
    
    # Add slider for peak shaving percentage
    shaving_percentage = st.slider(
        "Pourcentage de réduction des pics de puissance",
        min_value=0,
        max_value=20,
        value=10,
        step=1,
        format="%d%%"
    )
    
    # Perform peak shaving analysis
    df_shaved = perform_peak_shaving(df, shaving_percentage)
    
    # Get power cost rate
    power_cost_rate = df_shaved.power_cost_rate if hasattr(df_shaved, 'power_cost_rate') else 6.19
    
    # Create tabs for yearly and monthly views
    view_tab1, view_tab2 = st.tabs(["Vue annuelle", "Vue mensuelle"])
    
    with view_tab1:
        # Calculate overall financial statistics
        total_peak_reduction = sum(month['peak_reduction'] for month in df_shaved.monthly_peaks.values())
        total_financial_savings = sum(month['financial_savings'] for month in df_shaved.monthly_peaks.values())
        avg_monthly_savings = total_financial_savings / len(df_shaved.monthly_peaks) if df_shaved.monthly_peaks else 0
        
        # Display statistics with a more flashy style
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; margin: 15px 0;">
                <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 10px 0 0; text-align: center;">
                    <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Économies financières totales</p>
                    <p style="font-size: 1.6rem; font-weight: bold; color: #2C82C9; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                        {total_financial_savings:.2f} CHF
                    </p>
                </div>
                <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 10px; text-align: center;">
                    <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Réduction cumulée des pics</p>
                    <p style="font-size: 1.6rem; font-weight: bold; color: #16A085; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                        {total_peak_reduction:.2f} kW
                    </p>
                </div>
                <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 0 0 10px; text-align: center;">
                    <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Économie mensuelle moyenne</p>
                    <p style="font-size: 1.6rem; font-weight: bold; color: #8E44AD; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                        {avg_monthly_savings:.2f} CHF/mois
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Explain the calculation
        st.write(f"*Calcul basé sur un tarif de puissance de {power_cost_rate} CHF/kW/mois*")
        
        # Show the yearly peak shaving plot
        fig = plot_peak_shaving(df_shaved, show_full_year=True)
        st.plotly_chart(fig, use_container_width=True)
    
    with view_tab2:
        # Get available months
        available_months = sorted(df_shaved.monthly_peaks.keys())
        
        if available_months:
            # Select month
            selected_month = st.select_slider(
                "Sélectionnez un mois:",
                options=available_months,
                value=available_months[0]
            )
            
            # Get monthly peak data
            month_data = df_shaved.monthly_peaks[selected_month]
            month_peak_original = month_data['original_peak']
            month_peak_shaved = month_data['shaved_peak']
            month_peak_reduction = month_data['peak_reduction']
            month_financial_savings = month_data['financial_savings']
            
            # Display monthly statistics with a more flashy style
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; margin: 15px 0;">
                    <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 10px 0 0; text-align: center;">
                        <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Pic de puissance original</p>
                        <p style="font-size: 1.6rem; font-weight: bold; color: #2C82C9; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                            {month_peak_original:.2f} kW
                        </p>
                    </div>
                    <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 0 0 10px; text-align: center;">
                        <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Pic de puissance après shaving</p>
                        <p style="font-size: 1.6rem; font-weight: bold; color: #16A085; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                            {month_peak_shaved:.2f} kW
                        </p>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin: 15px 0;">
                    <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 10px 0 0; text-align: center;">
                        <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Réduction de puissance</p>
                        <p style="font-size: 1.6rem; font-weight: bold; color: #8E44AD; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                            {month_peak_reduction:.2f} kW
                        </p>
                    </div>
                    <div style="flex: 1; padding: 15px; border-radius: 8px; border: 2px solid #ff1100; box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: linear-gradient(to bottom, white, #f8f8f8); margin: 0 0 0 10px; text-align: center;">
                        <p style="font-size: 1rem; color: #333; margin-bottom: 5px; font-weight: bold;">Économie financière</p>
                        <p style="font-size: 1.6rem; font-weight: bold; color: #ff1100; text-shadow: 1px 1px 1px rgba(0,0,0,0.2); margin: 0;">
                            {month_financial_savings:.2f} CHF
                        </p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Show the monthly peak shaving plot
            fig = plot_peak_shaving(df_shaved, show_full_year=False, selected_month=selected_month)
            st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("À propos du Peak Shaving (Ecrêtage des pics)"):
        st.markdown(f"""
        ### Qu'est-ce que le Peak Shaving (Ecrêtage des pointes)?
        
        Le **Peak Shaving** (ou écrêtage des pointes) est une technique de gestion de l'énergie qui consiste à réduire la consommation d'électricité pendant les périodes où la demande atteint des pics.
        
        ### Impact financier du Peak Shaving
        
        Dans cet exemple, nous utilisons un tarif de puissance de **{power_cost_rate} CHF/kW/mois**. Cela signifie que pour chaque kilowatt de puissance maximale que vous réduisez sur un mois, vous économisez {power_cost_rate} CHF sur votre facture mensuelle.
        
        ### Avantages du Peak Shaving:
        
        1. **Réduction des coûts** : Les fournisseurs d'électricité facturent souvent en fonction de la puissance maximale consommée. Réduire ces pics peut conduire à des économies substantielles.
        
        2. **Stabilité du réseau** : Aide à équilibrer la charge sur le réseau électrique.
        
        3. **Durabilité** : Réduit la nécessité d'activer des centrales électriques de pointe, souvent plus polluantes.
        
        ### Méthodes de mise en œuvre:
        
        - **Stockage d'énergie** : Utiliser des batteries pour stocker l'énergie pendant les périodes creuses et la restituer pendant les pics.
        - **Gestion de la demande** : Décaler certaines consommations hors des périodes de pointe.
        - **Autoproduction** : Produire sa propre électricité pendant les pics de demande.
        """)