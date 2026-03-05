# Configuration et fonctions pour Google Analytics
import streamlit as st
import streamlit.components.v1 as components

def inject_google_analytics(ga_id: str):
    """
    Injecte le code de suivi Google Analytics dans l'application Streamlit
    
    Args:
        ga_id (str): L'ID de mesure Google Analytics (ex: G-XXXXXXXXXX)
    """
    if not ga_id:
        return
        
    # Code Google Analytics 4 (gtag)
    ga_code = f"""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>
    """
    
    # Injecter le code dans le head de la page
    components.html(ga_code, height=0)

def track_event(event_name: str, parameters: dict = None):
    """
    Suit un événement personnalisé dans Google Analytics
    
    Args:
        event_name (str): Nom de l'événement
        parameters (dict): Paramètres additionnels pour l'événement
    """
    if parameters is None:
        parameters = {}
    
    # Convertir les paramètres en string JavaScript
    params_str = ""
    if parameters:
        params_list = [f"'{k}': '{v}'" for k, v in parameters.items()]
        params_str = ", " + ", ".join(params_list)
    
    event_code = f"""
    <script>
      if (typeof gtag !== 'undefined') {{
        gtag('event', '{event_name}'{params_str});
      }}
    </script>
    """
    
    components.html(event_code, height=0)

def track_page_view(page_title: str, page_location: str = None):
    """
    Suit une vue de page spécifique
    
    Args:
        page_title (str): Titre de la page
        page_location (str): URL ou identifiant de la page
    """
    params = {
        'page_title': page_title
    }
    
    if page_location:
        params['page_location'] = page_location
    
    track_event('page_view', params)

def track_user_interaction(interaction_type: str, element: str, value: str = None):
    """
    Suit les interactions utilisateur (clics, formulaires, etc.)
    
    Args:
        interaction_type (str): Type d'interaction (click, form_submit, file_upload, etc.)
        element (str): Élément avec lequel l'utilisateur interagit
        value (str): Valeur optionnelle associée à l'interaction
    """
    params = {
        'interaction_type': interaction_type,
        'element': element
    }
    
    if value:
        params['value'] = value
    
    track_event('user_interaction', params)

def track_analysis_completion(analysis_type: str, user_type: str, file_type: str = None):
    """
    Suit la completion d'une analyse
    
    Args:
        analysis_type (str): Type d'analyse (dashboard, clustering, cost_analysis, etc.)
        user_type (str): Type d'utilisateur (Particulier, Professionnel)
        file_type (str): Type de fichier uploadé (optionnel)
    """
    params = {
        'analysis_type': analysis_type,
        'user_type': user_type
    }
    
    if file_type:
        params['file_type'] = file_type
    
    track_event('analysis_completion', params)
