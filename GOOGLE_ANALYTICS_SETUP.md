# Configuration Google Analytics pour DataWatt

Ce guide vous explique comment configurer Google Analytics pour suivre l'utilisation de votre application DataWatt.

## 📋 Étapes de configuration

### 1. Créer un compte Google Analytics

1. Rendez-vous sur [Google Analytics](https://analytics.google.com/)
2. Connectez-vous avec votre compte Google
3. Cliquez sur "Commencer" si c'est votre première fois

### 2. Créer une propriété

1. Cliquez sur "Créer une propriété"
2. Donnez un nom à votre propriété (ex: "DataWatt App")
3. Sélectionnez votre fuseau horaire et devise
4. Choisissez "Web" comme plateforme

### 3. Configurer le flux de données

1. Entrez l'URL de votre site (ex: https://votredomaine.com ou localhost pour les tests)
2. Donnez un nom au flux (ex: "DataWatt - Site Web")
3. Cliquez sur "Créer un flux"

### 4. Récupérer votre ID de mesure

1. Une fois le flux créé, vous verrez votre **ID de mesure** (format: `G-XXXXXXXXXX`)
2. Copiez cet ID

### 5. Configurer l'application

1. Ouvrez le fichier `src/analytics/config.py`
2. Remplacez `"G-XXXXXXXXXX"` par votre véritable ID de mesure :

```python
GOOGLE_ANALYTICS_ID = "G-VOTRE_ID_ICI"
```

### 6. Configuration optionnelle

Dans le même fichier `config.py`, vous pouvez ajuster :

```python
ANALYTICS_CONFIG = {
    # Active ou désactive le suivi
    "enabled": True,  # Mettez False pour désactiver temporairement
    
    # Mode de débogage
    "debug_mode": False,  # Mettez True pour voir les événements dans la console
    
    # Respect de la vie privée
    "anonymize_ip": True,  # Recommandé pour le respect de la vie privée
    
    # Délai d'envoi
    "send_timeout": 2000
}
```

## 📊 Données trackées

L'application suit automatiquement :

### Événements de base
- **Visites de pages** : Quand un utilisateur visite votre application
- **Upload de fichiers** : Quand un fichier de courbe de charge est uploadé
- **Sélection du type d'utilisateur** : Particulier ou Professionnel
- **Navigation entre onglets** : Analyse principale, Cartographie, Analyse personnalisée

### Analyses complétées
- **Dashboard** : Quand le tableau de bord est affiché
- **Clustering** : Quand l'analyse de profil est terminée
- **Analyses spécifiques** : Chaque type d'analyse effectuée

## 🔍 Voir vos données

1. Retournez sur [Google Analytics](https://analytics.google.com/)
2. Sélectionnez votre propriété
3. Consultez les rapports :
   - **Temps réel** : Visiteurs actuels
   - **Audience** : Données démographiques
   - **Comportement** : Pages visitées, événements
   - **Événements** : Actions spécifiques des utilisateurs

## 🛡️ Respect de la vie privée

L'implémentation respecte la vie privée :
- Les adresses IP sont anonymisées
- Aucune donnée personnelle n'est transmise
- Les fichiers uploadés ne sont pas suivis (seul le fait qu'un upload a eu lieu)

## 🔧 Désactivation temporaire

Pour désactiver le suivi temporairement (utile en développement) :

```python
ANALYTICS_CONFIG = {
    "enabled": False,  # Désactive complètement
    # ... autres paramètres
}
```

## 🐛 Dépannage

### Le suivi ne fonctionne pas
1. Vérifiez que votre ID de mesure est correct
2. Assurez-vous que `enabled: True` dans la config
3. Consultez la console du navigateur pour les erreurs

### Tester en local
- Google Analytics fonctionne même en localhost
- Utilisez `debug_mode: True` pour voir les événements dans la console
- Les données peuvent prendre quelques minutes à apparaître dans GA

### Données manquantes
- Les événements peuvent prendre 24-48h pour apparaître dans les rapports
- Utilisez l'onglet "Temps réel" pour un feedback immédiat

## 📈 Métriques importantes à surveiller

1. **Nombre de visiteurs uniques** : Combien de personnes utilisent votre app
2. **Pages vues** : Quelles sections sont les plus populaires
3. **Événements d'upload** : Combien de fichiers sont analysés
4. **Types d'utilisateurs** : Répartition Particuliers/Professionnels
5. **Analyses complétées** : Quelles fonctionnalités sont les plus utilisées

## ⚡ Performance

L'intégration Google Analytics :
- N'affecte pas les performances de l'application
- Se charge de manière asynchrone
- N'interrompt pas l'expérience utilisateur

---

*Pour toute question technique, consultez la [documentation Google Analytics](https://support.google.com/analytics/) ou contactez votre équipe de développement.*
