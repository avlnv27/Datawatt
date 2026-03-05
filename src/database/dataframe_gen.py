"""
=====================================================================================
                    MODULE DE TRAITEMENT DES FICHIERS DE COURBES DE CHARGE
=====================================================================================
Fichier central pour le traitement et la standardisation des fichiers de consommation énergétique
uploadés dans l'application DataWatt.

RESPONSABILITÉS PRINCIPALES:
1. Réception et validation des fichiers uploadés (CSV/XLSX)
2. Détection automatique du format et du fournisseur d'énergie
3. Standardisation vers le format interne de l'application
4. Nettoyage et validation des données temporelles
5. Gestion de l'état de session pour éviter les retraitements

FORMATS SUPPORTÉS ACTUELLEMENT:
- Format SIE SA : colonnes 'Date & Heure', 'Consommation', 'Excédent', 'Autoconsommation'
- Format Romande Energie : colonnes 'Date', 'Consommation kWh (...)', 'Site Production kWh (...)'
- Format standard : colonnes 'Datetime', 'Consumption (kWh)'

STRUCTURE STANDARDISÉE DE SORTIE:
- Index temporel : 'Datetime' (DatetimeIndex pandas)
- Consommation principale : 'Consumption (kWh)' 
- Données solaires optionnelles : 'Excedent', 'Autoconsumption', 'Total Consumption (kWh)'
- Colonnes d'analyse : 'Year', 'Month', 'Day', 'Hour', 'Week', 'DayName'

PISTES D'AMÉLIORATION FUTURES:
1. Support de nouveaux fournisseurs (Groupe E, SIG, EWZ, etc.)
2. Détection automatique avancée par patterns de données
3. Support multi-langues (DE, IT, EN) pour colonnes
4. Validation de cohérence temporelle renforcée
5. Support des formats JSON/XML pour APIs temps réel
6. Gestion des données météorologiques associées
7. Support des courbes de charge industrielles (HTA/HTB)  
8. Lier cette partie du code à une API et au portail SIE SA directement

EXTENSION POUR NOUVEAUX FORMATS:
Pour ajouter un nouveau format de fichier :
1. Créer une fonction process_[fournisseur]_file() similaire à process_romande_energie_file()
2. Ajouter la détection dans gen_pdf() avant le traitement CSV standard
3. Mapper les colonnes vers le format standardisé
4. Tester avec des fichiers réels du fournisseur
5. Documenter le format dans les expected_columns

AUTEURS: Sven Hominal & Quentin Poindextre (EPFL) - SIE SA
DATE: Février-Août 2025
=====================================================================================
"""

import pandas as pd
import streamlit as st  

# ============================================================================
# FONCTIONS DE TRAITEMENT SPÉCIALISÉES POUR ROMANDE ENERGIE (TEST)
# ============================================================================

def process_romande_energie_file(uploaded_file):
    """
    Traite un fichier CSV au format Romande Energie et le convertit au format standard utilisé par l'application.
    
    SPÉCIFICITÉS FORMAT ROMANDE ENERGIE:
    - Délimiteur CSV : point-virgule (;)
    - Colonnes typiques : 'Date', 'Consommation kWh (XXXXXXXXX)', 'Site Production kWh (XXXXXXXXX)'
    - Identifiants entre parenthèses dans les noms de colonnes (numéro de compteur)
    - Données solaires optionnelles dans 'Site Production kWh'
    
    AMÉLIORATIONS FUTURES POUR CE FORMAT:
    1. Support des fichiers multi-compteurs (plusieurs colonnes de consommation)
    2. Détection automatique de l'encodage (UTF-8 vs ISO-8859-1)
    3. Gestion des métadonnées Romande Energie (adresse, type de compteur)
    4. Support des données de facturation intégrées
    
    Args:
        uploaded_file: Objet fichier de Streamlit (st.uploaded_file)
    
    Returns:
        tuple: (DataFrame standardisé, booléen_format_reconnu)
            - DataFrame avec colonnes 'Datetime', 'Consumption (kWh)', 'Excedent' optionnel
            - True si format Romande Energie détecté, False sinon
    
    Raises:
        Exception: En cas d'erreur de lecture ou de conversion des données
    """
    try:
        # === PHASE 1: DÉTECTION DU FORMAT ROMANDE ENERGIE ===
        # Lecture d'échantillon pour identifier les colonnes caractéristiques
        header_sample = pd.read_csv(uploaded_file, delimiter=';', nrows=1)
        uploaded_file.seek(0)  # Réinitialiser le pointeur du fichier pour lecture complète
        
        # Pattern de détection : colonnes avec 'Consommation kWh (' + identifiant + ')'
        romande_energie_format = any(col.startswith('Consommation kWh (') for col in header_sample.columns)
        
        if not romande_energie_format:
            return None, False
        
        # === PHASE 2: LECTURE ET NETTOYAGE DES DONNÉES ===
        # Format confirmé, procéder au traitement complet
        df = pd.read_csv(uploaded_file, delimiter=';')
        
        # === PHASE 3: NORMALISATION DES NOMS DE COLONNES ===
        # Suppression des identifiants entre parenthèses pour standardisation
        new_columns = {}
        for col in df.columns:
            if '(' in col and ')' in col:
                # Extraire le nom de base en supprimant l'identifiant (XXXXXXXXX)
                base_name = col.split('(')[0].strip()
                new_columns[col] = base_name
        
        df.rename(columns=new_columns, inplace=True)
        
        # === PHASE 4: MAPPING VERS LE FORMAT STANDARDISÉ DATAWATT ===
        # Correspondance entre colonnes Romande Energie et format interne
        column_mapping = {
            'Date': 'Datetime',                               # Colonne temporelle principale
            'Consommation kWh': 'Consumption (kWh)',         # Consommation du réseau
            'Site Production kWh': 'Excedent'                # Production solaire (pas vraiment excédent mais compatible)
            # NOTE: Site Production = Excédent + Autoconsommation dans le format Romande Energie
            # TODO: Séparer correctement Production vs Excédent vs Autoconsommation
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # === PHASE 5: CONVERSION ET VALIDATION DES TYPES DE DONNÉES ===
        # Assurer la cohérence des types pour les calculs ultérieurs
        df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
        df['Consumption (kWh)'] = pd.to_numeric(df['Consumption (kWh)'], errors='coerce')
        
        # Traitement optionnel des données solaires si présentes
        if 'Excedent' in df.columns:
            df['Excedent'] = pd.to_numeric(df['Excedent'], errors='coerce')
        
        return df, True
    
    except Exception as e:
        # Logging de l'erreur pour debugging (console développeur)
        print(f"Erreur lors du traitement du fichier Romande Energie: {e}")
        return None, False

# ============================================================================
# FONCTION PRINCIPALE DE TRAITEMENT DES FICHIERS UPLOADÉS
# ============================================================================

def gen_pdf():
    """
    Fonction principale de gestion des uploads de fichiers et de génération du DataFrame standardisé.
    
    ARCHITECTURE FONCTIONNELLE:
    Cette fonction implémente une machine à états pour gérer le cycle de vie des fichiers :
    1. État initial : Aucun fichier (upload requis)
    2. État chargé : Fichier traité et en cache
    3. État rechargement : Nouveau fichier détecté
    
    GESTION DE L'ÉTAT DE SESSION:
    - current_file_name : Nom du fichier actuellement traité
    - current_file_data : DataFrame en cache pour éviter les retraitements
    - file_processed : Flag indiquant si un fichier a été traité avec succès
    
    FORMATS DÉTECTÉS AUTOMATIQUEMENT:
    1. Romande Energie (CSV avec ';' et colonnes spécifiques)
    2. SIE SA (Excel/CSV avec 'Date & Heure' et 'Consommation')
    3. Format standard (colonnes 'Datetime' et 'Consumption (kWh)')
    
    PIPELINE DE TRAITEMENT:
    Upload → Détection format → Conversion → Validation → Enrichissement → Cache
    
    AMÉLIORATIONS FUTURES:
    1. Support batch processing (multiple fichiers simultanés)
    2. Détection automatique de l'encodage des fichiers CSV
    3. Validation de cohérence temporelle (gaps, doublons)
    4. Support des fuseaux horaires
    5. Intégration avec APIs fournisseurs d'énergie
    6. Support des formats JSON/XML pour IoT
    7. Compression automatique pour gros fichiers
    
    Returns:
        tuple: (DataFrame_traité, flag_nouveau_fichier)
            - DataFrame avec données standardisées et enrichies ou None
            - 1 si nouveau fichier traité, 0 si utilisation du cache
    
    Raises:
        Diverses exceptions gérées avec messages d'erreur utilisateur via st.error()
    """
    # === INITIALISATION DE L'ÉTAT DE SESSION ===
    # Gestion de l'état pour éviter les retraitements et améliorer les performances
    if 'current_file_name' not in st.session_state:
        st.session_state['current_file_name'] = None
    if 'current_file_data' not in st.session_state:
        st.session_state['current_file_data'] = None
    if 'file_processed' not in st.session_state:
        st.session_state['file_processed'] = False
        
    # === INTERFACE D'UPLOAD AVEC VALIDATION ===
    # Configuration de l'uploader avec restrictions de format pour sécurité
    uploaded_file = st.file_uploader("Déposez votre courbe de charge ici", 
                                    type=["csv", "xlsx"], 
                                    key="load_curve_uploader",
                                    help="Formats acceptés : CSV (délimiteur ';') ou Excel (.xlsx)")
    
    # ========================================================================
    # MACHINE À ÉTATS POUR LA GESTION DES FICHIERS
    # ========================================================================
    
    # === ÉTAT 1: AUCUN FICHIER UPLOADÉ ET AUCUN TRAITEMENT PRÉCÉDENT ===
    if uploaded_file is None and not st.session_state['file_processed']:
        # Pas de fichier par défaut - l'utilisateur doit charger un fichier
        # ANCIEN COMPORTEMENT (commenté) : Chargement automatique d'un fichier de démo
        # test2 = pd.read_excel('fichiers_test/groupe3_pod_01040.xlsx')
        # st.session_state['current_file_name'] = 'default_file'
        # st.session_state['file_processed'] = True
        # flag = 1
        
        # NOUVEAU COMPORTEMENT : Forcer l'upload utilisateur pour professionnalisme
        return None, 0
    
    # === ÉTAT 2: RETOUR AU CACHE (FICHIER DÉJÀ TRAITÉ) ===
    elif uploaded_file is None and st.session_state['file_processed']:
        # Optimisation : Retourner le DataFrame précédemment stocké sans retraitement
        return st.session_state['current_file_data'], 0
    
    # === ÉTAT 3: MÊME FICHIER UPLOADÉ (ÉVITER RETRAITEMENT) ===
    elif uploaded_file is not None and uploaded_file.name == st.session_state['current_file_name']:
        # Cache hit : Même fichier, retourner les données en cache
        return st.session_state['current_file_data'], 0
    
    # === ÉTAT 4: NOUVEAU FICHIER DÉTECTÉ (TRAITEMENT COMPLET) ===
    elif uploaded_file is not None:
        # Mise à jour du tracking du fichier courant
        st.session_state['current_file_name'] = uploaded_file.name
        
        try:
            # ================================================================
            # PHASE DE DÉTECTION ET LECTURE DU FORMAT
            # ================================================================
            
            # Dispatcher selon l'extension du fichier
            if uploaded_file.name.endswith('.csv'):
                # === TRAITEMENT CSV AVEC DÉTECTION AUTOMATIQUE ===
                
                # Tentative 1: Format Romande Energie (priorité car plus spécifique)
                test2, is_romande_format = process_romande_energie_file(uploaded_file)
                
                # Tentative 2: Format CSV standard si pas Romande Energie
                if not is_romande_format:
                    uploaded_file.seek(0)  # Reset pointeur pour nouvelle lecture
                    # TODO: Ajouter ici d'autres process_[fournisseur]_file() pour nouveaux formats
                    # Exemple: test2, is_groupe_e_format = process_groupe_e_file(uploaded_file)
                    # Exemple: test2, is_sig_format = process_sig_file(uploaded_file)
                    
                    # Fallback : Lecture CSV standard avec délimiteur point-virgule
                    test2 = pd.read_csv(uploaded_file, delimiter=';', dayfirst=True)
            else:
                # === TRAITEMENT EXCEL ===
                # Format Excel généralement utilisé par SIE SA et autres fournisseurs locaux
                test2 = pd.read_excel(uploaded_file)
                # TODO: Ajouter détection de sous-formats Excel selon métadonnées
            
            # ================================================================
            # PHASE DE VALIDATION DU FORMAT
            # ================================================================
            
            # Définition des colonnes acceptées pour compatibilité multi-fournisseurs
            expected_columns = ['Date & Heure', 'Datetime', 'Date']  # Colonnes temporelles
            expected_consumption_columns = ['Consommation', 'Consumption (kWh)', 'Consommation kWh']  # Colonnes de consommation
            
            # TODO: Étendre cette liste pour nouveaux fournisseurs
            # Exemples pour extension future :
            # - Groupe E : 'Date/Heure', 'Energie Active (kWh)'
            # - SIG Genève : 'Timestamp', 'Consommation [kWh]'
            # - EWZ Zurich : 'Zeitstempel', 'Verbrauch kWh'
            
            # Validation de la présence des colonnes essentielles
            has_date_column = any(col in test2.columns for col in expected_columns)
            has_consumption_column = any(col in test2.columns for col in expected_consumption_columns)
            
            if not has_date_column or not has_consumption_column:
                # === GESTION D'ERREUR : FORMAT NON RECONNU ===
                st.error(f"""
                ❌ **Format de fichier non reconnu**
                
                Le fichier '{uploaded_file.name}' ne correspond pas aux formats acceptés par l'application.
                
                **Colonnes détectées dans votre fichier :**
                {', '.join(test2.columns.tolist())}
                
                **Formats acceptés actuellement :**
                - **Format SIE SA** : colonnes 'Date & Heure' et 'Consommation'
                - **Format Romande Energie** : colonnes 'Date' et 'Consommation kWh (...)'
                - **Format standard** : colonnes 'Datetime' et 'Consumption (kWh)'
                
                **Pour ajouter votre format :**
                1. Contactez le support technique avec un échantillon de fichier
                2. Spécifiez votre fournisseur d'énergie
                3. Le format sera ajouté dans une prochaine version
                
                **Solutions immédiates :**
                1. Vérifiez que votre fichier contient bien des données de consommation énergétique
                2. Renommez vos colonnes selon un format supporté
                3. Exportez depuis votre portail fournisseur au format SIE SA ou Romande Energie
                """)
                
                # Reset de l'état pour permettre un nouvel essai
                st.session_state['current_file_name'] = None
                st.session_state['file_processed'] = False
                return None, 0
                
            # Format validé, marquer comme traité
            st.session_state['file_processed'] = True
            flag = 1
            
        except Exception as e:
            # === GESTION D'ERREUR : PROBLÈME DE LECTURE ===
            st.error(f"""
            ❌ **Erreur lors du chargement du fichier**
            
            Une erreur s'est produite lors de la lecture du fichier '{uploaded_file.name}' :
            
            **Erreur technique :** {str(e)}
            
            **Causes possibles et solutions :**
            1. **Fichier corrompu** → Réexportez depuis votre portail fournisseur
            2. **Format CSV incorrect** → Vérifiez le délimiteur (';' requis)
            3. **Encodage incompatible** → Sauvegardez en UTF-8
            4. **Fichier Excel protégé** → Supprimez la protection
            5. **Taille excessive** → Limitez à 2 ans de données maximum
            
            **Support technique :** Si le problème persiste, contactez support@sie.ch
            """)
            
            # Reset de l'état pour permettre un nouvel upload
            st.session_state['current_file_name'] = None
            st.session_state['file_processed'] = False
            return None, 0
    
    # ========================================================================
    # PHASE DE STANDARDISATION DES COLONNES
    # ========================================================================
    
    # === NORMALISATION DES NOMS DE COLONNES SIE SA ===
    # Transformation des colonnes SIE SA vers format standardisé
    if 'Date & Heure' in test2.columns:
        # === TRAITEMENT SPÉCIFIQUE DU FORMAT SIE SA ===
        # Suppression des caractères parasites en fin de colonne de date (généralement " (UTC)")
        test2['Date & Heure'] = test2['Date & Heure'].str[:-9]
        
        # Mapping des colonnes SIE SA vers le schéma standardisé de l'application
        # Colonnes essentielles (OBLIGATOIRES)
        test2.rename(columns={'Date & Heure': 'Datetime'}, inplace=True)
        test2.rename(columns={'Consommation': 'Consumption (kWh)'}, inplace=True)
        
        # Colonnes optionnelles (selon disponibilité dans le fichier)
        test2.rename(columns={'Unité': 'Unite'}, inplace=True)  # Unité de mesure
        test2.rename(columns={'Temp de mesure': 'Intervalle'}, inplace=True)  # Intervalle de mesure
        test2.rename(columns={'Excédent': 'Excedent'}, inplace=True)  # Production excédentaire
        test2.rename(columns={'Totalité Autoconsommation': 'Autoconsumption'}, inplace=True)  # Autoconsommation
        
        # TODO: Ajouter d'autres mappings pour nouveaux fournisseurs
        # Exemples futurs :
        # - Groupe E : {'Horodate': 'Datetime', 'Consommation active': 'Consumption (kWh)'}
        # - SIG : {'Date/Heure': 'Datetime', 'Energie [kWh]': 'Consumption (kWh)'}
    
    # ========================================================================
    # VALIDATION POST-TRAITEMENT
    # ========================================================================
    
    # === CONTRÔLE D'INTÉGRITÉ DES COLONNES ESSENTIELLES ===
    if 'Datetime' not in test2.columns or 'Consumption (kWh)' not in test2.columns:
        st.error(f"""
        ❌ **Erreur de traitement du fichier**
        
        Après traitement, les colonnes essentielles sont manquantes :
        - Colonne de date manquante : {'❌' if 'Datetime' not in test2.columns else '✅'}
        - Colonne de consommation manquante : {'❌' if 'Consumption (kWh)' not in test2.columns else '✅'}
        
        **Colonnes disponibles après traitement :**
        {', '.join(test2.columns.tolist())}
        
        **Diagnostic technique :**
        Cette erreur indique un problème lors de la transformation des colonnes.
        Cela peut signifier que le format du fichier a évolué ou qu'un nouveau format non supporté a été détecté.
        
        **Actions recommandées :**
        1. Vérifiez la structure de votre fichier source
        2. Contactez le support technique avec ce fichier pour analyse
        3. Utilisez un fichier d'un format confirmé compatible
        """)
        
        # Reset complet de l'état pour permettre un nouvel upload
        st.session_state['current_file_name'] = None
        st.session_state['file_processed'] = False
        st.session_state['current_file_data'] = None
        return None, 0

    # ========================================================================
    # PHASE DE CONVERSION ET NETTOYAGE DES DONNÉES
    # ========================================================================
    
    # === CONVERSION DES TYPES DE DONNÉES ===
    # Transformation des colonnes en types appropriés pour l'analyse
    # Conversion de la colonne Datetime avec gestion d'erreurs sophistiquée
    test2['Datetime'] = pd.to_datetime(test2['Datetime'], errors='coerce')
    print(test2.head())  # Debug : Affichage des premières lignes pour validation

    # Conversion de la colonne de consommation en numérique
    test2['Consumption (kWh)'] = pd.to_numeric(test2['Consumption (kWh)'], errors='coerce')

    # === VALIDATION DE LA QUALITÉ DES DONNÉES ===
    # Comptage des valeurs valides après conversion pour détection de problèmes majeurs
    valid_datetime_count = test2['Datetime'].notna().sum()
    valid_consumption_count = test2['Consumption (kWh)'].notna().sum()
    
    if valid_datetime_count == 0 or valid_consumption_count == 0:
        st.error(f"""
        ❌ **Données invalides détectées**
        
        Le fichier ne contient pas de données valides après conversion :
        - Dates valides : {valid_datetime_count}/{len(test2)} ({valid_datetime_count/len(test2)*100:.1f}%)
        - Valeurs de consommation valides : {valid_consumption_count}/{len(test2)} ({valid_consumption_count/len(test2)*100:.1f}%)
        
        **Problèmes possibles et solutions :**
        1. **Format de date incompatible**
           - Formats supportés : DD/MM/YYYY HH:MM, YYYY-MM-DD HH:MM, DD.MM.YYYY HH:MM
           - Solution : Vérifiez le format de vos dates
        
        2. **Valeurs de consommation non numériques**
           - Caractères parasites (lettres, symboles spéciaux)
           - Solution : Nettoyez vos données ou exportez depuis votre portail fournisseur
        
        3. **Séparateur décimal incorrect**
           - Utilisez '.' ou ',' selon votre configuration régionale
           - Solution : Vérifiez les paramètres d'export de votre fichier
        
        4. **Encodage de caractères**
           - Problème d'accents ou caractères spéciaux
           - Solution : Sauvegardez en UTF-8
        
        **Support :** Contactez support@sie.ch avec votre fichier pour analyse approfondie
        """)
        
        # Reset complet pour nouvel essai
        st.session_state['current_file_name'] = None
        st.session_state['file_processed'] = False
        st.session_state['current_file_data'] = None
        return None, 0

    # ========================================================================
    # PHASE DE NETTOYAGE ET PRÉPARATION DES DONNÉES
    # ========================================================================
    
    # === SUPPRESSION DES LIGNES AVEC DONNÉES MANQUANTES ===
    # Suppression des lignes avec valeurs de consommation manquantes (NaN)
    # Ces lignes peuvent provenir d'erreurs de mesure ou de transmission
    test2.dropna(subset=['Consumption (kWh)'], inplace=True)

    # === CORRECTION DES TIMESTAMPS MINUIT ===
    # Ajustement temporel pour les mesures de minuit (standard énergétique)
    # Les mesures à 00:00:00 sont généralement attribuées au jour précédent
    test2.loc[test2['Datetime'].dt.time == pd.Timestamp('00:00:00').time(), 'Datetime'] -= pd.Timedelta(days=1)

    # === DÉFINITION DE L'INDEX TEMPOREL ===
    # Transformation en série temporelle pour analyses avancées
    test2.set_index('Datetime', inplace=True)

    # ========================================================================
    # PHASE D'ENRICHISSEMENT DES DONNÉES
    # ========================================================================
    
    # === GÉNÉRATION DES COLONNES TEMPORELLES ===
    # Ajout de dimensions temporelles pour analyses par période
    test2['Year'] = test2.index.year          # Année (pour analyses annuelles)
    test2['Month'] = test2.index.month        # Mois (pour saisonnalité)
    test2['Day'] = test2.index.day            # Jour du mois
    test2['Hour'] = test2.index.hour          # Heure (pour profils journaliers)
    test2['Week'] = test2.index.isocalendar().week    # Numéro de semaine ISO
    test2['DayName'] = test2.index.day_name() # Nom du jour (Monday, Tuesday, etc.)
    
    # === OPTION : LOCALISATION FRANÇAISE (DÉSACTIVÉE) ===
    # Mapping pour obtenir les noms de jours en français si souhaité
    # TODO: Ajouter support multilingue avec détection locale automatique
    # jour_map = {
    #     'Monday': 'Lundi',
    #     'Tuesday': 'Mardi',
    #     'Wednesday': 'Mercredi',
    #     'Thursday': 'Jeudi',
    #     'Friday': 'Vendredi',
    #     'Saturday': 'Samedi',
    #     'Sunday': 'Dimanche'
    # }
    # test2['JourNom'] = test2['DayName'].map(jour_map)

    # ========================================================================
    # TRAITEMENT DES COLONNES OPTIONNELLES (AUTOCONSOMMATION & PRODUCTION)
    # ========================================================================
    
    # === GESTION DE L'AUTOCONSOMMATION ===
    if 'Autoconsumption' in test2.columns:
        # === TRAITEMENT DE L'AUTOCONSOMMATION PHOTOVOLTAÏQUE ===
        # Conversion en numérique pour calculs (gestion des valeurs corrompues)
        test2['Autoconsumption'] = pd.to_numeric(test2['Autoconsumption'], errors='coerce')
        
        # Création de la consommation totale (réseau + autoconsommation)
        # Formule : Consommation_Totale = Consommation_Réseau + Autoconsommation_PV
        test2['Total Consumption (kWh)'] = test2['Consumption (kWh)'] + test2['Autoconsumption']
        print('Autoconsommation traitée avec succès')  # Debug confirmation

    # ========================================================================
    # PHASE DE NETTOYAGE DES VALEURS ABERRANTES
    # ========================================================================
    
    # === FILTRAGE DES MICRO-VALEURS ===
    # Suppression des valeurs inférieures au seuil de précision des compteurs
    energy_columns = ['Consumption (kWh)']  # Colonnes énergétiques de base
    
    # Ajout conditionnel des colonnes optionnelles selon disponibilité
    if 'Excedent' in test2.columns:
        # Conversion et ajout de la production excédentaire (injection réseau)
        test2['Excedent'] = pd.to_numeric(test2['Excedent'], errors='coerce')
        energy_columns.append('Excedent')
    
    if 'Autoconsumption' in test2.columns:
        # Ajout de l'autoconsommation aux colonnes à traiter
        energy_columns.append('Autoconsumption')
    
    if 'Total Consumption (kWh)' in test2.columns:
        # Ajout de la consommation totale calculée
        energy_columns.append('Total Consumption (kWh)')
    
    # === APPLICATION DU SEUIL DE FILTRAGE ===
    # Filtrage des micro-valeurs (erreurs de mesure, bruit électronique)
    threshold = 1e-5  # Seuil : 0.00001 kWh (précision typique des compteurs intelligents)
    
    for column in energy_columns:
        # Remplacement des valeurs < seuil par zéro (considérées comme bruit)
        test2[column] = test2[column].apply(lambda x: 0 if abs(x) < threshold else x)
    
    # ========================================================================
    # VALIDATION FINALE ET CONTRÔLES DE QUALITÉ
    # ========================================================================
    
    # === VÉRIFICATION DE LA SUFFISANCE DES DONNÉES ===
    # Détection automatique de l'intervalle de mesure pour validation adaptée
    if len(test2) >= 2:
        # Calcul de l'intervalle moyen entre les mesures
        time_diff = test2.index[1] - test2.index[0]
        interval_minutes = time_diff.total_seconds() / 60
        
        # Détermination du seuil minimum selon l'intervalle détecté
        if interval_minutes <= 15:  # Données quart d'heure (15 min)
            min_records_day = 96    # 96 mesures pour 1 journée
            min_records_month = 2880  # ~30 jours
            min_records_year = 35040  # ~365 jours
            interval_desc = "quart d'heure (15 min)"
        elif interval_minutes <= 30:  # Données demi-heure (30 min)
            min_records_day = 48    # 48 mesures pour 1 journée
            min_records_month = 1440  # ~30 jours
            min_records_year = 17520  # ~365 jours
            interval_desc = "demi-heure (30 min)"
        else:  # Données horaires (60 min) ou plus
            min_records_day = 24    # 24 mesures pour 1 journée
            min_records_month = 720   # ~30 jours
            min_records_year = 8760   # ~365 jours
            interval_desc = "horaire (60 min)"
    else:
        # Fallback si impossible de déterminer l'intervalle
        min_records_day = 24
        min_records_month = 720
        min_records_year = 8760
        interval_desc = "indéterminé"
    
    if len(test2) < min_records_day:  # Seuil adaptatif selon l'intervalle de mesure
        st.error(f"""
        ❌ **Volume de données insuffisant**
        
        Le fichier ne contient que {len(test2)} enregistrements après nettoyage.
        
        **Intervalle de mesure détecté :** {interval_desc}
        
        **Exigences minimales pour cet intervalle :**
        - **Minimum absolu :** {min_records_day} enregistrements (1 journée)
        - **Recommandé :** {min_records_month} enregistrements (1 mois)
        - **Optimal :** {min_records_year}+ enregistrements (1+ année)
        
        **Causes possibles :**
        1. **Période d'export trop courte** → Étendez la période d'export depuis votre portail
        2. **Données majoritairement invalides** → Vérifiez la qualité du fichier source
        3. **Problème de format** → Contactez votre fournisseur d'énergie
        4. **Fichier test/démo** → Utilisez un fichier de données réelles
        
        **Solutions recommandées :**
        1. Exportez au minimum 1 mois de données depuis votre portail fournisseur
        2. Vérifiez que votre installation mesure bien la consommation
        3. Contactez le support technique si le problème persiste
        
        **Analyse optimale :** Pour des résultats fiables, utilisez au moins 1 an de données
        """)
        
        # Reset complet pour nouveau fichier
        st.session_state['current_file_name'] = None
        st.session_state['file_processed'] = False
        st.session_state['current_file_data'] = None
        return None, 0
    
    # ========================================================================
    # FINALISATION ET SAUVEGARDE
    # ========================================================================
    
    # === SAUVEGARDE DU DATASET NETTOYÉ ===
    # Export CSV pour traçabilité et réutilisation (debug, analyse externe)
    test2.to_csv('clean_dataset.csv')
    
    # === MISE EN CACHE POUR OPTIMISATION ===
    # Stockage en session pour éviter les retraitements lors de navigation dans l'app
    st.session_state['current_file_data'] = test2

    print("Traitement terminé avec succès")  # Confirmation debug

    # === INDICATEUR DE NOUVEAU TRAITEMENT ===
    flag = 1  # Signale qu'un nouveau fichier a été traité

    return test2, flag