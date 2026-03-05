"""
ÉTAPE 1 : NETTOYAGE ET EXTRACTION DES FEATURES POUR CLUSTERING

Ce script constitue la première étape du pipeline de clustering DataWatt. Il traite les données
brutes de consommation électrique pour extraire les caractéristiques comportementales nécessaires
à la segmentation des consommateurs.

PROCESSUS PRINCIPAL:

1. NETTOYAGE DES DONNÉES:
   - Chargement du dataset principal (dataset_clean_with_datetime.csv)
   - Filtrage automatique des colonnes POD avec uniquement des zéros
   - Exclusion des colonnes temporelles pour le calcul des features
   - Sauvegarde de la liste des colonnes exclues pour référence

2. EXTRACTION DES FEATURES COMPORTEMENTALES:
   - Statistiques de base (moyenne, écart-type, skewness)
   - Base load : consommation nocturne (1h-4h30)
   - Moyennes et pics saisonniers (été, hiver, printemps, automne)
   - Ratios comportementaux (semaine/weekend, jour/nuit par saison)
   - Pentes de consommation (transitions matin 6h-9h et soir 18h-22h)

3. GESTION ROBUSTE DES ERREURS:
   - Remplacement automatique des valeurs NaN par la médiane
   - Initialisation par défaut en cas d'échec de calcul
   - Validation finale et nettoyage des données manquantes

SORTIE:
- column_features_v3.csv : Matrice des features pour tous les POD
- excluded_zero_columns.csv : Liste des colonnes exclues

OPTIMISATION FUTURE:
Il est recommandé de refaire le clustering pour améliorer la précision de la segmentation,
notamment en optimisant les poids des features et en ajustant les algorithmes de clustering
selon les nouveaux patterns de consommation identifiés.

VERSION:
Ce script utilise une version antérieure des méthodes de calcul des features. Certaines
fonctions peuvent générer des erreurs dues à l'évolution du codebase. En cas d'erreur,
veuillez contacter sven.hominal@epfl.ch pour une mise à jour.

DÉPENDANCES:
- methods_weight_features_explicative.py : Contient les fonctions de calcul des features
- dataset_clean_with_datetime.csv : Dataset principal nettoyé avec timestamps
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LinearRegression
from methods_weight_features_explicative import *

# --- Configuration ---
input_csv_file = 'dataset_clean_with_datetime.csv'
output_csv_file = 'column_features_v3.csv'
# Nombre de lignes à vérifier pour la présence de zéros
n_first_rows_to_check = 10000

# --- Traitement ---
print(f"Chargement du fichier : {input_csv_file}...")
try:
    # Charger le dataset
    df = pd.read_csv(input_csv_file)

    print("Prétraitement des données...")
    
    # Identifier les colonnes des pods (non-temporelles)
    time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour']
    pod_columns_initial = [col for col in df.columns if col not in time_cols]
    print(f"Nombre de colonnes POD initiales : {len(pod_columns_initial)}")
    
    # --- Filtrer les colonnes avec uniquement des zéros dans les premières lignes ---
    zero_only_cols = []
    df_first_rows = df.iloc[:min(n_first_rows_to_check, len(df))]
    
    for col in pod_columns_initial:
        # Vérifier si toutes les premières lignes sont égales à zéro
        if (df_first_rows[col] == 0).all():
            zero_only_cols.append(col)
    
    print(f"Colonnes avec uniquement des zéros dans les {n_first_rows_to_check} premières lignes : {len(zero_only_cols)}")
    print(f"Pourcentage de colonnes filtrées : {(len(zero_only_cols)/len(pod_columns_initial))*100:.1f}%")
    
    # Filtrer les colonnes (garder celles qui ne sont pas dans zero_only_cols)
    pod_columns = [col for col in pod_columns_initial if col not in zero_only_cols]
    
    print(f"Nombre de colonnes POD après filtrage : {len(pod_columns)}")

    # --- Sauvegarde des colonnes exclues pour référence future ---
    excluded_cols_df = pd.DataFrame({'excluded_columns': zero_only_cols})
    excluded_cols_df.to_csv('excluded_zero_columns.csv', index=False)
    print(f"Liste des colonnes exclues (colonnes avec uniquement des zéros) sauvegardée")

    print("Calcul des features par colonne...")
    # Calculer uniquement la moyenne et l'écart-type pour les colonnes des pods filtrées
    features_raw = df[pod_columns].describe()
    
    # Ne conserver que mean et std
    features_df = features_raw.loc[['mean', 'std'], :]

    # Fonction helper pour gérer les features en cas d'échec
    def safe_add_feature(features_df, feature_name, feature_values, error_message):
        try:
            features_df.loc[feature_name] = feature_values
            # Vérifier et remplacer les NaN par la médiane de la ligne
            if features_df.loc[feature_name].isna().any():
                median_val = features_df.loc[feature_name].median()
                features_df.loc[feature_name] = features_df.loc[feature_name].fillna(median_val)
                print(f"Info: Des valeurs NaN dans '{feature_name}' ont été remplacées par la médiane ({median_val:.4f})")
        except Exception as e:
            print(f"Avertissement : {error_message} - {e}")
            # En cas d'échec complet, ajouter une ligne de zéros
            features_df.loc[feature_name] = 0.0
            print(f"         La feature '{feature_name}' a été initialisée avec des zéros.")
        return features_df

    # Ajouter skewness
    safe_add_feature(features_df, 'skew', df[pod_columns].skew(), 
                    "Impossible de calculer skewness")
    
    # Ajouter base load
    try:
        base_load = calculate_base_load(df[time_cols + pod_columns])
        safe_add_feature(features_df, 'base_load', base_load, 
                         "Impossible de calculer le Base Load")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer le Base Load - {e}")
        features_df.loc['base_load'] = 0.0
    
    # Ajouter les moyennes saisonnières
    try:
        summer_mean, winter_mean, spring_mean, autumn_mean = calculate_seasonal_means(df[time_cols + pod_columns])
        safe_add_feature(features_df, 'mean_consumption_summer', summer_mean, 
                         "Impossible de calculer mean_consumption_summer")
        safe_add_feature(features_df, 'mean_consumption_winter', winter_mean, 
                         "Impossible de calculer mean_consumption_winter")
        safe_add_feature(features_df, 'mean_consumption_spring', spring_mean, 
                         "Impossible de calculer mean_consumption_spring")
        safe_add_feature(features_df, 'mean_consumption_autumn', autumn_mean, 
                         "Impossible de calculer mean_consumption_autumn")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer les moyennes saisonnières - {e}")
        features_df.loc['mean_consumption_summer'] = 0.0
        features_df.loc['mean_consumption_winter'] = 0.0
        features_df.loc['mean_consumption_spring'] = 0.0
        features_df.loc['mean_consumption_autumn'] = 0.0
        
    # Ajouter les pics saisonniers
    try:
        summer_peak, winter_peak, spring_peak, autumn_peak = calculate_seasonal_peaks(df[time_cols + pod_columns])
        safe_add_feature(features_df, 'peak_consumption_summer', summer_peak, 
                         "Impossible de calculer peak_consumption_summer")
        safe_add_feature(features_df, 'peak_consumption_winter', winter_peak, 
                         "Impossible de calculer peak_consumption_winter")
        safe_add_feature(features_df, 'peak_consumption_spring', spring_peak, 
                         "Impossible de calculer peak_consumption_spring")
        safe_add_feature(features_df, 'peak_consumption_autumn', autumn_peak, 
                         "Impossible de calculer peak_consumption_autumn")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer les pics saisonniers - {e}")
        features_df.loc['peak_consumption_summer'] = 0.0
        features_df.loc['peak_consumption_winter'] = 0.0
        features_df.loc['peak_consumption_spring'] = 0.0
        features_df.loc['peak_consumption_autumn'] = 0.0
        
    # Ajouter le ratio semaine/weekend
    try:
        weekday_weekend_ratio = calculate_weekday_weekend_ratio(df[time_cols + pod_columns])
        safe_add_feature(features_df, 'ratio_weekday_weekend', weekday_weekend_ratio, 
                         "Impossible de calculer ratio_weekday_weekend")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer le ratio semaine/weekend - {e}")
        features_df.loc['ratio_weekday_weekend'] = 1.0
    
    # Ajouter les ratios jour/nuit par saison
    try:
        winter_ratio, spring_ratio, summer_ratio, autumn_ratio = calculate_day_night_ratio_per_season(df[time_cols + pod_columns])
        safe_add_feature(features_df, 'ratio_day_night_winter', winter_ratio, 
                         "Impossible de calculer ratio_day_night_winter")
        safe_add_feature(features_df, 'ratio_day_night_spring', spring_ratio, 
                         "Impossible de calculer ratio_day_night_spring")
        safe_add_feature(features_df, 'ratio_day_night_summer', summer_ratio, 
                         "Impossible de calculer ratio_day_night_summer")
        safe_add_feature(features_df, 'ratio_day_night_autumn', autumn_ratio, 
                         "Impossible de calculer ratio_day_night_autumn")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer les ratios jour/nuit par saison - {e}")
        features_df.loc['ratio_day_night_winter'] = 1.0
        features_df.loc['ratio_day_night_spring'] = 1.0
        features_df.loc['ratio_day_night_summer'] = 1.0
        features_df.loc['ratio_day_night_autumn'] = 1.0
    
    # Ajouter les pentes de consommation
    try:
        morning_slope = calculate_consumption_slope(df[time_cols + pod_columns], 6, 10)  # 6h-9h inclus
        safe_add_feature(features_df, 'slope_morning_6_9', morning_slope, 
                         "Impossible de calculer slope_morning_6_9")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer la pente de consommation matinale - {e}")
        features_df.loc['slope_morning_6_9'] = 0.0
    
    try:
        evening_slope = calculate_consumption_slope(df[time_cols + pod_columns], 18, 23)  # 18h-22h inclus
        safe_add_feature(features_df, 'slope_evening_18_22', evening_slope, 
                         "Impossible de calculer slope_evening_18_22")
    except Exception as e:
        print(f"Avertissement : Impossible de calculer la pente de consommation en soirée - {e}")
        features_df.loc['slope_evening_18_22'] = 0.0

    # Vérification finale pour les NaN
    if features_df.isna().any().any():
        print("⚠️ Attention: Des valeurs NaN restent dans le dataframe après tous les calculs.")
        print(f"Colonnes avec NaN: {features_df.columns[features_df.isna().any()].tolist()}")
        print("Remplacement des NaN restants par 0...")
        features_df = features_df.fillna(0)

    print("\nFeatures calculées (premières colonnes) :")
    # Afficher un aperçu
    print(features_df.iloc[:, :5])

    print(f"\nSauvegarde des features dans : {output_csv_file}...")
    features_df.to_csv(output_csv_file)

    print("Terminé !")

except FileNotFoundError:
    print(f"Erreur : Le fichier '{input_csv_file}' n'a pas été trouvé.")
    print("Veuillez vérifier que le fichier est dans le même répertoire que le script ou fournir le chemin complet.")
except Exception as e:
    print(f"Une erreur inattendue est survenue : {e}")