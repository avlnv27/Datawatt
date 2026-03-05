"""
ÉTAPE 3 : PHASE DE PRÉDICTION ET INTÉGRATION AVEC L'APPLICATION PRINCIPALE

Ce module constitue le pont entre le système de clustering entraîné et l'application web DataWatt.
Il permet de classifier de nouveaux utilisateurs et de générer des analyses comparatives en temps réel
à partir des données de consommation uploadées via l'interface utilisateur.

FONCTIONNALITÉS PRINCIPALES:

1. PRÉDICTION DE CLUSTER EN TEMPS RÉEL:
   - Chargement des modèles pré-entraînés (KMeans, scaler, weights)
   - Calcul des 8 features comportementales à partir des données utilisateur
   - Application du même pipeline de normalisation et pondération que l'entraînement
   - Prédiction du groupe d'appartenance avec gestion robuste des outliers (clipping)

2. GÉNÉRATION DE VISUALISATIONS COMPARATIVES:
   - Graphique de distribution des groupes (pie chart interactif)
   - Profils de consommation journaliers comparés aux moyennes des clusters
   - Profils hebdomadaires avec mise en évidence des différences
   - Calcul automatique des ratios de consommation vs groupe prédit

3. INTÉGRATION AVEC L'APPLICATION PRINCIPALE (main.py):
   - Fonction `predict_cluster_from_clean_dataset()` appelée depuis l'onglet clustering
   - Traitement automatique du fichier clean_dataset.csv généré par dataframe_gen.py
   - Stockage des features utilisateur dans st.session_state pour réutilisation
   - Génération des graphiques Plotly intégrés dans l'interface Streamlit

PIPELINE DE TRAITEMENT:

1. Chargement automatique de clean_dataset.csv (données utilisateur nettoyées)
2. Extraction des features temporelles avec gestion des timestamps
3. Application de la même normalisation que lors de l'entraînement (RobustScaler)
4. Pondération selon le système de poids optimisé (8 features principales)
5. Clipping des valeurs extrêmes pour cohérence avec les données d'entraînement
6. Prédiction du cluster et calcul des distances aux centroïdes
7. Génération des visualisations comparatives interactives

UTILISATION DANS MAIN.PY:
```python
from Clustering_enhanced.predict_phase import predict_cluster_from_clean_dataset

# Dans l'onglet clustering
predicted_cluster, dist_fig, daily_fig, weekly_fig = predict_cluster_from_clean_dataset()

# Affichage des résultats
st.plotly_chart(daily_fig)
st.plotly_chart(weekly_fig)
```

ROBUSTESSE ET GESTION D'ERREURS:
- Validation automatique des fichiers modèles requis
- Gestion des valeurs manquantes et outliers
- Fallback sur des valeurs par défaut en cas d'échec de calcul de features
- Messages d'erreur informatifs pour diagnostic

VERSION ET SUPPORT:
Module optimisé pour l'intégration production avec l'application DataWatt. En cas d'erreur
ou de problème de prédiction, veuillez contacter sven.hominal@epfl.ch.  

DÉPENDANCES:
- Modèles pré-entraînés (feature_kmeans_model_weight_8features.joblib, etc.)
- Profils de clusters (daily/weekly_profiles_by_cluster_8features.csv)
- methods_weight_features_explicative.py pour calcul des features
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import joblib
import traceback
from datetime import datetime
import streamlit as st

current_dir = os.path.dirname(os.path.realpath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)  

from methods_weight_features_explicative import get_feature_weights, calculate_base_load, calculate_seasonal_means, calculate_weekday_weekend_ratio, calculate_day_night_ratio, calculate_consumption_slope

# --- Fonction simplifiée pour charger le dataset ---

def load_clean_dataset(file_path='clean_dataset.csv'):
    """
    Charge directement le fichier clean_dataset.csv généré par dataframe_gen.py
    """
    print(f"🔄 Chargement du fichier: {file_path}")
    
    try:
        # Charger le CSV avec l'index comme datetime
        df = pd.read_csv(file_path, index_col=0)
        
        # Convertir l'index en datetime
        df.index = pd.to_datetime(df.index)
        
        print(f"   - Dimensions du dataset: {df.shape}")
        print(f"   - Colonnes: {df.columns.tolist()}")
        
        # Vérifier que la colonne de consommation existe
        if 'Consumption (kWh)' not in df.columns:
            print("❌ Colonne 'Consumption (kWh)' non trouvée dans le fichier")
            return None, None
        
        # Extraire la série temporelle et les timestamps
        timeseries = df['Consumption (kWh)']
        timestamps = df.index
        
        return timeseries, timestamps
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement du fichier: {e}")
        traceback.print_exc()
        return None, None


# --- Conservation des fonctions originales ---

def calculate_timeseries_features_8(series: pd.Series, timestamps=None) -> pd.Series:
    """
    Calcule uniquement les 8 features statistiques importantes pour une série temporelle.
    """
    if series.empty or series.isnull().all():
        print("⚠️ Avertissement: La série temporelle est vide ou ne contient que des NaN.")
        return pd.Series(np.nan, index=list(get_feature_weights().keys()))

    # Extraire les informations temporelles si disponibles
    has_time_data = False
    if timestamps is not None and len(timestamps) == len(series):
        try:
            # Créer le DataFrame avec les valeurs
            df = pd.DataFrame({'value': series.values})
            
            # Gérer différemment selon le type de timestamps
            if isinstance(timestamps, pd.DatetimeIndex):
                # DatetimeIndex a des attributs directs sans .dt
                df['Datetime'] = timestamps
                df['Year'] = timestamps.year
                df['Month'] = timestamps.month
                df['Day'] = timestamps.day
                df['Hour'] = timestamps.hour
                has_time_data = True
            else:
                # Pour les Series ou listes, on utilise pd.to_datetime
                timestamps_series = pd.to_datetime(timestamps)
                df['Datetime'] = timestamps_series
                df['Year'] = timestamps_series.dt.year
                df['Month'] = timestamps_series.dt.month
                df['Day'] = timestamps_series.dt.day
                df['Hour'] = timestamps_series.dt.hour
                has_time_data = True
        except Exception as e:
            print(f"⚠️ Erreur extraction infos temporelles: {e}")
            has_time_data = False

    # Création d'un dict pour stocker les 8 features importantes
    features_dict = {}
    
    # Statistiques de base - std
    desc = series.describe()
    features_dict['std'] = desc['std']
    
    # Features temporelles - seulement les 7 autres features importantes
    if has_time_data:
        try:
            # Base load
            base_load_result = calculate_base_load(df)
            features_dict['base_load'] = base_load_result['value'] if isinstance(base_load_result, pd.Series) and 'value' in base_load_result else np.nan
            
            # Seasonal means - seulement summer et winter
            summer_mean, winter_mean = calculate_seasonal_means(df)
            features_dict['mean_consumption_summer'] = summer_mean['value'] if isinstance(summer_mean, pd.Series) and 'value' in summer_mean else np.nan
            features_dict['mean_consumption_winter'] = winter_mean['value'] if isinstance(winter_mean, pd.Series) and 'value' in winter_mean else np.nan
            
            # Ratio weekday/weekend
            weekday_weekend_ratio = calculate_weekday_weekend_ratio(df)
            features_dict['ratio_weekday_weekend'] = weekday_weekend_ratio['value'] if isinstance(weekday_weekend_ratio, pd.Series) and 'value' in weekday_weekend_ratio else np.nan
            
            # Ratio day/night global
            day_night_ratio = calculate_day_night_ratio(df)
            features_dict['ratio_day_night'] = day_night_ratio['value'] if isinstance(day_night_ratio, pd.Series) and 'value' in day_night_ratio else np.nan
            
            # Slope morning et evening
            morning_slope = calculate_consumption_slope(df, 6, 10)
            features_dict['slope_morning_6_9'] = morning_slope['value'] if isinstance(morning_slope, pd.Series) and 'value' in morning_slope else np.nan
            
            evening_slope = calculate_consumption_slope(df, 18, 23)
            features_dict['slope_evening_18_22'] = evening_slope['value'] if isinstance(evening_slope, pd.Series) and 'value' in evening_slope else np.nan
            
        except Exception as e:
            print(f"⚠️ Erreur calcul features temporelles: {e}")
            # S'assurer que toutes les 8 features sont présentes
            for feature in get_feature_weights().keys():
                if feature not in features_dict:
                    features_dict[feature] = np.nan
    else:
        # Si pas de données temporelles, définir toutes les features temporelles à NaN
        features_dict['base_load'] = np.nan
        features_dict['mean_consumption_summer'] = np.nan
        features_dict['mean_consumption_winter'] = np.nan
        features_dict['ratio_weekday_weekend'] = np.nan
        features_dict['ratio_day_night'] = np.nan
        features_dict['slope_morning_6_9'] = np.nan
        features_dict['slope_evening_18_22'] = np.nan

    # Créer Series à partir du dictionnaire
    features = pd.Series(features_dict)
    
    # Vérifier les valeurs NaN et les remplacer par 0
    if features.isnull().any():
        print(f"⚠️ NaN détecté dans les features, remplacement par 0")
        features = features.fillna(0)
    
    return features


# --- Fonctions de visualisation inchangées ---
def format_features_for_legend(features: pd.Series, precision=3) -> str:
    """Formate un pd.Series de features pour la légende Plotly."""
    important_features = list(get_feature_weights().keys())
    available_keys = [f for f in important_features if f in features.index]

    legend_str = ""
    for key in available_keys:
        value = features[key]
        if pd.isna(value):
            value_str = "N/A"
        else:
            value_str = f"{value:.{precision}g}"
        legend_str += f"<br>  {key}: {value_str}"
    return legend_str


def create_feature_cluster_distribution_chart(user_cluster, sample_features=None, 
                                             clusters_path='pod_feature_clusters_weight_8features.csv', 
                                             output_filename=None):
    """Crée un graphique circulaire montrant la distribution des clusters avec les features clés."""
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        full_clusters_path = os.path.join(dir_path, clusters_path)
        if not os.path.exists(full_clusters_path):
            print(f"⚠️ Fichier de clusters introuvable: {full_clusters_path}")
            return None
        clusters_df = pd.read_csv(full_clusters_path)
    except Exception as e:
        print(f"❌ Erreur chargement {clusters_path}: {e}")
        return None

    if 'Feature_Cluster' not in clusters_df.columns:
        print(f"❌ Erreur: Colonne 'Feature_Cluster' manquante dans {clusters_path}.")
        return None

    feature_similarities = {}
    
    cluster_avg_features = pd.Series({f: 0 for f in get_feature_weights().keys()})
    if sample_features is not None:
        try:
            for feature in sample_features.index:
                if feature in cluster_avg_features.index:
                    feature_similarities[feature] = {
                        'sample_val': sample_features[feature],
                        'feature_weight': get_feature_weights().get(feature, 1.0)
                    }
        except Exception as e:
            print(f"⚠️ Erreur de calcul des similarités: {e}")
    
    # Distribution des clusters
    cluster_counts = clusters_df['Feature_Cluster'].value_counts().sort_index()
    labels = [f"Groupe {i}" for i in cluster_counts.index]

    # Couleurs et création du graphique
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    highlight_colors = []
    for i in cluster_counts.index:
        if int(i) == user_cluster:
            highlight_colors.append(colors[int(i) % len(colors)])
        else:
            base_color = colors[int(i) % len(colors)]
            rgb = tuple(int(base_color.lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
            highlight_colors.append(f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.6)')

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=labels,
        values=cluster_counts.values,
        hole=0.5,
        textinfo='label+percent',
        textposition='outside',
        marker=dict(colors=highlight_colors, line=dict(color='#ffffff', width=2)),
        pull=[0.1 if int(i) == user_cluster else 0 for i in cluster_counts.index],
        hovertemplate='%{label}<br>%{value} utilisateurs (%{percent})<extra></extra>',
        sort=False
    ))

    central_text = f"Données utilisateur<br>dans le<br><b>Groupe {user_cluster}</b>"

    fig.update_layout(
        title={
            'text': "Distribution des Groupes",
            'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top',
            'font': {'size': 20, 'color': 'black', 'family': 'Arial, sans-serif'}
        },
        annotations=[{
            'text': central_text,
            'x': 0.5, 'y': 0.5, 'font': {'size': 13, 'color': 'black'}, 'showarrow': False
        }],
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.2, 'xanchor': 'center', 'x': 0.5},
        height=650, width=650
    )

    # Sauvegarde du graphique si nécessaire
    if output_filename:
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            full_output_path = os.path.join(dir_path, output_filename)
            fig.write_image(full_output_path, scale=2)
            print(f"   ✅ Graphique de distribution sauvegardé: {output_filename}")
        except Exception as e:
            print(f"   ⚠️ Erreur sauvegarde PNG: {e}")
    
    return fig


def create_daily_profile_comparison(user_name, user_timeseries, timestamps, 
                                  predicted_cluster,
                                  daily_profiles_path='daily_profiles_by_cluster_8features.csv',
                                  output_filename=None):
    """
    Crée un graphique comparant le profil journalier de l'utilisateur avec les profils moyens des clusters.
    """
    try:
        # Vérifier si les timestamps sont valides
        if timestamps is None or len(timestamps) != len(user_timeseries):
            print("⚠️ Impossible de créer le profil journalier sans timestamps valides")
            return None
            
        # Préparation des données utilisateur
        user_df = pd.DataFrame({
            'value': user_timeseries.values,
            'Datetime': timestamps
        })
        user_df['Hour'] = user_df['Datetime'].dt.hour
        
        # Calculer le profil horaire moyen de l'utilisateur
        hourly_profile = user_df.groupby('Hour')['value'].mean()
        
        # Charger les profils journaliers des clusters
        dir_path = os.path.dirname(os.path.realpath(__file__))
        full_profiles_path = os.path.join(dir_path, daily_profiles_path)
        
        if not os.path.exists(full_profiles_path):
            print(f"⚠️ Profils journaliers non disponibles: {full_profiles_path}")
            # Création d'un graphique simple
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hourly_profile.index,
                y=hourly_profile.values,
                mode='lines+markers',
                name='Profil utilisateur',
                line=dict(color='black', width=2.5),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title=f"Profil de consommation journalière: {user_name}",
                xaxis_title="Heure de la journée",
                yaxis_title="Consommation moyenne (kWh/h)",
                xaxis=dict(
                    tickmode='array',
                    tickvals=list(range(0, 24)),
                    ticktext=[f"{h}h" for h in range(0, 24)]
                )
            )
            
            if output_filename:
                try:
                    output_file = os.path.join(dir_path, output_filename)
                    fig.write_image(output_file, scale=2)
                except Exception as e:
                    print(f"   ⚠️ Erreur sauvegarde graphique: {e}")
                
            return fig
        
        # Traitement des profils journaliers
        cluster_profiles = pd.read_csv(full_profiles_path, index_col=0)
        
        fig = go.Figure()
        
        # Tracer les profils de chaque cluster
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        for i, col in enumerate(cluster_profiles.columns):
            cluster_id = int(col.split('_')[1])  # Cluster_X -> X
            color = colors[i % len(colors)]
            
            # Style différent pour le cluster prédit
            if cluster_id == predicted_cluster:
                fig.add_trace(go.Scatter(
                    x=cluster_profiles.index,
                    y=cluster_profiles[col],
                    mode='lines',
                    name=f'Groupe {cluster_id} (PRÉDIT)',
                    line=dict(color=color, width=3, dash='solid'),
                    opacity=1.0
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=cluster_profiles.index,
                    y=cluster_profiles[col],
                    mode='lines',
                    name=f'Groupe {cluster_id}',
                    line=dict(color=color, width=1.5, dash='dash'),
                    opacity=0.7
                ))
        
        # Ajouter le profil de l'utilisateur
        fig.add_trace(go.Scatter(
            x=hourly_profile.index,
            y=hourly_profile.values,
            mode='lines+markers',
            name=f'Utilisateur {user_name}',
            line=dict(color='black', width=2.5),
            marker=dict(size=8)
        ))
        
        # Configurer le layout
        fig.update_layout(
            title={
                'text': f"Profil de consommation journalière: {user_name}",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 20}
            },
            xaxis_title="Heure de la journée",
            yaxis_title="Consommation moyenne (kWh/h)",
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(0, 24)),
                ticktext=[f"{h}h" for h in range(0, 24)]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            height=600,
            width=800
        )
        
        # Sauvegarde optionnelle
        if output_filename:
            try:
                output_file = os.path.join(dir_path, output_filename)
                fig.write_image(output_file, scale=2)
            except Exception as e:
                print(f"   ⚠️ Erreur sauvegarde graphique: {e}")
        
        return fig
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du graphique journalier: {e}")
        traceback.print_exc()
        return None


def create_weekly_profile_comparison(user_name, user_timeseries, timestamps,
                                   predicted_cluster,
                                   weekly_profiles_path='weekly_profiles_by_cluster_8features.csv',
                                   output_filename=None):
    """
    Crée un graphique comparant le profil hebdomadaire de l'utilisateur avec les profils moyens des clusters.
    """
    try:
        # Vérification des timestamps
        if timestamps is None or len(timestamps) != len(user_timeseries):
            print("⚠️ Impossible de créer le profil hebdomadaire sans timestamps valides")
            return None
            
        # Préparation des données utilisateur
        user_df = pd.DataFrame({
            'value': user_timeseries.values,
            'Datetime': timestamps
        })
        
        # Extraire jour de semaine et heure
        user_df['DayOfWeek'] = user_df['Datetime'].dt.dayofweek  # 0=Lundi, 6=Dimanche
        user_df['Hour'] = user_df['Datetime'].dt.hour
        user_df['WeekHourIndex'] = user_df['DayOfWeek'] * 24 + user_df['Hour']  # 0-167
        
        # Calculer le profil hebdomadaire moyen
        weekly_profile = user_df.groupby('WeekHourIndex')['value'].mean()
        
        # Charger les profils hebdomadaires des clusters
        dir_path = os.path.dirname(os.path.realpath(__file__))
        full_profiles_path = os.path.join(dir_path, weekly_profiles_path)
        
        if not os.path.exists(full_profiles_path):
            print(f"⚠️ Profils hebdomadaires non disponibles: {full_profiles_path}")
            # Création d'un graphique simple
            fig = go.Figure()
            
            # Pour le WeekHourIndex, créer un axe X plus informatif
            days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            day_labels = []
            x_ticks = []
            
            for i, day in enumerate(days):
                x_ticks.append(i*24 + 12)  # Milieu de la journée
                day_labels.append(day)
            
            fig.add_trace(go.Scatter(
                x=weekly_profile.index,
                y=weekly_profile.values,
                mode='lines',
                name='Profil utilisateur',
                line=dict(color='black', width=2)
            ))
            
            # Ajouter des lignes verticales pour séparer les jours
            for day in range(1, 7):
                fig.add_shape(
                    type="line", 
                    x0=day*24, 
                    x1=day*24, 
                    y0=0, 
                    y1=1, 
                    yref="paper",
                    line=dict(color="gray", width=1, dash="dash")
                )
            
            fig.update_layout(
                title=f"Profil de consommation hebdomadaire: {user_name}",
                xaxis_title="Jour de la semaine",
                yaxis_title="Consommation moyenne (kWh/h)",
                xaxis=dict(
                    tickvals=x_ticks,
                    ticktext=day_labels
                ),
                height=500,
                width=900
            )
            
            if output_filename:
                try:
                    output_file = os.path.join(dir_path, output_filename)
                    fig.write_image(output_file, scale=2)
                except Exception as e:
                    print(f"   ⚠️ Erreur sauvegarde graphique: {e}")
                
            return fig
        
        # Charger les profils hebdomadaires pré-générés
        cluster_profiles = pd.read_csv(full_profiles_path)
        # Garder uniquement les colonnes des clusters
        cluster_cols = [col for col in cluster_profiles.columns if col.startswith('Cluster_')]
        
        # Créer la visualisation avec plotly
        fig = go.Figure()
        
        # Tracer les profils de chaque cluster
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # Variable pour stocker la référence au profil du cluster prédit
        predicted_cluster_profile = None
        predicted_cluster_color = None
        
        for i, col in enumerate(cluster_cols):
            cluster_id = int(col.split('_')[1])  # Cluster_X -> X
            color = colors[i % len(colors)]
            
            # Style différent pour le cluster prédit
            if cluster_id == predicted_cluster:
                predicted_cluster_profile = cluster_profiles[col].values
                predicted_cluster_color = color
                fig.add_trace(go.Scatter(
                    x=cluster_profiles['WeekHourIndex'],
                    y=cluster_profiles[col],
                    mode='lines',
                    name=f'Groupe {cluster_id} (PRÉDIT)',
                    line=dict(color=color, width=3, dash='solid'),
                    opacity=1.0
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=cluster_profiles['WeekHourIndex'],
                    y=cluster_profiles[col],
                    mode='lines',
                    name=f'Groupe {cluster_id}',
                    line=dict(color=color, width=1.5, dash='dash'),
                    opacity=0.3  # Réduire l'opacité des autres clusters
                ))
        
        # Ajouter le profil de l'utilisateur
        fig.add_trace(go.Scatter(
            x=weekly_profile.index,
            y=weekly_profile.values,
            mode='lines',
            name=f'Utilisateur {user_name}',
            line=dict(color='black', width=2.5)
        ))
        
        # Ajouter des lignes verticales pour séparer les jours
        for day in range(1, 7):
            fig.add_shape(
                type="line", 
                x0=day*24, 
                x1=day*24, 
                y0=0, 
                y1=1, 
                yref="paper",
                line=dict(color="gray", width=1, dash="dash")
            )
        
        # Ajouter la surface colorée entre les profils utilisateur et le groupe prédit
        if predicted_cluster_profile is not None:
            # S'assurer que les deux séries ont le même index
            x_values = list(range(168))  # 0-167 pour les 168 heures de la semaine
            
            # Compléter le profil utilisateur si nécessaire
            user_profile_complete = np.zeros(168)
            for idx in weekly_profile.index:
                if 0 <= idx < 168:
                    user_profile_complete[idx] = weekly_profile[idx]
            
            # Ajouter la surface colorée
            fig.add_trace(go.Scatter(
                x=x_values + x_values[::-1],
                y=list(user_profile_complete) + list(predicted_cluster_profile)[::-1],
                fill='toself',
                fillcolor=f'rgba{tuple(list(int(predicted_cluster_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.2])}',
                line=dict(color='rgba(0,0,0,0)'),
                name='Différence de profil',
                hoverinfo='skip',
                showlegend=False
            ))
            
            # Calculer le rapport entre les profils
            user_total = np.sum(user_profile_complete)
            predicted_total = np.sum(predicted_cluster_profile)
            profile_ratio = user_total / predicted_total if predicted_total > 0 else 0
            
            # Déterminer si le profil est supérieur ou inférieur
            if profile_ratio > 1.05:
                ratio_text = f"Votre consommation est {profile_ratio:.1f}x supérieure à la moyenne du groupe {predicted_cluster}"
                ratio_color = "rgba(220, 20, 60, 0.8)"  # Rouge pour supérieur
            elif profile_ratio < 0.95:
                ratio_text = f"Votre consommation est {1/profile_ratio:.1f}x inférieure à la moyenne du groupe {predicted_cluster}"
                ratio_color = "rgba(46, 139, 87, 0.8)"  # Vert pour inférieur
            else:
                ratio_text = f"Votre consommation est similaire à la moyenne du groupe {predicted_cluster}"
                ratio_color = "rgba(70, 70, 70, 0.8)"  # Gris pour équivalent
        
        # Configurer les ticks de l'axe x pour montrer les jours
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        x_ticks = [i*24 + 12 for i in range(7)]  # Milieu de chaque jour
        
        fig.update_layout(
            title={
                'text': f"Profil de consommation hebdomadaire: {user_name}",
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 18}
            },
            xaxis_title="Jour de la semaine",
            yaxis_title="Consommation moyenne (kWh/h)",
            xaxis=dict(
                tickvals=x_ticks,
                ticktext=days
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.4,
                xanchor="center",
                x=0.5
            ),
            height=550,
            width=900
        )
        
        # Ajouter l'annotation pour le rapport entre les profils
        if predicted_cluster_profile is not None:
            fig.add_annotation(
                text=ratio_text,
                x=0.5,
                y=1.05,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(
                    color=ratio_color,
                    size=14,
                    family="Arial, sans-serif",
                    weight="bold"
                ),
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor=ratio_color,
                borderwidth=1,
                borderpad=4,
                align="center"
            )
        
        # Sauvegarde optionnelle
        if output_filename:
            try:
                output_file = os.path.join(dir_path, output_filename)
                fig.write_image(output_file, scale=2)
            except Exception as e:
                print(f"   ⚠️ Erreur sauvegarde graphique: {e}")
        

        return fig
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du graphique hebdomadaire: {e}")
        traceback.print_exc()
        return None


# --- Fonction principale modifiée incluant le clipping ---

def predict_cluster_from_clean_dataset(file_path='clean_dataset.csv'):
    """
    Fonction simplifiée qui analyse directement le fichier clean_dataset.csv
    et applique le clipping comme dans la phase d'entraînement
    """
    try:
        # Charger les données propres
        timeseries, timestamps = load_clean_dataset(file_path)
        
        if timeseries is None or timestamps is None:
            print("❌ Impossible de charger clean_dataset.csv")
            return None, None, None, None
        
        print(f"✅ Données chargées: {len(timeseries)} points")
        
        # --- Configuration des chemins ---
        dir_path = os.path.dirname(os.path.realpath(__file__))
        model_path = os.path.join(dir_path, 'feature_kmeans_model_weight_8features.joblib')
        scaler_path = os.path.join(dir_path, 'feature_scaler_weight_8features.joblib')
        weights_path = os.path.join(dir_path, 'feature_weights_weight_8features.joblib')
        stats_path = os.path.join(dir_path, 'feature_stats_weight_8features.joblib')
        
        # --- Vérification des fichiers requis ---
        required_files = [model_path, scaler_path, weights_path]
        for file_path in required_files:
            if not os.path.exists(file_path):
                print(f"❌ Fichier requis non trouvé: {os.path.basename(file_path)}")
                return None, None, None, None
        
        # --- Calcul des features pour la prédiction ---
        print("Calcul des features à partir des données temporelles...")
        user_features = calculate_timeseries_features_8(timeseries, timestamps)
        
        if user_features is None or user_features.isnull().all():
            print("❌ Échec du calcul des features")
            return None, None, None, None
        
        # Stocker les features dans la session Streamlit pour utilisation ultérieure
        if 'st' in globals():
            st.session_state['user_features'] = user_features
        
        # --- Chargement du modèle et prédiction avec clipping ---
        try:
            kmeans_model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            weights = joblib.load(weights_path)
            
            # S'assurer que l'ordre des features correspond à celui du scaler
            feature_order = list(get_feature_weights().keys())
            ordered_features = np.array([user_features.get(feat, 0) for feat in feature_order]).reshape(1, -1)
            
            # Préparation des features avec scaling
            features_scaled = scaler.transform(ordered_features)
            features_scaled_weighted = features_scaled * weights
            
            # --- AJOUT DU CLIPPING COMME DANS LA PHASE D'ENTRAÎNEMENT ---
            print("   - Applying clipping to limit outlier effects...")
            
            # Approche 1: Si le fichier de statistiques existe, l'utiliser
            if os.path.exists(stats_path):
                try:
                    print(f"   - Loading feature statistics from {os.path.basename(stats_path)}")
                    feature_stats = joblib.load(stats_path)
                    lower_clip = feature_stats['lower_clip']
                    upper_clip = feature_stats['upper_clip']
                    
                    # Appliquer le clipping
                    features_clipped = np.clip(features_scaled_weighted, lower_clip, upper_clip)
                    predicted_cluster = kmeans_model.predict(features_clipped)[0]
                    
                    # Afficher les distances pour diagnostic
                    distances = kmeans_model.transform(features_clipped)[0]
                    print("Distances aux centroïdes de chaque cluster:")
                    for i, dist in enumerate(distances):
                        is_predicted = "(PRÉDIT)" if i == predicted_cluster else ""
                        print(f"   - Distance au Groupe {i}: {dist:.4f} {is_predicted}")
                        
                except Exception as e:
                    print(f"⚠️ Erreur lors du chargement des statistiques: {e}")
                    # Calcul manuel des bornes de clipping
                    clip_threshold = 3.0
                    print(f"   - Calcul manuel des limites de clipping (seuil = {clip_threshold} écarts-types)")
                    mean_vals = np.mean(features_scaled_weighted, axis=0)
                    std_vals = np.std(features_scaled_weighted, axis=0)
                    lower_clip = mean_vals - clip_threshold * std_vals
                    upper_clip = mean_vals + clip_threshold * std_vals
                    
                    # Appliquer le clipping
                    features_clipped = np.clip(features_scaled_weighted, lower_clip, upper_clip)
                    predicted_cluster = kmeans_model.predict(features_clipped)[0]
            else:
                # Approche 2: Calcul manuel des bornes de clipping (identique à la phase d'entraînement)
                clip_threshold = 3.0
                print(f"   - Statistiques non trouvées, calcul manuel des limites de clipping (seuil = {clip_threshold} écarts-types)")
                
                # Créer des bornes basées uniquement sur les données actuelles (moins idéal)
                mean_vals = np.mean(features_scaled_weighted, axis=0)
                std_vals = np.std(features_scaled_weighted, axis=0) + 1e-10  # Éviter division par zéro
                lower_clip = mean_vals - clip_threshold * std_vals
                upper_clip = mean_vals + clip_threshold * std_vals
                
                # Appliquer le clipping
                features_clipped = np.clip(features_scaled_weighted, lower_clip, upper_clip)
                predicted_cluster = kmeans_model.predict(features_clipped)[0]
            
            print(f"✅ Groupe prédit: {predicted_cluster}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la prédiction: {e}")
            traceback.print_exc()
            return None, None, None, None
        
        # --- Génération des visualisations ---
        # Distribution des clusters
        dist_fig = None
        
        # Profil journalier
        daily_fig = create_daily_profile_comparison(
            "Votre profil",
            timeseries,
            timestamps,
            predicted_cluster,
            output_filename=None
        )
        
        # Profil hebdomadaire
        weekly_fig = create_weekly_profile_comparison(
            "Votre profil",
            timeseries,
            timestamps,
            predicted_cluster,
            output_filename=None
        )
        
        print("✅ Analyse terminée avec succès")
        return predicted_cluster, dist_fig, daily_fig, weekly_fig
        
    except Exception as e:
        print(f"❌ Erreur lors de la prédiction: {e}")
        traceback.print_exc()
        return None, None, None, None


# --- Fonction pour sauvegarder manuellement les statistiques de clipping ---
def save_clipping_stats():
    """
    Crée un fichier de statistiques pour le clipping si nécessaire.
    Cette fonction peut être utilisée une seule fois si le fichier est manquant.
    """
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        stats_path = os.path.join(dir_path, 'feature_stats_weight_8features.joblib')
        
        # Vérifier si le fichier existe déjà
        if os.path.exists(stats_path):
            print(f"⚠️ Fichier de statistiques existe déjà: {stats_path}")
            return
            
        # Valeurs par défaut pour les limites (basées sur la phase d'entraînement)
        # Ces valeurs sont approximatives et devraient idéalement être calculées à partir des données d'entraînement
        clip_threshold = 3.0
        
        # Créer un dict avec les statistiques
        # Note: Ces valeurs sont fictives, il faudrait idéalement les extraire 
        # du processus d'entraînement en amont
        feature_stats = {
            'clip_threshold': clip_threshold,
            'lower_clip': np.array([-3.0, -3.0, -3.0, -3.0, -3.0, -3.0, -3.0, -3.0]),
            'upper_clip': np.array([3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0])
        }
        
        # Sauvegarder les statistiques
        joblib.dump(feature_stats, stats_path)
        print(f"✅ Statistiques de clipping sauvegardées dans: {stats_path}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde des statistiques: {e}")
        traceback.print_exc()


# --- Main Execution ---
if __name__ == "__main__":
    print("📊 Prédiction du cluster à partir du fichier clean_dataset.csv")
    # Vérifier et créer le fichier de statistiques si nécessaire
    # save_clipping_stats()  # Décommenter si nécessaire pour générer le fichier de stats
    predict_cluster_from_clean_dataset()