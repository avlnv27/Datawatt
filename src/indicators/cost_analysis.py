"""
=====================================================================================
                        ANALYSE DES COÛTS ÉNERGÉTIQUES 
=====================================================================================

Ce module implémente l'analyse complète des coûts énergétiques avec gestion avancée
des tarifications électriques suisses. Il permet aux utilisateurs de comprendre
l'impact financier de leur consommation selon différents types de contrats.

FONCTIONNALITÉS PRINCIPALES:
1. **Gestion des tarifs multiples** : Tarif unique vs HP/HC (Heures Pleines/Heures Creuses)
2. **Calcul automatique des coûts** : Application des tarifs selon les créneaux horaires
3. **Analyse comparative** : Évolution des coûts mensuels entre années
4. **Répartition HP/HC** : Visualisation graphique de la distribution des consommations
5. **Détection de tendances** : Identification automatique des variations significatives
6. **Interface adaptative** : Affichage selon le mode de sélection des années

LOGIQUE MÉTIER - TARIFICATION ÉLECTRIQUE:
Le système électrique suisse propose généralement deux types de tarifications :
- **Tarif unique** : Prix constant 24h/24, 7j/7 (simplicité de gestion)
- **Tarif HP/HC** : Prix variables selon les créneaux horaires (optimisation coûts)

STRUCTURE TARIFAIRE HP/HC STANDARD:
- **Heures Pleines (HP)** : 6h00-22h00, du lundi au vendredi (demande élevée)
- **Heures Creuses (HC)** : 22h00-6h00 + week-ends (demande réduite)
- **Principe** : Inciter à consommer pendant les périodes de faible demande

MÉTHODES DE CALCUL:
1. **Tarif unique** : Consommation(kWh) × Prix_unique(CHF/kWh)
2. **Tarif HP/HC** : Σ[Consommation_HP × Prix_HP + Consommation_HC × Prix_HC]
3. **Prix moyen pondéré** : Moyenne pondérée par la répartition réelle HP/HC

VISUALISATIONS AVANCÉES:
- Graphiques en barres groupées pour comparaisons multi-annuelles
- Graphiques en anneau (donut) pour répartition HP/HC
- Annotations automatiques des tendances avec flèches directionnelles
- Adaptation automatique des échelles et couleurs

INTÉGRATION AVEC L'ÉCOSYSTÈME DATAWATT:
- Dashboard principal : Graphiques de coûts mensuels simplifiés
- Configuration utilisateur : Paramètres de tarification dans la sidebar
- Analyses personnalisées : Impact financier des recommandations
- Clustering : Analyse comparative des coûts par groupe

SOURCES DE DONNÉES TARIFAIRES:
- Grilles tarifaires officielles SIE SA
- Paramètres configurables par l'utilisateur
- Mise à jour annuelle des tarifs de référence

AUTEURS: Équipe DataWatt - SIE SA & EPFL
DATE: Développement continu 2025 - Module actif en production
=====================================================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from src.textual.tools import *

# ============================================================================
# FONCTIONS UTILITAIRES POUR LA GESTION TARIFAIRE
# ============================================================================
def is_peak_hour(timestamp, peak_start_hour=6, peak_end_hour=22, peak_days=[0, 1, 2, 3, 4]):
    """
    Détermine si un timestamp correspond à une heure pleine (HP) selon la tarification suisse
    
    Cette fonction implémente la logique de classification HP/HC selon les standards
    de l'industrie électrique suisse, avec possibilité de personnalisation selon
    les contrats spécifiques des fournisseurs.
    
    LOGIQUE STANDARD HP/HC:
    - **Heures Pleines** : Périodes de forte demande énergétique
      - Jours ouvrables (lundi-vendredi) de 6h00 à 22h00
      - Tarif majoré pour inciter à la modération
    - **Heures Creuses** : Périodes de faible demande énergétique
      - Nuits (22h00-6h00) et week-ends complets
      - Tarif réduit pour encourager la consommation différée
    
    PERSONNALISATION POSSIBLE:
    - Horaires ajustables selon les contrats régionaux
    - Jours HP modifiables (certains fournisseurs incluent le samedi)
    - Configuration via interface utilisateur dans la sidebar
    
    Args:
        timestamp (pandas.Timestamp): Moment temporel à classifier
        peak_start_hour (int): Heure de début HP (0-23, défaut: 6h)
        peak_end_hour (int): Heure de fin HP (0-23, défaut: 22h)
        peak_days (list): Jours HP en format Python (0=lundi...6=dimanche, défaut: lun-ven)
        
    Returns:
        bool: True si Heure Pleine (HP), False si Heure Creuse (HC)
        
    Exemples:
        - Mardi 14h30 → True (HP : jour ouvrable, heure de bureau)
        - Mardi 23h15 → False (HC : nuit, même en semaine)
        - Samedi 14h30 → False (HC : week-end, même en journée)
        - Lundi 5h45 → False (HC : avant 6h, même en semaine)
    """
    # === EXTRACTION DES COMPOSANTES TEMPORELLES ===
    # Récupération des informations nécessaires depuis le timestamp
    weekday = timestamp.weekday()  # Jour de la semaine (0=lundi, 6=dimanche)
    hour = timestamp.hour         # Heure du jour (0-23)
    
    # === APPLICATION DE LA LOGIQUE DE CLASSIFICATION HP/HC ===
    # Double condition : jour ET créneau horaire doivent correspondre aux HP
    # Condition 1 : Le jour doit être dans la liste des jours HP (défaut: lun-ven)
    # Condition 2 : L'heure doit être dans la plage HP (défaut: 6h-22h)
    return weekday in peak_days and (hour >= peak_start_hour and hour < peak_end_hour)

def calculate_average_price():
    """
    Calcule le prix moyen du kWh selon la configuration tarifaire utilisateur
    
    Cette fonction utilitaire extrait les paramètres de tarification depuis
    st.session_state et calcule un prix moyen représentatif pour l'affichage
    dans le dashboard et les cartes de résumé.
    
    LOGIQUES DE CALCUL:
    - **Tarif unique** : Retourne directement le prix configuré
    - **Tarif HP/HC** : Moyenne arithmétique simple (HP + HC) / 2
      Note: Une moyenne pondérée serait plus précise mais nécessite
      l'accès aux données de consommation (non disponibles à ce niveau)
    
    SOURCES DES PARAMÈTRES:
    - st.session_state.tariff_type : Type de tarif sélectionné
    - st.session_state.tariff_unique_price : Prix tarif unique (CHF/kWh)
    - st.session_state.tariff_hp_price : Prix heures pleines (CHF/kWh)
    - st.session_state.tariff_hc_price : Prix heures creuses (CHF/kWh)
    
    UTILISATION:
    - Dashboard principal : Calculs de coûts approximatifs
    - Cartes de résumé : Affichage du prix de référence
    - Comparaisons rapides : Estimations sans analyse détaillée
    
    Returns:
        float: Prix moyen du kWh en CHF (défaut: 0.35 si non configuré)
        
    Note:
        Pour des calculs précis avec répartition HP/HC réelle,
        utiliser display_cost_analysis() qui accède aux données temporelles.
    """
    # === RÉCUPÉRATION DES PARAMÈTRES DE TARIFICATION ===
    # Type de tarif configuré par l'utilisateur dans la sidebar
    tariff_type = st.session_state.get('tariff_type', 'Tarif Unique')
    
    # === CALCUL SELON LE TYPE DE TARIF ===
    if tariff_type == "Tarif Unique":
        # Cas simple : prix unique 24h/24, 7j/7
        return st.session_state.get('tariff_unique_price', 0.35)
    else:  # Tarif HP/HC
        # Cas complexe : moyenne arithmétique des deux tarifs
        # Note: Approximation acceptable pour le dashboard
        # Pour une précision maximale, use display_cost_analysis() avec données réelles
        hp_price = st.session_state.get('tariff_hp_price', 0.40)
        hc_price = st.session_state.get('tariff_hc_price', 0.27)
        # Moyenne simple (non pondérée par la consommation réelle)
        return (hp_price + hc_price) / 2

# ============================================================================
# FONCTION PRINCIPALE D'ANALYSE ET VISUALISATION DES COÛTS
# ============================================================================

def display_cost_analysis(df, default_price=0.35):
    """
    Affiche l'interface complète d'analyse des coûts énergétiques avec tarification avancée
    
    Cette fonction constitue le cœur de l'analyse financière de DataWatt. Elle orchestre
    l'ensemble des calculs et visualisations liés aux coûts de l'énergie, en s'adaptant
    automatiquement aux paramètres de tarification configurés par l'utilisateur.
    
    ARCHITECTURE FONCTIONNELLE:
    1. **Validation et préparation** : Vérification des données, génération des palettes
    2. **Application tarifaire** : Calcul des coûts selon le type de tarif (Unique/HP-HC)
    3. **Visualisations principales** : Graphiques mensuels avec comparaisons multi-annuelles
    4. **Analyses spécialisées** : Répartition HP/HC avec graphiques en anneau
    5. **Détection de tendances** : Identification automatique des variations significatives
    6. **Interface informative** : Explications contextuelles et liens vers documentation
    
    ADAPTATIONS SELON LE MODE D'ANALYSE:
    - **Mode année unique** : Focus sur les variations mensuelles d'une année
    - **Mode données complètes** : Comparaisons multi-annuelles avec tendances
    
    GESTION AVANCÉE DES TARIFS:
    - **Tarif unique** : Application directe du prix configuré
    - **Tarif HP/HC** : Classification temporelle automatique + application différentielle
    
    VISUALISATIONS GÉNÉRÉES:
    - Graphiques en barres (mensuels) avec axes doubles (CHF + kWh)
    - Graphiques en anneau pour répartition HP/HC (si applicable)
    - Annotations automatiques des tendances avec flèches directionnelles
    - Cartes d'information tarifaire avec liens vers documentation officielle
    
    Args:
        df (pandas.DataFrame): DataFrame des données de consommation avec index temporel
        default_price (float): Prix par défaut (conservé pour compatibilité, non utilisé)
        
    Note:
        Les paramètres tarifaires sont extraits de st.session_state :
        - tariff_type, tariff_unique_price, tariff_hp_price, tariff_hc_price
        - peak_start_hour, peak_end_hour, peak_days (configuration HP/HC)
        - analysis_mode, year_selection_mode (modes d'affichage)
        
    Returns:
        float: Prix moyen pondéré calculé sur les données réelles (pour Dashboard)
    """
    # PHASE 1: VÉRIFICATION ET VALIDATION DES DONNÉES
    # ===============================================
    # Contrôle de sécurité essentiel - l'analyse financière nécessite une base de données solide
    if df is None or df.empty:
        st.warning("Aucune donnée disponible pour l'analyse des coûts.")
        return
    
    # PHASE 2: GÉNÉRATION DES PALETTES DE COULEURS
    # ============================================
    # Système de couleurs extensible pour maintenir la cohérence visuelle DataWatt
    # Supporte jusqu'à 20 années différentes avec rotation automatique si nécessaire
    default_colors = ['#42A5F5', '#7C4DFF', '#FF9800', '#1E88E5', '#26A69A', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548']
    
    # PHASE 3: ASSIGNATION AUTOMATIQUE DES COULEURS PAR ANNÉE
    # =======================================================
    # Génération dynamique du mapping couleur/année basé sur les données réelles
    # Cette approche garantit une correspondance stable même avec des datasets partiels
    color_map = {}
    unique_years = sorted(df['Year'].unique())
    for i, year in enumerate(unique_years):
        color_map[year] = default_colors[i % len(default_colors)]
    
    # PHASE 4: RÉCUPÉRATION DE LA CONFIGURATION TARIFAIRE
    # ===================================================
    # Extraction des paramètres configurés par l'utilisateur dans la sidebar
    # Cette architecture modulaire sépare la logique métier de l'interface utilisateur
    tariff_type = st.session_state.get('tariff_type', 'Tarif Unique')
    
    # PHASE 5: GÉNÉRATION DES CARTES INFORMATIVES TARIFAIRES
    # ======================================================
    # Ces cartes offrent un rappel visuel de la configuration active
    # et orientent l'utilisateur vers les paramètres de personnalisation
    
    if tariff_type == "Tarif Unique":
        # === TARIF UNIQUE : Simplicité et clarté ===
        kwh_price = st.session_state.get('tariff_unique_price', 0.35)
        st.markdown(f"""
        <div style="background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;">
            <p style="margin: 0;"><strong>💰 Rappel du tarif utilisé :</strong> {kwh_price:.2f} CHF/kWh (tarif unique, appliqué à toutes les années)</p>
            <p style="margin-top: 5px; font-size: 0.9em; color: #666;">Modifiable dans la barre latérale ← "Configuration des tarifs"</p>
        </div>
        """, unsafe_allow_html=True)
    else:  # Tarif HP/HC
        # === TARIF HP/HC : Complexité avec guidance utilisateur ===
        # Récupération de tous les paramètres HP/HC pour affichage complet
        hp_price = st.session_state.get('tariff_hp_price', 0.40)
        hc_price = st.session_state.get('tariff_hc_price', 0.27)
        peak_start = st.session_state.get('peak_start_hour', 6)
        peak_end = st.session_state.get('peak_end_hour', 22)
        peak_days = st.session_state.get('peak_days', [0, 1, 2, 3, 4])
        
        # === TRADUCTION DES JOURS POUR AFFICHAGE UTILISATEUR ===
        # Conversion des indices (0-6) vers les noms français pour plus de clarté
        days_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        days_selected = [days_names[i] for i in peak_days if i < 7]
        days_text = ", ".join(days_selected) if days_selected else "Aucun"
        
        # === CARTE INFORMATIVE HP/HC ===
        # Affichage complet des paramètres avec guidance utilisateur
        st.markdown(f"""
        <div style="background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;">
            <p style="margin: 0;"><strong>💰 Tarif HP/HC appliqué :</strong> HP: {hp_price:.2f} CHF/kWh | HC: {hc_price:.2f} CHF/kWh (appliqué à toutes les années)</p>
            <p style="margin-top: 5px; font-size: 0.9em; color: #666;">HP (heures pleines): {days_text}, de {peak_start}h à {peak_end}h</p>
        </div>
        """, unsafe_allow_html=True)
    
    # PHASE 6: DOCUMENTATION CONTEXTUELLE AVANCÉE
    # ===========================================
    # Intégration de la documentation utilisateur directement dans l'interface
    # Améliore l'autonomie de l'utilisateur et réduit les incompréhensions
    tooltip_info("Information")
    with st.expander("À propos des tarifs électriques"):
        st.markdown("""
        ### Comprendre votre tarif électrique
        
        Le tarif électrique varie selon:
        - **Type de contrat**: Tarif Unique (même prix toute la journée) ou Tarif HP/HC (prix variables selon l'heure)
        - **Période de consommation pour le tarif HP/HC**:
          - **Heures pleines (HP)**: De 06h00 à 22h00 
          - **Heures creuses (HC)**: De 22h00 à 06h00 
        
        Les tarifs incluent:
        - Le prix de l'énergie
        - Les coûts d'acheminement (réseau)
        - Les taxes et redevances
        
        💡 **Modification des tarifs**: Vous pouvez ajuster les paramètres de tarification dans la barre latérale (section "Configuration des tarifs").
        
        Pour des informations détaillées, consultez la [grille tarifaire officielle de SIE SA](https://www.sie.ch/media/document/0/sie-grilles-tarifaires-a4-2025-particuliers-preview-2.pdf).
        """)
    
    # PHASE 7: CALCULS DES COÛTS SELON LA TARIFICATION
    # ================================================
    # Cœur de l'analyse financière - application des tarifs aux données de consommation
    # La logique s'adapte automatiquement au type de tarif configuré
    df_with_cost = df.copy()
    
    if tariff_type == "Tarif Unique":
        # === CALCUL SIMPLE : TARIF UNIQUE ===
        # Application directe du prix unique à toute la consommation
        # Formule : Coût = Consommation (kWh) × Prix unique (CHF/kWh)
        df_with_cost['Cost'] = df_with_cost['Consumption (kWh)'] * kwh_price
    else:  # Tarif HP/HC
        # === CALCUL COMPLEXE : TARIF HP/HC ===
        # Étape 1: Classification temporelle HP/HC pour chaque point de données
        # Utilise la fonction is_peak_hour() avec les paramètres configurés
        df_with_cost['is_peak'] = df_with_cost.index.map(
            lambda timestamp: is_peak_hour(timestamp, peak_start, peak_end, peak_days)
        )
        
        # Étape 2: Application différentielle des tarifs selon la classification
        # Formule conditionnelle :
        # - Si HP : Coût = Consommation × Prix HP
        # - Si HC : Coût = Consommation × Prix HC
        df_with_cost['Cost'] = df_with_cost.apply(
            lambda row: row['Consumption (kWh)'] * hp_price if row['is_peak'] 
                        else row['Consumption (kWh)'] * hc_price,
            axis=1
        )
    
    # PHASE 8: VALIDATION ET PRÉPARATION POUR VISUALISATION
    # =====================================================
    # Vérification de la disponibilité des données post-traitement
    available_years = sorted(df_with_cost['Year'].unique())
    if not available_years:
        st.warning("Aucune donnée annuelle disponible.")
        return
    
    # PHASE 9: ADAPTATION AUX MODES D'ANALYSE
    # =======================================
    # L'interface s'adapte selon le mode sélectionné dans la sidebar :
    # - Mode année unique : focus sur une année spécifique
    # - Mode multi-années : comparaisons et tendances
    
    # Note importante : Pas de nouveau sélecteur d'année car l'utilisateur
    # a déjà effectué son choix dans la barre latérale principale
    
    # === DÉTERMINATION DU SCHÉMA DE COULEURS ===
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    
    if analysis_mode == 'single_year':
        # === MODE ANNÉE UNIQUE : Couleur cohérente ===
        # Utilisation d'une couleur unique pour maintenir la cohérence visuelle
        selected_year = st.session_state.get('selected_analysis_year')
        selected_year_color = color_map.get(selected_year, '#42A5F5')
        
        # === SECTION D'AFFICHAGE DE L'ANNÉE (COMMENTÉE) ===
        # Évite la redondance avec les informations déjà présentes dans la sidebar
        # st.markdown(f"""
        # <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #4361ee;">
        #     <p style="margin: 0;"><strong>🎯 Analyse des coûts pour l'année {selected_year}</strong></p>
        # </div>
        # """, unsafe_allow_html=True)
    else:
        # Mode données complètes : utiliser une couleur par défaut ou celle de la dernière année
        years_to_use = st.session_state.get('years_to_use', available_years)
        selected_year_color = color_map.get(max(years_to_use), '#42A5F5')
        
        # Section d'affichage des années analysées commentée pour éviter la redondance
        # if len(years_to_use) > 1:
        #     st.markdown(f"""
        #     <div style="background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;">
        #         <p style="margin: 0;"><strong>📈 Analyse des coûts pour les années {min(years_to_use)}-{max(years_to_use)}</strong></p>
        #     </div>
        #     """, unsafe_allow_html=True)
        # else:
        #     st.markdown(f"""
        #     <div style="background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #0ea5e9;">
        #         <p style="margin: 0;"><strong>📊 Analyse des coûts pour l'année {years_to_use[0]}</strong></p>
        #     </div>
        #     """, unsafe_allow_html=True)
    
    # Utiliser toutes les données disponibles (déjà filtrées selon la sélection utilisateur)
    year_data = df_with_cost
    
    if year_data.empty:
        st.warning("Aucune donnée disponible pour la période sélectionnée")
        return
    
    
    # PHASE 10: PRÉPARATION DES DONNÉES POUR VISUALISATION
    # ====================================================
    # Utilisation des données déjà filtrées selon la sélection utilisateur (sidebar)
    # Cette approche évite la duplication des logiques de filtrage
    year_data = df_with_cost
    
    if year_data.empty:
        st.warning("Aucune donnée disponible pour la période sélectionnée")
        return
    
    # PHASE 11: ANALYSE SPÉCIALISÉE HP/HC (SI APPLICABLE)
    # ==================================================
    # Cette section ne s'active que pour les tarifs HP/HC
    # Elle fournit une vue détaillée de la répartition temporelle de la consommation
    
    if tariff_type == "Tarif HP/HC":
        # === CALCULS STATISTIQUES HP/HC ===
        # Séparation des données selon la classification temporelle
        peak_consumption = year_data[year_data['is_peak']]['Consumption (kWh)'].sum()
        offpeak_consumption = year_data[~year_data['is_peak']]['Consumption (kWh)'].sum()
        total_consumption = peak_consumption + offpeak_consumption
        
        # === CALCULS FINANCIERS CORRESPONDANTS ===
        # Application des tarifs différentiels pour analyse de répartition
        peak_cost = peak_consumption * hp_price
        offpeak_cost = offpeak_consumption * hc_price
        total_cost = peak_cost + offpeak_cost
        
        # === CALCULS DE POURCENTAGES ===
        # Conversion en pourcentages pour faciliter la compréhension utilisateur
        peak_pct = (peak_consumption / total_consumption * 100) if total_consumption > 0 else 0
        offpeak_pct = (offpeak_consumption / total_consumption * 100) if total_consumption > 0 else 0
        
        # === INTERFACE DÉDIÉE À LA RÉPARTITION HP/HC ===
        st.markdown("""
        <h4 style='text-align: center; margin-top: 20px;'>Répartition HP/HC de votre consommation</h4>
        """, unsafe_allow_html=True)
        
        # Structure en colonnes pour affichage côte à côte des métriques
        cols = st.columns(2)
        
        with cols[0]:
            # Graphique en anneau pour la consommation
            fig_consumption = go.Figure(data=[go.Pie(
                labels=['Heures Pleines', 'Heures Creuses'],
                values=[peak_consumption, offpeak_consumption],
                hole=.4,
                marker_colors=['#FF5252', '#4CAF50']
            )])
            
            fig_consumption.update_layout(
                title="Répartition de la consommation",
                annotations=[dict(text=f'{total_consumption:.1f} kWh', x=0.5, y=0.5, font_size=12, showarrow=False)]
            )
            
            st.plotly_chart(fig_consumption, use_container_width=True)
            
        with cols[1]:
            # Graphique en anneau pour les coûts
            fig_cost = go.Figure(data=[go.Pie(
                labels=['Heures Pleines', 'Heures Creuses'],
                values=[peak_cost, offpeak_cost],
                hole=.4,
                marker_colors=['#FF5252', '#4CAF50']
            )])
            
            fig_cost.update_layout(
                title="Répartition des coûts",
                annotations=[dict(text=f'{total_cost:.1f} CHF', x=0.5, y=0.5, font_size=12, showarrow=False)]
            )
            
            st.plotly_chart(fig_cost, use_container_width=True)
        
    # --------- GRAPHIQUE DES COÛTS MENSUELS ---------
    
    # Dictionnaire de correspondance pour les mois en français
    mois_fr = {
        'Jan': 'Jan', 
        'Feb': 'Fév', 
        'Mar': 'Mar', 
        'Apr': 'Avr',
        'May': 'Mai', 
        'Jun': 'Juin', 
        'Jul': 'Juil', 
        'Aug': 'Août',
        'Sep': 'Sep', 
        'Oct': 'Oct', 
        'Nov': 'Nov', 
        'Dec': 'Déc'
    }
    
    # Adapter l'affichage selon le mode d'analyse
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    
    if analysis_mode == 'single_year':
        # Mode année unique : affichage mensuel pour cette année (inchangé)
        selected_year = st.session_state.get('selected_analysis_year')
        
        # Assurer que tous les mois sont représentés même s'il n'y a pas de données
        all_months = pd.date_range(start=f"{selected_year}-01-01", 
                                  end=f"{selected_year}-12-31", 
                                  freq='M')
        
        # Créer un DataFrame avec tous les mois de l'année
        monthly_df = pd.DataFrame(index=all_months, columns=['Cost', 'Consumption'])
        monthly_df['Cost'] = 0  # Initialiser avec des zéros
        monthly_df['Consumption'] = 0  # Initialiser avec des zéros
        
        # Remplir avec les données réelles disponibles
        actual_monthly_costs = year_data.resample('M')['Cost'].sum()
        actual_monthly_consumption = year_data.resample('M')['Consumption (kWh)'].sum()
        
        for date, cost in actual_monthly_costs.items():
            if date in monthly_df.index:
                monthly_df.at[date, 'Cost'] = cost
        
        for date, consumption in actual_monthly_consumption.items():
            if date in monthly_df.index:
                monthly_df.at[date, 'Consumption'] = consumption
        
        # Créer la figure avec go.Figure pour un meilleur contrôle
        fig = go.Figure()
        
        # Ajouter les barres pour les coûts (axe gauche)
        fig.add_trace(go.Bar(
            x=[d.strftime("%b") for d in monthly_df.index],
            y=monthly_df['Cost'],
            marker_color=selected_year_color,
            name=f'{selected_year}',
            customdata=monthly_df['Consumption'],
            hovertemplate=f'<b>{selected_year}</b><br>' +
                         'Mois: %{x}<br>' +
                         'Coût: %{y:.2f} CHF<br>' +
                         'Consommation: %{customdata:.1f} kWh<br>' +
                         '<extra></extra>'
        ))
        
        # Ajouter une trace invisible pour l'axe droit (échelle kWh)
        fig.add_trace(go.Scatter(
            x=[d.strftime("%b") for d in monthly_df.index],
            y=monthly_df['Consumption'],
            mode='markers',
            marker=dict(color='rgba(0,0,0,0)', size=0),  # Complètement invisible
            name=f'{selected_year} - kWh',
            yaxis='y2',
            showlegend=False,
            hoverinfo='skip'  # Pas d'interaction hover
        ))

        # Configuration de la mise en page
        fig.update_layout(
            title=f"Coûts mensuels pour {selected_year}",
            xaxis_title="Mois",
            plot_bgcolor='white',
            margin=dict(t=50, b=50),
            xaxis=dict(
                tickmode='array',
                tickvals=[d.strftime("%b") for d in monthly_df.index],
                ticktext=[mois_fr[d.strftime("%b")] for d in monthly_df.index],
                tickangle=0,
                showgrid=False
            ),
            # Configuration de l'axe gauche (coûts)
            yaxis=dict(
                title="Coût (CHF)",
                side="left",
                color="#2c3e50",
                showgrid=False
            ),
            # Configuration de l'axe droit (consommation)
            yaxis2=dict(
                title="Consommation (kWh)",
                side="right",
                overlaying="y",
                color="#34495e",
                showgrid=False
            )
        )
        
    else:
        # Mode données complètes : nouveau graphique avec mois côte à côte
        years_to_use = st.session_state.get('years_to_use', available_years)
        
        # Interface utilisateur pour la sélection des années à comparer
        if len(years_to_use) > 3:
            st.markdown("**💰 Sélection des années à comparer :**")
            
            # Proposer par défaut les trois années les plus récentes
            recent_years = sorted(years_to_use)[-3:]
            
            # Sélecteur multiple pour choisir les années
            selected_years_for_comparison = st.multiselect(
                "Choisissez jusqu'à 3 années à afficher pour optimiser la lisibilité :",
                options=sorted(years_to_use, reverse=True),  # Du plus récent au plus ancien
                default=recent_years,
                help="Sélectionnez jusqu'à 3 années pour comparer leurs coûts mensuels côte à côte",
                max_selections=3
            )
            
            # Limiter à 3 années pour la lisibilité (sécurité supplémentaire)
            if len(selected_years_for_comparison) > 3:
                st.warning("⚠️ Maximum 3 années peuvent être affichées. Seules les 3 premières sélectionnées seront utilisées.")
                selected_years_for_comparison = selected_years_for_comparison[:3]
            
            # Si aucune année sélectionnée, utiliser les 3 plus récentes
            if not selected_years_for_comparison:
                selected_years_for_comparison = recent_years
                
        else:
            # Si 3 années ou moins, les utiliser toutes
            selected_years_for_comparison = years_to_use
        
        # Créer la figure
        fig = go.Figure()
        
        # Liste des mois pour l'axe X
        months_list = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 
                      'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
        months_order = list(range(1, 13))  # 1 à 12 pour janvier à décembre
        
        # Créer les données pour chaque année sélectionnée
        for i, year in enumerate(sorted(selected_years_for_comparison)):
            year_monthly_data = year_data[year_data['Year'] == year]
            
            # Créer des dictionnaires pour stocker les coûts et consommations mensuels
            monthly_costs_dict = {}
            monthly_consumption_dict = {}
            
            if not year_monthly_data.empty:
                # Grouper par mois et sommer les coûts et consommations
                monthly_costs = year_monthly_data.groupby(year_monthly_data.index.month)['Cost'].sum()
                monthly_consumption = year_monthly_data.groupby(year_monthly_data.index.month)['Consumption (kWh)'].sum()
                
                # Remplir les dictionnaires avec les données disponibles
                for month_num, cost in monthly_costs.items():
                    monthly_costs_dict[month_num] = cost
                for month_num, consumption in monthly_consumption.items():
                    monthly_consumption_dict[month_num] = consumption
            
            # Créer les listes des coûts et consommations pour tous les mois (0 si pas de données)
            monthly_costs_list = []
            monthly_consumption_list = []
            for month_num in months_order:
                monthly_costs_list.append(monthly_costs_dict.get(month_num, 0))
                monthly_consumption_list.append(monthly_consumption_dict.get(month_num, 0))
            
            # Ajouter la trace pour les coûts (axe gauche)
            fig.add_trace(go.Bar(
                x=months_list,
                y=monthly_costs_list,
                name=f'{year}',
                marker_color=color_map.get(year, '#42A5F5'),
                yaxis='y',
                customdata=monthly_consumption_list,
                hovertemplate=f'<b>{year}</b><br>' +
                             'Mois: %{x}<br>' +
                             'Coût: %{y:.2f} CHF<br>' +
                             'Consommation: %{customdata:.1f} kWh<br>' +
                             '<extra></extra>'
            ))
            
            # Ajouter une trace invisible pour l'axe droit (échelle kWh)
            fig.add_trace(go.Scatter(
                x=months_list,
                y=monthly_consumption_list,
                mode='markers',
                name=f'{year} - kWh',
                marker=dict(color='rgba(0,0,0,0)', size=0),  # Complètement invisible
                yaxis='y2',
                showlegend=False,
                hoverinfo='skip'  # Pas d'interaction hover
            ))
        
        # Configuration de la mise en page
        years_range = f"{min(selected_years_for_comparison)}-{max(selected_years_for_comparison)}" if len(selected_years_for_comparison) > 1 else str(selected_years_for_comparison[0])
        
        fig.update_layout(
            title=f"Comparaison des coûts mensuels ({years_range})",
            xaxis_title="Mois",
            plot_bgcolor='white',
            margin=dict(t=50, b=50),
            barmode='group',  # Important : pour afficher les barres côte à côte
            xaxis=dict(
                tickmode='array',
                tickvals=months_list,
                ticktext=months_list,
                tickangle=0,
                showgrid=False
            ),
            # Configuration de l'axe gauche (coûts)
            yaxis=dict(
                title="Coût (CHF)",
                side="left",
                color="#2c3e50",
                showgrid=False
            ),
            # Configuration de l'axe droit (consommation)
            yaxis2=dict(
                title="Consommation (kWh)",
                side="right",
                overlaying="y",
                color="#34495e",
                showgrid=False
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Ajouter des flèches d'évolution si on compare exactement 2 années
        # Mais seulement pour les mois avec les plus grandes variations (cohérence avec l'analyse détaillée)
        if len(selected_years_for_comparison) == 2:
            year1, year2 = sorted(selected_years_for_comparison)
            year1_data_graph = {}
            year2_data_graph = {}
            
            # Récupérer les données des deux années pour le graphique
            for year in selected_years_for_comparison:
                year_monthly_data = year_data[year_data['Year'] == year]
                if not year_monthly_data.empty:
                    monthly_costs = year_monthly_data.groupby(year_monthly_data.index.month)['Cost'].sum()
                    if year == year1:
                        year1_data_graph = {month_num: cost for month_num, cost in monthly_costs.items()}
                    else:
                        year2_data_graph = {month_num: cost for month_num, cost in monthly_costs.items()}
            
            # Calculer les évolutions et identifier les plus grandes variations
            evolutions_graph = []
            for month_num in range(1, 13):
                if month_num in year1_data_graph and month_num in year2_data_graph:
                    cost1 = year1_data_graph[month_num]
                    cost2 = year2_data_graph[month_num]
                    if cost1 > 0:
                        evolution_pct = ((cost2 - cost1) / cost1) * 100
                        evolutions_graph.append({
                            'month_num': month_num,
                            'evolution_pct': evolution_pct,
                            'cost1': cost1,
                            'cost2': cost2
                        })
            
            # Identifier les mois à mettre en évidence (même logique que l'analyse détaillée)
            months_to_highlight = []
            if evolutions_graph:
                augmentations = [e for e in evolutions_graph if e['evolution_pct'] > 0]
                baisses = [e for e in evolutions_graph if e['evolution_pct'] < 0]
                
                if augmentations:
                    max_augmentation = max(augmentations, key=lambda x: x['evolution_pct'])
                    months_to_highlight.append({
                        'month_num': max_augmentation['month_num'],
                        'type': 'augmentation',
                        'evolution_pct': max_augmentation['evolution_pct'],
                        'cost1': max_augmentation['cost1'],
                        'cost2': max_augmentation['cost2']
                    })
                
                if baisses:
                    max_baisse = min(baisses, key=lambda x: x['evolution_pct'])
                    months_to_highlight.append({
                        'month_num': max_baisse['month_num'],
                        'type': 'baisse',
                        'evolution_pct': max_baisse['evolution_pct'],
                        'cost1': max_baisse['cost1'],
                        'cost2': max_baisse['cost2']
                    })
            
            # Ajouter les flèches uniquement pour les mois à mettre en évidence
            for highlight in months_to_highlight:
                month_name = months_list[highlight['month_num'] - 1]
                evolution_pct = highlight['evolution_pct']
                
                # Déterminer la couleur et le symbole de la flèche
                if highlight['type'] == 'augmentation':
                    arrow_color = '#e74c3c'
                    arrow_symbol = '↗'
                else:  # baisse
                    arrow_color = '#2ecc71'
                    arrow_symbol = '↘'
                
                # Position de la flèche (au-dessus de la barre la plus haute)
                max_cost = max(highlight['cost1'], highlight['cost2'])
                
                # Ajouter l'annotation de la flèche avec le pourcentage
                fig.add_annotation(
                    x=month_name,
                    y=max_cost,
                    text=f"{arrow_symbol}<br><span style='font-size:10px'>{evolution_pct:+.1f}%</span>",
                    showarrow=False,
                    yshift=25,
                    font=dict(color=arrow_color, size=14),
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor=arrow_color,
                    borderwidth=1,
                    borderpad=3
                )
    
    st.plotly_chart(fig)
    
    # Calcul des statistiques clés adaptées au mode d'analyse
    analysis_mode = st.session_state.get('analysis_mode', 'multi_year')
    
    if analysis_mode == 'single_year':
        # Mode année unique - pas d'affichage de statistiques supplémentaires
        pass
    else:
        # Mode données complètes : analyse des tendances mensuelles entre les deux années les plus récentes
        years_to_use = st.session_state.get('years_to_use', available_years)
        
        # Analyse des tendances mensuelles si on a au moins 2 années
        if len(years_to_use) >= 2:
            
            # Prendre les deux années les plus récentes
            recent_years = sorted(years_to_use)[-2:]
            year1, year2 = recent_years[0], recent_years[1]
            
            # Calculer les coûts mensuels pour chaque année
            year1_data = year_data[year_data['Year'] == year1]
            year2_data = year_data[year_data['Year'] == year2]
            
            if not year1_data.empty and not year2_data.empty:
                monthly_costs_year1 = year1_data.groupby(year1_data.index.month)['Cost'].sum()
                monthly_costs_year2 = year2_data.groupby(year2_data.index.month)['Cost'].sum()
                
                # Noms des mois
                month_names = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                              'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
                
                # Calculer les évolutions pour les mois complets dans les deux années
                evolutions = []
                for month_num in range(1, 13):
                    if month_num in monthly_costs_year1.index and month_num in monthly_costs_year2.index:
                        cost1 = monthly_costs_year1[month_num]
                        cost2 = monthly_costs_year2[month_num]
                        if cost1 > 0:  # Éviter division par zéro
                            evolution_pct = ((cost2 - cost1) / cost1) * 100
                            evolution_abs = cost2 - cost1
                            evolutions.append({
                                'month': month_names[month_num - 1],
                                'month_num': month_num,
                                'cost1': cost1,
                                'cost2': cost2,
                                'evolution_pct': evolution_pct,
                                'evolution_abs': evolution_abs
                            })
                
                if evolutions:
                    # Séparer les augmentations et les baisses
                    augmentations = [e for e in evolutions if e['evolution_pct'] > 0]
                    baisses = [e for e in evolutions if e['evolution_pct'] < 0]
                    
                    # Déterminer quelles cartes afficher
                    cards_to_show = []
                    
                    if augmentations:
                        # Plus grande augmentation
                        max_augmentation = max(augmentations, key=lambda x: x['evolution_pct'])
                        cards_to_show.append({
                            'data': max_augmentation,
                            'title': '📈 Plus grande augmentation',
                            'color': '#e74c3c'
                        })
                    
                    if baisses:
                        # Plus grande baisse (en valeur absolue)
                        max_baisse = min(baisses, key=lambda x: x['evolution_pct'])
                        cards_to_show.append({
                            'data': max_baisse,
                            'title': '📉 Plus grande baisse',
                            'color': '#2ecc71'
                        })
                    
                    # Les tendances sont maintenant uniquement affichées via les flèches sur le graphique
                    # La section détaillée des cartes de tendances a été supprimée
                    
                    # Expander avec explication des tendances détectées
                    if cards_to_show:  
                        tooltip_info("Information")
                        with st.expander("À propos des tendances détectées", expanded=False):
                            st.markdown(f"""
                            ### Analyse des tendances
                            
                            Les tendances affichées sur le graphique représentent les **plus grandes variations mensuelles** 
                            entre les années **{year1}** et **{year2}** (les deux années les plus récentes disponibles).
                            
                            #### Comment sont calculées ces tendances :
                            
                            - **Plus grande augmentation** : Le mois où l'augmentation du coût en pourcentage est la plus importante
                            - **Plus grande baisse** : Le mois où la diminution du coût en pourcentage est la plus importante
                            
                            #### Tendances identifiées :
                            """)
                            
                            for card in cards_to_show:
                                data = card['data']
                                title = card['title']
                                color = card['color']
                                
                                evolution_abs = data['evolution_abs']
                                evolution_pct = data['evolution_pct']
                                month = data['month']
                                cost1 = data['cost1']
                                cost2 = data['cost2']
                                
                                st.markdown(f"""
                                <div style="background-color: {color}15; border-left: 3px solid {color}; padding: 10px; margin: 10px 0; border-radius: 5px;">
                                    <strong style="color: {color};">{title}</strong> - {month}<br>
                                    • <strong>{year1}</strong> : {cost1:.2f} CHF<br>
                                    • <strong>{year2}</strong> : {cost2:.2f} CHF<br>
                                    • <strong>Variation</strong> : {evolution_pct:+.1f}% ({evolution_abs:+.2f} CHF)
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.markdown("""
                            💡 **Note** : Ces variations peuvent être dues à des changements d'habitudes, 
                            des conditions météorologiques différentes, ou des modifications dans vos équipements.
                            """)
    

    # ============================================================================
    # PHASE 12: CALCUL DU PRIX MOYEN PONDÉRÉ POUR LE DASHBOARD
    # ============================================================================
    # Cette section finale calcule un prix de référence utilisé par d'autres modules
    # DataWatt, notamment le dashboard principal pour les calculs de coûts globaux

    if tariff_type == "Tarif Unique":
        # === CAS SIMPLE : TARIF UNIQUE ===
        # Le prix moyen est directement le prix configuré (pas de pondération nécessaire)
        avg_price = kwh_price
    else:  # Tarif HP/HC
        # === CAS COMPLEXE : TARIF HP/HC ===
        # Calcul d'une moyenne pondérée basée sur la consommation réelle
        # Cette approche offre une représentation précise du coût effectif
        
        if 'peak_consumption' in locals() and 'offpeak_consumption' in locals() and (peak_consumption + offpeak_consumption) > 0:
            # Utilisation des données déjà calculées pour la visualisation HP/HC
            # Cette optimisation évite les re-calculs inutiles
            total_consumption = peak_consumption + offpeak_consumption
            weighted_avg = (peak_consumption * hp_price + 
                            offpeak_consumption * hc_price) / total_consumption
            avg_price = weighted_avg
        else:
            # Calcul de secours sur l'ensemble des données disponibles
            # Cette branche s'exécute si la visualisation HP/HC n'a pas été affichée
            peak_consumption_all = df_with_cost[df_with_cost['is_peak']]['Consumption (kWh)'].sum()
            offpeak_consumption_all = df_with_cost[~df_with_cost['is_peak']]['Consumption (kWh)'].sum()
            total_consumption_all = peak_consumption_all + offpeak_consumption_all
            
            if total_consumption_all > 0:
                # Pondération basée sur la consommation réelle totale
                weighted_avg = (peak_consumption_all * hp_price + 
                                offpeak_consumption_all * hc_price) / total_consumption_all
                avg_price = weighted_avg
            else:
                # Fallback : moyenne arithmétique simple si aucune donnée de consommation
                # Ce cas ne devrait pas se produire en usage normal
                avg_price = (hp_price + hc_price) / 2
    
    # RETOUR DU PRIX MOYEN POUR INTÉGRATION DANS L'ÉCOSYSTÈME DATAWATT
    return avg_price

# ============================================================================
# NOTES D'INTÉGRATION ET DE MAINTENANCE
# ============================================================================
"""
INTÉGRATION DANS DATAWATT:
- Ce module est intégré dans le dashboard principal via src/dashboard/
- Les paramètres tarifaires sont gérés centralement dans la sidebar
- La valeur retournée (avg_price) est utilisée pour les calculs globaux
- Les visualisations s'harmonisent avec le design system DataWatt

DÉPENDANCES EXTERNES:
- streamlit : Interface utilisateur et gestion d'état
- pandas : Manipulation des données temporelles
- plotly : Génération des graphiques interactifs
- src.textual.tools : Fonctions utilitaires et palettes de couleurs

POINTS D'ATTENTION POUR LA MAINTENANCE:
- Les paramètres HP/HC doivent rester cohérents avec les standards suisses
- Les palettes de couleurs doivent être synchronisées avec les autres modules
- Les calculs de moyenne pondérée sont critiques pour la précision financière
- L'interface doit rester accessible même pour des utilisateurs non-techniques

ÉVOLUTIONS POSSIBLES:
- Intégration de tarifs variables (été/hiver)
- Support des tarifs réseau différenciés
- Connexion avec APIs des fournisseurs d'énergie
- Alertes automatiques sur les variations tarifaires importantes
- Export des analyses en PDF pour archivage

PERFORMANCE:
- Les calculs sont optimisés pour des datasets multi-années
- La classification HP/HC utilise des opérations vectorisées pandas
- Les visualisations sont générées à la demande pour économiser la mémoire
"""