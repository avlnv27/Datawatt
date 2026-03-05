# DataWatt

**Application web d'analyse de consommation énergétique développée en collaboration EPFL - SIE SA**

## Description

DataWatt est une application web complète d'analyse de courbes de charge énergétiques, conçue pour aider les particuliers et professionnels à visualiser, analyser et optimiser leurs patterns de consommation électrique. L'application utilise des techniques d'intelligence artificielle pour la classification automatique des profils et fournit des analyses personnalisées avec des recommandations d'optimisation.

## Architecture de l'Application

DataWatt est construite sur une architecture modulaire avec Streamlit, offrant deux modes d'analyse distincts selon le type d'utilisateur : Particuliers, Professionnels. L'application intègre un système de clustering automatique basé sur l'apprentissage automatique pour classifier les profils de consommation.

## Fonctionnalités Principales

### Interface Utilisateur
- **Dashboard synthétique** : Vue d'ensemble avec indicateurs clés et graphiques interactifs
- **Interface à onglets** : Organisation claire des analyses (Principale/Cartographie/Personnalisée)
- **Visualisations interactives** : Graphiques Plotly avec zoom, sélection temporelle et infobulles
- **Navigation fluide** : Système d'ancres et boutons de retour pour une expérience optimisée

### Analyses pour Tous Utilisateurs
- **Courbe de charge interactive** : Visualisation multi-échelles (année/saison/semaine/jour)
- **Heatmaps de consommation** : Cartographies journalière et hebdomadaire des patterns
- **Analyse des coûts** : Simulation tarifaire (Tarif Unique ou HP/HC) avec projections
- **Ratios comportementaux** : 
  - Ratio jour/nuit (6h-22h vs 22h-6h)
  - Ratio semaine/week-end (analyse des habitudes)
- **Charge de base** : Détection et suivi de la consommation de veille
- **Analyse des tendances** : Évolution interannuelle avec régression linéaire

### Analyse pour les Particuliers
- **Classification automatique** : Clustering ML en 4 profils de consommation typiques
- **Analyse personnalisée** : Consommation par m² et par habitant avec benchmarks
- **Recommandations** : Suggestions d'optimisation basées sur le profil (en développement)  
- **Solaire** : En développement

### Analyses pour les Professionnels  
- **Analyses surface** : Consommation normalisée par m² avec comparatifs industrie
- **Détection d'anomalies** : Identification automatique des pics anormaux
- **Peak shaving** : Analyse d'optimisation des pointes avec calculs d'économies

## Structure du Projet

```
DESIGN_PROJECT_SIE/
│
├── main.py                             # Application principale Streamlit
├── README.md                           # Documentation du projet
├── requirements.txt                    # Dépendances Python
├── .env.example                        # Template configuration environnement
├── GOOGLE_ANALYTICS_SETUP.md          # Guide configuration analytics (à retirer)
│
├── .streamlit/                         # Configuration Streamlit
│   └── config.toml
│
├── design/                             # Assets visuels
│   ├── logo_sie_sa.png                # Logo SIE SA
│   ├── SIE_Logo_*.png                 # Variantes du logo
│   └── style.css                      # Styles CSS personnalisés
│
├── data/                               # Données de test et exemples
│   ├── groupe*_pod_*.xlsx              # Fichiers test par groupe
│   └── treating_college.py             # Scripts de traitement
│
├── fichiers_tests/                     # Jeux de données de test
│   ├── *.xlsx                         # Courbes de charge exemples
│   └── *.csv                          # Données converties
│
├── Clustering_enhanced/                # Système de clustering ML
│   ├── Scripts Python/
│   │   ├── 1_data_feature_clean.py     # Extraction features temporelles
│   │   ├── 2_training_phase.py         # Entraînement K-means
│   │   ├── predict_phase.py            # Classification nouveaux profils
│   │   ├── extract_pod.py              # Extraction de profils pods
│   │   └── methods_weight_features_explicative.py
│   │
│   ├── Modèles ML/
│   │   ├── feature_kmeans_model_weight_8features.joblib     # Modèle K-means
│   │   ├── feature_scaler_weight_8features.joblib          # Normalisation
│   │   ├── feature_weights_weight_8features.joblib         # Poids features
│   │   └── feature_stats_weight_8features.joblib           # Statistiques
│   │
│   └── Données de référence/
│       ├── daily_profiles_by_cluster_8features.csv         # Profils journaliers
│       ├── weekly_profiles_by_cluster_8features.csv        # Profils hebdomadaires
│       ├── feature_deciles_by_cluster_8features.csv        # Distributions
│       └── pod_feature_clusters_weight_8features.csv       # Assignations
│
└── src/                                # Code source modulaire
    ├── analytics/                      # Google Analytics (optionnel)
    │   ├── google_analytics.py         # Fonctions de tracking
    │   └── config.py                   # Configuration analytics
    │
    ├── dashboard/                      # Tableau de bord
    │   └── dashboard.py                # Interface dashboard avec cartes
    │
    ├── database/                       # Traitement des données
    │   └── dataframe_gen.py            # Upload et nettoyage fichiers
    │
    ├── indicators/                     # Analyses et indicateurs
    │   ├── interactive_plot.py         # Graphiques interactifs principaux
    │   ├── heatmap_plot.py            # Cartographies de consommation
    │   ├── weekly_pattern_heatmap.py   # Heatmaps patterns hebdomadaires
    │   ├── cost_analysis.py           # Analyses tarifaires HP/HC
    │   ├── day_night_ratio.py         # Ratios jour/nuit
    │   ├── weekday_weekend_ratio.py   # Ratios semaine/week-end
    │   ├── base_load.py               # Charge de base et veille
    │   ├── cluster_indic.py           # Interface clustering
    │   ├── personalized_analysis.py   # Analyses personnalisées
    │   ├── peak.py                    # Détection anomalies et peak shaving
    │   ├── pro_indicators.py          # Indicateurs professionnels
    │   ├── solar.py                   # Analyses photovoltaïques
    │   ├── linear_regression.py       # Analyses de tendances
    │   ├── bar_plot_lin_reg.py       # Graphiques avec régression
    │   └── hotel.py                   # Analyses secteur hôtelier
    │
    └── textual/                       # Interface et textes
        ├── text.py                    # Textes et bannières
        ├── tools.py                   # Utilitaires interface
        └── user_form.py               # Formulaires utilisateur
```


## Installation et Démarrage

### Prérequis

- **Python 3.12** (version requise - compatibilité testée uniquement avec 3.12)
- **pip** (gestionnaire de paquets Python)
- **Git** (pour cloner le repository)
- **Navigateur web moderne** (Chrome, Firefox, Safari, Edge)

### Installation par Système d'Exploitation

#### 🍎 **macOS**

1. **Installer Python 3.12** (si pas déjà installé) :
   ```bash
   # Via Homebrew (recommandé)
   brew install python@3.12
   
   # Ou télécharger Python 3.12 depuis python.org
   # https://www.python.org/downloads/release/python-3120/
   ```

2. **Cloner le repository** :
   ```bash
   git clone https://github.com/svenhominal/DESIGN_PROJECT_SIE.git
   cd DESIGN_PROJECT_SIE
   ```

3. **Créer un environnement virtuel** (recommandé) :
   ```bash
   python3 -m venv datawatt_env
   source datawatt_env/bin/activate
   ```

4. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

5. **Lancer l'application** :
   ```bash
   streamlit run main.py
   ```

#### 🪟 **Windows**

1. **Installer Python 3.12** (si pas déjà installé) :
   - Télécharger **Python 3.12** depuis [python.org](https://www.python.org/downloads/release/python-3120/)
   - ⚠️ **Important** : Cocher "Add Python to PATH" lors de l'installation
   
2. **Ouvrir PowerShell ou Command Prompt** :
   ```cmd
   # Vérifier l'installation Python 3.12
   python --version
   # Doit afficher: Python 3.12.x
   pip --version
   ```

3. **Cloner le repository** :
   ```cmd
   git clone https://github.com/svenhominal/DESIGN_PROJECT_SIE.git
   cd DESIGN_PROJECT_SIE
   ```

4. **Créer un environnement virtuel** (recommandé) :
   ```cmd
   python -m venv datawatt_env
   datawatt_env\Scripts\activate
   ```

5. **Installer les dépendances** :
   ```cmd
   pip install -r requirements.txt
   ```

6. **Lancer l'application** :
   ```cmd
   streamlit run main.py
   ```

## Format des Données

L'application accepte les formats de courbes de charge suivants :

### Formats Supportés
- **Excel** (.xlsx) : Format principal recommandé (Attention structure de fichiers acceptés limités, regarder dans le dossier du présent code ce qui est accepté, sinon modifier les formats dans 'src/database/dataframe_gen.py')
- **CSV** (.csv) : Alternative avec délimiteurs standards

### Structure Attendue
- **Colonne temporelle** : Index avec timestamps (résolution 15min typique)
- **Colonne consommation** : Valeurs en kWh (nommage flexible)
- **Colonnes solaires** (optionnel) : 
  - Autoconsommation
  - Excédent/Production

### Exemple de Structure  

```
Datetime               | Consumption (kWh)
2024-01-01 00:00:00    | 0.25              
2024-01-01 00:15:00    | 0.23                          
...                    | ...               
``` 


```
Datetime               | Consumption (kWh) | Autoconsommation | Excédent
2024-01-01 00:00:00    | 0.25              | 0.00             | 0.00
2024-01-01 00:15:00    | 0.23              | 0.00             | 0.00
...                    | ...               | ...              | ...
```

## Modules utilisés

### Framework Principal
- **Streamlit** : Interface web interactive
- **Plotly** : Visualisations graphiques avancées
- **Pandas** : Manipulation et analyse de données

### Intelligence Artificielle
- **Scikit-learn** : Clustering K-means et preprocessing
- **Joblib** : Sérialisation des modèles ML

### Outils Complémentaires
- **NumPy** : Calculs numériques optimisés
- **Meteostat** : Données météorologiques (analyses avancées)
- **OpenPyXL** : Lecture fichiers Excel
- **Python-dotenv** : Gestion variables d'environnement

## Support et Contact

### Développement
- **Etudiants** : Sven Hominal & Quentin Poindextre (EPFL)
- **Collaboration** : SIE SA


### Support Technique
- **Contact SIE** : info@sie.ch  
- **sven.hominal@epfl.ch**

---

**DataWatt © 2025** | Design Project EPFL - SIE SA