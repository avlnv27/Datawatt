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