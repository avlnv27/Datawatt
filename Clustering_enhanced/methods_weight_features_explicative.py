"""
MÉTHODES DE CALCUL DES FEATURES ET SYSTÈME DE PONDÉRATION POUR CLUSTERING

Ce module constitue le cœur algorithmique du système de clustering DataWatt. Il définit les méthodes
de calcul des caractéristiques (features) comportementales des consommateurs électriques et leur
système de pondération pour une segmentation optimale.

SYSTÈME DE PONDÉRATION (WEIGHTS):

Le système de poids permet de prioriser certaines caractéristiques dans l'algorithme de clustering :
- 'std' (1.5) : Variabilité globale de la consommation
- 'base_load' (1.0) : Consommation nocturne de base (1h-4h)
- 'mean_consumption_winter/summer' (1.5) : Moyennes saisonnières normalisées
- 'ratio_weekday_weekend' (1.5) : Différence comportementale semaine/weekend
- 'ratio_day_night' (2.0) : Ratio jour/nuit (poids le plus élevé)
- 'slope_morning/evening' (1.0) : Pentes de transition matin/soir

CALCUL DES FEATURES COMPORTEMENTALES:

1. BASE LOAD (CHARGE DE BASE):
   - Consommation moyenne entre 1h et 4h30 du matin
   - Indicateur de la consommation incompressible (veille, frigo, etc.)

2. MOYENNES SAISONNIÈRES:
   - Hiver (Déc-Fév) et Été (Jun-Aoû) normalisées par la moyenne globale
   - Capture les variations de chauffage/climatisation

3. RATIOS COMPORTEMENTAUX:
   - Semaine/Weekend : Différence d'usage professionnel vs personnel
   - Jour/Nuit : Pattern d'activité principal (7h-18h vs 19h-6h)

4. PENTES DE TRANSITION:
   - Matin (6h-9h) : Indicateur de réveil/départ au travail
   - Soir (18h-22h) : Indicateur de retour à domicile

ARCHITECTURE ALGORITHMIQUE:
- Utilisation de pandas pour manipulation efficace des séries temporelles
- Gestion robuste des erreurs et valeurs manquantes
- Normalisation par moyennes globales pour comparabilité
- Calculs vectorisés pour performance sur gros datasets

INTÉGRATION CLUSTERING:
Ces features sont utilisées par les algorithmes K-means dans les phases d'entraînement et de prédiction
du système de clustering. Elles permettent d'identifier des groupes homogènes de consommateurs selon
leurs profils comportementaux énergétiques.

VERSION: 8 features optimisées suite à l'analyse PCA (Principal Component Analysis)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LinearRegression

def get_feature_weights():
    """
    Retourne les poids à appliquer à chaque feature pour le clustering.
    Version simplifiée avec seulement 8 features clés.
    """
    # Seulement les 8 features sélectionnées suite à l'analyse PCA
    weights = {
        # Statistiques de base
        'std': 1.5,   # Variabilité globale , monter ça aussi 
        
        # Charge de base
        'base_load': 1.0,  # Consommation nocturne (1h-4h)
        
        # Moyennes saisonnières principales
        'mean_consumption_winter': 1.5, # monter légèrement
        'mean_consumption_summer': 1.5, # monter légèrement
        
        # Ratio comportemental clé
        'ratio_weekday_weekend': 1.5,  # Différence semaine/weekend
        
        # Ratio jour/nuit global (au lieu des ratios saisonniers)
        'ratio_day_night': 2.0, # augmenter la valeur 
        
        # Pentes de consommation pour les transitions
        'slope_morning_6_9': 1.0,     # Indicateur de réveil/départ au travail
        'slope_evening_18_22': 1.0    # Indicateur de retour à la maison
    }
    
    return weights

def calculate_base_load(df):
    """Calcule la consommation moyenne entre 1h et 4h30 (Base Load)"""
    try:
        if 'Hour' in df.columns:
            # Filtrer pour les heures entre 1h et 4h inclus
            mask = df['Hour'].isin([1, 2, 3, 4])
            
            # Exclure les colonnes temporelles pour le calcul de la moyenne
            time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour']
            cols_to_use = [col for col in df.columns if col not in time_cols]
            
            base_load_df = df[mask]
            return base_load_df[cols_to_use].mean()
        else:
            print("Avertissement: Colonne 'Hour' non trouvée pour calculer le Base Load")
            return pd.Series()
    except Exception as e:
        print(f"Erreur dans calculate_base_load: {e}")
        return pd.Series()

def calculate_seasonal_means(df):
    """Calcule la consommation moyenne pour l'été et l'hiver uniquement"""
    try:
        if 'Month' in df.columns:
            # Définir les saisons (hémisphère nord)
            winter_mask = df['Month'].isin([12, 1, 2])
            summer_mask = df['Month'].isin([6, 7, 8])
            
            # Exclure les colonnes temporelles pour le calcul
            time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour']
            cols_to_use = [col for col in df.columns if col not in time_cols]
            
            global_mean = df[cols_to_use].mean()

            winter_mean = df.loc[winter_mask, cols_to_use].mean()/(global_mean*4)
            summer_mean = df.loc[summer_mask, cols_to_use].mean()/(global_mean*4)
            
            return summer_mean, winter_mean
        else:
            print("Avertissement: Colonne 'Month' non trouvée pour calculer les moyennes saisonnières")
            return pd.Series(), pd.Series()
    except Exception as e:
        print(f"Erreur dans calculate_seasonal_means: {e}")
        return pd.Series(), pd.Series()
    
def calculate_seasonal_means_with_size(df):
    """Calcule la consommation moyenne pour l'été et l'hiver uniquement"""
    try:
        if 'Month' in df.columns:
            # Définir les saisons (hémisphère nord)
            winter_mask = df['Month'].isin([12, 1, 2])
            summer_mask = df['Month'].isin([6, 7, 8])
            
            # Exclure les colonnes temporelles pour le calcul
            time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour']
            cols_to_use = [col for col in df.columns if col not in time_cols]
            
            winter_mean = df.loc[winter_mask, cols_to_use].mean()
            summer_mean = df.loc[summer_mask, cols_to_use].mean()
            
            return summer_mean, winter_mean
        else:
            print("Avertissement: Colonne 'Month' non trouvée pour calculer les moyennes saisonnières")
            return pd.Series(), pd.Series()
    except Exception as e:
        print(f"Erreur dans calculate_seasonal_means: {e}")
        return pd.Series(), pd.Series()


def calculate_weekday_weekend_ratio(df):
    """Calcule le ratio entre consommation jours ouvrables / weekend"""
    try:
        if 'Datetime' in df.columns and 'Day' in df.columns and 'Month' in df.columns and 'Year' in df.columns:
            df_copy = df.copy()
            # Créer une colonne datetime pour déterminer le jour de la semaine
            df_copy['date'] = pd.to_datetime(df_copy['Datetime'])
            
            # Si le format est différent, essayer cette alternative
            if pd.isna(df_copy['date'].iloc[0]):
                df_copy['date'] = pd.to_datetime(
                    df_copy['Year'].astype(str) + '-' + 
                    df_copy['Month'].astype(str).str.zfill(2) + '-' + 
                    df_copy['Day'].astype(str).str.zfill(2)
                )
            
            # Déterminer les weekends (0=lundi, 6=dimanche)
            weekday_mask = df_copy['date'].dt.dayofweek < 5  # Lundi à vendredi
            weekend_mask = df_copy['date'].dt.dayofweek >= 5  # Samedi et dimanche
            
            # Exclure les colonnes temporelles pour le calcul
            time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour', 'date']
            cols_to_use = [col for col in df_copy.columns if col not in time_cols]
            
            weekday_mean = df_copy.loc[weekday_mask, cols_to_use].mean()
            weekend_mean = df_copy.loc[weekend_mask, cols_to_use].mean()
            
            # Calculer le ratio (avec gestion des divisions par zéro)
            ratio = weekday_mean / weekend_mean.replace(0, np.nan)
            
            return ratio
        else:
            print("Avertissement: Colonnes temporelles manquantes pour calculer le ratio semaine/weekend")
            return pd.Series()
    except Exception as e:
        print(f"Erreur dans calculate_weekday_weekend_ratio: {e}")
        return pd.Series()

def calculate_day_night_ratio(df):
    """Calcule le ratio global consommation jour/nuit (toutes saisons confondues)"""
    try:
        if 'Hour' in df.columns:
            # Définir jour (7h-19h) et nuit (19h-7h)
            day_mask = df['Hour'].between(7, 18)  # 7h à 18h inclus
            night_mask = ~day_mask  # Toutes les autres heures
            
            # Exclure les colonnes temporelles pour le calcul
            time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour']
            cols_to_use = [col for col in df.columns if col not in time_cols]
            
            # Calculer les moyennes jour et nuit globales
            day_mean = df.loc[day_mask, cols_to_use].mean()
            night_mean = df.loc[night_mask, cols_to_use].mean()
            
            # Calculer le ratio (avec gestion des divisions par zéro)
            ratio = day_mean / night_mean.replace(0, np.nan)
            
            return ratio
        else:
            print("Avertissement: Colonne Hour manquante pour calculer le ratio jour/nuit global")
            return pd.Series()
    except Exception as e:
        print(f"Erreur dans calculate_day_night_ratio: {e}")
        return pd.Series()

def calculate_consumption_slope(df, start_hour, end_hour):
    """Calcule la pente de consommation pour une plage horaire donnée"""
    try:
        if 'Hour' in df.columns:
            # Filtrer pour les heures dans la plage spécifiée
            mask = df['Hour'].between(start_hour, end_hour - 1)  # -1 car end_hour exclu
            
            # Exclure les colonnes temporelles pour le calcul
            time_cols = ['Datetime', 'Year', 'Month', 'Day']
            cols_to_use = [col for col in df.columns if col not in time_cols and col != 'Hour']
            
            # Filtrer les données
            filtered_df = df.loc[mask]
            
            if len(filtered_df) == 0:
                print(f"Avertissement: Pas de données trouvées entre {start_hour}h et {end_hour}h")
                return pd.Series(index=cols_to_use)
            
            # Calculer la pente pour chaque colonne
            slopes = pd.Series(index=cols_to_use)
            for col in cols_to_use:
                try:
                    # Grouper par heure et calculer la moyenne
                    hourly_avg = filtered_df.groupby('Hour')[col].mean()
                    
                    if len(hourly_avg) > 1:  # Au moins deux points pour calculer une pente
                        # Préparer les données pour la régression linéaire
                        X = hourly_avg.index.values.reshape(-1, 1)
                        y = hourly_avg.values
                        
                        # Calculer la pente (coefficient directeur)
                        model = LinearRegression().fit(X, y)
                        slopes[col] = model.coef_[0]
                    else:
                        slopes[col] = np.nan
                except Exception as e:
                    print(f"Erreur lors du calcul de la pente pour {col}: {e}")
                    slopes[col] = np.nan
            
            return slopes
        else:
            print("Avertissement: Colonne 'Hour' non trouvée pour calculer la pente de consommation")
            return pd.Series()
    except Exception as e:
        print(f"Erreur dans calculate_consumption_slope: {e}")
        return pd.Series()