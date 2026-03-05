"""
UTILITAIRE D'EXTRACTION DE DONNÉES POD POUR TESTS DE CLUSTERING

Ce fichier utilitaire fait partie de la phase de développement et de test du système de clustering
DataWatt. Il permet d'extraire des données spécifiques de Points de Distribution (POD) à partir
des datasets de consommation électrique pour valider et tester les algorithmes de clustering.

UTILITÉ POUR LE CLUSTERING:

1. EXTRACTION DE DONNÉES DE TEST:
   - Extraction ciblée de consommateurs spécifiques (POD) depuis les datasets CSV
   - Préparation de jeux de données individuels pour validation des algorithmes
   - Support des formats CSV et Excel pour analyse externe

2. VALIDATION DU PROCESSUS DE CLUSTERING:
   - Permet d'analyser en détail le comportement de consommateurs individuels
   - Facilite la vérification de l'assignation correcte aux clusters
   - Support pour l'analyse des caractéristiques calculées (features) sur des cas spécifiques

3. PHASE DE TESTS ET DÉVELOPPEMENT:
   - Outil de debug pour comprendre les profils de consommation individuels
   - Génération de fichiers de test pour validation des méthodes de clustering
   - Extraction rapide de données pour prototypage et expérimentation

FONCTIONNEMENT:
- Charge les datasets de consommation avec timestamps
- Extrait les données d'un POD spécifique (par défaut pod_01024)
- Génère des fichiers de sortie aux formats CSV et Excel
- Inclut la gestion d'erreurs et validation des données

STATUT: Phase de test et développement - Utilisé pour valider le système de clustering
avant déploiement en production dans l'application web DataWatt.
"""

import pandas as pd
import os

def extract_pod_data(file_path, pod_id="pod_01024"):
    """
    Extrait les données d'un POD spécifique à partir d'un fichier CSV.
    
    Args:
        file_path (str): Chemin vers le fichier CSV
        pod_id (str): Identifiant du POD à extraire
    
    Returns:
        tuple: (Series des données du POD, timestamps)
    """
    print(f"Tentative d'extraction du {pod_id} depuis {file_path}")
    
    try:
        # Vérifier si le fichier existe
        if not os.path.exists(file_path):
            print(f"Erreur: Le fichier {file_path} n'existe pas.")
            return None, None
        
        # Lire le fichier CSV
        df = pd.read_csv(file_path)
        print(f"Fichier chargé avec succès. Colonnes disponibles: {df.columns.tolist()}")
        
        # Vérifier si le POD existe dans les colonnes
        if pod_id not in df.columns:
            print(f"Erreur: Le {pod_id} n'est pas présent dans le fichier.")
            return None, None
        
        # Extraire les données du POD
        pod_data = df[pod_id].astype(float)
        
        # Extraire les timestamps si disponibles
        timestamps = None
        if 'Datetime' in df.columns:
            timestamps = pd.to_datetime(df['Datetime'])
            print(f"Timestamps extraits: {len(timestamps)} entrées")
        
        print(f"Données extraites: {len(pod_data)} entrées")
        return pod_data, timestamps
    
    except Exception as e:
        print(f"Une erreur est survenue lors de l'extraction: {e}")
        return None, None

if __name__ == "__main__":
    # Chemin vers le fichier - à modifier selon votre environnement
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "dataset_clean_with_datetime.csv")
    
    # Extraction des données
    pod_series, timestamps = extract_pod_data(file_path, "pod_01024")
    
    # Affichage des résultats
    if pod_series is not None:
        print("\nAperçu des données:")
        print(f"Premières valeurs: {pod_series.head().tolist()}")
        print(f"Statistiques: Min={pod_series.min():.2f}, Max={pod_series.max():.2f}, Moyenne={pod_series.mean():.2f}")
        
        # Préparer le DataFrame à sauvegarder
        if timestamps is not None:
            output_df = pd.DataFrame({"Datetime": timestamps, "Consumption (kWh)": pod_series})
        else:
            output_df = pd.DataFrame({"Consumption (kWh)": pod_series})
            
        # Sauvegarder en CSV
        csv_output_file = "pod_01024_data.csv"
        output_df.to_csv(csv_output_file, index=False)
        print(f"Données sauvegardées en CSV dans {csv_output_file}")
        
        # Sauvegarder en Excel (.xlsx)
        # Note: Nécessite le package openpyxl (pip install openpyxl)
        xlsx_output_file = "pod_01024_data.xlsx"
        output_df.to_excel(xlsx_output_file, index=False, sheet_name="POD Data")
        print(f"Données sauvegardées en Excel dans {xlsx_output_file}")