"""
MODULE D'INDICATEURS DE CLUSTERING ET ANALYSE COMPARATIVE - ANALYSE PERSONNALISÉE

Ce module fournit les outils d'analyse comparative permettant de positionner un utilisateur
par rapport à son groupe de consommateurs similaires dans l'onglet "ANALYSE PERSONNALISÉE" 
de l'application web DataWatt.

FONCTIONNALITÉS PRINCIPALES:

1. POSITIONNEMENT DANS LE GROUPE:
   - Calcul de la position de l'utilisateur dans les déciles de son cluster
   - Comparaison avec 5 caractéristiques clés : charge nocturne, consommations saisonnières (hivernales et estivales), ratio jour/nuit et ratio semaine/weekend
   - Visualisation interactive sous forme de graphique en barres colorées avec échelle centrée sur la médiane
   - Sauvegarde locale des positions calculées pour réutilisation

2. RÉSUMÉ RAPIDE DES INDICATEURS:
   - Interface utilisateur simplifiée avec codes couleurs
   - Logique différenciée pour consommations vs ratios comportementaux
   - Affichage en colonnes avec pourcentages d'écart à la médiane

3. SYSTÈME DE RECOMMANDATIONS:
   - Génération automatique de conseils personnalisés basés sur la position dans les déciles
   - Recommandations d'amélioration pour les caractéristiques > 70ème percentile
   - Félicitations pour les performances < 30ème percentile
   - Focus sur les actions concrètes : isolation, veille, optimisation saisonnière

ARCHITECTURE TECHNIQUE:
- Utilisation des données de clustering pré-calculées (feature_deciles_by_cluster_8features.csv)
- Intégration avec les 8 features définies dans methods_weight_features_explicative.py
- Graphiques Plotly avec échelle centrée (-50% à +50%) pour visualisation intuitive
- Persistance des données utilisateur via CSV local pour continuité d'analyse
- Interface Streamlit avec expanders pour explications détaillées

INTÉGRATION CLUSTERING:
Ce module s'appuie sur le système de clustering DataWatt qui segmente les utilisateurs en groupes
homogènes selon leurs profils de consommation. Il utilise les déciles pré-calculés pour chaque
cluster et permet une analyse comparative précise et personnalisée.

UTILISATION: Intégré dans l'onglet "ANALYSE PERSONNALISÉE" pour fournir une analyse comparative
contextuelle et des recommandations d'optimisation énergétique personnalisées.
"""

import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import os

def save_user_cluster_positions(user_features, cluster_id, positions_dict):
    """
    Sauvegarde les positions de l'utilisateur dans les déciles de son cluster dans un CSV local
    
    Args:
        user_features: Series pandas avec les caractéristiques de l'utilisateur
        cluster_id: ID du cluster auquel l'utilisateur appartient
        positions_dict: Dictionnaire contenant les positions calculées pour chaque feature
    """
    try:
        # Créer le répertoire de sauvegarde s'il n'existe pas (dossier indicators)
        save_dir = os.path.dirname(os.path.realpath(__file__))
        
        # Créer le DataFrame avec les données de position
        data = {
            'feature': [],
            'feature_name_fr': [],
            'user_value': [],
            'position_percentile': [],
            'cluster_id': []
        }
        
        feature_names_fr = {
            'base_load': 'Charge nocturne (01h00-05h00)',
            'mean_consumption_winter': 'Consommation moyenne hivernale (Déc-Fév)',
            'mean_consumption_summer': 'Consommation moyenne estivale (Jun-Aoû)',
            'ratio_weekday_weekend': 'Ratio semaine/weekend',
            'ratio_day_night': 'Ratio jour/nuit'
        }
        
        for feature, position in positions_dict.items():
            data['feature'].append(feature)
            data['feature_name_fr'].append(feature_names_fr.get(feature, feature))
            data['user_value'].append(user_features[feature] if feature in user_features else None)
            # Convertir la position en échelle centrée sur 0% (-50% à +50%)
            # position va de 0 à 10, on veut -50 à +50
            centered_position = (position - 5) * 10  # Centrer sur 0 et étendre à -50/+50
            data['position_percentile'].append(centered_position)
            data['cluster_id'].append(cluster_id)
        
        df = pd.DataFrame(data)
        
        # Sauvegarder dans un CSV
        csv_path = os.path.join(save_dir, 'user_cluster_positions.csv')
        df.to_csv(csv_path, index=False)
        
        return csv_path
        
    except Exception as e:
        st.warning(f"Erreur lors de la sauvegarde des positions: {e}")
        return None

def load_user_cluster_positions():
    """
    Charge les positions de l'utilisateur depuis le CSV local
    
    Returns:
        DataFrame avec les positions ou None si erreur
    """
    try:
        csv_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                               'user_cluster_positions.csv')
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
        else:
            return None
    except Exception as e:
        st.warning(f"Erreur lors du chargement des positions: {e}")
        return None

def get_user_feature_position(feature_name):
    """
    Récupère la position d'une caractéristique spécifique de l'utilisateur
    
    Args:
        feature_name: Nom de la caractéristique ('base_load', 'mean_consumption_winter', etc.)
        
    Returns:
        Tuple (position_percentile, user_value, cluster_id) ou None si non trouvé
    """
    df = load_user_cluster_positions()
    if df is not None and not df.empty:
        feature_row = df[df['feature'] == feature_name]
        if not feature_row.empty:
            return (
                feature_row['position_percentile'].iloc[0],
                feature_row['user_value'].iloc[0],
                feature_row['cluster_id'].iloc[0]
            )
    return None

def get_all_user_positions():
    """
    Récupère toutes les positions de l'utilisateur sous forme de dictionnaire
    
    Returns:
        Dictionnaire {feature_name: position_percentile} ou None si erreur
    """
    df = load_user_cluster_positions()
    if df is not None and not df.empty:
        return dict(zip(df['feature'], df['position_percentile']))
    return None

def display_user_positions_summary():
    """
    Affiche un résumé des positions de l'utilisateur (utile pour debug ou information)
    """
    df = load_user_cluster_positions()
    if df is not None and not df.empty:
        
        # Créer les colonnes pour l'affichage
        cols = st.columns(2)
        
        for i, (_, row) in enumerate(df.iterrows()):
            position = row['position_percentile']
            if position < -20:
                emoji = "🟢"
                status = "Consommation plus faible que la médiane (très bon)"
                border_color = "#27ae60"
                text_color = "#27ae60"
            elif position < 20:
                emoji = "🟡"
                status = "Consommation proche de la médiane du groupe"
                border_color = "#f39c12"
                text_color = "#f39c12"
            else:
                emoji = "🔴"
                status = "Consommation plus élevée que la médiane (à optimiser)"
                border_color = "#e74c3c"
                text_color = "#e74c3c"
            
            # Afficher dans les colonnes avec le même design que display_quick_indicators_summary
            col_index = i % 2
            with cols[col_index]:
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 3px solid {border_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <span style="font-weight: bold; font-size: 0.9em;">{emoji} {row['feature_name_fr']}</span>
                        <span style="font-weight: bold; color: {text_color};">{position:+.0f}%</span>
                    </div>
                    <div style="font-size: 0.8em; color: #666; font-style: italic;">
                        {status}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with st.expander("Données détaillées"):
            st.dataframe(df)
    else:
        st.info("Aucune donnée de positionnement trouvée. Veuillez d'abord générer l'analyse de cluster.")

def get_decile_position(value, deciles):
    """Détermine entre quels déciles se trouve la valeur"""
    if value <= deciles[0]:
        return 0
    for i in range(len(deciles)-1):
        if deciles[i] <= value <= deciles[i+1]:

            return i + (value - deciles[i]) / (deciles[i+1] - deciles[i])
    return len(deciles) - 1

def create_cluster_decile_comparison(user_features, cluster_id):
    """
    Crée une visualisation comparative des features de l'utilisateur par rapport aux déciles de son cluster
    
    Args:
        user_features: Series pandas avec les caractéristiques de l'utilisateur
        cluster_id: ID du cluster auquel l'utilisateur appartient
    """
    # Charger le fichier de déciles
    try:
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                '../../Clustering_enhanced/feature_deciles_by_cluster_8features.csv')
        deciles_df = pd.read_csv(file_path)
    except Exception as e:
        st.error(f"Erreur lors du chargement des déciles: {e}")
        return None
    
    # Filtrer les déciles pour le cluster spécifique
    cluster_deciles = deciles_df[deciles_df['Cluster'] == f'Cluster_{cluster_id}']
    
    # Caractéristiques à visualiser
    consumption_features = ['base_load', 'mean_consumption_winter', 'mean_consumption_summer']
    ratio_features = ['ratio_weekday_weekend', 'ratio_day_night']
    
    # Préparer les données pour le graphique
    features_to_plot = consumption_features + ratio_features
    
    # Fonction pour obtenir la position y avec un espace entre les groupes
    def get_y_position(feature_index):
        # Ajouter un espace supplémentaire après les caractéristiques de consommation
        if feature_index >= len(consumption_features):
            return feature_index + 1  # Ajouter un espace de séparation
        return feature_index
    
    feature_names_fr = {
        'base_load': 'Charge nocturne (01h00-05h00)',
        'mean_consumption_winter': 'Consommation moyenne hivernale (Déc-Fév)',
        'mean_consumption_summer': 'Consommation moyenne estivale (Jun-Aoû)',
        'ratio_weekday_weekend': 'Ratio semaine/weekend',
        'ratio_day_night': 'Ratio jour/nuit'
    }
    
    # Créer la figure
    fig = go.Figure()
    
    # Dictionnaire pour stocker les positions calculées
    positions_dict = {}
    
    # Pour chaque caractéristique
    for feature in features_to_plot:
        if feature in user_features:
            feature_data = cluster_deciles[cluster_deciles['Feature'] == feature]
            if not feature_data.empty:
                # Extraire les déciles pour cette caractéristique (p0 à p100)
                decile_values = [feature_data[f'p{i*10}'].values[0] for i in range(0, 11)]
                
                # Déterminer la position de la valeur de l'utilisateur
                user_value = user_features[feature]
                # Position relative entre 0 et 10 (pour 11 points de décile)
                position = get_decile_position(user_value, decile_values)
                
                # Convertir en échelle centrée sur 0% (-50% à +50%)
                centered_position = (position - 5) * 10
                
                # Sauvegarder la position dans le dictionnaire (position originale pour le calcul du graphique)
                positions_dict[feature] = position
                
                # Créer une échelle de couleurs pour les barres (10 segments pour 11 points de décile)
                if feature in consumption_features:
                    # Vert à rouge pour les caractéristiques de consommation
                    colors = ['#1a9850', '#66bd63', '#a6d96a', '#d9ef8b', '#ffffbf', 
                              '#fee08b', '#fdae61', '#f46d43', '#d73027', '#bd0026']
                elif feature in ['ratio_day_night', 'ratio_weekday_weekend']:
                    # Pour les ratios : rouge aux extrêmes (-50% et +50%), vert au centre (médiane 0%)
                    # Rouge (-50%) → Orange → Vert (centre 0%) → Orange → Rouge (+50%)
                    colors = ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b',
                              '#d9ef8b', '#fee08b', '#fdae61', '#f46d43', '#d73027']
                else:
                    # Couleurs par défaut pour d'autres ratios
                    colors = ['#ffffe5', '#ffffd9', '#edf8b1', '#c7e9b4', '#7fcdbb', 
                            '#41b6c4', '#1d91c0', '#225ea8', '#253494', '#081d58']
                
                # Position y avec espace entre les groupes
                y_position = get_y_position(features_to_plot.index(feature))
                
                # Ajouter les segments de décile comme barres colorées
                for i in range(10):  # 10 segments pour p0-p10, p10-p20, ..., p90-p100
                    # Convertir les positions en échelle centrée (-5 à +5)
                    x0 = (i - 5)
                    x1 = (i + 1 - 5)
                    fig.add_shape(
                        type="rect",
                        x0=x0,
                        x1=x1,
                        y0=y_position - 0.4,
                        y1=y_position + 0.4,
                        fillcolor=colors[i],
                        line=dict(width=0),
                        layer="below"
                    )
                
                # Ajouter un marqueur indiquant la position de l'utilisateur
                # Convertir la position en échelle centrée
                marker_position = position - 5
                
                # Créer un texte de tooltip personnalisé avec le pourcentage de l'axe X
                tooltip_text = f"{feature_names_fr.get(feature, feature)}<br>Position par rapport à la médiane: {centered_position:+.0f}%"

                fig.add_trace(go.Scatter(
                    x=[marker_position],
                    y=[y_position],
                    mode='markers',
                    marker=dict(symbol='diamond', size=12, color='black'),
                    name=feature_names_fr.get(feature, feature),
                    text=[tooltip_text],
                    hovertemplate='%{text}<extra></extra>',
                    showlegend=False
                ))

            
    # Ajouter une ligne verticale à 0% pour indiquer la médiane du groupe
    fig.add_shape(
        type="line",
        x0=0, x1=0,  # Position à 0% (médiane)
        y0=-0.5, y1=len(features_to_plot) + 0.5,  # Couvre toute la hauteur du graphique
        line=dict(color="red", width=2, dash="dash"),
        layer="above"
    )
    
    # Ajouter une annotation pour expliquer la ligne de médiane
    fig.add_annotation(
        x=0, y=len(features_to_plot) + 0.2,
        text="Médiane du groupe (0%)",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor="red",
        font=dict(color="red", size=10),
        xanchor="center"
    )
    
    # Créer des étiquettes d'axe y avec l'espace
    y_tickvals = [get_y_position(i) for i in range(len(features_to_plot))]
    y_ticktext = [feature_names_fr.get(f, f) for f in features_to_plot]
    
    # Configurer la mise en page
    fig.update_layout(
        title="Positionnement par rapport à votre groupe",
        xaxis=dict(
            title="Écart par rapport à la médiane (%)",
            tickmode='array',
            tickvals=list(range(-5, 6)),
            ticktext=['-50%', '-40%', '-30%', '-20%', '-10%', '0%', '+10%', '+20%', '+30%', '+40%', '+50%']
        ),
        yaxis=dict(
            title="Caractéristiques",
            tickmode='array',
            tickvals=y_tickvals,
            ticktext=y_ticktext
        ),
        showlegend=False,
        height=450,
        margin=dict(l=150, r=20, t=50, b=80)
    )
    

    # Sauvegarder les positions dans un CSV local pour utilisation ultérieure
    if positions_dict:  # S'assurer qu'il y a des positions à sauvegarder
        save_user_cluster_positions(user_features, cluster_id, positions_dict)
    
    return fig

def display_quick_indicators_summary(user_features, cluster_id):
    """
    Affiche un résumé rapide des 5 indicateurs avec couleurs et explications courtes
    
    Args:
        user_features: Series pandas avec les caractéristiques de l'utilisateur
        cluster_id: ID du cluster auquel l'utilisateur appartient
    """
    try:
        # Charger le fichier de déciles
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                '../../Clustering_enhanced/feature_deciles_by_cluster_8features.csv')
        deciles_df = pd.read_csv(file_path)
        cluster_deciles = deciles_df[deciles_df['Cluster'] == f'Cluster_{cluster_id}']
    except Exception as e:
        st.warning(f"Impossible de charger les données de déciles: {e}")
        return

    # Caractéristiques à afficher
    features_to_display = ['base_load', 'mean_consumption_winter', 'mean_consumption_summer', 
                          'ratio_weekday_weekend', 'ratio_day_night']
    
    feature_names_fr = {
        'base_load': 'Charge nocturne (01h00-05h00)',
        'mean_consumption_winter': 'Consommation hivernale (Déc-Fév)',
        'mean_consumption_summer': 'Consommation estivale (Jun-Aoû)',
        'ratio_weekday_weekend': 'Ratio semaine/week-end',
        'ratio_day_night': 'Ratio jour/nuit'
    }
    
    # Fonction pour déterminer l'emoji, statut et explication
    def get_quick_status_info(percentile, feature_type):
        if feature_type == "consumption":
            # Pour les caractéristiques de consommation (logique inchangée)
            if percentile < -20:
                emoji = "🟢"
                explanation = "Consommation plus faible que la médiane (très bon)"
            elif percentile < 20:
                emoji = "🟡"
                explanation = "Consommation proche de la médiane du groupe"
            else:
                emoji = "🔴"
                explanation = "Consommation plus élevée que la médiane (à optimiser)"
        else:
            # Pour les ratios : nouvelle logique basée sur la distance absolue à la médiane
            abs_percentile = abs(percentile)  # Valeur absolue par rapport à la médiane
            if abs_percentile <= 10:
                emoji = "🟢"
                explanation = "Ratio proche de la médiane du groupe (similaire)"
            elif abs_percentile <= 30:
                emoji = "🟡"
                explanation = "Ratio légèrement différent de la médiane du groupe"
            else:  # > 30%
                emoji = "🔴"
                explanation = "Ratio très différent de la médiane du groupe"
        return emoji, explanation

    # Créer les colonnes pour l'affichage
    cols = st.columns(2)
    
    indicators_data = []
    
    for feature in features_to_display:
        if feature in user_features:
            feature_data = cluster_deciles[cluster_deciles['Feature'] == feature]
            if not feature_data.empty:
                # Extraire les déciles
                decile_values = [feature_data[f'p{i*10}'].values[0] for i in range(0, 11)]
                user_value = user_features[feature]
                
                # Calculer la position
                position = get_decile_position(user_value, decile_values)
                centered_position = (position - 5) * 10  # Convertir en échelle centrée
                
                # Déterminer le type de caractéristique
                feature_type = "consumption" if feature in ['base_load', 'mean_consumption_winter', 'mean_consumption_summer'] else "ratio"
                
                emoji, explanation = get_quick_status_info(centered_position, feature_type)
                
                indicators_data.append({
                    'feature': feature,
                    'name': feature_names_fr[feature],
                    'position': centered_position,
                    'emoji': emoji,
                    'explanation': explanation
                })

    # Afficher les indicateurs dans les colonnes
    for i, indicator in enumerate(indicators_data):
        col_index = i % 2
        with cols[col_index]:
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 3px solid {'#27ae60' if indicator['emoji'] == '🟢' else '#f39c12' if indicator['emoji'] == '🟡' else '#e74c3c'};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 0.9em;">{indicator['emoji']} {indicator['name']}</span>
                    <span style="font-weight: bold; color: {'#27ae60' if indicator['emoji'] == '🟢' else '#f39c12' if indicator['emoji'] == '🟡' else '#e74c3c'};">{indicator['position']:+.0f}%</span>
                </div>
                <div style="font-size: 0.8em; color: #666; font-style: italic;">
                    {indicator['explanation']}
                </div>
            </div>
            """, unsafe_allow_html=True)

def display_cluster_positioning_explanation():
    """
    Affiche l'explication sur l'interprétation du positionnement dans le groupe
    """
    # Explication sur l'interprétation du positionnement
    st.info("Ce graphique montre où vous vous situez par rapport aux autres utilisateurs de votre groupe pour diﬀérentes caractéristiques. Les marqueurs en forme de losange noir indiquent votre position.")

    with st.expander("Comment interpréter ces pourcentages ?", expanded=False):
        st.markdown("""
        **Échelle centrée sur la médiane :**
        
        **Pour les caractéristiques de consommation :**
        - **-50% à -20% 🟢** : Votre consommation est nettement inférieure à la médiane (très bon)  
        - **-20% à +20% 🟡** : Votre consommation est proche de la médiane du groupe  
        - **+20% à +50% 🔴** : Votre consommation est nettement supérieure à la médiane (à optimiser)  
        
        **Pour les ratios (jour/nuit et semaine/week-end) :**
        - **-10% à +10% 🟢** : Votre ratio est similaire à la médiane du groupe  
        - **-30% à -10% ou +10% à +30% 🟡** : Votre ratio est légèrement différent de la médiane  
        - **-50% à -30% ou +30% à +50% 🔴** : Votre ratio est très différent de la médiane (en valeur absolue)  
        """)

def generate_cluster_decile_recommendations(user_features, cluster_id):
    """
    Génère des recommandations personnalisées basées sur la position des caractéristiques 
    de l'utilisateur dans les déciles de son cluster.
    
    Args:
        user_features: Series pandas avec les caractéristiques de l'utilisateur
        cluster_id: ID du cluster auquel l'utilisateur appartient
        
    Returns:
        high_decile_recommendations: Liste de recommandations pour les caractéristiques > 70e percentile
        low_decile_remarks: Liste de remarques positives pour les caractéristiques < 30e percentile
    """
    # Charger le fichier de déciles
    try:
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 
                                '../../Clustering_enhanced/feature_deciles_by_cluster_8features.csv')
        deciles_df = pd.read_csv(file_path)
        cluster_deciles = deciles_df[deciles_df['Cluster'] == f'Cluster_{cluster_id}']
    except Exception as e:
        st.warning(f"Impossible de charger les données de déciles pour les recommandations: {e}")
        return [], []

    # Variables pour stocker les recommandations et remarques
    high_decile_recommendations = []
    low_decile_remarks = []
    
    # Caractéristiques de consommation à vérifier
    consumption_features = ['base_load', 'mean_consumption_winter', 'mean_consumption_summer']
    feature_names_fr = {
        'base_load': 'Charge nocturne (01h00-05h00)',
        'mean_consumption_winter': 'Consommation moyenne (hiver Déc-Fév)',
        'mean_consumption_summer': 'Consommation moyenne (été Jun-Aoû)'
    }
    
    # Vérifier la position de chaque caractéristique dans les déciles
    for feature in consumption_features:
        if feature in user_features:
            feature_data = cluster_deciles[cluster_deciles['Feature'] == feature]
            if not feature_data.empty:
                # Extraire les déciles
                p30 = feature_data['p30'].values[0]
                p70 = feature_data['p70'].values[0]
                user_value = user_features[feature]
                
                # Si > 70ème percentile - recommandation d'amélioration (correspond à +20% dans la nouvelle échelle)
                if user_value > p70:
                    if feature == 'base_load':
                        high_decile_recommendations.append(f"Votre **{feature_names_fr[feature]}** est particulièrement élevée par rapport aux autres utilisateurs de votre groupe. Identifiez les appareils en veille ou fonctionnant en continu et envisagez leur remplacement ou leur optimisation.")
                    elif feature == 'mean_consumption_winter':
                        high_decile_recommendations.append(f"Votre **{feature_names_fr[feature]}** est élevée. Pensez à améliorer l'isolation thermique et optimiser votre chauffage pour réduire cette consommation hivernale.")
                    elif feature == 'mean_consumption_summer':
                        high_decile_recommendations.append(f"Votre **{feature_names_fr[feature]}** est plus haute que la majorité des utilisateurs similaires. Vérifiez l'efficacité de votre système de climatisation si vous en utilisez un, ou identifiez d'autres sources de consommation estivale.")
                
                # Si < 30ème percentile - remarque positive (correspond à -20% dans la nouvelle échelle)
                elif user_value < p30:
                    if feature == 'base_load':
                        low_decile_remarks.append(f"Félicitations ! Votre **{feature_names_fr[feature]}** est particulièrement basse, ce qui indique une bonne gestion des appareils en veille.")
                    elif feature == 'mean_consumption_winter':
                        low_decile_remarks.append(f"Bravo ! Votre **{feature_names_fr[feature]}** est inférieure à la majorité des utilisateurs de votre groupe, ce qui suggère une bonne efficacité thermique en hiver.")
                    elif feature == 'mean_consumption_summer':
                        low_decile_remarks.append(f"Excellent ! Votre **{feature_names_fr[feature]}** est basse comparée aux autres utilisateurs similaires, indiquant une utilisation efficace de l'énergie en été.")
    
    return high_decile_recommendations, low_decile_remarks