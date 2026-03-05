import streamlit as st

def intro():
    st.markdown("""
    ## Bienvenue sur DataWatt

    DataWatt est une application conçue pour analyser et visualiser les données de consommation énergétique. 
    Elle vous permet de :

    - Visualiser vos données de consommation énergétique sous forme de graphiques interactifs.
    - Comparer votre consommation avec d'autres utilisateurs.
    - Estimer votre autoconsommation et détecter les anomalies de consommation.
    - Utiliser des outils d'intelligence artificielle pour prédire vos consommations futures.

    ### Comment utiliser l'application

    1. **Sélectionnez votre type d'utilisateur** : Choisissez entre "Privé" et "SMB" dans la barre latérale.
    2. **Téléchargez vos données** : Utilisez le formulaire pour télécharger vos données de consommation.
    3. **Explorez les graphiques** : Visualisez vos données à travers différents graphiques et analyses.
    4. **Comparez et analysez** : Comparez votre consommation avec d'autres utilisateurs et analysez les tendances.
                
    Nous espérons que vous trouverez DataWatt utile pour mieux comprendre et gérer votre consommation énergétique.
    """)  

def key_features():
    st.markdown("""
    <div style="max-width: 800px; margin: 0 auto;">
        <p style="text-align: left; margin-left: 10%; margin-right: 20%;">📤 <span style="color: #e6321e; font-weight: bold;">Chargez</span> facilement votre courbe de charge au format Excel</p>
        <p style="text-align: right; margin-left: 20%; margin-right: 10%;">📊 <span style="color: #e6321e; font-weight: bold;">Explorez</span> vos données avec des graphiques interactifs</p>
        <p style="text-align: left; margin-left: 10%; margin-right: 20%;">📈 <span style="color: #e6321e; font-weight: bold;">Analysez</span> votre consommation quotidienne et hebdomadaire</p>
        <p style="text-align: right; margin-left: 20%; margin-right: 10%;">🔍 <span style="color: #e6321e; font-weight: bold;">Identifiez</span> les anomalies et pics de consommation</p>
        <p style="text-align: left; margin-left: 10%; margin-right: 20%;">📉 <span style="color: #e6321e; font-weight: bold;">Comparez</span> votre consommation avec des références</p>
        <p style="text-align: right; margin-left: 20%; margin-right: 10%;">💰 <span style="color: #e6321e; font-weight: bold;">Optimisez</span> votre consommation pour réduire vos coûts</p>
    </div>
    """, unsafe_allow_html=True)


def flashy_keywords():
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; margin: 10px 0; text-align: center;">
        <div>
            <h2 style="color: #e6321e; font-size: 2em; font-weight: bold; margin: 0;">DEPOSEZ,   VISUALISEZ,   ANALYSEZ</h2>
        </div>
 
    </div>
    """, unsafe_allow_html=True)


def header_banner():
    """
    Affiche un bandeau rouge en haut de page avec le titre DataWatt et le slogan
    """
    st.markdown("""
    <div style="
        background-color: #e6321e;
        color: white;
        padding: 10px 20px;
        margin: -1rem -1rem 2rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="
            font-size: 2.2em;
            font-weight: bold;
            margin: 0;
        ">
            DataWatt
        </div>
        <div style="
            font-size: 1.3em;
            font-weight: bold;
            letter-spacing: 2px;
            margin: 0;
        ">
            DEPOSEZ,   VISUALISEZ,   ANALYSEZ
        </div>
    </div>
    """, unsafe_allow_html=True)


def section_title(title_text):
    """
    Affiche un titre de section stylisé de manière cohérente
    
    Args:
        title_text (str): Le texte du titre de la section
    """
    st.markdown(f"""
    <div style="margin: 32px 0 17px 0;">
        <h3 style="text-align: center; color: #818081; padding-bottom: 8px; border-bottom: 2px solid #818081;">
            {title_text}
        </h3>
    </div>
    """, unsafe_allow_html=True)



def side_info():   
    # Expander pour les informations supplémentaires
    with st.sidebar.expander("### Informations supplémentaires"):
        # SIE-TVT SA information
        st.markdown("""
        #### SIE-TVT SA
        DataWatt est une application développée grâce à une collaboration entre l'EPFL et SIE SA.
        """)
        
        # Privacy information
        st.markdown("""
        #### Confidentialité
        Vos données sont sécurisées et ne seront pas partagées avec des tiers sans votre consentement.
        """)
        
        # Calculowatt information
        st.markdown("""
        #### Autres outils
        SIE SA propose également [Calculowatt](https://calculowatt.sie.ch/), un outil de calcul de consommation énergétique pour les particuliers et entreprises.
        
        Découvrez aussi le [diagnostic énergétique CECB](https://www.sie.ch/prestations/diagnostic-energetique-cecb-817) pour une analyse complète de votre bâtiment.
        """)
    
    # Section Support retirée (en haut dans un expander)


def load_curve():
    
    # Put the detailed explanation in an expander
    with st.expander("À propos de la courbe de charge"):
        st.markdown("""
        La courbe de charge est un graphique qui représente la consommation d'énergie électrique en fonction du temps. 
        Elle permet de visualiser la variation de la consommation sur une période donnée, généralement une journée ou une semaine.

        ### Comment interpréter la courbe de charge

        - **Périodes de pointe** : Les périodes où la consommation est la plus élevée. Elles peuvent indiquer des moments de forte activité ou l'utilisation d'appareils énergivores.
        - **Périodes creuses** : Les périodes où la consommation est la plus faible.
        - **Variations saisonnières** : Les changements de consommation en fonction des saisons, par exemple une augmentation de la consommation en hiver due au chauffage
                    (électrique ou pompe à chaleur (PAC)) ou en été dû à la climatisation.

        """)

def heatmap_info():
    
    # Put the detailed explanation in an expander
    with st.expander("À propos de la cartographie de consommation"):
        st.markdown("""
        La cartographie de consommation est un graphique qui représente la consommation d'énergie sur l'année. 

        ### Comment interpréter la cartographie de consommation

        - **Pic de consommation** : Les zones de la cartographie où la couleur est la plus rouge représentent les périodes de pic de consommation.
        - **Consommation moyenne** : Les zones de la cartographie où la couleur est plus jaune-orange représentent les périodes de consommation moyenne.
        - **Consommation faible** : Les zones de la cartographie où la couleur est la plus verte représentent les périodes de consommation faible.

        En analysant la cartographie de consommation, vous pouvez identifier les tendances de consommation et les habitudes de consommation de votre foyer ou de votre entreprise, selon un jour de la semaine moyen et l'heure de la journée.  
                    
        ### Cartographie de consommation hebdomadaire
                    
        - Cette cartographie montre le profil de consommation typique en moyenne sur 2 années. Les pics (notés 'Pic!' sur le graphique) correspondent aux 3 heures de consommation les plus élevées 
            de la semaine type. Les consommations par heure correspondent à la somme de quatre quarts d'heure. Par exemple, la valeur pour 00:00 du lundi correspond à votre consommation 
            moyenne entre 00:00 et 01:00, moyennée pour tous les lundis de la période où la consommation est disponible.  
                    
        ### Cartographie de consommation journalière
        - Cette cartographie représente la consommation journalière moyenne calculée sur 2 années. Chaque cellule montre la moyenne de consommation journalière pour ce jour du mois sur 
            toutes les années disponibles. Les pics correspondent aux 3 jours avec la consommation journalière moyenne la plus élevée.
        """)


def cost_trends_info():
    # Display a brief introduction outside the expander
    st.markdown("L'analyse des tendances de coûts vous aide à comprendre l'évolution de vos dépenses énergétiques dans le temps.")
    
    # Put the detailed explanation in an expander
    with st.expander("À propos de l'analyse des tendances de coûts"):
        st.markdown("""
        L'analyse des tendances compare l'évolution de vos coûts énergétiques entre la première et la dernière année de données disponibles.

        ### Interprétation des tendances

        - **📉 Baisse** (< -5%) : Vos coûts ont diminué de manière significative. Cela peut indiquer une amélioration de l'efficacité énergétique, des changements d'habitudes ou une réduction de la consommation.
        - **➡️ Stable** (-5% à +5%) : Vos coûts sont restés relativement constants. Cela suggère une consommation stable et prévisible.
        - **📈 Augmentation** (> +5%) : Vos coûts ont augmenté de manière notable. Cela peut être dû à une hausse de la consommation, l'ajout d'équipements ou des changements d'habitudes.

        ### Facteurs influençant les tendances

        - **Changements d'habitudes** : Télétravail, nouveaux équipements, modification des horaires
        - **Évolutions saisonnières** : Variations dues au chauffage/climatisation
        - **Améliorations énergétiques** : Isolation, changement d'équipements plus efficaces
        - **Composition du foyer** : Nombre d'occupants, âge des habitants

        Cette analyse vous aide à identifier si vos efforts d'économie d'énergie portent leurs fruits ou si des actions correctives sont nécessaires.
        """)


def high_consumption_point_plot():
    st.markdown("""

    Le graphique des points de consommation élevée affiche les périodes où la consommation d'énergie est très supérieure à la moyenne. 
    Il permet d'identifier les moments où la consommation est anormalement élevée et de prendre des mesures pour réduire la consommation.

    ### Comment interpréter le graphique des points de consommation élevée

    - **Points de consommation élevée** : Les points rouges sur le graphique représentent les périodes où la consommation est supérieure à la moyenne.
    - **Analyse des points** : En cliquant sur un point, vous pouvez obtenir des informations détaillées sur la période de consommation élevée.
    - **Actions à prendre** : En identifiant les points de consommation élevée, vous pouvez prendre des mesures pour réduire la consommation et optimiser l'utilisation de l'énergie.

    En analysant le graphique des points de consommation élevée, vous pouvez améliorer l'efficacité énergétique de votre foyer ou de votre entreprise et réduire vos coûts énergétiques.
    """)
