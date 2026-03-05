"""
=====================================================================================
                        GÉNÉRATEUR DE DONNÉES DE TEST CSV 
=====================================================================================
[FICHIER NON UTILISÉ DANS L'APPLICATION ACTUELLE]

Ce module était initialement prévu pour générer des données de test synthétiques
pour l'application DataWatt. Il crée un fichier CSV avec des courbes de charge
simulées incluant des variations saisonnières et du bruit aléatoire.
Un exemple de ce fichier charge_curve.csv est fourni dans le dossier fichiers_tests/.

STATUT ACTUEL:
- NON-UTILISÉ dans la version actuelle de DataWatt
- REMPLACÉ par des fichiers de test réels dans le dossier fichiers_tests/
- CONSERVÉ pour référence et futurs développements

FONCTIONNALITÉ ORIGINALE:
- Génération de données de consommation sur 2+ années (2023-2025)
- Granularité 15 minutes (compatible avec format DataWatt)
- Modulation saisonnière cosinus (+20% hiver, -20% été)
- Bruit gaussien pour simulation réaliste
- Format de sortie: charge_curve.csv

UTILISATION THÉORIQUE:
1. Exécuter ce script: python csv_generator.py
2. Fichier généré: charge_curve.csv dans le répertoire courant
3. Importer dans DataWatt comme un fichier de données standard

DÉVELOPPEMENTS FUTURS POSSIBLES:
- Intégration dans une suite de tests automatisés
- Génération de scenarios spécifiques
- Simulation de données solaires (autoconsommation/excédent)
- Génération de datasets pour validation des algorithmes de clustering

DATE: Archivé août 2025
=====================================================================================
"""

import csv
import datetime
import math
import random  
 

# ============================================================================
# PARAMÈTRES DE GÉNÉRATION DES DONNÉES SYNTHÉTIQUES
# ============================================================================
# Configuration temporelle pour la génération de la courbe de charge
start_date = datetime.datetime(2023, 1, 1, 0, 0)      # Date de début: 1er janvier 2023 00h00
end_date = datetime.datetime(2025, 2, 21, 23, 45)     # Date de fin: 21 février 2025 23h45
step = datetime.timedelta(minutes=15)                  # Pas temporel: 15 minutes (standard DataWatt)

# ============================================================================
# PARAMÈTRES DE CONSOMMATION ÉNERGÉTIQUE
# ============================================================================

# Configuration de la consommation annuelle de référence pour la simulation
intervals_per_year = 365 * 24 * 4                     # 35040 intervalles de 15min par année standard
baseline = 10000 / intervals_per_year                  # Consommation moyenne par intervalle (en kWh)
                                                       # Base: 10'000 kWh/an ≈ ménage suisse moyen

# ============================================================================
# PARAMÈTRES DE MODULATION SAISONNIÈRE
# ============================================================================

# Configuration de la variation saisonnière basée sur une fonction cosinus
# Simule la réalité: forte consommation hivernale (chauffage) vs été (climatisation minimale)
amplitude = 0.20                                       # Amplitude de variation: ±20% autour de la baseline
phase_shift = 15                                       # Décalage de phase: maximum vers 15 janvier (plein hiver)

# ============================================================================
# FONCTION DE CALCUL DU FACTEUR SAISONNIER
# ============================================================================

def saison_factor(dt):
    """
    Calcule le facteur de modulation saisonnière pour une date donnée
    
    Utilise une fonction cosinus pour simuler les variations saisonnières:
    - Maximum en hiver (janvier): facteur ≈ 1.20 (+20% de consommation)
    - Minimum en été (juillet): facteur ≈ 0.80 (-20% de consommation)
    - Transition progressive au printemps et automne
    
    Args:
        dt (datetime): Date pour laquelle calculer le facteur saisonnier
        
    Returns:
        float: Facteur multiplicateur (0.8 à 1.2) à appliquer à la consommation de base
        
    Note:
        Basé sur les patterns réels de consommation en Suisse avec chauffage électrique
    """
    # Extraction du jour de l'année (1 à 365/366)
    day_of_year = dt.timetuple().tm_yday
    
    # Calcul de la modulation cosinus sur cycle annuel de 365 jours
    # Formule: 1 + amplitude * cos(2π * (jour - décalage) / 365)
    factor = 1 + amplitude * math.cos(2 * math.pi * (day_of_year - phase_shift) / 365)
    return factor

# ============================================================================
# GÉNÉRATION DU FICHIER CSV AVEC DONNÉES SYNTHÉTIQUES
# ============================================================================

# Processus principal de création du fichier de test avec courbe de charge réaliste
with open("charge_curve.csv", "w", newline="") as csvfile:
    # Configuration du writer CSV avec séparateur point-virgule (standard européen)
    writer = csv.writer(csvfile, delimiter=";")
    
    # === ÉCRITURE DE L'EN-TÊTE DU FICHIER ===
    # Format compatible avec le module dataframe_gen.py de DataWatt
    writer.writerow(["Datetime", "Consumption (kWh)"])

    # === BOUCLE DE GÉNÉRATION DES DONNÉES TEMPORELLES ===
    # Création d'un point de données toutes les 15 minutes sur la période définie
    current_date = start_date
    while current_date <= end_date:
        # === CALCUL DE LA CONSOMMATION POUR CET INTERVALLE ===
        
        # 1. Application du facteur saisonnier (variation hiver/été)
        seasonal = saison_factor(current_date)
        
        # 2. Ajout de bruit gaussien pour simuler les variations réelles
        # Distribution normale: moyenne=1, écart-type=0.1 (±10% de variation aléatoire)
        noise = random.gauss(1, 0.1)
        
        # 3. Calcul de la consommation finale pour cet intervalle
        # Formule: consommation_base × facteur_saisonnier × bruit_aléatoire
        consumption = baseline * seasonal * noise
        
        # === FORMATAGE ET ÉCRITURE DES DONNÉES ===
        # Format de date: YYYY-MM-DD HH:MM (compatible avec pandas et DataWatt)
        date_str = current_date.strftime("%Y-%m-%d %H:%M")
        
        # Écriture de la ligne avec consommation arrondie à 5 décimales
        writer.writerow([date_str, f"{consumption:.5f}"])
        
        # === AVANCEMENT À L'INTERVALLE SUIVANT ===
        current_date += step

# ============================================================================
# CONFIRMATION DE GÉNÉRATION
# ============================================================================
# Message de succès pour l'utilisateur
print("Fichier 'charge_curve.csv' généré avec succès.")
print("🔄 ATTENTION: Ce fichier n'est plus utilisé dans DataWatt actuel")
print("📁 Utilisez plutôt les fichiers de test dans: fichiers_tests/")

# ============================================================================
# FIN DU GÉNÉRATEUR CSV - MODULE ARCHIVÉ
# ============================================================================