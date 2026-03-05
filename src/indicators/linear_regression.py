import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import streamlit as st
from src.textual.tools import tooltip_info  
import src.textual.text as txt   
try:
    from src.indicators.cluster_indic import get_user_feature_position
except ImportError:
    get_user_feature_position = None   


## INDICATORS FUNCTIONS FOR PRIVATES  

def format_number_with_apostrophe(number, decimal_places=0):
    """
    Formate un nombre avec des apostrophes comme séparateurs de milliers
    Ex: 1234567.89 -> "1'234'567.89" ou "1'234'568" si decimal_places=0
    """
    if number is None:
        return "0"
    
    # Arrondir selon le nombre de décimales souhaité
    if decimal_places == 0:
        formatted = f"{number:.0f}"
    elif decimal_places == 1:
        formatted = f"{number:.1f}"
    elif decimal_places == 2:
        formatted = f"{number:.2f}"
    else:
        formatted = f"{number:.{decimal_places}f}"
    
    # Séparer la partie entière et décimale
    if '.' in formatted:
        integer_part, decimal_part = formatted.split('.')
        formatted_with_apostrophe = f"{int(integer_part):_}".replace('_', "'")
        return f"{formatted_with_apostrophe}.{decimal_part}"
    else:
        return f"{int(formatted):_}".replace('_', "'")

def get_consumption_column(df):
    """Determine which consumption column to use"""
    return 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in df.columns else 'Consumption (kWh)'  


# Concerne la charge de base


def perform_linear_regression(years, base_loads):
    # Convert years and base_loads to numpy arrays
    X = np.array(years).reshape(-1, 1)
    y = np.array(base_loads)  # Exclude the overall base load
    
    # Perform linear regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Get the slope and intercept
    slope = model.coef_[0]
    intercept = model.intercept_
    
    return slope, intercept

def display_linear_regression_results(slope, years, metric_name="Charge de base", intercept=0):
    """
    Affiche les résultats de régression linéaire de manière stylisée
    
    Args:
        slope: Pente de la régression linéaire
        years: Liste des années
        metric_name: Nom de la métrique (Base Load, etc.)
        intercept: Ordonnée à l'origine de la régression linéaire
    """
    # Generate a trend interpretation
    if abs(slope) < 0.1:
        trend_text = "stable"
        trend_color = "#228B22"  # Forest green
        trend_icon = "➡️"
    elif slope > 0:
        trend_text = "en augmentation"
        trend_color = "#FF4500"  # OrangeRed
        trend_icon = "📈"
    else:
        trend_text = "en diminution"
        trend_color = "#1E90FF"  # DodgerBlue
        trend_icon = "📉"
    
    # Calculate percentage change per year
    if years and len(years) > 1:
        years_range = years[-1] - years[0]
        if years_range > 0:
            change_per_year_pct = (slope * years_range / (slope * years[0] + intercept)) * 100 if slope * years[0] + intercept != 0 else 0
            change_text = f"{abs(change_per_year_pct):.1f}% par an"
        else:
            change_text = "Calcul impossible (données insuffisantes)"
    else:
        change_text = "Calcul impossible (données insuffisantes)"
    
    unit = "W" if metric_name == "Charge de base" else " kWh/m²"

    # Transform kW to W if unit is == "W"
    if unit == "W":
        slope *= 1000
    # Stylish display
    st.markdown(f"""
    <div style="max-width: 500px; margin: 20px auto; text-align: center;">
        <div style="border: 2px solid #ff1100; border-radius: 15px; padding: 25px; background-color: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="color: #666666; margin-bottom: 15px;">Tendance de {metric_name}</h3>
            <div style="font-size: 1.5em; margin: 15px 0;">
                <span style="color: {trend_color}; font-weight: bold;">{trend_text.capitalize()}</span>
            </div>
            <p style="font-size: 1.2em; color: #333; margin: 10px 0;">
                <span style="font-weight: bold;">{slope:.1f} {unit}</span> par an
            </p>
            <p style="color: #555; font-style: italic; margin-top: 10px;">{change_text}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Expander with detailed explanation
    with st.expander("À propos de l'analyse de tendance"):
        st.markdown(f"""
        ### Qu'est-ce que la tendance de {metric_name} ?
        
        Cette analyse utilise une régression linéaire pour calculer l'évolution de votre {metric_name.lower()} au fil du temps.
        
        ### Comment interpréter ces résultats ?
        
        - **Pente ({slope:.1f})** : Représente le changement annuel moyen
        - **Tendance {trend_text}** : Indique la direction générale de l'évolution
        
        Une tendance à la hausse peut indiquer l'ajout d'appareils électriques ou un changement d'habitudes de consommation.
        Une tendance à la baisse peut refléter des efforts d'efficacité énergétique ou des changements d'équipements.
        """)