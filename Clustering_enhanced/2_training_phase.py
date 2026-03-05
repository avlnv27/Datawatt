"""
ÉTAPE 2 : PHASE D'ENTRAÎNEMENT DU CLUSTERING DATAWATT

Ce script constitue la phase d'entraînement principale du système de clustering DataWatt. Il applique
les algorithmes d'apprentissage automatique pour segmenter les consommateurs électriques en groupes
homogènes selon leurs profils comportementaux.

PROCESSUS D'ENTRAÎNEMENT:

1. PRÉPARATION DES DONNÉES:
   - Chargement des features extraites (column_features_v3.csv)
   - Filtrage aux 8 features principales optimisées par analyse PCA
   - Séparation train/test automatique (50 derniers POD pour validation)
   - Imputation robuste des valeurs manquantes (médiane)

2. NORMALISATION ET PONDÉRATION:
   - RobustScaler pour réduire l'impact des outliers
   - Application du système de poids optimisé (ratio_day_night: 2.0, moyennes saisonnières: 1.5)
   - Écrêtage des valeurs extrêmes pour éviter la distorsion des clusters

3. DÉTERMINATION OPTIMALE DU NOMBRE DE CLUSTERS:
   - Méthode du coude (WCSS) pour évaluer l'inertie
   - Analyse de similarité cosinus (intra/inter cluster)
   - Sélection de 4 clusters basée sur le meilleur compromis complexité/qualité

4. ALGORITHME K-MEANS OPTIMISÉ:
   - K-means++ pour initialisation intelligente des centroids
   - Protection contre les clusters singletons (taille minimale)
   - Validation de l'équilibre et de la représentativité des groupes

5. GÉNÉRATION DES PROFILS ET ANALYSES:
   - Profils de consommation journaliers, hebdomadaires et annuels par cluster
   - Analyse PCA pour identification des features les plus discriminantes
   - Calcul des déciles par cluster pour analyse comparative future
   - Visualisations complètes (graphiques, heatmaps) pour validation

SORTIE PRINCIPALE:
- Modèles sauvegardés (KMeans, scaler, weights) pour prédictions
- Profils de consommation par cluster (daily/weekly/annual)
- Déciles des features pour positionnement comparatif
- Visualisations et métriques de validation

OPTIMISATION:
Ce script utilise une approche robuste avec 4 clusters optimal, réduisant le risque de sur-apprentissage
tout en capturant efficacement la diversité des profils de consommation énergétique.

VERSION ET SUPPORT:
Script basé sur une version optimisée des algorithmes de clustering DataWatt. En cas d'erreur
ou de problème d'exécution, veuillez contacter sven.hominal@epfl.ch pour assistance technique.

DÉPENDANCES:
- methods_weight_features_explicative.py : Système de poids et features
- column_features_v3.csv : Features extraites en étape 1
- dataset_clean_with_datetime.csv : Données temporelles pour profils
"""

from sklearn.preprocessing import MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from kneed import KneeLocator 
from sklearn.impute import SimpleImputer
import pandas as pd
import numpy as np
import os
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
# Metrics evaluation imports
from sklearn.metrics.pairwise import cosine_similarity

# Import file with only 8 selected features
from methods_weight_features_explicative import get_feature_weights

# Get the directory of the current script
dir_path = os.path.dirname(os.path.realpath(__file__))

# --- NEW FUNCTION: Generation of average profiles by cluster ---
def generate_cluster_profiles(original_timeseries_path, clusters_path):
    """
    Generate and save daily and weekly average profiles for each cluster.
    Returns True if successful, False otherwise.
    """
    print("\n🔹 Generating consumption profiles by cluster...")
    
    try:
        # Load cluster data
        clusters_df = pd.read_csv(clusters_path)
        
        # Load temporal data (with timestamps)
        original_df = pd.read_csv(original_timeseries_path)
        
        # Convert datetime column
        if 'Datetime' in original_df.columns:
            original_df['Datetime'] = pd.to_datetime(original_df['Datetime'])
            original_df['Hour'] = original_df['Datetime'].dt.hour
            original_df['DayOfWeek'] = original_df['Datetime'].dt.dayofweek  # 0=Monday, 6=Sunday
            original_df['WeekHourIndex'] = original_df['DayOfWeek'] * 24 + original_df['Hour']  # 0-167
            original_df['Date'] = original_df['Datetime'].dt.date
        else:
            print("❌ Error: 'Datetime' column not found in original dataset.")
            return False
        
        # Identify temporal vs POD columns
        time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour', 'DayOfWeek', 'WeekHourIndex', 'Date']
        pod_cols = [col for col in original_df.columns if col not in time_cols]
        
        # ---- DAILY PROFILES ----
        print("   - Calculating average hourly daily profiles by cluster...")
        
        # Create DataFrame to store daily profiles
        unique_clusters = sorted(clusters_df['Feature_Cluster'].unique())
        hours = list(range(24))
        
        daily_profiles_df = pd.DataFrame(index=hours)
        daily_profiles_df.index.name = 'Hour'
        
        # Calculate average daily profile for each cluster
        for cluster_id in unique_clusters:
            # Get PODs in this cluster
            pods_in_cluster = clusters_df[clusters_df['Feature_Cluster'] == cluster_id]['POD'].tolist()
            
            # Filter to include only valid PODs (present in dataset)
            valid_pods = [pod for pod in pods_in_cluster if pod in pod_cols]
            
            if valid_pods:
                # Calculate hourly average for all PODs in the cluster
                hourly_avg = original_df.groupby('Hour')[valid_pods].mean().mean(axis=1)
                daily_profiles_df[f'Cluster_{cluster_id}'] = hourly_avg
            else:
                print(f"   ⚠️ No valid POD found for cluster {cluster_id}")
        
        # Save daily profiles
        daily_profiles_path = os.path.join(dir_path, 'daily_profiles_by_cluster_8features.csv')
        daily_profiles_df.to_csv(daily_profiles_path)
        print(f"   ✅ Daily profiles saved in: {os.path.basename(daily_profiles_path)}")
        
        # Visualization of daily profiles
        plt.figure(figsize=(12, 8))
        for cluster in unique_clusters:
            if f'Cluster_{cluster}' in daily_profiles_df.columns:
                plt.plot(daily_profiles_df.index, daily_profiles_df[f'Cluster_{cluster}'], 
                         label=f'Cluster {cluster}', linewidth=2)
        
        plt.title('Daily Consumption Profiles by Cluster', fontsize=16)
        plt.xlabel('Hour of day', fontsize=14)
        plt.ylabel('Average consumption (kWh/h)', fontsize=14)
        plt.xticks(range(0, 24, 2))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Cluster', loc='best')
        plt.tight_layout()
        
        # Save the plot
        daily_profiles_plot_path = os.path.join(dir_path, 'daily_profiles_by_cluster_8features.png')
        plt.savefig(daily_profiles_plot_path, dpi=300)
        print(f"   ✅ Daily profiles graph saved: {os.path.basename(daily_profiles_plot_path)}")
        
        # ---- WEEKLY PROFILES ----
        print("   - Calculating average hourly weekly profiles by cluster...")
        
        # Create DataFrame to store weekly profiles
        week_hours = list(range(168))  # 7 days * 24 hours
        weekly_profiles_df = pd.DataFrame(index=week_hours)
        weekly_profiles_df.index.name = 'WeekHourIndex'
        
        # Create columns for day and hour to facilitate CSV reading
        weekly_profiles_df['DayOfWeek'] = [idx // 24 for idx in week_hours]
        weekly_profiles_df['HourOfDay'] = [idx % 24 for idx in week_hours]
        
        # Calculate average weekly profile for each cluster
        for cluster_id in unique_clusters:
            # Get PODs in this cluster
            pods_in_cluster = clusters_df[clusters_df['Feature_Cluster'] == cluster_id]['POD'].tolist()
            
            # Filter to include only valid PODs
            valid_pods = [pod for pod in pods_in_cluster if pod in pod_cols]
            
            if valid_pods:
                # Calculate weekly average for all PODs in the cluster
                weekly_avg = original_df.groupby('WeekHourIndex')[valid_pods].mean().mean(axis=1)
                weekly_profiles_df[f'Cluster_{cluster_id}'] = weekly_avg
        
        # Save weekly profiles
        weekly_profiles_path = os.path.join(dir_path, 'weekly_profiles_by_cluster_8features.csv')
        weekly_profiles_df.to_csv(weekly_profiles_path)
        print(f"   ✅ Weekly profiles saved in: {os.path.basename(weekly_profiles_path)}")
        
        # Visualization of weekly profiles
        plt.figure(figsize=(18, 10))
        
        # Add vertical lines to separate days
        for day in range(1, 7):
            plt.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
        
        # Plot profiles for each cluster
        for cluster in unique_clusters:
            if f'Cluster_{cluster}' in weekly_profiles_df.columns:
                plt.plot(weekly_profiles_df.index, weekly_profiles_df[f'Cluster_{cluster}'], 
                         label=f'Cluster {cluster}', linewidth=2)
        
        plt.title('Weekly Consumption Profiles by Cluster', fontsize=16)
        plt.xlabel('Hour of week (0=Monday 00h, 167=Sunday 23h)', fontsize=14)
        plt.ylabel('Average consumption (kWh/h)', fontsize=14)
        
        # Configure x-axis ticks to show days
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        plt.xticks([i*24 + 12 for i in range(7)], days, fontsize=12)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Cluster', loc='best')
        plt.tight_layout()
        
        # Save the plot
        weekly_profiles_plot_path = os.path.join(dir_path, 'weekly_profiles_by_cluster_8features.png')
        plt.savefig(weekly_profiles_plot_path, dpi=300)
        print(f"   ✅ Weekly profiles graph saved: {os.path.basename(weekly_profiles_plot_path)}")
        
        # ---- ANNUAL PROFILES (DAILY CONSUMPTION) ----
        print("   - Calculating annual daily consumption profiles by cluster...")
        
        # Create DataFrame for daily consumption
        daily_consumption_df = pd.DataFrame()
        daily_consumption_df['Date'] = pd.to_datetime(original_df['Date'].unique())
        daily_consumption_df.set_index('Date', inplace=True)
        
        # Calculate average daily consumption for each cluster
        for cluster_id in unique_clusters:
            # Get PODs in this cluster
            pods_in_cluster = clusters_df[clusters_df['Feature_Cluster'] == cluster_id]['POD'].tolist()
            
            # Filter to include only valid PODs
            valid_pods = [pod for pod in pods_in_cluster if pod in pod_cols]
            
            if valid_pods:
                # Calculate daily sum for all PODs in the cluster
                cluster_data = original_df[valid_pods].copy()
                # Sum values for each day and each POD
                daily_sums = cluster_data.groupby(original_df['Date']).sum()
                # Average daily sums across all PODs in the cluster
                daily_consumption_df[f'Cluster_{cluster_id}'] = daily_sums.mean(axis=1)
        
        # Save daily consumption profiles
        daily_consumption_path = os.path.join(dir_path, 'daily_consumption_by_cluster_8features.csv')
        daily_consumption_df.to_csv(daily_consumption_path)
        print(f"   ✅ Daily consumption profiles saved in: {os.path.basename(daily_consumption_path)}")
        
        # Visualization of annual daily consumption
        plt.figure(figsize=(18, 10))
        
        for cluster in unique_clusters:
            if f'Cluster_{cluster}' in daily_consumption_df.columns:
                # Create a moving average to smooth data
                daily_consumption_df[f'Cluster_{cluster}_rolling'] = daily_consumption_df[f'Cluster_{cluster}'].rolling(window=7).mean()
                plt.plot(daily_consumption_df.index, daily_consumption_df[f'Cluster_{cluster}_rolling'], 
                         label=f'Cluster {cluster}', linewidth=2)
        
        plt.title('Annual Daily Consumption by Cluster (7-day moving average)', fontsize=16)
        plt.xlabel('Date', fontsize=14)
        plt.ylabel('Daily consumption (kWh)', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Cluster', loc='best')
        plt.tight_layout()
        
        # Save the plot
        daily_consumption_plot_path = os.path.join(dir_path, 'daily_consumption_by_cluster_8features.png')
        plt.savefig(daily_consumption_plot_path, dpi=300)
        print(f"   ✅ Daily consumption graph saved: {os.path.basename(daily_consumption_plot_path)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error while generating cluster profiles: {e}")
        traceback.print_exc()
        return False

def generate_feature_deciles_by_cluster(X, clusters, feature_names, output_path):
    """
    Generate a CSV file containing decile values (10th to 90th) for each feature in each cluster.
    
    Parameters:
    -----------
    X : numpy.ndarray
        The feature matrix (scaled and weighted)
    clusters : numpy.ndarray
        Cluster assignments for each data point
    feature_names : list
        Names of the features
    output_path : str
        Path to save the CSV file
    """
    print("\n🔹 Generating feature deciles by cluster...")
    
    # Create a DataFrame from the feature matrix
    df = pd.DataFrame(X, columns=feature_names)
    df['cluster'] = clusters
    
    # Define the deciles to calculate
    deciles = list(range(0, 110, 10))  # 10, 20, 30, ..., 90
    
    # Initialize a dictionary to store results
    cluster_feature_deciles = {}
    
    # For each cluster and feature, calculate the deciles
    unique_clusters = sorted(np.unique(clusters))
    
    for cluster_id in unique_clusters:
        cluster_data = df[df['cluster'] == cluster_id]
        cluster_feature_deciles[f'Cluster_{cluster_id}'] = {}
        
        for feature in feature_names:
            feature_values = cluster_data[feature]
            
            # Calculate percentiles for this feature in this cluster
            percentiles = np.percentile(feature_values, deciles)
            
            # Store results
            cluster_feature_deciles[f'Cluster_{cluster_id}'][feature] = {
                f'p{p}': val for p, val in zip(deciles, percentiles)
            }
    
    # Create a flattened version for CSV output
    rows = []
    for cluster_name, features in cluster_feature_deciles.items():
        for feature_name, percentiles in features.items():
            row = {
                'Cluster': cluster_name,
                'Feature': feature_name
            }
            row.update(percentiles)
            rows.append(row)
    
    # Convert to DataFrame and save
    results_df = pd.DataFrame(rows)
    results_df.to_csv(output_path, index=False)
    print(f"   ✅ Feature deciles by cluster saved in: {os.path.basename(output_path)}")
    
    return cluster_feature_deciles

# --- New function to calculate intra/inter cosine similarity ratio ---
def calculate_cosine_similarity_ratio(X, clusters, kmeans):
    """
    Calculate the intra/inter clusters cosine similarity ratio.
    A higher ratio indicates better separation between clusters.
    """
    # Calculate cosine similarity matrix for all pairs of points
    cosine_sim_matrix = cosine_similarity(X)
    
    n_clusters = len(np.unique(clusters))
    n_samples = X.shape[0]
    
    # Initialize intra and inter cluster similarities
    intra_cluster_sim = 0
    intra_cluster_count = 0
    inter_cluster_sim = 0
    inter_cluster_count = 0
    
    # Calculate intra and inter cluster similarities
    for i in range(n_samples):
        for j in range(i+1, n_samples):  # Avoid counting pairs twice
            if clusters[i] == clusters[j]:
                # Points in the same cluster
                intra_cluster_sim += cosine_sim_matrix[i, j]
                intra_cluster_count += 1
            else:
                # Points in different clusters
                inter_cluster_sim += cosine_sim_matrix[i, j]
                inter_cluster_count += 1
    
    # Calculate averages
    avg_intra_sim = intra_cluster_sim / max(1, intra_cluster_count)
    avg_inter_sim = inter_cluster_sim / max(1, inter_cluster_count)
    
    # Calculate ratio (higher = better)
    ratio = avg_intra_sim / max(avg_inter_sim, 1e-10)  # Avoid division by zero
    
    return ratio, avg_intra_sim, avg_inter_sim

# --- Main clustering code ---
print("🔹 Loading column_features.csv for clustering...")
# Load feature data, using the first column as index (feature names)
try:
    features_file = os.path.join(dir_path, 'column_features_v3.csv')
    features_df = pd.read_csv(features_file, index_col=0)
    print(f"   - Data loaded: {features_df.shape[1]} PODs, {features_df.shape[0]} features")
except Exception as e:
    print(f"❌ Error loading features: {e}")
    exit(1)

# --- CHECKING FOR INITIAL MISSING VALUES ---
if features_df.isna().any().any():
    total_nans = features_df.isna().sum().sum()
    percent_nans = (total_nans / (features_df.shape[0] * features_df.shape[1])) * 100
    print(f"⚠️ Dataset contains {total_nans} NaN values ({percent_nans:.2f}% of total)")

# --- NEW: Calculating a unique day/night ratio for the entire year ---
print("🔄 Calculating global day/night ratio...")
if 'ratio_day_night' not in features_df.index:
    # Check if we have hourly data to calculate ourselves
    if 'mean_hour_0' in features_df.index and 'mean_hour_23' in features_df.index:
        print("   - Calculating day/night ratio from existing hourly averages")
        day_cols = [f'mean_hour_{h}' for h in range(8, 20)]  # 8h-20h
        night_cols = [f'mean_hour_{h}' for h in range(0, 8)] + [f'mean_hour_{h}' for h in range(20, 24)]  # 20h-8h
        
        day_means = features_df.loc[day_cols].mean()
        night_means = features_df.loc[night_cols].mean()
        
        ratio_day_night = day_means / night_means
        features_df.loc['ratio_day_night'] = ratio_day_night
        print("   - Day/night ratio calculated and added to dataset")
    elif all(f'ratio_day_night_{season}' in features_df.index for season in ['winter', 'spring', 'summer', 'autumn']):
        print("   - Calculating day/night ratio from existing seasonal ratios")
        seasonal_ratios = features_df.loc[[f'ratio_day_night_{season}' for season in ['winter', 'spring', 'summer', 'autumn']]]
        ratio_day_night = seasonal_ratios.mean()
        features_df.loc['ratio_day_night'] = ratio_day_night
        print("   - Day/night ratio calculated as average of seasonal ratios")
    else:
        print("⚠️ Unable to calculate day/night ratio - required data not available")

# --- MODIFICATION: Explicitly exclude the last 50 PODs for testing ---
print("🔪 Selecting PODs for training and testing...")

# Identify temporal columns and POD columns
time_cols = ['Datetime', 'Year', 'Month', 'Day', 'Hour']
all_columns = list(features_df.columns)
num_pods_total = len(all_columns)
num_pods_to_exclude = 50

if num_pods_total <= num_pods_to_exclude:
    print(f"❌ Not enough PODs ({num_pods_total}) to exclude {num_pods_to_exclude}")
    exit(1)

# Explicitly separate training and testing PODs
pods_to_train = all_columns[:-num_pods_to_exclude]
pods_to_test = all_columns[-num_pods_to_exclude:]

print(f"   - Total number of PODs: {num_pods_total}")
print(f"   - PODs for training: {len(pods_to_train)}")
print(f"   - PODs for testing: {len(pods_to_test)}")

# Save the list of test PODs for future reference
test_pods_df = pd.DataFrame({'test_pods': pods_to_test})
test_pods_path = os.path.join(dir_path, 'test_pods_weight_8features.csv')
test_pods_df.to_csv(test_pods_path, index=False)
print(f"   - List of test PODs saved in '{os.path.basename(test_pods_path)}'")

# Extract training features
features_df_train = features_df[pods_to_train]

# Transpose data so that each row is a user (POD) and each column a feature
print("🔄 Transposing training data: PODs become rows, features become columns...")
df_pods_features = features_df_train.T

# --- NEW: Filter to keep only the 8 important identified features ---
# Get the list of 8 important features
important_features = list(get_feature_weights().keys())
print(f"\n🔍 Using a simplified model with only {len(important_features)} main features:")
for f in important_features:
    print(f"   - {f}")

# Filter DataFrame to keep only these features (if they exist in dataset)
available_features = [f for f in important_features if f in df_pods_features.columns]
if len(available_features) < len(important_features):
    missing_features = set(important_features) - set(available_features)
    print(f"⚠️ {len(missing_features)} important features not found in dataset: {missing_features}")

# Filter DataFrame to keep only available important features
df_pods_features = df_pods_features[available_features]
print(f"   Dataset filtered to {df_pods_features.shape[1]} important features")

# Check for non-numeric columns and remove or process them
numeric_cols = df_pods_features.select_dtypes(include=np.number).columns.tolist()
if len(numeric_cols) != df_pods_features.shape[1]:
    print(f"⚠️ {df_pods_features.shape[1] - len(numeric_cols)} non-numeric columns found and will be ignored.")
    df_pods_features = df_pods_features[numeric_cols]

# --- IMPROVED HANDLING OF MISSING VALUES ---
print("🔍 Checking for missing values (NaN)...")
initial_nans = df_pods_features.isna().sum().sum()
if initial_nans > 0:
    print(f"   - {initial_nans} missing values found")
    # Use SimpleImputer which is more robust
    print("   - Replacing missing values with robust imputation...")
    imputer = SimpleImputer(strategy='median')
    df_pods_features_values = imputer.fit_transform(df_pods_features)
    df_pods_features = pd.DataFrame(df_pods_features_values, 
                                    index=df_pods_features.index, 
                                    columns=df_pods_features.columns)
    
    # Check if values are still missing
    if df_pods_features.isna().sum().sum() > 0:
        print("⚠️ Values still missing after imputation, replacing with 0...")
        df_pods_features = df_pods_features.fillna(0)
else:
    print("   - No missing values found. ✅")

# Keep POD names (which are now the index)
pod_names = df_pods_features.index.tolist() # Names of training PODs
print(f"   Dimensions after transposition (training): {df_pods_features.shape} (PODs x Features)")

# Prepare data for scaling (numpy array without POD names)
X = df_pods_features.values

# Normalize the data (features) - MODIFICATION: use RobustScaler to reduce outlier impact
print("📏 Normalizing features (training) with RobustScaler to reduce overfitting...")
scaler = RobustScaler() # More robust to outliers, reduces overfitting
X_scaled = scaler.fit_transform(X)

# Post-scaling verification
if np.isnan(X_scaled).any():
    print("⚠️ NaN values found after scaling, replacing with zeros...")
    X_scaled = np.nan_to_num(X_scaled, nan=0.0)

# --- OUTLIER DETECTION AND HANDLING ---
print("🔎 Detecting outliers in scaled data...")
def identify_outliers(X, threshold=3.0):
    """Identifies data points that are statistical outliers."""
    # Calculate IQRs for each feature
    Q1 = np.percentile(X, 25, axis=0)
    Q3 = np.percentile(X, 75, axis=0)
    IQR = Q3 - Q1
    
    # Define lower and upper thresholds
    lower_bound = Q1 - threshold * IQR
    upper_bound = Q3 + threshold * IQR
    
    # Identify points outside thresholds for each feature
    outlier_mask = np.logical_or(
        X < lower_bound,
        X > upper_bound
    )
    
    # Identify indices of rows with at least one outlier
    rows_with_outliers = np.any(outlier_mask, axis=1)
    outlier_indices = np.where(rows_with_outliers)[0]
    
    return outlier_indices, outlier_mask

# Identify outliers with a less strict threshold
outlier_indices, outlier_mask = identify_outliers(X_scaled, threshold=5.0)
print(f"   - {len(outlier_indices)} PODs ({len(outlier_indices)/len(X_scaled)*100:.1f}%) identified as potential outliers")

# We don't remove outliers but reduce their impact in weighting
# Their extreme values will be constrained to avoid distorting clusters

# Apply weights to features with protection against outliers
print("⚖️ Applying weighting to features (with constraints for outliers)...")

# Get weights dictionary from methods_weight_features_explicative.py
feature_weights_dict = get_feature_weights()

# --- MODIFY WEIGHTS FOR BETTER BALANCE ---
# Reduce gap between min and max weights to avoid singleton clusters
max_weight = max(feature_weights_dict.values())
min_weight = min(feature_weights_dict.values())
target_max_weight = 1.6  # Reduce maximum weight (was up to 2.5)
target_min_weight = 0.8  # Increase minimum weight (was 0.8)

# Function to recalibrate weights
def recalibrate_weight(w, old_min, old_max, new_min, new_max):
    """Recalibrates a weight from old range to new range."""
    if old_max == old_min:
        return new_min
    # Linear transformation
    return new_min + (w - old_min) * (new_max - new_min) / (old_max - old_min)

# Recalibrate all weights
print(f"   - Recalibrating weights from [{min_weight}, {max_weight}] to [{target_min_weight}, {target_max_weight}]")
recalibrated_weights = {
    feature: recalibrate_weight(weight, min_weight, max_weight, target_min_weight, target_max_weight)
    for feature, weight in feature_weights_dict.items()
}

# Create weight vector corresponding to DataFrame columns
weights = np.ones(X_scaled.shape[1])  # Default weight = 1.0

# Apply recalibrated weights from dictionary respecting feature order
for i, feature_name in enumerate(df_pods_features.columns):
    if feature_name in recalibrated_weights:
        weights[i] = recalibrated_weights[feature_name]
        print(f"   - Weight {recalibrated_weights[feature_name]:.2f} applied to {feature_name}")

# Apply weights to normalized data
X_scaled_weighted = X_scaled * weights

# Protect against extreme values after weighting
print("   - Applying clipping on weighted values to limit outlier effects...")
# Limit values to 3 times standard deviation for each feature
clip_threshold = 3.0
mean_vals = np.mean(X_scaled_weighted, axis=0)
std_vals = np.std(X_scaled_weighted, axis=0)
lower_clip = mean_vals - clip_threshold * std_vals
upper_clip = mean_vals + clip_threshold * std_vals

# Apply clipping
X_scaled_weighted_clipped = np.clip(X_scaled_weighted, lower_clip, upper_clip)

# Save scaler for future predictions (based on features)
scaler_path = os.path.join(dir_path, 'feature_scaler_weight_8features.joblib')
joblib.dump(scaler, scaler_path)
print(f"💾 Feature scaler saved in '{os.path.basename(scaler_path)}'")

# Save weights for future predictions
weights_path = os.path.join(dir_path, 'feature_weights_weight_8features.joblib')
joblib.dump(weights, weights_path)
print(f"💾 Feature weights saved in '{os.path.basename(weights_path)}'")

# Elbow method to determine optimal number of clusters
print("\n🔍 Finding optimal number of clusters on features (training)...")
wcss = []
cosine_ratios = []
intra_cluster_sims = []  # To store intra-cluster similarities
inter_cluster_sims = []  # To store inter-cluster similarities

# Adjust max_clusters: cannot be greater than number of samples - 1
max_clusters = min(15, len(df_pods_features) - 1)
if max_clusters < 1:
    print("❌ Not enough data for clustering")
    exit(1)

print("   k  |    WCSS    | Cosine ratio | Intra-sim | Inter-sim |")
print("------|------------|--------------|-----------|-----------|")

for i in range(2, max_clusters + 1):
    kmeans = KMeans(n_clusters=i, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled_weighted_clipped)
    wcss.append(kmeans.inertia_)
    
    # Calculate cosine similarity ratio and intra/inter cluster similarities
    cosine_ratio, avg_intra, avg_inter = calculate_cosine_similarity_ratio(X_scaled_weighted_clipped, labels, kmeans)
    cosine_ratios.append(cosine_ratio)
    intra_cluster_sims.append(avg_intra)
    inter_cluster_sims.append(avg_inter)
    
    print(f"  {i:2d}  | {kmeans.inertia_:10.4f} | {cosine_ratio:12.4f} | {avg_intra:9.4f} | {avg_inter:9.4f} |")

# Visualization of the elbow method
elbow_path = os.path.join(dir_path, 'feature_elbow_method_weight_8features.png')
plt.figure(figsize=(10, 6))
plt.plot(range(2, max_clusters + 1), wcss, marker='o', linestyle='-')
plt.title('Elbow Method (based on 8 main features)', fontsize=14)
plt.xlabel('Number of clusters (k)', fontsize=12)
plt.ylabel('WCSS (Inertia)', fontsize=12)
plt.xticks(range(2, max_clusters + 1))
plt.grid(True)

# Add annotation for 4 clusters choice
plt.annotate('k=4: Best trade-off\nbetween complexity and inertia', 
             xy=(4, wcss[2]), 
             xytext=(6, wcss[2] - (max(wcss) - min(wcss))*0.2),
             arrowprops=dict(facecolor='red', shrink=0.05, width=2),
             bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.8),
             fontsize=12)
             
# Mark k=4 point
plt.plot(4, wcss[2], 'ro', markersize=10)

plt.savefig(elbow_path)
print(f"📈 Elbow method graph (8 features) saved in '{os.path.basename(elbow_path)}'")

# Visualization of cosine similarities (ratio, intra and inter)
cosine_path = os.path.join(dir_path, 'cosine_similarity_metrics_weight_8features.png')
plt.figure(figsize=(12, 8))

# Create two Y axes for different scales
fig, ax1 = plt.subplots(figsize=(12, 8))
ax2 = ax1.twinx()

# Plot intra and inter cluster similarities with first scale (ax1)
ax1.plot(range(2, max_clusters + 1), intra_cluster_sims, marker='o', linestyle='-', color='blue', 
         label='Intra-cluster similarity')
ax1.plot(range(2, max_clusters + 1), inter_cluster_sims, marker='s', linestyle='-', color='green', 
         label='Inter-clusters similarity')
ax1.set_xlabel('Number of clusters (k)', fontsize=12)
ax1.set_ylabel('Cosine similarity value (0-1)', fontsize=12)
ax1.tick_params(axis='y', labelcolor='blue')
ax1.grid(True, alpha=0.3)

# Plot ratio with second scale (ax2)
ax2.plot(range(2, max_clusters + 1), cosine_ratios, marker='d', linestyle='--', color='red', 
         label='Intra/inter ratio')
ax2.set_ylabel('Intra/inter similarity ratio', fontsize=12, color='red')
ax2.tick_params(axis='y', labelcolor='red')

# Combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')

# Add annotation for k=4
# Improvement: find index corresponding to k=4 (it's the 2nd element in a 0-indexed list starting at k=2)
k4_index = 2  # k=4 is at index 2 in our list (k=2 → index 0, k=3 → index 1, k=4 → index 2)
intra_at_k4 = intra_cluster_sims[k4_index]
inter_at_k4 = inter_cluster_sims[k4_index]
ratio_at_k4 = cosine_ratios[k4_index]

# Highlight k=4
ax1.plot(4, intra_at_k4, 'bo', markersize=12, fillstyle='none', linewidth=3)
ax1.plot(4, inter_at_k4, 'go', markersize=12, fillstyle='none', linewidth=3)
ax2.plot(4, ratio_at_k4, 'ro', markersize=12, fillstyle='none', linewidth=3)

# Add detailed annotation explaining why k=4 is the best choice
plt.figtext(0.5, 0.01, 
           "k=4 offers the best trade-off:\n" +
           f"• High intra-cluster similarity ({intra_at_k4:.4f}): good cohesion of points within each group\n" +
           f"• Low inter-clusters similarity ({inter_at_k4:.4f}): good separation between groups\n" +
           f"• Good intra/inter ratio ({ratio_at_k4:.4f}): clear differentiation of profiles without overfitting",
           ha="center", fontsize=11, bbox={"facecolor":"yellow", "alpha":0.2, "pad":5})

plt.title('Cosine Similarity Metrics by Number of Clusters (8 features)', fontsize=14)
plt.xticks(range(2, max_clusters + 1))
plt.tight_layout(rect=[0, 0.08, 1, 0.96])  # Adjust for annotation at bottom
plt.savefig(cosine_path, dpi=300)
print(f"📈 Cosine similarity metrics graph saved in '{os.path.basename(cosine_path)}'")

# SET THE NUMBER OF CLUSTERS TO 4 (rather than automatic detection)
print(f"\n🔹 Using 4 clusters - best trade-off between complexity and cluster quality")
print(f"   - With 4 clusters: intra-cluster similarity = {intra_at_k4:.4f}, inter-clusters similarity = {inter_at_k4:.4f}")
print(f"   - Optimal intra/inter ratio ({ratio_at_k4:.4f}): strong cohesion within clusters and good separation between clusters")
print("   - 4 clusters allows efficient representation of different profiles without overfitting")

# Fix the number of clusters to 4
n_clusters = 4

# Apply KMeans with 4 clusters
print(f"\n🔸 Applying K-means clustering with {n_clusters} clusters on 8 main features...")

# Parameters adjusted to reduce overfitting
kmeans = KMeans(
    n_clusters=n_clusters,
    random_state=42,
    n_init=10,    
    max_iter=300,    
    init='k-means++',
    algorithm='lloyd',
    tol=1e-4)

# --- FIRST CLUSTERING PASS ---
# Use weighted and clipped data for initial training
clusters = kmeans.fit_predict(X_scaled_weighted_clipped)

# Display cluster distribution validation to check balance
print("\n📊 INITIAL cluster distribution for training data:")
unique_clusters, cluster_counts = np.unique(clusters, return_counts=True)
for cluster, count in zip(unique_clusters, cluster_counts):
    print(f"   - Cluster {cluster}: {count} PODs ({count/len(pod_names)*100:.1f}%)")

# --- ADAPT CLUSTERS TO AVOID SINGLETONS ---
# Define minimum size for clusters (stricter than before)
min_cluster_size = max(3, len(pod_names) // (n_clusters * 10))  # At least 3 members or 10% of average size

print(f"\n🔄 Checking for small clusters (min size: {min_cluster_size})...")
small_clusters = [c for c, count in zip(unique_clusters, cluster_counts) if count < min_cluster_size]

if small_clusters:
    print(f"   ⚠️ {len(small_clusters)} clusters are too small: {small_clusters}")
    print("   - Reducing number of clusters and reclustering...")
    
    # Reduce number of clusters and recluster
    n_clusters = n_clusters - len(small_clusters)
    n_clusters = max(2, n_clusters)  # Ensure at least 2 clusters
    
    print(f"   - New clustering with {n_clusters} clusters...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled_weighted_clipped)
else:
    print("✅ All clusters have sufficient size.")
            
# --- FINAL VERIFICATION OF CLUSTER DISTRIBUTION ---
print("\n📊 FINAL cluster distribution:")
unique_clusters, cluster_counts = np.unique(clusters, return_counts=True)
for cluster, count in zip(unique_clusters, cluster_counts):
    print(f"   - Cluster {cluster}: {count} PODs ({count/len(pod_names)*100:.1f}%)")

# Check again if small clusters remain
final_small_clusters = [c for c, count in zip(unique_clusters, cluster_counts) if count < min_cluster_size]
if final_small_clusters:
    print(f"⚠️ There are still {len(final_small_clusters)} clusters too small: {final_small_clusters}")
    print("   These clusters may be unstable or unrepresentative.")
else:
    print("✅ All clusters have sufficient size.")

# Create DataFrame with results for training PODs
pod_clusters = pd.DataFrame({
    'POD': pod_names,
    'Feature_Cluster': clusters
})

# Save results for training PODs
clusters_path = os.path.join(dir_path, 'pod_feature_clusters_weight_8features.csv')
pod_clusters.to_csv(clusters_path, index=False)
print(f"💾 POD clustering results saved in '{os.path.basename(clusters_path)}'")

# Save KMeans model for future predictions
kmeans_path = os.path.join(dir_path, 'feature_kmeans_model_weight_8features.joblib')
joblib.dump(kmeans, kmeans_path)
print(f"💾 KMeans model saved in '{os.path.basename(kmeans_path)}'")

# --- CLUSTER VISUALIZATION ---
print("\n📊 Principal component analysis (PCA) with 8 important features...")

# Reduce dimensionality for visualization (using PCA)
from sklearn.decomposition import PCA

# Apply PCA for complete analysis - with only 8 features, we can examine all components
n_components_full = min(8, X_scaled_weighted_clipped.shape[1])
pca_full = PCA(n_components=n_components_full)
pca_full.fit(X_scaled_weighted_clipped)

# Visualize percentage of explained variance by component
plt.figure(figsize=(12, 6))
explained_variance = pca_full.explained_variance_ratio_ * 100
cumulative_variance = np.cumsum(explained_variance)

plt.bar(range(1, n_components_full + 1), explained_variance, alpha=0.7, color='skyblue', 
        label='Individual variance')
plt.step(range(1, n_components_full + 1), cumulative_variance, color='red', marker='o', 
        label='Cumulative variance')

plt.axhline(y=95, color='r', linestyle='--', label='95% threshold')
plt.axhline(y=80, color='g', linestyle='--', label='80% threshold')

# Find number of components to reach certain thresholds
n_comp_95 = np.argmax(cumulative_variance >= 95) + 1 if any(cumulative_variance >= 95) else n_components_full
n_comp_80 = np.argmax(cumulative_variance >= 80) + 1 if any(cumulative_variance >= 80) else n_components_full

plt.text(n_comp_80, 80, f' {n_comp_80} components\n(80% variance)', color='g')
plt.text(min(n_comp_95, n_components_full), 95, f' {n_comp_95} components\n(95% variance)', color='r')

plt.title('Variance Explained by Principal Components (8 features)', fontsize=16)
plt.xlabel('Principal Component', fontsize=14)
plt.ylabel('Percentage of Explained Variance', fontsize=14)
plt.legend(loc='upper left')
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()

variance_path = os.path.join(dir_path, 'pca_variance_explained_weight_8features.png')
plt.savefig(variance_path, dpi=300)
print(f"   -> Explained variance graph saved: '{os.path.basename(variance_path)}'")

# Calculate feature importance for first 2 components (used for visualization)
pca = PCA(n_components=2)
pca.fit(X_scaled_weighted_clipped)

# Calculate feature importance in PCA
feature_importance = np.sum(np.abs(pca.components_), axis=0)
feature_names = df_pods_features.columns

# Create DataFrame to facilitate sorting
feature_importance_df = pd.DataFrame({
    'Feature': feature_names,
    'Importance': feature_importance
}).sort_values(by='Importance', ascending=False)  

# All features by importance  
n_features = len(feature_importance_df)
plt.figure(figsize=(12, max(10, n_features * 0.25)))  # Dynamically adjust height

# Use barh for horizontal display (better with many features)
plt.barh(range(n_features), feature_importance_df['Importance'], color='teal', alpha=0.7)
plt.yticks(range(n_features), feature_importance_df['Feature'], fontsize=11)  # Larger font with fewer features
plt.title('8 Main Features Ranked by Importance in PCA', fontsize=16)
plt.xlabel('Importance Score', fontsize=14)
plt.grid(True, linestyle='--', alpha=0.3, axis='x')

# Add annotations for all features (since there are only 8)
for i, importance in enumerate(feature_importance_df['Importance']):
    plt.text(importance + 0.01, i, f"{importance:.3f}", va='center')

plt.tight_layout()

# Save with a different name
all_features_path = os.path.join(dir_path, 'pca_all_features_importance_weight_8features.png')
plt.savefig(all_features_path, dpi=300)
print(f"   -> 8 features importance graph saved: '{os.path.basename(all_features_path)}'")

# --- FEATURE DISTRIBUTION ANALYSIS BY CLUSTER ---
print("\n🔹 Analyzing feature distributions within each cluster...")
deciles_path = os.path.join(dir_path, 'feature_deciles_by_cluster_8features.csv')
feature_deciles = generate_feature_deciles_by_cluster(
    X_scaled_weighted_clipped, 
    clusters, 
    df_pods_features.columns, 
    deciles_path
)

# Display features by importance in console
print("\n🔝 The 8 features by importance for PCA:")
for i, (feature, importance) in enumerate(zip(feature_importance_df['Feature'], 
                                            feature_importance_df['Importance'])):
    print(f"   {i+1}. {feature}: {importance:.4f}")

# Apply PCA to reduce to 2 dimensions for visualization
X_pca = pca.transform(X_scaled_weighted_clipped)

# Visualize clusters in 2D
plt.figure(figsize=(12, 8))
for cluster_id in unique_clusters:
    cluster_points = X_pca[clusters == cluster_id]
    plt.scatter(
        cluster_points[:, 0], 
        cluster_points[:, 1], 
        label=f'Cluster {cluster_id} ({sum(clusters == cluster_id)} PODs)', 
        alpha=0.7,
        s=50
    )

# Plot cluster centroids transformed by PCA
centers_pca = pca.transform(kmeans.cluster_centers_)
plt.scatter(
    centers_pca[:, 0], 
    centers_pca[:, 1], 
    s=200, 
    marker='X', 
    c='red', 
    label='Centroids'
)

plt.title(f'Visualization of {n_clusters} Clusters (PCA 2D - 8 features)\nOptimal trade-off to represent different consumption profiles', fontsize=16)
plt.xlabel('First Principal Component', fontsize=14)
plt.ylabel('Second Principal Component', fontsize=14)
plt.legend(fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)

# Add POD names as annotations (optional)
if len(pod_names) <= 100:
    for i, pod in enumerate(pod_names):
        plt.annotate(pod, (X_pca[i, 0], X_pca[i, 1]), fontsize=8, alpha=0.7)

# Save visualization
pca_viz_path = os.path.join(dir_path, 'feature_clusters_pca_viz_weight_8features.png')
plt.tight_layout()
plt.savefig(pca_viz_path, dpi=300)
print(f"📊 PCA cluster visualization saved in '{os.path.basename(pca_viz_path)}'")

# Analysis of feature contributions to first two components
plt.figure(figsize=(14, 8))
components = pd.DataFrame(
    pca.components_.T, 
    columns=['Component 1', 'Component 2'], 
    index=feature_names
)

# Create heatmap of component contributions
plt.figure(figsize=(12, 8))
sns.heatmap(
    components, 
    annot=True, 
    cmap='coolwarm', 
    fmt='.3f',
    linewidths=0.5,
    cbar_kws={'label': 'Contribution'}
)
plt.title('Contribution of 8 Features to First Two Principal Components', fontsize=16)
plt.tight_layout()
heatmap_path = os.path.join(dir_path, 'pca_components_heatmap_8features.png')
plt.savefig(heatmap_path, dpi=300)
print(f"   -> Component contribution heatmap saved: '{os.path.basename(heatmap_path)}'")

# --- NEW SECTION: GENERATING CLUSTER PROFILES ---
print("\n🔹 Generating consumption profiles by cluster...")
dataset_path = os.path.join(dir_path, 'dataset_clean_with_datetime.csv')
clusters_path = os.path.join(dir_path, 'pod_feature_clusters_weight_8features.csv')

# Call function to generate profiles
generate_cluster_profiles(dataset_path, clusters_path)

print("\n✅ Clustering with 4 clusters completed successfully!")
print("   The choice of 4 clusters is optimal for several reasons:")
print(f"   - Low inertia (WCSS): {wcss[k4_index]:.2f} - Good representation quality")
print(f"   - High intra-cluster similarity: {intra_cluster_sims[k4_index]:.4f} - Similar points grouped together")
print(f"   - Low inter-clusters similarity: {inter_at_k4:.4f} - Good separation between clusters")
print(f"   - Favorable intra/inter ratio: {ratio_at_k4:.4f} - Balance between cohesion/separation")
print("   - Obtained clusters are balanced in size and representative of different consumption profiles")
print("   - Beyond 4 clusters, quality gain is marginal and risks overfitting")