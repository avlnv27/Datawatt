import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from meteostat import Point, Daily

### FONCTION A RETRAVAILLER ET NON MISE A JOUR


def get_city_coordinates(city):
    """
    Renvoie les coordonnées prédéfinies pour les villes de la région.
    
    Args:
        city (str): Nom de la ville
        
    Returns:
        tuple: (latitude, longitude)
    """
    city_coordinates = {
        "Renens": (46.5390, 6.5887),
        "Ecublens": (46.5260, 6.5664),
        "Crissier": (46.5523, 6.5746),
        "Chavannes-près-Renens": (46.5300, 6.5775)
    }
    
    # Si la ville est dans notre dictionnaire, renvoyer ses coordonnées
    if city in city_coordinates:
        return city_coordinates[city]
    # Sinon renvoyer les coordonnées d'Ecublens par défaut
    else:
        return city_coordinates["Ecublens"]


def calculate_cdd(city, pdf, base_temp):
    """
    Calcule les Cooling Degree Days (CDD) pour une ville donnée sur la période
    correspondant aux données de consommation, avec une température de base définie.
    
    Args:
        city (str): Nom de la ville
        pdf (pd.DataFrame): DataFrame contenant les données de consommation avec index temporel
        base_temp (float): Température de base pour le calcul des CDD
        
    Returns:
        pd.DataFrame: DataFrame contenant les CDD journaliers et les données de consommation
    """
    try:
        # Obtenir les coordonnées de la ville
        latitude, longitude = get_city_coordinates(city)
        
        # Extraire la période des données de consommation
        start_date = pdf.index.min().to_pydatetime()
        end_date = pdf.index.max().to_pydatetime()
        
        # Créer un point géographique pour la requête Meteostat
        location = Point(latitude, longitude)
        
        # Obtenir les données météorologiques
        data = Daily(location, start_date, end_date)
        data = data.fetch()
        
        if data.empty:
            return None
        
        # Calculer les CDD journaliers
        data['cdd'] = data['tavg'].apply(lambda x: max(0, x - base_temp) if not np.isnan(x) else 0)
        
        # Calculer la somme totale des CDD
        total_cdd = data['cdd'].sum()
        
        # Réaggréger les données horaires de consommation en données journalières
        daily_consumption = pdf.resample('D').sum()
        
        # Fusionner les données de CDD et de consommation
        result = pd.DataFrame()
        result['date'] = data.index
        result['cdd'] = data['cdd']
        
        if len(daily_consumption) == len(data):
            result['consumption'] = daily_consumption.iloc[:, 2].values
        
        result = result.set_index('date')
        result['total_cdd'] = total_cdd
        
        return result
    
    
    except Exception as e:
        return None
    
def calculate_hdd(city, pdf, base_temp):
    """
    Calcule les Heating Degree Days (HDD) pour une ville donnée sur la période
    correspondant aux données de consommation, avec une température de base définie.
    
    Args:
        city (str): Nom de la ville
        pdf (pd.DataFrame): DataFrame contenant les données de consommation avec index temporel
        base_temp (float): Température de base pour le calcul des HDD
        
    Returns:
        pd.DataFrame: DataFrame contenant les HDD journaliers et les données de consommation
    """
    try:
        # Obtenir les coordonnées de la ville
        latitude, longitude = get_city_coordinates(city)
        
        # Extraire la période des données de consommation
        start_date = pdf.index.min().to_pydatetime()
        end_date = pdf.index.max().to_pydatetime()
        
        # Créer un point géographique pour la requête Meteostat
        location = Point(latitude, longitude)
        
        # Obtenir les données météorologiques
        data = Daily(location, start_date, end_date)
        data = data.fetch()
        
        if data.empty:
            return None
        
        # Calculer les HDD journaliers (logique inverse des CDD)
        data['hdd'] = data['tavg'].apply(lambda x: max(0, base_temp - x) if not np.isnan(x) else 0)
        
        # Calculer la somme totale des HDD
        total_hdd = data['hdd'].sum()
        
        # Réaggréger les données horaires de consommation en données journalières
        daily_consumption = pdf.resample('D').sum()
        
        # Fusionner les données de HDD et de consommation
        result = pd.DataFrame()
        result['date'] = data.index
        result['hdd'] = data['hdd']
        
        if len(daily_consumption) == len(data):
            result['consumption'] = daily_consumption.iloc[:, 2].values
        
        result = result.set_index('date')
        result['total_hdd'] = total_hdd
        
        return result
    
    except Exception as e:
        return None


def analyze_hotel_consumption(surface,city, pdf):

    
    st.header(f"Analyse spécifique pour un hôtel de {surface} m² à {city}")

    # Note "En travaux"
    st.markdown("""
    <div style="background-color: #FFF3CD; border-left: 6px solid #FFC107; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0; color: #856404;">⚠️ Section en développement</h4>
        <p style="margin-bottom: 0; color: #856404;">Cette section d'analyse spécifique pour hôtels est actuellement en travaux. Certaines fonctionnalités 
        peuvent être incomplètes ou produire des résultats approximatifs. Merci de votre compréhension.</p>
    </div>
    """, unsafe_allow_html=True)


    num_rooms = st.number_input(
        "Nombre de chambres de l'hôtel",
        min_value=1,
        max_value=1000,
        value=int(surface/30),  # Estimation par défaut basée sur la surface
        step=1,
        help="Indiquez le nombre total de chambres dans votre hôtel"
    )
    
    # Interface pour sélectionner la température de base
    base_temp = st.slider(
        "Température intérieure de référence (°C)",
        min_value=17.0,
        max_value=26.0,
        value=20.0,
        step=0.2,
        help="La température intérieure de référence pour calculer les besoins en climatisation"
    )
    
    # Calcul des CDD
    cdd_data = calculate_cdd(city, pdf, base_temp+2)
    hdd_data = calculate_hdd(city, pdf, base_temp-2)

        # Section pour entrer le taux d'occupation saisonnier
    st.subheader("Taux d'occupation saisonnier")
    st.info("Veuillez indiquer le taux d'occupation moyen de votre hôtel pour chaque saison. Ces données permettront une analyse plus précise de votre consommation énergétique en fonction de l'activité réelle.")
    
    # Création d'un layout en colonnes pour organiser les sliders
    col1, col2 = st.columns(2)
    
    # Initialisation du dictionnaire pour stocker les taux d'occupation
    occupation_rates = {}
    
    # Première colonne avec Hiver et Printemps
    with col1:
        occupation_rates["Hiver"] = st.slider(
            "Hiver (Déc-Fév)",
            min_value=0,
            max_value=100,
            value=60,  # Valeur par défaut
            step=5,
            format="%d%%",
            help="Taux d'occupation moyen en hiver (décembre, janvier, février)"
        )
        
        occupation_rates["Printemps"] = st.slider(
            "Printemps (Mar-Mai)",
            min_value=0,
            max_value=100,
            value=70,  # Valeur par défaut
            step=5,
            format="%d%%",
            help="Taux d'occupation moyen au printemps (mars, avril, mai)"
        )
    
    # Deuxième colonne avec Été et Automne
    with col2:
        occupation_rates["Été"] = st.slider(
            "Été (Juin-Août)",
            min_value=0,
            max_value=100,
            value=85,  # Valeur par défaut
            step=5,
            format="%d%%",
            help="Taux d'occupation moyen en été (juin, juillet, août)"
        )
        
        occupation_rates["Automne"] = st.slider(
            "Automne (Sep-Nov)",
            min_value=0,
            max_value=100,
            value=65,  # Valeur par défaut
            step=5,
            format="%d%%",
            help="Taux d'occupation moyen en automne (septembre, octobre, novembre)"
        )
    
    # Création d'un DataFrame pour le taux d'occupation
    seasons = ["Hiver", "Printemps", "Été", "Automne"]
    colors = ["#87CEFA", "#90EE90", "#FFA07A", "#D2B48C"]  # Couleurs représentatives des saisons
    
    occupation_df = pd.DataFrame({
        'Saison': seasons,
        'Taux d\'occupation (%)': [occupation_rates[season] for season in seasons]
    })
    
    # Calcul de l'indicateur de rendement par chambre occupée
    if pdf is not None and num_rooms > 0:
        try:
            # Calculer la consommation totale sur la période
            total_consumption = float(pdf.iloc[:, 2].sum())
            
            # Calculer le nombre moyen de chambres occupées sur la période
            avg_occupation_rate = float(occupation_df['Taux d\'occupation (%)'].mean()) / 100.0
            avg_occupied_rooms = float(num_rooms) * avg_occupation_rate
            
            # Calculer l'indicateur de rendement (kWh/chambre occupée)
            if avg_occupied_rooms > 0.001:  # Éviter la division par zéro ou des valeurs très petites
                efficiency_indicator = total_consumption / avg_occupied_rooms
                
                # Afficher l'indicateur de rendement
                st.subheader("Indicateur de rendement énergétique")
                
                # Déterminer la couleur en fonction de la valeur (vert = bon, rouge = mauvais)
                if efficiency_indicator <= 20:
                    color = "green"
                    assessment = "Excellent rendement énergétique"
                elif efficiency_indicator <= 40:
                    color = "lightgreen"
                    assessment = "Bon rendement énergétique"
                elif efficiency_indicator <= 60:
                    color = "orange"
                    assessment = "Rendement énergétique moyen"
                else:
                    color = "red"
                    assessment = "Rendement énergétique à améliorer"
                
                # Afficher la métrique avec style
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 5px; background-color: {color}; color: white;">
                    <h3 style="margin: 0;">{efficiency_indicator:.1f} kWh/chambre occupée</h3>
                    <p style="margin: 5px 0 0 0;">{assessment}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Contexte sur les valeurs de référence
                st.markdown("""
                **Valeurs de référence:**
                - **10-20 kWh/chambre occupée**: Excellent rendement énergétique
                - **20-40 kWh/chambre occupée**: Bon rendement énergétique
                - **40-60 kWh/chambre occupée**: Rendement énergétique moyen
                - **60-70 kWh/chambre occupée**: Rendement énergétique à améliorer
                - **>70 kWh/chambre occupée**: Consommation excessive
                """)
                
                # Recommandations basées sur le rendement
                st.subheader("Recommandations")
                
                if efficiency_indicator > 60:
                    st.warning("""
                    **Actions prioritaires pour améliorer votre rendement énergétique:**
                    1. Auditer les systèmes de chauffage et climatisation
                    2. Vérifier l'isolation des chambres et espaces communs
                    3. Installer des systèmes de gestion d'énergie dans les chambres
                    4. Former le personnel aux bonnes pratiques énergétiques
                    """)
                elif efficiency_indicator > 40:
                    st.info("""
                    **Suggestions pour optimiser votre rendement énergétique:**
                    1. Installer des capteurs de présence pour l'éclairage
                    2. Optimiser la température des chambres inoccupées
                    3. Envisager un système de récupération de chaleur
                    """)
                else:
                    st.success("""
                    **Pour maintenir votre bon rendement énergétique:**
                    1. Continuer les bonnes pratiques actuelles
                    2. Envisager l'installation de panneaux solaires
                    3. Communiquer sur vos performances environnementales auprès de vos clients
                    """)
                
                # Détails de calcul pour transparence
                with st.expander("Voir détails du calcul"):
                    st.write(f"""
                    - Consommation totale: {total_consumption:.2f} kWh
                    - Nombre total de chambres: {num_rooms}
                    - Taux d'occupation moyen: {avg_occupation_rate*100:.1f}%
                    - Nombre moyen de chambres occupées: {avg_occupied_rooms:.1f}
                    - Calcul: {total_consumption:.2f} kWh ÷ {avg_occupied_rooms:.1f} chambres = {efficiency_indicator:.2f} kWh/chambre occupée
                    """)
            else:
                st.warning("Le taux d'occupation est trop faible pour calculer un indicateur fiable (proche de 0%).")
        
        except Exception as e:
            st.error(f"Erreur lors du calcul de l'indicateur de rendement: {e}")
            st.info("Vérifiez que vos données de consommation sont correctes et que le taux d'occupation est supérieur à 0%.")

    return None