import pandas as pd
import os
import numpy as np
from datetime import datetime


# Ce fichier sur les collèges ainsi que les CSVs présents dans le dossier  
# data/csv_college ne sont pas utilisés pour l'affichage sur l'application  
# mais le code est gardé pour une amélioration future et une prochaine itération du projet

def load_college_data(file_path="Consommateurs_communaux_collège.xlsx"):
    """
    Load and process college consumption data from Excel file,
    downsampling from 15-min to hourly intervals
    
    Parameters:
    -----------
    file_path : str
        Path to the Excel file
        
    Returns:
    --------
    buildings_df : DataFrame
        Information about buildings
    consumption_df : DataFrame
        Hourly consumption data with datetime index
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier {file_path} n'a pas été trouvé.")
        
    print(f"Chargement des données depuis {file_path}...")
    
    # Load sheets from Excel file
    buildings_df = pd.read_excel(file_path, sheet_name="Bâtiments")
    curves_df = pd.read_excel(file_path, sheet_name="Courbes de charge")
    
    # Process buildings data
    print(f"Données de bâtiments chargées: {len(buildings_df)} bâtiments")
    
    # Process consumption data
    # Convert Date column to datetime
    curves_df['Date'] = pd.to_datetime(curves_df['Date'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    
    # Set Date as index
    curves_df = curves_df.set_index('Date')
    
    # Rename columns to match building references if needed
    ref_map = {ref: ref for ref in buildings_df['Référence'] if ref in curves_df.columns}
    curves_df = curves_df.rename(columns=ref_map)
    
    # Downsample from 15-min to hourly data by taking mean within each hour
    print("Downsampling des données de 15 min à 1 heure...")
    consumption_df = curves_df.resample('H').mean()
    
    # Add year, month, day, hour columns for easier analysis
    consumption_df['Year'] = consumption_df.index.year
    consumption_df['Month'] = consumption_df.index.month
    consumption_df['Day'] = consumption_df.index.day
    consumption_df['Hour'] = consumption_df.index.hour
    consumption_df['Weekday'] = consumption_df.index.weekday
    
    # Replace any negative values with zero (if applicable)
    for col in consumption_df.columns:
        if consumption_df[col].dtype in [np.float64, np.int64]:
            consumption_df[col] = consumption_df[col].clip(lower=0)
    
    print(f"Données de consommation chargées et traitées: {len(consumption_df)} relevés horaires sur {len(consumption_df.columns) - 5} bâtiments")
    
    return buildings_df, consumption_df

def process_specific_building(buildings_df, consumption_df, reference):
    """
    Extract data for a specific building reference
    
    Parameters:
    -----------
    buildings_df : DataFrame
        Buildings information
    consumption_df : DataFrame
        Consumption data
    reference : str
        Building reference to extract
        
    Returns:
    --------
    building_info : Series
        Information about the building
    building_consumption : DataFrame
        Consumption data for the building
    """
    if reference not in buildings_df['Référence'].values:
        raise ValueError(f"Référence '{reference}' non trouvée dans les données des bâtiments")
        
    if reference not in consumption_df.columns:
        raise ValueError(f"Données de consommation pour '{reference}' non trouvées")
        
    building_info = buildings_df[buildings_df['Référence'] == reference].iloc[0]
    
    # Extract consumption for this building and metadata columns
    building_consumption = consumption_df[[reference, 'Year', 'Month', 'Day', 'Hour', 'Weekday']].copy()
    
    # Rename the consumption column to a standard name
    building_consumption = building_consumption.rename(columns={reference: 'Consumption (kWh)'})
    
    return building_info, building_consumption

def calculate_mean_hourly_load(consumption_df):
    """
    Calculate mean hourly load for each building reference, per year and overall
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Consumption data with datetime index
        
    Returns:
    --------
    hourly_by_year : dict of DataFrames
        Mean hourly load for each building, by year
    hourly_overall : DataFrame
        Overall mean hourly load for each building
    """
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in consumption_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Calculate mean hourly load by year
    hourly_by_year = {}
    for year in consumption_df['Year'].unique():
        yearly_data = consumption_df[consumption_df['Year'] == year]
        
        # For each hour (0-23) calculate mean for each building
        hourly_means = []
        for hour in range(24):
            hour_data = yearly_data[yearly_data['Hour'] == hour]
            means = {building: hour_data[building].mean() for building in buildings}
            means['Hour'] = hour
            hourly_means.append(means)
            
        hourly_by_year[year] = pd.DataFrame(hourly_means).set_index('Hour')
    
    # Calculate overall mean hourly load (across all years)
    overall_hourly_means = []
    for hour in range(24):
        hour_data = consumption_df[consumption_df['Hour'] == hour]
        means = {building: hour_data[building].mean() for building in buildings}
        means['Hour'] = hour
        overall_hourly_means.append(means)
    
    hourly_overall = pd.DataFrame(overall_hourly_means).set_index('Hour')
    
    return hourly_by_year, hourly_overall

def calculate_load_curve_percentiles(consumption_df):
    """
    Calculate mean, 25th percentile and 75th percentile load curves
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Downsampled hourly consumption data
        
    Returns:
    --------
    percentiles : DataFrame
        DataFrame with mean, 25th, and 75th percentile load curves for all buildings
    """
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in consumption_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Create DataFrames to store results
    mean_curves = pd.DataFrame(index=range(24))
    p25_curves = pd.DataFrame(index=range(24))
    p75_curves = pd.DataFrame(index=range(24))
    
    for building in buildings:
        # For each hour (0-23), calculate statistics
        mean_values = []
        p25_values = []
        p75_values = []
        
        for hour in range(24):
            hour_data = consumption_df[consumption_df['Hour'] == hour][building]
            
            mean_values.append(hour_data.mean())
            p25_values.append(hour_data.quantile(0.25))
            p75_values.append(hour_data.quantile(0.75))
        
        # Add to DataFrames
        mean_curves[building] = mean_values
        p25_curves[building] = p25_values
        p75_curves[building] = p75_values
    
    return {
        'mean': mean_curves,
        '25th_percentile': p25_curves,
        '75th_percentile': p75_curves
    }

def save_analysis_to_csv(hourly_by_year, hourly_overall, percentiles, output_dir="csv_college"):
    """
    Save analysis results to CSV files
    
    Parameters:
    -----------
    hourly_by_year : dict of DataFrames
        Mean hourly load for each building, by year
    hourly_overall : DataFrame
        Overall mean hourly load for each building
    percentiles : dict of DataFrames
        Load curve percentiles for each building
    output_dir : str
        Output directory path
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save yearly hourly means
    for year, df in hourly_by_year.items():
        df.to_csv(os.path.join(output_dir, f"mean_hourly_load_{year}.csv"))
    
    # Save overall hourly mean
    hourly_overall.to_csv(os.path.join(output_dir, "mean_hourly_load_overall.csv"))
    
    # Save percentiles for each building
    for building, df in percentiles.items():
        # Replace any problematic characters in building reference for filename
        safe_name = building.replace("/", "_").replace("\\", "_")
        df.to_csv(os.path.join(output_dir, f"load_curve_percentiles_{safe_name}.csv"))
    
    # Create consolidated files for all buildings
    # Mean for all buildings
    mean_data = pd.DataFrame({building: df['mean'] for building, df in percentiles.items()})
    mean_data.to_csv(os.path.join(output_dir, "all_buildings_mean_load.csv"))
    
    # 25th percentile for all buildings
    p25_data = pd.DataFrame({building: df['25th_percentile'] for building, df in percentiles.items()})
    p25_data.to_csv(os.path.join(output_dir, "all_buildings_25th_percentile.csv"))
    
    # 75th percentile for all buildings
    p75_data = pd.DataFrame({building: df['75th_percentile'] for building, df in percentiles.items()})
    p75_data.to_csv(os.path.join(output_dir, "all_buildings_75th_percentile.csv"))

def save_load_curves_to_csv(load_curves, output_dir="csv_college"):
    """
    Save load curve analyses to CSV files
    
    Parameters:
    -----------
    load_curves : dict
        Dictionary containing mean, 25th, and 75th percentile DataFrames
    output_dir : str
        Output directory path
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save each curve type
    load_curves['mean'].to_csv(os.path.join(output_dir, "mean_load_curves.csv"))
    load_curves['25th_percentile'].to_csv(os.path.join(output_dir, "25th_percentile_load_curves.csv"))
    load_curves['75th_percentile'].to_csv(os.path.join(output_dir, "75th_percentile_load_curves.csv"))
    
    print(f"Courbes de charge enregistrées dans le dossier {output_dir}")

def calculate_datetime_load_curves(consumption_df):
    """
    Calculate mean, 25th and 75th percentile load curves across all buildings for each timestamp
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Consumption data with datetime index
        
    Returns:
    --------
    load_curves_df : DataFrame
        DataFrame with datetime index and mean, 25th, 75th percentile columns
    """
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in consumption_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Create a DataFrame with datetime index for results
    result_df = pd.DataFrame(index=consumption_df.index)
    
    # For each timestamp, calculate statistics across all buildings
    print("Calcul des courbes de charge pour chaque horodatage...")
    
    # Select only building columns for calculations
    buildings_data = consumption_df[buildings]
    
    # Calculate statistics across rows (axis=1)
    result_df['mean_load'] = buildings_data.mean(axis=1)
    result_df['25th_percentile'] = buildings_data.quantile(0.25, axis=1)
    result_df['75th_percentile'] = buildings_data.quantile(0.75, axis=1)
    
    # Keep the datetime-related columns
    for col in ['Year', 'Month', 'Day', 'Hour', 'Weekday']:
        result_df[col] = consumption_df[col]
    
    return result_df

def save_datetime_load_curves(load_curves_df, output_dir="csv_college"):
    """
    Save datetime-based load curves to CSV file
    
    Parameters:
    -----------
    load_curves_df : DataFrame
        DataFrame with datetime index and load curve statistics
    output_dir : str
        Output directory path
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to CSV
    output_file = os.path.join(output_dir, "datetime_load_curves.csv")
    load_curves_df.to_csv(output_file)
    
    print(f"Courbes de charge par horodatage enregistrées dans {output_file}")

def calculate_yearly_hourly_stats(consumption_df):
    """
    Calculate mean, 25th and 75th percentile hourly power for all buildings combined,
    broken down by year
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Consumption data with datetime index
        
    Returns:
    --------
    yearly_stats : dict
        Dictionary with year as key and DataFrame with hourly stats as value
    """
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in consumption_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Create a dictionary to store results for each year
    yearly_stats = {}
    
    print("Calcul des statistiques horaires par année...")
    
    # Process each year
    for year in consumption_df['Year'].unique():
        # Filter data for current year
        yearly_data = consumption_df[consumption_df['Year'] == year]
        
        # Create DataFrame to store statistics for this year
        stats_df = pd.DataFrame(index=range(24), 
                               columns=['mean_power', '25th_percentile', '75th_percentile'])
        
        # For each hour of the day
        for hour in range(24):
            # Filter data for current hour
            hourly_data = yearly_data[yearly_data['Hour'] == hour]
            
            if len(hourly_data) > 0:
                # Calculate total power across all buildings for each timestamp
                hourly_data['total_power'] = hourly_data[buildings].sum(axis=1)
                
                # Calculate statistics
                stats_df.loc[hour, 'mean_power'] = hourly_data['total_power'].mean()
                stats_df.loc[hour, '25th_percentile'] = hourly_data['total_power'].quantile(0.25)
                stats_df.loc[hour, '75th_percentile'] = hourly_data['total_power'].quantile(0.75)
        
        # Store results for this year
        yearly_stats[year] = stats_df
    
    return yearly_stats

def save_yearly_hourly_stats(yearly_stats, output_dir="csv_college"):
    """
    Save yearly hourly statistics to CSV files
    
    Parameters:
    -----------
    yearly_stats : dict
        Dictionary with year as key and DataFrame with hourly stats as value
    output_dir : str
        Output directory path
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save statistics for each year
    for year, df in yearly_stats.items():
        output_file = os.path.join(output_dir, f"hourly_power_stats_{year}.csv")
        df.to_csv(output_file)
    
    print(f"Statistiques horaires par année enregistrées dans le dossier {output_dir}")

def calculate_daily_period_stats(consumption_df):
    """
    Calculate mean, 25th and 75th percentile power for combined periods of the day
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Consumption data with datetime index
        
    Returns:
    --------
    period_stats : DataFrame
        DataFrame with statistics for each period of the day
    """
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in consumption_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Define periods of the day
    periods = {
        'Nuit (0h-6h)': range(0, 6),
        'Matin (6h-12h)': range(6, 12),
        'Après-midi (12h-18h)': range(12, 18),
        'Soirée (18h-24h)': range(18, 24)
    }
    
    # Create DataFrame to store results
    period_stats = pd.DataFrame(
        columns=['period', 'mean_power', '25th_percentile', '75th_percentile']
    )
    
    print("Calcul des statistiques par période de la journée...")
    
    # Calculate statistics for each period
    for period_name, hours in periods.items():
        # Filter data for hours in this period
        period_data = consumption_df[consumption_df['Hour'].isin(hours)]
        
        if len(period_data) > 0:
            # Calculate total power across all buildings for each timestamp
            period_data['total_power'] = period_data[buildings].sum(axis=1)
            
            # Calculate statistics
            period_stats.loc[len(period_stats)] = [
                period_name,
                period_data['total_power'].mean(),
                period_data['total_power'].quantile(0.25),
                period_data['total_power'].quantile(0.75)
            ]
    
    # Calculate overall daily statistics
    all_data = consumption_df.copy()
    all_data['total_power'] = all_data[buildings].sum(axis=1)
    
    period_stats.loc[len(period_stats)] = [
        'Journée entière',
        all_data['total_power'].mean(),
        all_data['total_power'].quantile(0.25),
        all_data['total_power'].quantile(0.75)
    ]
    
    return period_stats.set_index('period')

def calculate_yearly_daily_period_stats(consumption_df):
    """
    Calculate mean, 25th and 75th percentile power for combined periods of the day,
    broken down by year
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Consumption data with datetime index
        
    Returns:
    --------
    yearly_period_stats : dict
        Dictionary with year as key and DataFrame with period stats as value
    """
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in consumption_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Define periods of the day
    periods = {
        'Nuit (0h-6h)': range(0, 6),
        'Matin (6h-12h)': range(6, 12),
        'Après-midi (12h-18h)': range(12, 18),
        'Soirée (18h-24h)': range(18, 24)
    }
    
    # Create a dictionary to store results for each year
    yearly_period_stats = {}
    
    print("Calcul des statistiques par période de la journée et par année...")
    
    # Process each year
    for year in consumption_df['Year'].unique():
        # Filter data for current year
        yearly_data = consumption_df[consumption_df['Year'] == year]
        
        # Create DataFrame to store statistics for this year
        stats_df = pd.DataFrame(
            columns=['period', 'mean_power', '25th_percentile', '75th_percentile']
        )
        
        # Calculate statistics for each period
        for period_name, hours in periods.items():
            # Filter data for hours in this period
            period_data = yearly_data[yearly_data['Hour'].isin(hours)]
            
            if len(period_data) > 0:
                # Calculate total power across all buildings for each timestamp
                period_data['total_power'] = period_data[buildings].sum(axis=1)
                
                # Calculate statistics
                stats_df.loc[len(stats_df)] = [
                    period_name,
                    period_data['total_power'].mean(),
                    period_data['total_power'].quantile(0.25),
                    period_data['total_power'].quantile(0.75)
                ]
        
        # Calculate overall daily statistics for this year
        all_data = yearly_data.copy()
        all_data['total_power'] = all_data[buildings].sum(axis=1)
        
        stats_df.loc[len(stats_df)] = [
            'Journée entière',
            all_data['total_power'].mean(),
            all_data['total_power'].quantile(0.25),
            all_data['total_power'].quantile(0.75)
        ]
        
        # Store results for this year
        yearly_period_stats[year] = stats_df.set_index('period')
    
    return yearly_period_stats

def save_daily_period_stats(period_stats, yearly_period_stats, output_dir="csv_college"):
    """
    Save daily period statistics to CSV files
    
    Parameters:
    -----------
    period_stats : DataFrame
        Overall period statistics
    yearly_period_stats : dict
        Dictionary with year as key and DataFrame with period stats as value
    output_dir : str
        Output directory path
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save overall period statistics
    period_stats.to_csv(os.path.join(output_dir, "daily_period_stats_overall.csv"))
    
    # Save statistics for each year
    for year, df in yearly_period_stats.items():
        df.to_csv(os.path.join(output_dir, f"daily_period_stats_{year}.csv"))
    
    print(f"Statistiques par période de la journée enregistrées dans le dossier {output_dir}")

def normalize_consumption_by_surface(consumption_df, buildings_df):
    """
    Normalize consumption data by dividing each building's consumption by its surface area
    
    Parameters:
    -----------
    consumption_df : DataFrame
        Consumption data with datetime index
    buildings_df : DataFrame
        Buildings information with 'Référence' and 'surface' columns
        
    Returns:
    --------
    normalized_df : DataFrame
        Consumption data normalized by surface area (kWh/m²)
    """
    # Create a copy of consumption data
    normalized_df = consumption_df.copy()
    
    # Get list of all building references (excluding metadata columns)
    buildings = [col for col in normalized_df.columns if col not in ['Year', 'Month', 'Day', 'Hour', 'Weekday']]
    
    # Create surface mapping dictionary
    surface_map = {}
    for _, row in buildings_df.iterrows():
        reference = row['Référence']
        surface = row['Surface']
        if pd.notna(surface) and surface > 0:  # Only include valid surface values
            surface_map[reference] = surface
    
    # Normalize each building's consumption by its surface area
    for building in buildings:
        if building in surface_map:
            normalized_df[building] = normalized_df[building] / surface_map[building]
    
    return normalized_df

if __name__ == "__main__":
    try:
        buildings, consumption = load_college_data()
        
        # Show sample of the data
        print("\nAperçu des bâtiments:")
        print(buildings.head())
        
        print("\nAperçu des courbes de charge:")
        print(consumption.head())
        
        # Normalize consumption by surface area
        print("\nNormalisation des données de consommation par unité de surface (kWh/m²)...")
        normalized_consumption = normalize_consumption_by_surface(consumption, buildings)
        
        # Calculate statistics by period of day using normalized data
        print("\nCalcul des statistiques par période de la journée...")
        period_stats = calculate_daily_period_stats(normalized_consumption)
        yearly_period_stats = calculate_yearly_daily_period_stats(normalized_consumption)
        
        # Save results to CSV
        print("\nEnregistrement des résultats dans des fichiers CSV...")
        save_daily_period_stats(period_stats, yearly_period_stats)
        
        print(f"\nAnalyse terminée. Les résultats sont disponibles dans le dossier 'csv_college'")
        # Note: All consumption values now represent kWh/m²
        
    except Exception as e:
        print(f"Erreur: {e}")