# Configuration pour Google Analytics
# 
# Pour configurer Google Analytics :
# 1. Allez sur https://analytics.google.com/
# 2. Créez un nouveau compte/propriété Google Analytics 4
# 3. Récupérez votre ID de mesure (format: G-XXXXXXXXXX)
# 4. Remplacez la valeur ci-dessous par votre véritable ID

import os
from dotenv import load_dotenv

# Charger les variables d'environnement si le fichier .env existe
load_dotenv()

# Votre ID de mesure Google Analytics 4
# Peut être défini via variable d'environnement ou directement ici
GOOGLE_ANALYTICS_ID = os.getenv("GOOGLE_ANALYTICS_ID", "G-XXXXXXXXXX")

# Configuration optionnelle
ANALYTICS_CONFIG = {
    # Active ou désactive le suivi (utile pour le développement)
    "enabled": os.getenv("ANALYTICS_ENABLED", "true").lower() == "true",
    
    # Mode de débogage (affiche les événements dans la console)
    "debug_mode": os.getenv("ANALYTICS_DEBUG_MODE", "false").lower() == "true",
    
    # Respect de la vie privée - anonymise les IPs
    "anonymize_ip": os.getenv("ANALYTICS_ANONYMIZE_IP", "true").lower() == "true",
    
    # Délai avant envoi des événements (en ms)
    "send_timeout": 2000
}
