"""
=====================================================================================
              GRAPHIQUES EN BARRES AVEC RÉGRESSION LINÉAIRE 
=====================================================================================
[FICHIER NON UTILISÉ DANS L'APPLICATION ACTUELLE]

Ce module contenait les fonctions de visualisation pour créer des graphiques en barres
avec superposition de droites de régression linéaire et calcul des coefficients R².
Il était initialement prévu pour analyser les tendances de consommation énergétique.

STATUT ACTUEL:
- ❌ NON UTILISÉ dans la version actuelle de DataWatt
- 🔄 FONCTIONNALITÉS INTÉGRÉES dans d'autres modules, notamment :
  - src/indicators/base_load.py : Analyse des tendances de charge nocturne
  - src/indicators/personalized_analysis.py : Graphiques de consommation surfacique
  - src/dashboard/dashboard.py : Visualisations simplifiées pour le tableau de bord
- 📦 CONSERVÉ pour référence et futurs développements

FONCTIONNALITÉS ORIGINALES:
1. **bar_plot_lin_reg()** : Graphique charge de base avec régression
   - Visualisation en barres de la charge nocturne par année
   - Superposition d'une droite de régression linéaire
   - Calcul et affichage du coefficient de détermination R²
   - Palette de couleurs cohérente avec interactive_plot.py

2. **bar_plot_lin_reg_surface()** : Graphique consommation surfacique avec régression
   - Visualisation de la consommation par m² par année
   - Analyse de tendance avec régression linéaire
   - Calcul de la qualité de l'ajustement (R²)
   - Formatage adapté aux analyses personnalisées

INTÉGRATION ACTUELLE:
- **Analyse des tendances** → Intégrée dans base_load.py avec calcul automatique
- **Visualisations simplifiées** → Dashboard principal sans régression explicite
- **Cohérence des couleurs** → Système unifié dans tout l'application
- **Calculs statistiques** → Intégrés dans les fonctions d'analyse principales

POURQUOI NON UTILISÉ:
- Redondance avec les nouvelles fonctions d'analyse intégrées
- Interface utilisateur simplifiée privilégiée (moins de graphiques techniques)
- Calculs de tendance automatisés sans besoin de visualisation séparée
- Maintenance réduite avec moins de modules spécialisés

MIGRATION DES FONCTIONNALITÉS:
- **Tendances charge de base** → display_base_load() dans base_load.py
- **Analyses surfaciques** → display_surface_consumption() dans personalized_analysis.py
- **Cartes de tendance** → Dashboard principal avec indicateurs visuels simples
- **Calculs R²** → Remplacés par calculs de pourcentage de variation plus accessibles

DÉVELOPPEMENTS FUTURS POSSIBLES:
- Réactivation pour analyses avancées optionnelles
- Intégration dans une section "Analyses expertes"
- Extension pour autres types de régressions (polynomiale, exponentielle)
- Module de diagnostic énergétique approfondi

DÉPENDANCES TECHNIQUES:
- streamlit : Interface web (remplacé par intégration directe)
- plotly.graph_objects : Graphiques interactifs (toujours utilisé ailleurs)
- sklearn.metrics.r2_score : Calcul coefficient R² (remplacé par stats simples)
- numpy : Calculs numériques (toujours utilisé dans l'application)

AUTEURS: Équipe DataWatt - SIE SA & EPFL
DATE: Développement initial 2025, archivé août 2025
=====================================================================================
"""

import streamlit as st
import plotly.graph_objects as go
from sklearn.metrics import r2_score
import numpy as np

# ============================================================================
# FONCTION DE GRAPHIQUE EN BARRES - CHARGE DE BASE [ARCHIVÉE]
# ============================================================================
def bar_plot_lin_reg(base_loads, years, slope_base_load, intercept_base_load):
    """
    Crée un graphique en barres de la charge de base avec régression linéaire [FONCTION ARCHIVÉE]
    
    Cette fonction était utilisée pour visualiser l'évolution de la charge de base avec :
    - Graphique en barres des valeurs annuelles de charge nocturne
    - Superposition d'une droite de régression linéaire
    - Calcul du coefficient de détermination R²
    - Palette de couleurs cohérente avec l'application
    
    STATUT: ❌ NON UTILISÉE - Remplacée par l'affichage intégré dans display_base_load()
    
    Args:
        base_loads (list): Valeurs de charge de base en kW par année
        years (list): Années correspondantes aux valeurs de charge
        slope_base_load (float): Pente de la droite de régression en kW/an
        intercept_base_load (float): Ordonnée à l'origine de la régression en kW
        
    Note:
        Les fonctionnalités de cette fonction sont maintenant intégrées dans :
        - src/indicators/base_load.py : display_base_load() avec calcul de tendance
        - src/dashboard/dashboard.py : Cartes de tendance simplifiées
    """
    # === DÉFINITION DE LA PALETTE DE COULEURS (COHÉRENCE AVEC INTERACTIVE_PLOT) ===
    # Palette utilisée dans toute l'application pour maintenir la cohérence visuelle
    color_map = {
        2023: '#42A5F5',  # Bleu clair
        2024: '#7C4DFF',  # Violet
        2025: '#FF9800',  # Orange
        2026: '#1E88E5',  # Bleu 
        2027: '#26A69A'   # Turquoise
    }
    
    # Couleurs par défaut pour les années non définies explicitement
    default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A']
    
    # === CRÉATION DE LA FIGURE PLOTLY ===
    fig = go.Figure()

    # === ATTRIBUTION DES COULEURS AUX BARRES SELON L'ANNÉE ===
    bar_colors = []
    for i, year in enumerate(years):
        if year in color_map:
            bar_colors.append(color_map[year])
        else:
            bar_colors.append(default_colors[i % len(default_colors)])

    # === CONVERSION DES UNITÉS kW → W POUR COHÉRENCE AVEC L'APPLICATION ===
    base_loads_watts = [load * 1000 for load in base_loads]

    # === AJOUT DU GRAPHIQUE EN BARRES POUR LES DONNÉES DE CHARGE DE BASE ===
    fig.add_trace(go.Bar(
        x=years, 
        y=base_loads_watts,  # Valeurs converties en Watts pour cohérence
        name='Charge de Base',
        marker=dict(
            color=bar_colors,
            opacity=0.7,  # Opacité réduite pour meilleur rendu visuel
            line=dict(color=bar_colors, width=1)
        )
    ))
    
    # === CALCUL ET AJOUT DE LA DROITE DE RÉGRESSION LINÉAIRE ===
    # Conversion des valeurs de régression de kW vers W pour affichage
    regression_line_kw = [slope_base_load * year + intercept_base_load for year in years]
    regression_line_w = [value * 1000 for value in regression_line_kw]

    # Calcul du coefficient de détermination R² (utilise les valeurs kW originales)
    r2 = r2_score(base_loads, regression_line_kw)
    
    # Ajout de la droite de régression au graphique
    fig.add_trace(go.Scatter(
        x=years, 
        y=regression_line_w,  # Utilise les valeurs en W pour l'affichage
        mode='lines', 
        name=f'Regression linéaire',
        line=dict(color='red', width=2)
    ))

    # === CONFIGURATION DU LAYOUT DU GRAPHIQUE ===
    fig.update_layout(
        title='Charge de Base avec Régression Linéaire',
        xaxis_title='Année',
        yaxis_title='Charge de Base (W)',
        xaxis=dict(
            tickmode='array',
            tickvals=years,
            ticktext=[str(year) for year in years]
        ),
        barmode='group',
        plot_bgcolor='white',
        showlegend=False
    )

    # === AFFICHAGE DU GRAPHIQUE DANS STREAMLIT ===
    st.plotly_chart(fig)

# ============================================================================
# FONCTION DE GRAPHIQUE EN BARRES - CONSOMMATION SURFACIQUE [ARCHIVÉE]
# ============================================================================
def bar_plot_lin_reg_surface(surfc, years, slope_surface_daily_consumption, intercept_surface_daily_consumption):
    """
    Crée un graphique en barres de la consommation surfacique avec régression [FONCTION ARCHIVÉE]
    
    Cette fonction était utilisée pour visualiser l'évolution de la consommation par m² avec :
    - Graphique en barres des valeurs annuelles de consommation surfacique
    - Superposition d'une droite de régression linéaire
    - Calcul du coefficient de détermination R²
    - Analyse des tendances de consommation par surface
    
    STATUT: ❌ NON UTILISÉE - Remplacée par l'affichage intégré dans personalized_analysis.py
    
    Args:
        surfc (list): Valeurs de consommation surfacique journalière en kWh/m² par année
        years (list): Années correspondantes aux valeurs de consommation
        slope_surface_daily_consumption (float): Pente de la régression en (kWh/m²)/an
        intercept_surface_daily_consumption (float): Ordonnée à l'origine en kWh/m²
        
    Note:
        Les fonctionnalités de cette fonction sont maintenant intégrées dans :
        - src/indicators/personalized_analysis.py : display_surface_consumption()
        - src/indicators/bar_plot_lin_reg.py : Calculs de tendance automatisés
    """
    # === DÉFINITION DE LA PALETTE DE COULEURS (IDENTIQUE À LA PREMIÈRE FONCTION) ===
    color_map = {
        2023: '#42A5F5',  # Bleu clair
        2024: '#7C4DFF',  # Violet
        2025: '#FF9800',  # Orange
        2026: '#1E88E5',  # Bleu 
        2027: '#26A69A'   # Turquoise
    }
    
    # Couleurs par défaut pour cohérence avec l'application
    default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A']
    
    # === CRÉATION DE LA FIGURE PLOTLY ===
    fig = go.Figure()

    # === ATTRIBUTION DES COULEURS AUX BARRES SELON L'ANNÉE ===
    bar_colors = []
    for i, year in enumerate(years):
        if year in color_map:
            bar_colors.append(color_map[year])
        else:
            bar_colors.append(default_colors[i % len(default_colors)])

    # === AJOUT DU GRAPHIQUE EN BARRES POUR CONSOMMATION SURFACIQUE ===
    fig.add_trace(go.Bar(
        x=years, 
        y=surfc,  # Valeurs en kWh/m² (pas de conversion nécessaire)
        name='Consommation surfaçique journalière',
        marker=dict(
            color=bar_colors,
            opacity=0.7,  # Opacité réduite pour meilleur rendu visuel
            line=dict(color=bar_colors, width=1)
        )
    ))

    # === CALCUL ET AJOUT DE LA DROITE DE RÉGRESSION LINÉAIRE ===
    # Calcul des valeurs de la droite de régression pour chaque année
    regression_line = [slope_surface_daily_consumption * year + intercept_surface_daily_consumption for year in years]

    # Calcul du coefficient de détermination R²
    r2 = r2_score(surfc, [slope_surface_daily_consumption * year + intercept_surface_daily_consumption for year in years])

    # Ajout de la droite de régression avec valeur R² dans la légende
    fig.add_trace(go.Scatter(
        x=years, 
        y=regression_line, 
        mode='lines', 
        name=f'Régression linéaire',
        line=dict(color='red', width=2)
    ))

    # === CONFIGURATION DU LAYOUT DU GRAPHIQUE ===
    fig.update_layout(
        title='Consommation surfaçique journalière avec Régression Linéaire',
        xaxis_title='Année',
        yaxis_title='Consommation surfaçique journalière (kWh/m²)',
        xaxis=dict(
            tickmode='array',
            tickvals=years,
            ticktext=[str(year) for year in years]
        ),
        barmode='group',
        plot_bgcolor='white',
        showlegend=False
    )

    # === AFFICHAGE DU GRAPHIQUE DANS STREAMLIT ===
    st.plotly_chart(fig)

# ============================================================================
# FIN DU MODULE BAR_PLOT_LIN_REG - FONCTIONS ARCHIVÉES
# ============================================================================