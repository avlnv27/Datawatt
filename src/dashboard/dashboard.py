"""
Fichier pour la création et l'affichage du tableau de bord principal
=====================================================================================

Ce module contient toutes les fonctions liées au tableau de bord qui s'affiche en premier sur la page principale.
Le dashboard présente un résumé visuel des indicateurs clés de consommation électrique :
- Graphique de consommation annuelle avec timeline continue
- Graphique des coûts mensuels avec tarification HP/HC ou tarif unique
- Cartes résumées des indicateurs principaux (ratio jour/nuit, ratio semaine/weekend, charge de base, clustering)
- Cartes de consommation et coût avec tendances calculées

Architecture du dashboard :
- Section haute : Graphique annuel (gauche) + Cartes consommation/coût (droite)  
- Section basse : 4 cartes indicateurs en grille 2x2 (gauche) + Graphique coûts mensuels (droite)

Dépendances :
- streamlit : Interface utilisateur web
- plotly.graph_objects : Création des graphiques interactifs
- pandas : Manipulation des données temporelles
- src.textual.tools.tooltip_info : Fonction pour les infobulles d'aide
- src.indicators.cost_analysis : Fonctions de calcul des coûts HP/HC
"""

# Importation des librairies nécessaires pour le dashboard
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Import des fonctions internes au projet DataWatt
from src.textual.tools import tooltip_info  # Fonction pour afficher les infobulles d'information
from src.indicators.cost_analysis import is_peak_hour, calculate_average_price  # Fonctions de calcul des coûts énergétiques

# === FONCTIONS UTILITAIRES POUR LE FORMATAGE ET L'AFFICHAGE ===

def get_month_abbr_french(date):
    """
    Retourne l'abréviation du mois en français pour l'affichage des graphiques
    
    Args:
        date (datetime): Date dont on veut extraire le mois
        
    Returns:
        str: Abréviation du mois en français (ex: "jan", "fév", "mar"...)
    """
    months_abbr_fr = {
        1: "jan", 2: "fév", 3: "mar", 4: "avr", 
        5: "mai", 6: "jun", 7: "jul", 8: "aoû",
        9: "sep", 10: "oct", 11: "nov", 12: "déc"
    }
    return months_abbr_fr[date.month]


# === FONCTIONS DE CRÉATION DES GRAPHIQUES PRINCIPAUX DU DASHBOARD ===

def create_annual_view_plot(test2):
    """
    Crée un graphique Plotly de la vue annuelle pour le dashboard principal
    
    Cette fonction est adaptée de la fonction interactive_plot mais simplifiée pour n'afficher 
    que la vue "Year" avec une timeline continue. Elle gère :
    - La sélection automatique des années selon les paramètres utilisateur
    - La création d'une timeline continue sans gaps entre années non consécutives
    - L'application du cache des couleurs pour la cohérence visuelle
    - La gestion des modes "année unique" vs "données complètes"
    
    Args:
        test2 (DataFrame): DataFrame des données de consommation avec colonnes 'Year' et 'Consumption (kWh)'
        
    Returns:
        plotly.graph_objects.Figure or None: Figure Plotly du graphique annuel ou None si pas de données
        
    Données utilisées depuis st.session_state:
        - analysis_mode : 'single_year' ou 'multi_year'
        - year_selection_mode : "Données complètes" ou mode année spécifique
        - color_map_cache : Cache des couleurs pour la cohérence entre graphiques
    """
    # Vérification de la validité des données d'entrée
    if test2 is None or test2.empty:
        return None
    
    # === RÉCUPÉRATION DES PARAMÈTRES D'ANALYSE DEPUIS LA SESSION ===
    # Ces paramètres sont définis dans main.py selon les choix utilisateur dans la sidebar
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')  # Mode d'analyse : année unique ou multi-années
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")  # Mode de sélection des données
    
    # === DÉTERMINATION DES ANNÉES À AFFICHER SELON LE MODE D'ANALYSE ===
    if analysis_mode == 'single_year':
        # Mode année unique : afficher seulement l'année sélectionnée par l'utilisateur
        selected_analysis_year = st.session_state.get('selected_analysis_year')
        if selected_analysis_year:
            selected_years = [selected_analysis_year]
        else:
            selected_years = sorted(test2['Year'].unique())[:1]  # Première année disponible en fallback
    else:
        # Mode données complètes : afficher plusieurs années selon la sélection utilisateur
        available_years = sorted(test2['Year'].unique())
        
        if year_selection_mode == "Données complètes":
            # Limiter aux 3 années les plus récentes maximum pour éviter la surcharge visuelle
            selected_years = available_years[-3:] if len(available_years) > 3 else available_years
        else:
            # Années partielles sélectionnées par l'utilisateur - limiter aussi aux 3 plus récentes
            selected_partial_years = st.session_state.get('selected_partial_years', [])
            if selected_partial_years:
                # Prendre les 3 plus récentes des années sélectionnées pour éviter surcharge
                selected_years = sorted(selected_partial_years)[-3:] if len(selected_partial_years) > 3 else selected_partial_years
            else:
                # Fallback aux années disponibles (limitées aux 3 plus récentes)
                selected_years = available_years[-3:] if len(available_years) > 3 else available_years
    
    # === GESTION DU CACHE DES COULEURS POUR LA COHÉRENCE VISUELLE ===
    # Le cache de couleurs assure que chaque année garde la même couleur dans tous les graphiques de l'application
    if 'color_map_cache' not in st.session_state:
        # Première initialisation : créer la palette de couleurs extensible
        default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
        
        # Générer automatiquement le color_map pour toutes les années présentes dans les données
        color_map = {}
        unique_years = sorted(test2['Year'].unique())
        for i, year in enumerate(unique_years):
            color_map[year] = default_colors[i % len(default_colors)]  # Cycling des couleurs si plus de 20 années
        
        # Sauvegarder dans le cache de session
        st.session_state.color_map_cache = color_map
        st.session_state.cached_years = set(unique_years)
    else:
        # Vérifier si de nouvelles années sont présentes dans les données (rechargement fichier)
        current_years = set(test2['Year'].unique())
        cached_years = st.session_state.get('cached_years', set())
        
        if current_years != cached_years:
            # Régénérer le color_map si les années ont changé (nouveau fichier uploadé)
            default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
            color_map = {}
            unique_years = sorted(test2['Year'].unique())
            for i, year in enumerate(unique_years):
                color_map[year] = default_colors[i % len(default_colors)]
            
            # Mettre à jour le cache
            st.session_state.color_map_cache = color_map
            st.session_state.cached_years = current_years
        else:
            # Utiliser le cache existant
            color_map = st.session_state.color_map_cache
    
    # === CRÉATION DE LA FIGURE PLOTLY ===
    fig = go.Figure()
    
    # === FILTRAGE ET PRÉPARATION DES DONNÉES ===
    # Filtrer les données uniquement pour les années sélectionnées par l'utilisateur
    filtered_years_data = test2[test2['Year'].isin(selected_years)]
    
    # Vérification que nous avons des données après filtrage
    if filtered_years_data.empty:
        return None
    
    # Trier les années sélectionnées pour un affichage ordonné
    selected_years_sorted = sorted(selected_years)
    
    # === AGRÉGATION DES DONNÉES PAR JOUR ET PAR ANNÉE ===
    # Dictionnaire pour stocker les données journalières de chaque année
    year_data_dict = {}
    
    # Récupérer les données pour chaque année sélectionnée avec granularité journalière
    for year in selected_years_sorted:
        year_data = test2[test2['Year'] == year]
        if not year_data.empty:
            # Resample à la granularité journalière et sommer les consommations
            year_data_dict[year] = year_data.resample('D').sum(numeric_only=True)
    
    # === CRÉATION D'UNE TIMELINE CONTINUE SANS GAPS ===
    # Cette section transforme les dates pour créer une visualisation continue
    # même quand les années ne sont pas consécutives (ex: 2022, 2024, 2025)
    continuous_data = {}  # Pour stocker les données avec dates transformées
    shifted_dates_map = {}  # Mapper les dates transformées aux dates originales pour le hover
    
    for i, year in enumerate(selected_years_sorted):
        if year in year_data_dict:
            year_df = year_data_dict[year]
            
            # Pour la première année, utiliser les dates telles quelles
            if i == 0:
                continuous_data[year] = year_df
                # Créer le mapping date transformée -> date réelle pour le hover
                for date in year_df.index:
                    shifted_dates_map[date] = date
            else:
                # Pour les années suivantes, créer des dates adjacentes à l'année précédente
                prev_year = selected_years_sorted[i-1]
                last_date_prev_year = max(continuous_data[prev_year].index)
                
                # Calculer les dates transformées pour cette année (continuation de la timeline)
                transformed_dates = []
                real_dates = []
                
                for idx, date in enumerate(year_df.index):
                    # Calculer le jour de l'année (1-365/366)
                    day_of_year = (date - pd.Timestamp(f"{year}-01-01")).days + 1
                    # Créer une nouvelle date qui continue la timeline précédente
                    new_date = last_date_prev_year + pd.Timedelta(days=day_of_year)
                    
                    transformed_dates.append(new_date)
                    real_dates.append(date)
                    shifted_dates_map[new_date] = date  # Mapping pour le hover
                
                # Créer un nouveau DataFrame avec les dates transformées
                transformed_df = pd.DataFrame(
                    index=transformed_dates, 
                    data=year_df.values, 
                    columns=year_df.columns
                )
                continuous_data[year] = transformed_df
    
    # === AJOUT DES TRACES AU GRAPHIQUE PLOTLY ===
    # Tracer les données avec les dates transformées pour une timeline continue
    for i, year in enumerate(selected_years_sorted):
        if year in continuous_data:
            df = continuous_data[year]
            
            # === PRÉPARATION DES DONNÉES POUR LE HOVER (infobulles) ===
            # Récupérer les dates réelles pour affichage dans les infobulles
            hover_dates = [shifted_dates_map.get(date, date) for date in df.index]
            hover_text = [d.strftime('%Y-%m-%d') for d in hover_dates]
            hover_template = '%{text}<br>Consommation: %{y:.1f} kWh<extra></extra>'
            
            # === AJOUT DE LA COURBE PRINCIPALE POUR CETTE ANNÉE ===
            year_color = color_map.get(year, '#42A5F5')  # Récupérer la couleur assignée à cette année
            fig.add_trace(go.Scatter(
                x=df.index,  # Dates transformées pour timeline continue
                y=df['Consumption (kWh)'],  # Valeurs de consommation journalière
                mode='lines',
                name=str(year),  # Nom affiché dans la légende
                line=dict(color=year_color, width=2.5),  # Style de la ligne
                hovertemplate=hover_template,  # Template pour les infobulles
                text=hover_text  # Texte des dates réelles pour le hover
            ))
            
            # === AJOUT DES LIGNES DE CONNEXION ENTRE ANNÉES ===
            # Si ce n'est pas la première année, ajouter une connexion visuelle avec l'année précédente
            if i > 0:
                prev_year = selected_years_sorted[i-1]
                prev_df = continuous_data[prev_year]
                
                # Connecter le dernier point de l'année précédente au premier point de l'année courante
                last_idx_prev = prev_df.index[-1]  # Dernière date de l'année précédente
                first_idx_curr = df.index[0]  # Première date de l'année courante
                
                # Valeurs de consommation pour ces points de connexion
                last_val_prev = prev_df['Consumption (kWh)'].iloc[-1]
                first_val_curr = df['Consumption (kWh)'].iloc[0]
                
                # Tracer la ligne de connexion (même couleur que l'année précédente)
                prev_year_color = color_map.get(prev_year, '#42A5F5')
                fig.add_trace(go.Scatter(
                    x=[last_idx_prev, first_idx_curr],
                    y=[last_val_prev, first_val_curr],
                    mode='lines',
                    line=dict(color=prev_year_color, width=2.5),
                    showlegend=False,  # Ne pas afficher dans la légende
                    hoverinfo='skip'  # Pas d'infobulle pour la connexion
                ))
    
    # === CONFIGURATION DE L'AXE X AVEC TICKS PERSONNALISÉS ===
    # Déterminer la plage de dates pour le graphique (toutes les dates transformées)
    all_dates = []
    for year in selected_years_sorted:
        if year in continuous_data:
            all_dates.extend(continuous_data[year].index)
    
    # Vérification que nous avons des dates à afficher
    if not all_dates:
        return None
    
    # Calculer les bornes temporelles et la durée totale
    date_min = min(all_dates)
    date_max = max(all_dates)
    total_days = (date_max - date_min).days
    
    # === CRÉATION DES TICKS PERSONNALISÉS POUR L'AXE X ===
    # Créer des marqueurs temporels adaptés à la durée totale des données
    custom_ticks = []
    custom_tick_labels = []
    
    # Optimiser l'intervalle des ticks selon la durée totale pour éviter la surcharge
    if total_days <= 14:
        tick_interval = 1  # Quotidien pour les périodes courtes
    elif total_days <= 60:
        tick_interval = 5  # Tous les 5 jours pour les périodes moyennes
    elif total_days <= 120:
        tick_interval = 10  # Tous les 10 jours pour les périodes longues
    else:
        tick_interval = 30  # Mensuel pour les très longues périodes
    
    # Générer les ticks et leurs labels
    current_date = date_min
    while current_date <= date_max:
        custom_ticks.append(current_date)
        real_date = shifted_dates_map.get(current_date, current_date)  # Récupérer la date réelle
        
        # Format d'affichage adapté à la durée
        if total_days <= 60:
            # Format court pour les périodes courtes : "15 jan"
            custom_tick_labels.append(f"{real_date.day} {get_month_abbr_french(real_date)}")
        else:
            # Format avec année pour les longues périodes : "jan 2023"
            custom_tick_labels.append(f"{get_month_abbr_french(real_date)} {real_date.year}")
        
        current_date += pd.Timedelta(days=tick_interval)

    # === CONFIGURATION FINALE DU LAYOUT PLOTLY ===
    # Configuration optimisée pour l'affichage dans le dashboard (hauteur réduite, pas de zoom)
    fig.update_layout( 
        xaxis_title='Période',  # Titre de l'axe X
        yaxis_title='Consommation journalière (kWh)',  # Titre de l'axe Y
        height=400,  # Hauteur réduite pour mieux s'aligner avec les cartes du dashboard
        xaxis=dict(
            rangeslider=dict(visible=False),  # Retirer la barre de zoom pour économiser l'espace
            type="date",
            tickvals=custom_ticks,  # Positions des marqueurs
            ticktext=custom_tick_labels,  # Textes des marqueurs
            tickmode='array',
            range=[date_min, date_max]  # Plage d'affichage
        ),
        margin=dict(l=40, r=20, t=20, b=40),  # Marges réduites pour optimiser l'espace
        paper_bgcolor='rgba(0,0,0,0)',  # Fond transparent
        plot_bgcolor='rgba(0,0,0,0)',  # Fond de graphique transparent
        hovermode='closest',  # Mode de hover pour les infobulles
        legend=dict(
            orientation="h",  # Légende horizontale
            yanchor="bottom",
            y=1.02,  # Position au-dessus du graphique
            xanchor="center",
            x=0.5
        ),
        showlegend=True  # Afficher la légende des années
    )
    
    return fig


def create_monthly_cost_plot(test2):
    """
    Crée un graphique Plotly des coûts mensuels pour le dashboard
    
    Cette fonction génère un graphique en barres des coûts énergétiques mensuels en tenant compte :
    - Du type de tarif sélectionné (Unique ou HP/HC) dans la sidebar
    - Du mode d'analyse (année unique vs données complètes)
    - De la cohérence des couleurs avec les autres graphiques via le cache
    - De l'affichage en français des mois
    
    Args:
        test2 (DataFrame): DataFrame des données de consommation avec colonnes 'Year' et 'Consumption (kWh)'
        
    Returns:
        plotly.graph_objects.Figure or None: Figure Plotly du graphique des coûts mensuels
        
    Données utilisées depuis st.session_state:
        - tariff_type : "Tarif Unique" ou "Tarif HP/HC"
        - tariff_unique_price, tariff_hp_price, tariff_hc_price : Prix des tarifs
        - peak_start_hour, peak_end_hour, peak_days : Configuration HP/HC
        - analysis_mode, year_selection_mode : Modes de sélection des données
    """
    # Vérification de la validité des données d'entrée
    if test2 is None or test2.empty:
        return None
    
    # === RÉCUPÉRATION DES PARAMÈTRES D'ANALYSE DEPUIS LA SESSION ===
    # Même logique que create_annual_view_plot pour la cohérence
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    
    # === DÉTERMINATION DES ANNÉES À AFFICHER (même logique que le graphique annuel) ===
    if analysis_mode == 'single_year':
        # Mode année unique : afficher seulement l'année sélectionnée
        selected_analysis_year = st.session_state.get('selected_analysis_year')
        if selected_analysis_year:
            selected_years = [selected_analysis_year]
        else:
            selected_years = sorted(test2['Year'].unique())[:1]
    else:
        # Mode données complètes : gérer plusieurs années
        available_years = sorted(test2['Year'].unique())
        
        if year_selection_mode == "Données complètes":
            # Limiter aux 3 années les plus récentes maximum pour performance
            selected_years = available_years[-3:] if len(available_years) > 3 else available_years
        else:
            # Années partielles sélectionnées par l'utilisateur
            selected_partial_years = st.session_state.get('selected_partial_years', [])
            if selected_partial_years:
                selected_years = selected_partial_years[-3:] if len(selected_partial_years) > 3 else selected_partial_years
            else:
                selected_years = available_years[-3:] if len(available_years) > 3 else available_years
    
    # === RÉCUPÉRATION DU CACHE DE COULEURS (cohérence avec autres graphiques) ===
    if 'color_map_cache' not in st.session_state:
        # Initialisation si pas encore créé (normalement déjà fait par create_annual_view_plot)
        default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
        color_map = {}
        unique_years = sorted(test2['Year'].unique())
        for i, year in enumerate(unique_years):
            color_map[year] = default_colors[i % len(default_colors)]
        st.session_state.color_map_cache = color_map
    else:
        # Utiliser le cache existant pour la cohérence des couleurs
        color_map = st.session_state.color_map_cache
    
    # === RÉCUPÉRATION DES PARAMÈTRES DE TARIFICATION ===
    # Ces paramètres sont configurés par l'utilisateur dans la sidebar de main.py
    tariff_type = st.session_state.get('tariff_type', 'Tarif Unique')
    
    # === CALCUL DES COÛTS EN FONCTION DU TYPE DE TARIF ===
    df_with_cost = test2.copy()  # Copie pour ne pas modifier l'original
    
    if tariff_type == "Tarif Unique":
        # Tarif unique : prix constant par kWh
        kwh_price = st.session_state.get('tariff_unique_price', 0.35)  # Prix par défaut 0.35 CHF/kWh
        df_with_cost['Cost'] = df_with_cost['Consumption (kWh)'] * kwh_price
    else:  # Tarif HP/HC (Heures Pleines/Heures Creuses)
        # Récupération des paramètres HP/HC configurés dans la sidebar
        hp_price = st.session_state.get('tariff_hp_price', 0.40)  # Prix heures pleines
        hc_price = st.session_state.get('tariff_hc_price', 0.27)  # Prix heures creuses
        peak_start = st.session_state.get('peak_start_hour', 6)   # Début HP (6h par défaut)
        peak_end = st.session_state.get('peak_end_hour', 22)     # Fin HP (22h par défaut)
        peak_days = st.session_state.get('peak_days', [0, 1, 2, 3, 4])  # Jours HP (lun-ven par défaut)
        
        # Déterminer si chaque point de données est en HP ou HC
        # Utilisation de la fonction is_peak_hour du module cost_analysis
        df_with_cost['is_peak'] = df_with_cost.index.map(
            lambda timestamp: is_peak_hour(timestamp, peak_start, peak_end, peak_days)
        )
        
        # Appliquer le tarif approprié selon HP/HC
        df_with_cost['Cost'] = df_with_cost.apply(
            lambda row: row['Consumption (kWh)'] * hp_price if row['is_peak'] 
                        else row['Consumption (kWh)'] * hc_price,
            axis=1
        )
    
    # === FILTRAGE DES DONNÉES POUR LES ANNÉES SÉLECTIONNÉES ===
    year_data = df_with_cost[df_with_cost['Year'].isin(selected_years)]
    
    if year_data.empty:
        return None
    
    # === CONFIGURATION DES LABELS DE MOIS EN FRANÇAIS ===
    # Dictionnaire de correspondance pour l'affichage français des mois
    mois_fr = {
        'Jan': 'Jan', 'Feb': 'Fév', 'Mar': 'Mar', 'Apr': 'Avr',
        'May': 'Mai', 'Jun': 'Juin', 'Jul': 'Juil', 'Aug': 'Août',
        'Sep': 'Sep', 'Oct': 'Oct', 'Nov': 'Nov', 'Dec': 'Déc'
    }
    
    # === CRÉATION DE LA FIGURE PLOTLY ===
    fig = go.Figure()
    
    # === LOGIQUE D'AFFICHAGE SELON LE MODE D'ANALYSE ===
    if analysis_mode == 'single_year':
        # === MODE ANNÉE UNIQUE : AFFICHAGE MENSUEL POUR CETTE ANNÉE ===
        selected_year = selected_years[0]
        
        # Créer une base complète avec tous les mois de l'année (même si pas de données)
        all_months = pd.date_range(start=f"{selected_year}-01-01", 
                                  end=f"{selected_year}-12-31", 
                                  freq='M')  # Fréquence mensuelle
        
        # Initialiser un DataFrame avec tous les mois à zéro
        monthly_df = pd.DataFrame(index=all_months, columns=['Cost', 'Consumption'])
        monthly_df['Cost'] = 0
        monthly_df['Consumption'] = 0
        
        # === AGRÉGATION DES DONNÉES RÉELLES PAR MOIS ===
        # Remplir avec les données réelles disponibles (somme mensuelle)
        actual_monthly_costs = year_data.resample('M')['Cost'].sum()
        actual_monthly_consumption = year_data.resample('M')['Consumption (kWh)'].sum()
        
        # Intégrer les coûts réels dans le DataFrame complet
        for date, cost in actual_monthly_costs.items():
            if date in monthly_df.index:
                monthly_df.loc[date, 'Cost'] = cost
        
        # Intégrer les consommations réelles dans le DataFrame complet
        for date, consumption in actual_monthly_consumption.items():
            if date in monthly_df.index:
                monthly_df.loc[date, 'Consumption'] = consumption
        
        # === CRÉATION DU GRAPHIQUE EN BARRES POUR L'ANNÉE UNIQUE ===
        fig.add_trace(go.Bar(
            x=[d.strftime("%b") for d in monthly_df.index],  # Labels des mois en anglais (conversion en français plus bas)
            y=monthly_df['Cost'],  # Valeurs des coûts mensuels
            marker_color=color_map.get(selected_year, '#42A5F5'),  # Couleur cohérente avec autres graphiques
            name=f'{selected_year}',  # Nom pour la légende
            customdata=monthly_df['Consumption'],  # Données supplémentaires pour le hover
            hovertemplate=f'<b>{selected_year}</b><br>' +
                         'Mois: %{x}<br>' +
                         'Coût: %{y:.2f} CHF<br>' +
                         'Consommation: %{customdata:.1f} kWh<br>' +
                         '<extra></extra>'  # Template des infobulles
        ))
        
        # Configuration de l'axe X pour l'année unique
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=[d.strftime("%b") for d in monthly_df.index],
                ticktext=[mois_fr[d.strftime("%b")] for d in monthly_df.index],  # Conversion en français
                tickangle=0,
                showgrid=False
            )
        )
        
    else:
        # === MODE DONNÉES COMPLÈTES : GRAPHIQUE AVEC ANNÉES CÔTE À CÔTE ===
        selected_years_for_comparison = selected_years
        
        # Liste des mois en français pour l'axe X
        months_list = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 
                      'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
        months_order = list(range(1, 13))  # Ordre numérique des mois (1-12)
        
        # === CRÉATION DES DONNÉES POUR CHAQUE ANNÉE SÉLECTIONNÉE ===
        for year in sorted(selected_years_for_comparison):
            year_monthly_data = year_data[year_data['Year'] == year]
            
            # Dictionnaires pour stocker les coûts et consommations mensuels
            monthly_costs_dict = {}
            monthly_consumption_dict = {}
            
            if not year_monthly_data.empty:
                # Agrégation mensuelle des coûts et consommations
                monthly_costs = year_monthly_data.resample('M')['Cost'].sum()
                monthly_consumption = year_monthly_data.resample('M')['Consumption (kWh)'].sum()
                
                # Remplir les dictionnaires par numéro de mois
                for date, cost in monthly_costs.items():
                    monthly_costs_dict[date.month] = cost
                
                for date, consumption in monthly_consumption.items():
                    monthly_consumption_dict[date.month] = consumption
            
            # === CRÉATION DES LISTES DE DONNÉES POUR TOUS LES MOIS ===
            # Assurer que tous les mois sont représentés (même avec 0 si pas de données)
            monthly_costs_list = []
            monthly_consumption_list = []
            for month_num in months_order:
                monthly_costs_list.append(monthly_costs_dict.get(month_num, 0))
                monthly_consumption_list.append(monthly_consumption_dict.get(month_num, 0))
            
            # === AJOUT DE LA TRACE POUR CETTE ANNÉE ===
            fig.add_trace(go.Bar(
                x=months_list,  # Mois en français
                y=monthly_costs_list,  # Coûts mensuels
                name=f'{year}',  # Nom pour la légende
                marker_color=color_map.get(year, '#42A5F5'),  # Couleur cohérente
                customdata=monthly_consumption_list,  # Consommations pour le hover
                hovertemplate=f'<b>{year}</b><br>' +
                             'Mois: %{x}<br>' +
                             'Coût: %{y:.2f} CHF<br>' +
                             'Consommation: %{customdata:.1f} kWh<br>' +
                             '<extra></extra>'
            ))
        
        # === CONFIGURATION POUR COMPARAISON MULTI-ANNÉES ===
        fig.update_layout(
            barmode='group',  # Barres groupées par mois pour comparer les années
            xaxis=dict(
                tickmode='array',
                tickvals=months_list,
                ticktext=months_list,  # Déjà en français
                tickangle=0,
                showgrid=False
            ),
            legend=dict(
                orientation="h",  # Légende horizontale
                yanchor="bottom",
                y=1.02,  # Au-dessus du graphique
                xanchor="center",
                x=0.5
            )
        )
    
    # === CONFIGURATION COMMUNE DU LAYOUT ===
    fig.update_layout(
        xaxis_title="Mois",  # Titre de l'axe X
        yaxis_title="Coût (CHF)",  # Titre de l'axe Y
        plot_bgcolor='white',  # Fond blanc pour les barres
        margin=dict(l=40, r=20, t=20, b=40),  # Marges réduites pour le dashboard
        height=420,  # Hauteur optimisée pour le dashboard
        paper_bgcolor='rgba(0,0,0,0)'  # Fond transparent
    )
    
    return fig


# === FONCTIONS UTILITAIRES POUR LE FORMATAGE ET LES COULEURS ===

def format_number_with_apostrophe(number, decimal_places=0):
    """
    Formate un nombre avec des apostrophes comme séparateurs de milliers (norme suisse)
    
    Cette fonction applique le format suisse pour les grands nombres :
    - 1234567.89 devient "1'234'567.89" ou "1'234'568" si decimal_places=0
    - Utilisée pour l'affichage des valeurs dans les cartes du dashboard
    
    Args:
        number (float): Nombre à formater
        decimal_places (int): Nombre de décimales à afficher (défaut: 0)
        
    Returns:
        str: Nombre formaté avec apostrophes ou "0" si number est None
        
    Exemples:
        format_number_with_apostrophe(1234567.89, 2) -> "1'234'567.89"
        format_number_with_apostrophe(1234567.89, 0) -> "1'234'568"
        format_number_with_apostrophe(1234, 1) -> "1'234.0"
    """
    # Gestion des valeurs nulles
    if number is None:
        return "0"
    
    # === FORMATAGE SELON LE NOMBRE DE DÉCIMALES SOUHAITÉ ===
    if decimal_places == 0:
        formatted = f"{number:.0f}"
    elif decimal_places == 1:
        formatted = f"{number:.1f}"
    elif decimal_places == 2:
        formatted = f"{number:.2f}"
    else:
        formatted = f"{number:.{decimal_places}f}"
    
    # === SÉPARATION ET FORMATAGE AVEC APOSTROPHES ===
    if '.' in formatted:
        # Nombre avec décimales : séparer partie entière et décimale
        integer_part, decimal_part = formatted.split('.')
        formatted_with_apostrophe = f"{int(integer_part):_}".replace('_', "'")  # Remplacer _ par '
        return f"{formatted_with_apostrophe}.{decimal_part}"
    else:
        # Nombre entier : formatage direct avec apostrophes
        return f"{int(formatted):_}".replace('_', "'")


# === FONCTIONS DE DÉFINITION DES COULEURS ET STATUTS DES INDICATEURS ===

def get_day_night_ratio_color_and_status(ratio):
    """
    Détermine la couleur et le statut d'affichage pour le ratio jour/nuit
    
    Cette fonction applique la logique métier pour interpréter le ratio jour/nuit :
    - Ratio équilibré (1.7-2.3) : Vert, "Équilibré" (consommation normale)
    - Ratio élevé (>2.3) : Jaune, "Élevé" (forte consommation diurne)
    - Ratio faible (<1.7) : Rouge, "Faible" (consommation nocturne élevée, problème potentiel)
    
    Args:
        ratio (float): Valeur du ratio jour/nuit calculé par calculate_day_night_ratio
        
    Returns:
        tuple: (couleur_hex, statut_text)
            - couleur_hex (str): Code couleur hexadécimal pour l'affichage
            - statut_text (str): Texte descriptif du statut
    """
    if 1.7 <= ratio <= 2.3:
        return "#27ae60", "Équilibré"  # 🟢 Vert - situation normale
    elif ratio > 2.3:
        return "#f1c40f", "Élevé"      # 🟡 Jaune - forte consommation diurne
    else:  # ratio < 1.7
        return "#e74c3c", "Faible"     # 🔴 Rouge - consommation nocturne élevée (problème potentiel)


def get_weekday_weekend_ratio_color_and_status(ratio):
    """
    Détermine la couleur et le statut d'affichage pour le ratio semaine/week-end
    
    Cette fonction applique la logique métier pour interpréter le ratio semaine/week-end :
    - Ratio équilibré (2.2-2.8) : Vert, "Équilibré" (différence normale entre semaine et week-end)
    - Ratio élevé (>2.8) : Bleu, "Élevé" (forte activité en semaine vs week-end)
    - Ratio faible (<2.2) : Orange, "Faible" (peu de différence entre semaine et week-end)
    
    Args:
        ratio (float): Valeur du ratio semaine/week-end calculé par calculate_weekday_weekend_ratio
        
    Returns:
        tuple: (couleur_hex, statut_text)
            - couleur_hex (str): Code couleur hexadécimal pour l'affichage
            - statut_text (str): Texte descriptif du statut
    """
    if 2.2 <= ratio <= 2.8:
        return "#27ae60", "Équilibré"  # 🟢 Vert - différence normale semaine/week-end
    elif ratio > 2.8:
        return "#3498db", "Élevé"      # 🔵 Bleu - forte activité professionnelle en semaine
    else:  # ratio < 2.2
        return "#e67e22", "Faible"     # 🟠 Orange - peu de différence (usage plutôt résidentiel)


def get_trend_info(ratios_list, years_list):
    """
    Calcule les informations de tendance pour un indicateur basé sur les années complètes
    
    Cette fonction analyse l'évolution d'un indicateur (ratio, charge de base, etc.) entre
    les années complètes disponibles et détermine la tendance et les couleurs d'affichage.
    
    Critères de tendance :
    - Stable : variation < 10% (Bleu)
    - Hausse : variation >= 10% (Rouge)  
    - Baisse : variation <= -10% (Vert)
    
    Args:
        ratios_list (list): Liste des valeurs de l'indicateur par année
        years_list (list): Liste des années correspondantes
        
    Returns:
        tuple: (trend_icon, trend_text, trend_color, trend_percent, first_year, last_year)
            - trend_icon (str): Emoji de tendance ("➡️", "⬆️", "⬇️") ou None
            - trend_text (str): Texte de tendance ("Stable", "Hausse", "Baisse") ou None
            - trend_color (str): Couleur hexadécimale de la tendance ou None
            - trend_percent (float): Pourcentage de variation ou None
            - first_year (int): Première année de la tendance ou None
            - last_year (int): Dernière année de la tendance ou None
            
    Note:
        Utilise years_completeness de la session pour ne considérer que les années complètes (100% de données)
    """
    # Vérification que nous avons suffisamment de données pour calculer une tendance
    if len(ratios_list) >= 2 and len(years_list) >= 2:
        # === FILTRAGE DES ANNÉES COMPLÈTES POUR LA TENDANCE ===
        # Récupérer les informations de complétude des années depuis la session
        # (calculées dans main.py lors de l'analyse des données)
        years_completeness = st.session_state.get('years_completeness', {})
        valid_years_for_trend = []
        valid_ratios_for_trend = []
        
        # Créer des listes filtrées avec seulement les années complètes (100% de données)
        for i, year in enumerate(years_list):
            if year in years_completeness and years_completeness[year] >= 100:
                valid_years_for_trend.append(year)
                if i < len(ratios_list):
                    valid_ratios_for_trend.append(ratios_list[i])
        
        # === CALCUL DE LA TENDANCE ===
        # Afficher la tendance seulement si on a au moins 2 années complètes
        if len(valid_years_for_trend) >= 2 and len(valid_ratios_for_trend) >= 2:
            # Prendre les deux années complètes les plus récentes pour la tendance
            if len(valid_years_for_trend) >= 2:
                first_ratio = valid_ratios_for_trend[-2]   # Avant-dernière année complète
                last_ratio = valid_ratios_for_trend[-1]   # Dernière année complète
                first_year = valid_years_for_trend[-2]    # Avant-dernière année complète
                last_year = valid_years_for_trend[-1]     # Dernière année complète
            else:
                # Fallback si seulement 2 années
                first_ratio = valid_ratios_for_trend[0]   # Premier ratio (année la plus ancienne)
                last_ratio = valid_ratios_for_trend[-1]  # Dernier ratio (année la plus récente)
                first_year = valid_years_for_trend[0]    # Première année complète
                last_year = valid_years_for_trend[-1]    # Dernière année complète
            
            # Calcul du pourcentage de variation
            change_percent = ((last_ratio - first_ratio) / first_ratio) * 100 if first_ratio != 0 else 0
            
            # === DÉTERMINATION DE LA TENDANCE ET DES COULEURS ===
            if abs(change_percent) < 10:
                return "➡️", "Stable", "#3498db", change_percent, first_year, last_year  # Bleu pour stable
            elif change_percent >= 10:
                return "⬆️", "Hausse", "#e74c3c", change_percent, first_year, last_year  # Rouge pour augmentation
            else:  # change_percent <= -10
                return "⬇️", "Baisse", "#27ae60", change_percent, first_year, last_year  # Vert pour diminution
    
    # Retourner None si pas assez de données pour calculer une tendance
    return None, None, None, None, None, None


# === FONCTIONS DE CRÉATION DES CARTES INDICATEURS DU DASHBOARD ===

def create_ratio_card(ratio_data, card_type, col, target_id):
    """
    Crée une carte cliquable pour afficher un ratio (jour/nuit ou semaine/week-end) avec tendance
    
    Cette fonction génère une carte HTML interactive qui :
    - Affiche la valeur du ratio avec couleur selon le statut
    - Inclut l'icône et pourcentage de tendance si disponible
    - Redirige vers la section détaillée au clic
    - Applique un effet hover pour l'interactivité
    
    Args:
        ratio_data (dict): Données du ratio contenant 'overall_ratio', 'ratios_list', 'years'
        card_type (str): Type de carte ("day_night" ou "weekday_weekend")
        col (streamlit.container): Conteneur Streamlit où afficher la carte
        target_id (str): ID de la section cible pour le lien de navigation
        
    Note:
        Les données ratio_data proviennent des fonctions calculate_day_night_ratio ou 
        calculate_weekday_weekend_ratio du module indicators
    """
    # === DÉTERMINATION DU TYPE DE CARTE ET RÉCUPÉRATION DES DONNÉES ===
    if card_type == "day_night":
        ratio = ratio_data['overall_ratio']
        color, status = get_day_night_ratio_color_and_status(ratio)  # Appel fonction couleur jour/nuit
        title = "Ratio Jour/Nuit"
        link_text = "→ Voir votre ratio jour/nuit"
    elif card_type == "weekday_weekend":
        ratio = ratio_data['overall_ratio']
        color, status = get_weekday_weekend_ratio_color_and_status(ratio)  # Appel fonction couleur semaine/week-end
        title = "Ratio Semaine/Weekend"
        link_text = "→ Voir votre ratio semaine/weekend"
    
    # === CALCUL DE LA TENDANCE POUR CETTE CARTE ===
    # Utilisation de la fonction get_trend_info pour analyser l'évolution
    trend_icon, trend_text, trend_color, trend_percent, first_year, last_year = get_trend_info(
        ratio_data.get('ratios_list', []),  # Liste des ratios par année
        ratio_data.get('years', [])         # Liste des années correspondantes
    )
    
    # === CRÉATION DU HTML DE LA TENDANCE ===
    # Affichage conditionnel de la tendance si elle existe
    trend_display = ""
    if trend_icon:
        trend_display = f'''<div style="margin-top: 4px; font-size: 0.75em; color: {trend_color}; line-height: 1.1;">
            <div style="font-weight: bold;">{trend_icon} {trend_percent:+.0f}%</div>
            <div style="font-size: 0.7em; opacity: 0.75;">{first_year}-{last_year}</div>
        </div>'''
    
    # === CRÉATION DE LA CARTE HTML INTERACTIVE ===
    with col:
        st.markdown(f'''
        <div onclick="document.getElementById('{target_id}').scrollIntoView({{behavior: 'smooth'}})" style="
            background: linear-gradient(135deg, {color}20, {color}08);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 8px;
            height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            <div style="color: {color}; font-size: 0.85em; font-weight: bold; margin-bottom: 4px; line-height: 1.1;">{title}</div>
            <div style="color: {color}; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">{ratio:.2f}</div>
            <div style="color: {color}; font-size: 0.75em; font-weight: 500; line-height: 1.1;">{status}</div>
            {trend_display}
        </div>
        ''', unsafe_allow_html=True)
        
        # === LIEN DE NAVIGATION VERS LA SECTION DÉTAILLÉE ===
        st.markdown(f'''
        <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
            <a href="#{target_id}" style="color: #dc3545; text-decoration: none; font-size: 0.7em; font-weight: 500; line-height: 1.2;">
                {link_text}
            </a>
        </div>
        ''', unsafe_allow_html=True)


def create_base_load_card(base_loads, years, col):
    """
    Crée une carte pour afficher la charge de base (charge nocturne) avec tendance
    
    Cette fonction affiche la charge nocturne moyenne en watts avec :
    - Conversion automatique de kW vers W pour meilleure lisibilité
    - Calcul de tendance basé sur les années complètes disponibles
    - Formatage avec apostrophes selon norme suisse
    - Navigation vers la section détaillée de la charge de base
    
    Args:
        base_loads (list): Liste des charges de base par année (en kW)
        years (list): Liste des années correspondantes
        col (streamlit.container): Conteneur Streamlit où afficher la carte
        
    Note:
        Les données base_loads proviennent de la fonction calculate_base_load du module indicators.
        La dernière valeur de base_loads est souvent la moyenne globale si plusieurs années.
    """
    color_base = "#2c3e50"  # Gris foncé neutre pour toutes les cartes de charge
    
    if len(base_loads) > 0:
        # === LOGIQUE DE SÉLECTION DE LA VALEUR À AFFICHER ===
        # Même logique que dans le module indic_func pour la cohérence
        if len(years) >= 2 and len(base_loads) > len(years):
            # Si nous avons plus de base_loads que d'années, la dernière valeur est la moyenne globale
            avg_base_load = base_loads[-1]  # Moyenne globale calculée
            
            # === CALCUL DE LA TENDANCE POUR LA CHARGE DE BASE ===
            # La logique de filtrage des années complètes est maintenant faite dans calculate_base_load()
            # Si nous avons 2+ années dans years, elles sont déjà filtrées pour être complètes et récentes
            if len(years) >= 2 and len(base_loads) >= 2:
                # Les valeurs sont déjà dans le bon ordre
                first_year_value = base_loads[0]
                last_year_value = base_loads[-1] if len(base_loads) == len(years) else base_loads[-2]
                
                # Calculer le pourcentage de variation
                change_percent = ((last_year_value - first_year_value) / first_year_value) * 100 if first_year_value != 0 else 0
                
                # Déterminer la tendance et les couleurs
                if abs(change_percent) < 10:
                    trend_icon, trend_text, trend_color = "➡️", "Stable", "#3498db"  # Bleu pour stable
                elif change_percent >= 10:
                    trend_icon, trend_text, trend_color = "⬆️", "Hausse", "#e74c3c"  # Rouge pour augmentation
                else:  # change_percent <= -10
                    trend_icon, trend_text, trend_color = "⬇️", "Baisse", "#27ae60"  # Vert pour diminution
                
                # HTML de la tendance
                trend_display = f'''<div style="margin-top: 4px; font-size: 0.75em; color: {trend_color}; line-height: 1.1;">
                    <div style="font-weight: bold;">{trend_icon} {change_percent:+.0f}%</div>
                    <div style="font-size: 0.7em; opacity: 0.75;">{years[0]}-{years[-1]}</div>
                </div>'''
            else:
                trend_display = ""  # Pas assez de données pour la tendance
        else:
            # Une seule année ou pas de moyenne globale : prendre la première valeur
            avg_base_load = base_loads[0] if len(base_loads) > 0 else 0
            trend_display = ""  # Pas de tendance possible avec une seule année
        
        # === CRÉATION DE LA CARTE HTML ===
        with col:
            st.markdown(f'''
            <div onclick="document.getElementById('charge-base').scrollIntoView({{behavior: 'smooth'}})" style="
                background: linear-gradient(135deg, {color_base}20, {color_base}08);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 8px;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                overflow: hidden;
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style="color: {color_base}; font-size: 0.85em; font-weight: bold; margin-bottom: 4px; line-height: 1.1;">⚡ Charge Nocturne</div>
                <div style="color: {color_base}; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">{format_number_with_apostrophe(avg_base_load*1000, 1)} W</div>
                <div style="color: {color_base}; font-size: 0.75em; font-weight: 500;">Moyenne</div>
                {trend_display}
            </div>
            ''', unsafe_allow_html=True)
        
            # === LIEN DE NAVIGATION ===
            st.markdown(f'''
            <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                <a href="#charge-base" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                    → Voir votre charge de base
                </a>
            </div>
            ''', unsafe_allow_html=True)


def create_consumption_card(col):
    """
    Crée une carte pour afficher la consommation journalière moyenne avec tendance
    
    Cette fonction génère une carte affichant la consommation moyenne journalière en kWh.
    Elle gère automatiquement :
    - Le calcul selon le mode d'analyse (année unique vs données complètes)
    - La tendance basée sur les années complètes disponibles
    - Le formatage avec apostrophes selon norme suisse
    - La navigation vers la section courbe de charge
    
    Args:
        col (streamlit.container): Conteneur Streamlit où afficher la carte
        
    Données utilisées depuis st.session_state:
        - dashboard_consumption_data : Données de consommation calculées par calculate_dashboard_consumption_data
        - dashboard_consumption_years : Années disponibles pour les données
        - year_selection_mode : Mode de sélection des données
        - pdf_filtered : DataFrame filtré pour compter les jours réels
    """
    consumption_data = st.session_state.get('dashboard_consumption_data', {})
    consumption_years = st.session_state.get('dashboard_consumption_years', [])
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    color_consumption = "#2c3e50"  # Couleur noire comme demandé
    
    if consumption_data and consumption_years:
        # Mode données complètes : calculer la consommation globale
        if year_selection_mode == "Données complètes" and len(consumption_years) > 1:
            # Récupérer le DataFrame filtré pour compter les jours réels
            pdf_for_analysis = st.session_state.get('pdf_filtered')
            
            if pdf_for_analysis is not None:
                # Compter le nombre réel de jours de données dans le DataFrame filtré
                unique_days = pdf_for_analysis.index.normalize().nunique()
                
                # Calculer la somme totale divisée par le nombre réel de jours
                total_consumption = 0
                for year in consumption_years:
                    if year in consumption_data:
                        year_data = consumption_data[year]
                        total_consumption += year_data['total_year']
                
                display_consumption = total_consumption / unique_days if unique_days > 0 else 0
            else:
                # Fallback si pas de DataFrame filtré
                total_consumption = 0
                total_days = 0
                
                for year in consumption_years:
                    if year in consumption_data:
                        year_data = consumption_data[year]
                        total_consumption += year_data['total_year']
                        total_days += 365.25
                
                display_consumption = total_consumption / total_days if total_days > 0 else 0
            
            # Vérifier si on a au moins 2 années complètes dans la liste retournée (même logique que base_load)
            years_completeness = st.session_state.get('years_completeness', {})
            valid_years_for_trend = []
            
            for year in consumption_years:
                if year in years_completeness and years_completeness[year] >= 100:
                    valid_years_for_trend.append(year)
            
            # Afficher la tendance seulement si on a exactement 2+ années complètes dans la liste retournée
            if len(valid_years_for_trend) >= 2:
                # Prendre les deux années complètes les plus récentes pour la tendance
                recent_complete_years = sorted(valid_years_for_trend)[-2:]
                latest_year = recent_complete_years[-1]
                previous_year = recent_complete_years[0] if len(recent_complete_years) > 1 else None
                
                if previous_year and previous_year in consumption_data and latest_year in consumption_data:
                    latest_consumption = consumption_data[latest_year]['daily_avg']
                    prev_consumption = consumption_data[previous_year]['daily_avg']
                    trend_percent = ((latest_consumption - prev_consumption) / prev_consumption) * 100
                    
                    if abs(trend_percent) < 10:
                        trend_icon, trend_color = "➡️", "#3498db"  # Bleu pour stable
                    elif trend_percent >= 10:
                        trend_icon, trend_color = "⬆️", "#e74c3c"  # Rouge pour augmentation
                    else:  # trend_percent <= -10
                        trend_icon, trend_color = "⬇️", "#27ae60"  # Vert pour diminution
                    
                    trend_display = f'''<div style="margin-top: 4px; font-size: 0.75em; color: {trend_color}; line-height: 1.1;">
                        <div style="font-weight: bold;">{trend_icon} {trend_percent:+.0f}%</div>
                        <div style="font-size: 0.7em; opacity: 0.75;">{previous_year}-{latest_year}</div>
                    </div>'''
                else:
                    trend_display = ""
            else:
                trend_display = ""
        else:
            # Mode année unique ou une seule année disponible
            if len(consumption_years) >= 2:
                # Vérifier si on a au moins 2 années complètes dans la liste retournée (même logique que base_load)
                years_completeness = st.session_state.get('years_completeness', {})
                valid_years_for_trend = []
                
                for year in consumption_years:
                    if year in years_completeness and years_completeness[year] >= 100:
                        valid_years_for_trend.append(year)
                
                # Afficher la tendance seulement si on a exactement 2+ années complètes dans la liste retournée
                if len(valid_years_for_trend) >= 2:
                    # Prendre les deux années complètes les plus récentes pour la tendance
                    recent_complete_years = sorted(valid_years_for_trend)[-2:]
                    latest_year = recent_complete_years[-1]
                    previous_year = recent_complete_years[0] if len(recent_complete_years) > 1 else None
                    
                    if (previous_year and previous_year in consumption_data and 
                        latest_year in consumption_data):
                        latest_consumption = consumption_data[latest_year]['daily_avg']
                        prev_consumption = consumption_data[previous_year]['daily_avg']
                        trend_percent = ((latest_consumption - prev_consumption) / prev_consumption) * 100
                        
                        if abs(trend_percent) < 10:
                            trend_icon, trend_color = "➡️", "#3498db"  # Bleu pour stable
                        elif trend_percent >= 10:
                            trend_icon, trend_color = "⬆️", "#e74c3c"  # Rouge pour augmentation
                        else:  # trend_percent <= -10
                            trend_icon, trend_color = "⬇️", "#27ae60"  # Vert pour diminution
                        
                        trend_display = f'''<div style="margin-top: 4px; font-size: 0.75em; color: {trend_color}; line-height: 1.1;">
                            <div style="font-weight: bold;">{trend_icon} {trend_percent:+.0f}%</div>
                            <div style="font-size: 0.7em; opacity: 0.75;">{previous_year}-{latest_year}</div>
                        </div>'''
                    else:
                        trend_display = ""
                else:
                    trend_display = ""
                    
                # Prendre la dernière année pour l'affichage
                display_year = max(consumption_years)
                display_consumption = consumption_data[display_year]['daily_avg']
            else:
                # Une seule année disponible
                display_year = consumption_years[0] if year_selection_mode != "Données complètes" else max(consumption_years)
                display_consumption = consumption_data[display_year]['daily_avg']
                trend_display = ""
        
        with col:
            st.markdown(f'''
            <div onclick="document.getElementById('courbe-charge').scrollIntoView({{behavior: 'smooth'}})" style="
                background: linear-gradient(135deg, {color_consumption}20, {color_consumption}08);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 8px;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style="color: {color_consumption}; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">Consommation</div>
                <div style="color: {color_consumption}; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">{format_number_with_apostrophe(display_consumption, 1)}</div>
                <div style="color: {color_consumption}; font-size: 0.75em; font-weight: 500;">kWh/jour</div>
                {trend_display}
            </div>
            ''', unsafe_allow_html=True)
            
            # Lien vers la section
            st.markdown(f'''
            <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                <a href="#courbe-charge" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                    → Voir votre courbe de charge
                </a>
            </div>
            ''', unsafe_allow_html=True)
    else:
        # Pas de données disponibles
        with col:
            st.markdown(f'''
            <div style="
                background: linear-gradient(135deg, #95a5a620, #95a5a608);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 8px;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="color: #95a5a6; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">Consommation</div>
                <div style="color: #95a5a6; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">...</div>
                <div style="color: #95a5a6; font-size: 0.75em; font-weight: 500;">En calcul</div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Lien vers la section
            st.markdown(f'''
            <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                <a href="#courbe-charge" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                    → Voir votre courbe de charge
                </a>
            </div>
            ''', unsafe_allow_html=True)


def create_cost_card(col):
    """Crée une carte pour afficher les coûts annuels"""
    consumption_data = st.session_state.get('dashboard_consumption_data', {})
    consumption_years = st.session_state.get('dashboard_consumption_years', [])
    year_selection_mode = st.session_state.get('year_selection_mode', "Données complètes")
    color_cost = "#2c3e50"  # Gris foncé neutre
    
    if consumption_data and consumption_years:
        # Mode données complètes : afficher le total consolidé
        if year_selection_mode == "Données complètes" and len(consumption_years) > 1:
            total_data = consumption_data.get('total_all_years', {})
            if total_data:
                display_cost = total_data['total_cost']
                # Calculer le total des kWh pour toutes les années
                total_kwh = sum(consumption_data[year]['total_year'] for year in consumption_years if year in consumption_data)
                
                # Vérifier si on a au moins 2 années complètes dans la liste retournée (même logique que base_load)
                years_completeness = st.session_state.get('years_completeness', {})
                valid_years_for_trend = []
                
                for year in consumption_years:
                    if year in years_completeness and years_completeness[year] >= 100:
                        valid_years_for_trend.append(year)
                
                # Calculer la tendance entre les deux années complètes les plus récentes
                if len(valid_years_for_trend) >= 2:
                    # Prendre les deux années complètes les plus récentes pour la tendance
                    recent_complete_years = sorted(valid_years_for_trend)[-2:]
                    first_year = recent_complete_years[0]
                    last_year = recent_complete_years[-1]
                    
                    if first_year != last_year and first_year in consumption_data and last_year in consumption_data:
                        first_cost = consumption_data[first_year]['total_cost']
                        last_cost = consumption_data[last_year]['total_cost']
                        trend_percent = ((last_cost - first_cost) / first_cost) * 100 if first_cost != 0 else 0
                        
                        if abs(trend_percent) < 10:
                            trend_icon, trend_color = "➡️", "#3498db"  # Bleu pour stable
                        elif trend_percent >= 10:
                            trend_icon, trend_color = "⬆️", "#e74c3c"  # Rouge pour augmentation
                        else:  # trend_percent <= -10
                            trend_icon, trend_color = "⬇️", "#27ae60"  # Vert pour diminution
                        
                        trend_display = f'''<div style="margin-top: 4px; font-size: 0.75em; color: {trend_color}; line-height: 1.1;">
                            <div style="font-weight: bold;">{trend_icon} {trend_percent:+.0f}%</div>
                            <div style="font-size: 0.7em; opacity: 0.75;">{first_year}-{last_year}</div>
                        </div>'''
                    else:
                        trend_display = ""
                else:
                    trend_display = ""
                
                cost_label = f"Total"
                cost_unit = f"Total conso :  {format_number_with_apostrophe(total_kwh)} kWh"
            else:
                # Fallback si pas de données totales
                latest_year = max(consumption_years)
                display_cost = consumption_data[latest_year]['total_cost']
                total_kwh = consumption_data[latest_year]['total_year']
                trend_display = ""
                cost_label = "Coût Annuel"
                cost_unit = f"Total conso : {format_number_with_apostrophe(total_kwh)} kWh"
        else:
            # Mode année unique ou une seule année disponible
            if len(consumption_years) >= 2:
                # Vérifier si on a au moins 2 années complètes dans la liste retournée (même logique que base_load)
                years_completeness = st.session_state.get('years_completeness', {})
                valid_years_for_trend = []
                
                for year in consumption_years:
                    if year in years_completeness and years_completeness[year] >= 100:
                        valid_years_for_trend.append(year)
                
                # Afficher la tendance seulement si on a exactement 2+ années complètes dans la liste retournée
                if len(valid_years_for_trend) >= 2:
                    # Prendre les deux années complètes les plus récentes pour la tendance
                    recent_complete_years = sorted(valid_years_for_trend)[-2:]
                    latest_year = recent_complete_years[-1]
                    previous_year = recent_complete_years[0] if len(recent_complete_years) > 1 else None
                    
                    if (previous_year and previous_year in consumption_data and 
                        latest_year in consumption_data):
                        prev_cost = consumption_data[previous_year]['total_cost']
                        latest_cost = consumption_data[latest_year]['total_cost']
                        trend_percent = ((latest_cost - prev_cost) / prev_cost) * 100 if prev_cost != 0 else 0
                        
                        if abs(trend_percent) < 10:
                            trend_icon, trend_color = "➡️", "#3498db"  # Bleu pour stable
                        elif trend_percent >= 10:
                            trend_icon, trend_color = "⬆️", "#e74c3c"  # Rouge pour augmentation
                        else:  # trend_percent <= -10
                            trend_icon, trend_color = "⬇️", "#27ae60"  # Vert pour diminution
                        
                        trend_display = f'''<div style="margin-top: 4px; font-size: 0.75em; color: {trend_color}; line-height: 1.1;">
                            <div style="font-weight: bold;">{trend_icon} {trend_percent:+.0f}%</div>
                            <div style="font-size: 0.7em; opacity: 0.75;">{previous_year}-{latest_year}</div>
                        </div>'''
                    else:
                        trend_display = ""
                else:
                    trend_display = ""
                    
                # Prendre la dernière année pour l'affichage
                latest_year = max(consumption_years)
                display_cost = consumption_data[latest_year]['total_cost']
                display_kwh = consumption_data[latest_year]['total_year']
            else:
                # Une seule année disponible
                display_year = consumption_years[0]
                display_cost = consumption_data[display_year]['total_cost']
                display_kwh = consumption_data[display_year]['total_year']
                trend_display = ""
            
            cost_label = "Coût Annuel"
            cost_unit = f"CHF/an • {format_number_with_apostrophe(display_kwh)} kWh"
        
        with col:
            st.markdown(f'''
            <div onclick="document.getElementById('cout').scrollIntoView({{behavior: 'smooth'}})" style="
                background: linear-gradient(135deg, {color_cost}20, {color_cost}08);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 8px;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style="color: {color_cost}; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">{cost_label}</div>
                <div style="color: {color_cost}; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">CHF {format_number_with_apostrophe(display_cost)}.-</div>
                <div style="color: {color_cost}; font-size: 0.75em; font-weight: 500;">{cost_unit}</div>
                {trend_display}
            </div>
            ''', unsafe_allow_html=True)
            
            # Lien vers la section
            st.markdown(f'''
            <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                <a href="#indicateurs-consommation" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                    → Voir l'analyse des coûts
                </a>
            </div>
            ''', unsafe_allow_html=True)
    else:
        # Pas de données disponibles
        with col:
            st.markdown(f'''
            <div style="
                background: linear-gradient(135deg, #95a5a620, #95a5a608);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 8px;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="color: #95a5a6; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">💰 Coût Annuel</div>
                <div style="color: #95a5a6; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">...</div>
                <div style="color: #95a5a6; font-size: 0.75em; font-weight: 500;">En calcul</div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Lien vers la section
            st.markdown(f'''
            <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                <a href="#indicateurs-consommation" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                    → Voir l'analyse des coûts
                </a>
            </div>
            ''', unsafe_allow_html=True)


def create_cluster_card(col):
    """Crée une carte pour afficher le groupe de consommation (clustering)"""
    user_type = st.session_state.get('user_type', "Particulier")
    
    if user_type == "Particulier":
        cluster_predicted = st.session_state.get('cluster_predicted')
        color_cluster = "#34495e"  # Gris foncé neutre
        
        if cluster_predicted is not None:
            # Descriptions des clusters
            cluster_descriptions = {
                0: "Ménage à consommation élevée",
                1: "Ménage à consommation régulière", 
                2: "Ménage à faible consommation diurne",
                3: "Ménage avec activités professionnelles"
            }
            
            cluster_desc = cluster_descriptions.get(cluster_predicted, f"Groupe {cluster_predicted}")
            
            with col:
                st.markdown(f'''
                <div onclick="document.getElementById('clustering-early').scrollIntoView({{behavior: 'smooth'}})" style="
                    background: linear-gradient(135deg, {color_cluster}20, {color_cluster}08);
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin: 8px;
                    height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                    <div style="color: {color_cluster}; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">Votre Groupe</div>
                    <div style="color: {color_cluster}; font-size: 1.4em; font-weight: bold; line-height: 1.1; margin: 4px 0; text-align: center;">{cluster_desc}</div>
                </div>
                ''', unsafe_allow_html=True)
                
                # Lien vers la section
                st.markdown(f'''
                <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                    <a href="#clustering-early" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                        → Voir votre profil de consommateur
                    </a>
                </div>
                ''', unsafe_allow_html=True)
        else:
            with col:
                st.markdown(f'''
                <div style="
                    background: linear-gradient(135deg, #95a5a620, #95a5a608);
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin: 8px;
                    height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="color: #95a5a6; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">Votre Groupe</div>
                    <div style="color: #95a5a6; font-size: 1.8em; font-weight: bold; line-height: 1; margin: 4px 0;">...</div>
                    <div style="color: #95a5a6; font-size: 0.75em; font-weight: 500;">En calcul</div>
                </div>
                ''', unsafe_allow_html=True)
                
                # Lien vers la section
                st.markdown(f'''
                <div style="text-align: center; margin-top: 5px; padding: 6px; background-color: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                    <a href="#clustering-early" style="color: #dc3545; text-decoration: none; font-size: 0.75em; font-weight: 500;">
                        → Voir votre profil de consommateur
                    </a>
                </div>
                ''', unsafe_allow_html=True)
    else:
        # Pour les professionnels - afficher le type d'utilisateur sans bouton
        with col:
            st.markdown(f'''
            <div style="
                background: linear-gradient(135deg, #34495e20, #34495e08);
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                margin: 8px;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="color: #34495e; font-size: 0.85em; font-weight: bold; margin-bottom: 4px;">🏢 Type</div>
                <div style="color: #34495e; font-size: 1.6em; font-weight: bold; line-height: 1; margin: 4px 0;">Professionnel</div>
                <div style="color: #34495e; font-size: 0.75em; font-weight: 500;">Mode actuel</div>
            </div>
            ''', unsafe_allow_html=True)


# === FONCTION PRINCIPALE DE CRÉATION DU DASHBOARD ===

def create_dashboard():
    """
    Fonction principale de création du dashboard avec disposition optimisée
    
    Cette fonction organise le dashboard en deux sections principales :
    ╔══════════════════╗    ╔═══════════╗
    ║  Graphique       ║    ║ Consom.   ║
    ║  Annuel          ║    ║ Coût      ║
    ║  (Timeline)      ║    ║ (Cartes)  ║
    ╚══════════════════╝    ╚═══════════╝
    
    ╔═══════════════════════╗  ╔══════════╗
    ║ Ratios J/N + S/WE     ║  ║ Graphique║
    ║ Charge + Clustering   ║  ║ Coûts    ║
    ║ (Grille 2x2)          ║  ║ Mensuel  ║
    ╚═══════════════════════╝  ╚══════════╝
    
    Architecture :
    - Section haute : Graphique timeline (large) | Consommation + Coût (étroit)
    - Section basse : 4 cartes indicateurs en grille 2x2 (large) | Graphique coûts mensuels (étroit)
    
    Données récupérées automatiquement depuis st.session_state :
    - ratio_day_night_data, ratio_weekday_weekend_data : Calculés dans main.py
    - base_loads, years : Calculés par calculate_base_load
    - pdf_filtered : DataFrame filtré selon sélection utilisateur
    
    Appelle les fonctions de création des graphiques et cartes :
    - create_annual_view_plot() : Graphique timeline annuel
    - create_monthly_cost_plot() : Graphique coûts mensuels  
    - create_consumption_card(), create_cost_card() : Cartes métriques principales
    - create_ratio_card() : Cartes ratios jour/nuit et semaine/week-end
    - create_base_load_card(), create_cluster_card() : Cartes charge et clustering
    """
    # === RÉCUPÉRATION DES DONNÉES CALCULÉES DEPUIS LA SESSION ===
    # Ces données sont pré-calculées dans main.py pour optimiser les performances
    ratio_day_night_data = st.session_state.get('ratio_day_night_data', {})      # Données ratio jour/nuit
    ratio_weekday_weekend_data = st.session_state.get('ratio_weekday_weekend_data', {})  # Données ratio semaine/week-end
    base_loads = st.session_state.get('base_loads', [])  # Charges de base par année
    years = st.session_state.get('years', [])            # Années correspondantes
    
    # === SECTION HAUTE DU DASHBOARD ===
    # Disposition : Graphique timeline annuel (large) + Cartes consommation/coût (étroit)
    upper_col1, upper_col2 = st.columns([2, 1])  # Ratio 2:1 pour optimiser l'espace
    
    with upper_col1:        
        # === GRAPHIQUE TIMELINE ANNUEL (Colonne gauche large) ===
        # Récupérer les données filtrées selon la sélection utilisateur
        pdf_filtered = st.session_state.get('pdf_filtered')
        
        if pdf_filtered is not None and not pdf_filtered.empty:
            # Créer le graphique de la vue annuelle avec timeline continue
            annual_fig = create_annual_view_plot(pdf_filtered)
            
            if annual_fig is not None:
                # === CONFIGURATION PLOTLY POUR LE DASHBOARD ===
                # Désactiver tous les contrôles pour un affichage épuré
                config = {
                    'displayModeBar': False,    # Pas de barre d'outils
                    'staticPlot': False,        # Garder l'interactivité hover
                    'scrollZoom': False,        # Pas de zoom molette
                    'doubleClick': False,       # Pas de zoom double-clic
                    'showTips': False,          # Pas de tips
                    'displaylogo': False,       # Pas de logo Plotly
                    'modeBarButtonsToRemove': ['zoom', 'pan', 'select', 'lasso', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale']
                }
                
                # Afficher le graphique optimisé pour le dashboard
                st.plotly_chart(annual_fig, use_container_width=True, config=config)
            
            else:
                st.warning("Impossible de générer le graphique avec les données disponibles.")
        else:
            st.info("Aucune donnée disponible pour le graphique. Veuillez charger un fichier de données.")
    
    with upper_col2:
        # === CARTES MÉTRIQUES PRINCIPALES (Colonne droite étroite) ===
        
        # Carte consommation journalière moyenne
        create_consumption_card(st.container())
        
        # Espacement visuel entre les cartes
        st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
        
        # Carte coûts annuels
        create_cost_card(st.container())
    
    # === ESPACEMENT ENTRE LES SECTIONS ===
    st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)
    
    # === SECTION BASSE DU DASHBOARD ===
    # Disposition : Grille 2x2 d'indicateurs (large) + Graphique coûts mensuels (étroit)
    final_col1, final_col2 = st.columns([1.4, 1])  # Ratio 1.4:1 pour équilibrer l'espace
    
    with final_col1:
        # === GRILLE 2x2 DES CARTES INDICATEURS ===
        
        # Première ligne de la grille 2x2
        grid_row1_col1, grid_row1_col2 = st.columns(2)
        
        with grid_row1_col1:
            # Haut gauche : Carte Ratio Jour/Nuit
            create_ratio_card(ratio_day_night_data, "day_night", st.container(), "jour-nuit")
        
        with grid_row1_col2:
            # Haut droite : Carte Ratio Semaine/Week-end
            create_ratio_card(ratio_weekday_weekend_data, "weekday_weekend", st.container(), "ratios")
        
        # Espacement entre les lignes pour aération visuelle
        st.markdown("<div style='margin: 18px 0;'></div>", unsafe_allow_html=True)
        
        # Deuxième ligne de la grille 2x2
        grid_row2_col1, grid_row2_col2 = st.columns(2)
        
        with grid_row2_col1:
            # Bas gauche : Carte Charge de Base
            create_base_load_card(base_loads, years, st.container())
        
        with grid_row2_col2:
            # Bas droite : Carte Groupe de Consommation (Clustering)
            create_cluster_card(st.container())
    
    with final_col2:
        # === GRAPHIQUE COÛTS MENSUELS (Colonne droite) ===
        # Récupérer les mêmes données filtrées que pour le graphique annuel
        pdf_filtered = st.session_state.get('pdf_filtered')
        
        if pdf_filtered is not None and not pdf_filtered.empty:
            # Créer le graphique des coûts mensuels avec tarification
            monthly_cost_fig = create_monthly_cost_plot(pdf_filtered)
            
            if monthly_cost_fig is not None:
                # Afficher sans configuration spéciale (contrôles basiques OK pour ce graphique)
                st.plotly_chart(monthly_cost_fig, use_container_width=True)
            else:
                st.warning("Impossible de générer le graphique des coûts mensuels avec les données actuelles.")
        else:
            st.warning("Aucune donnée disponible pour afficher les coûts mensuels.")


# === FONCTION DE CALCUL DES DONNÉES DE CONSOMMATION POUR LE DASHBOARD ===

def calculate_dashboard_consumption_data(df):
    """
    Calcule les données de consommation et de coût pour l'affichage dans le dashboard
    
    Cette fonction analyse le DataFrame de consommation et calcule :
    - Consommation journalière moyenne par année
    - Consommation totale annuelle par année  
    - Coûts journaliers et annuels selon le tarif sélectionné (Unique ou HP/HC)
    - Totaux consolidés pour toutes les années
    
    Gestion des tarifs :
    - Tarif Unique : Prix constant par kWh (ex: 0.35 CHF/kWh)
    - Tarif HP/HC : Prix différenciés selon heures pleines/creuses et jours
      • HP (Heures Pleines) : 6h-22h, lun-ven (configurable)
      • HC (Heures Creuses) : 22h-6h, week-ends, jours fériés
    
    Args:
        df (DataFrame): DataFrame avec colonnes 'Consumption (kWh)' et index datetime
        
    Returns:
        tuple: (yearly_data, available_years)
            - yearly_data (dict): Données par année + totaux consolidés
                {year: {'daily_avg', 'total_year', 'daily_cost', 'total_cost'}}
                + 'total_all_years': totaux consolidés
            - available_years (list): Liste des années disponibles dans les données
    
    Données utilisées depuis st.session_state :
        - tariff_type : "Tarif Unique" ou "Tarif HP/HC"
        - tariff_unique_price : Prix tarif unique (CHF/kWh)
        - tariff_hp_price, tariff_hc_price : Prix HP et HC (CHF/kWh)  
        - peak_start_hour, peak_end_hour : Heures début/fin HP
    """
    # === DÉTECTION AUTOMATIQUE DE LA COLONNE DE CONSOMMATION ===
    # Rechercher la colonne de consommation dans l'ordre de priorité
    consumption_column = None
    for col in ['Consumption (kWh)', 'Consumption', 'kWh']:
        if col in df.columns:
            consumption_column = col
            break
    
    # Si aucune colonne standard trouvée, prendre la première colonne numérique
    if consumption_column is None:
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            consumption_column = numeric_cols[0]
        else:
            return None, None  # Aucune donnée numérique utilisable
    
    # === RÉCUPÉRATION DES PARAMÈTRES DE TARIFICATION ===
    # Ces paramètres sont configurés par l'utilisateur dans la sidebar
    tariff_type = st.session_state.get('tariff_type', "Tarif Unique")
    
    # Configuration des prix selon le type de tarif
    if tariff_type == "Tarif Unique":
        price = st.session_state.get('tariff_unique_price', 0.35)  # Prix unique par défaut
    else:  # Tarif HP/HC
        hp_price = st.session_state.get('tariff_hp_price', 0.40)   # Prix heures pleines
        hc_price = st.session_state.get('tariff_hc_price', 0.27)   # Prix heures creuses
        peak_start = st.session_state.get('peak_start_hour', 6)    # Début HP : 6h00
        peak_end = st.session_state.get('peak_end_hour', 22)       # Fin HP : 22h00
    
    # === IDENTIFICATION DES ANNÉES DISPONIBLES ===
    available_years = sorted(df['Year'].unique())
    if not available_years:
        return None, None
        
    # === CALCUL DES MÉTRIQUES POUR CHAQUE ANNÉE ===
    yearly_data = {}
    total_consumption_all_years = 0  # Cumul de toutes les années
    total_cost_all_years = 0         # Cumul des coûts de toutes les années
    
    for year in available_years:
        # Filtrer les données pour cette année
        year_data = df[df['Year'] == year]
        
        # === CALCULS DE CONSOMMATION ===
        # Consommation journalière moyenne (resample par jour puis moyenne)
        daily_avg = year_data[consumption_column].resample('D').sum().mean()
        # Consommation totale de l'année (somme de tous les points)
        total_year = year_data[consumption_column].sum()
        
        # === CALCULS DE COÛT SELON LE TYPE DE TARIF ===
        if tariff_type == "Tarif Unique":
            # Tarif unique : multiplication simple
            total_cost = total_year * price
            daily_cost = daily_avg * price
        else:  # Tarif HP/HC
            # === SÉPARATION HEURES PLEINES / HEURES CREUSES ===
            # Filtrer les données selon les plages horaires HP/HC
            year_data_hp = year_data.between_time(f'{peak_start:02d}:00', f'{peak_end-1:02d}:59')
            year_data_hc = year_data[~year_data.index.isin(year_data_hp.index)]
            
            # Calculer les consommations HP et HC
            consumption_hp = year_data_hp[consumption_column].sum()
            consumption_hc = year_data_hc[consumption_column].sum()
            
            # Calculer le coût total avec tarification différenciée
            total_cost = (consumption_hp * hp_price) + (consumption_hc * hc_price)
            
            # Pour le coût journalier, utiliser les proportions moyennes HP/HC
            daily_hp = year_data_hp[consumption_column].resample('D').sum().mean()
            daily_hc = year_data_hc[consumption_column].resample('D').sum().mean()
            daily_cost = (daily_hp * hp_price) + (daily_hc * hc_price)
        
        # === STOCKAGE DES DONNÉES DE L'ANNÉE ===
        yearly_data[year] = {
            'daily_avg': daily_avg,      # kWh/jour moyen
            'total_year': total_year,    # kWh total de l'année
            'daily_cost': daily_cost,    # CHF/jour moyen
            'total_cost': total_cost     # CHF total de l'année
        }
        
        # Cumul pour les totaux consolidés
        total_consumption_all_years += total_year
        total_cost_all_years += total_cost
    
    # === AJOUT DES TOTAUX CONSOLIDÉS ===
    # Ajouter une entrée spéciale avec les totaux de toutes les années
    yearly_data['total_all_years'] = {
        'total_consumption': total_consumption_all_years,
        'total_cost': total_cost_all_years,
        # Moyennes pondérées sur toutes les années
        'avg_daily_consumption': total_consumption_all_years / (len(available_years) * 365.25) if available_years else 0,
        'avg_daily_cost': total_cost_all_years / (len(available_years) * 365.25) if available_years else 0
    }
    
    return yearly_data, available_years
