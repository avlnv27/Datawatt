import streamlit as st

def display_user_form():
    # Initialize session state for form fields if not already set
    if 'surface' not in st.session_state:
        st.session_state['surface'] = 30
    if 'num_people' not in st.session_state:
        st.session_state['num_people'] = 1
    if 'housing_type' not in st.session_state:
        st.session_state['housing_type'] = "Appartement"
    if 'heating_type' not in st.session_state:
        st.session_state['heating_type'] = "Non électrique"
    if 'has_ecs' not in st.session_state:
        st.session_state['has_ecs'] = "Non électrique"

    # CSS personnalisé pour augmenter la taille du texte dans les champs de saisie
    st.markdown("""
    <style>
        .stNumberInput input, .stSelectbox select, .row-widget.stRadio > div {
            font-size: 1.1rem !important;
        }
        .stNumberInput label, .stSelectbox label, .stRadio label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    #st.markdown("<h3 style='text-align: center; color: #818081; margin: 20px 0 5px 0; padding-bottom: 8px; border-bottom: 2px solid #e6321e;'>Formulaire pour l'utilisateur</h3>", unsafe_allow_html=True)
    
    # Brief explanation of the form purpose
    #st.markdown("<p style='text-align: center; color: #888888; margin-top: 0; margin-bottom: 25px;'>Ces informations nous permettent de personnaliser l'analyse de votre consommation</p>", unsafe_allow_html=True)


    # Create the form with styled elements
    with st.form(key='user_form'):
        st.markdown("<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
        surface = st.number_input("Surface du logement (m²)", min_value=30, value=st.session_state['surface'], help="Surface habitable totale de votre logement")
        
        num_people = st.number_input("Nombre de personnes dans le logement", min_value=1, value=st.session_state['num_people'], help="Nombre de personnes résidant dans votre logement")
        
        housing_type = st.radio("Type de logement", options=["Appartement", "Maison"], 
                               index=["Appartement", "Maison"].index(st.session_state['housing_type']) if st.session_state['housing_type'] in ["Appartement", "Maison"] else 0,
                               help="Précisez si vous habitez dans un appartement ou une maison")
        
        heating_type = st.radio("Type de chauffage", options=["Électrique", "Non électrique", "PAC"], 
                               index=["Électrique", "Non électrique", "PAC"].index(st.session_state['heating_type']) if st.session_state['heating_type'] in ["Électrique", "Non électrique", "PAC"] else 1,
                               help="Précisez votre type de chauffage principal")
        
        # L'ECS suit le chauffage par défaut, mais peut être modifié
        if heating_type == "PAC":
            default_ecs = "Électrique"  # PAC utilise généralement l'électricité pour l'ECS
        else:
            default_ecs = heating_type
            
        has_ecs = st.radio("Eau chaude sanitaire (ECS)", options=["Électrique", "Non électrique"], 
                          index=["Électrique", "Non électrique"].index(default_ecs) if default_ecs in ["Électrique", "Non électrique"] else 0,
                          help="Précisez si votre eau chaude sanitaire est électrique ou non")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Centrer le bouton correctement
        st.markdown("<div style='display: flex; justify-content: center; margin: 20px 0;'>", unsafe_allow_html=True)
        submit_button = st.form_submit_button(label='Valider les informations', use_container_width=False)
        st.markdown("</div>", unsafe_allow_html=True)

    # Update session state with the form data if submitted
    if submit_button:
        st.session_state['surface'] = surface
        st.session_state['num_people'] = num_people
        st.session_state['housing_type'] = housing_type
        st.session_state['heating_type'] = heating_type
        st.session_state['has_ecs'] = has_ecs

        # Confirmation message when form is submitted
        st.success("Informations entrées avec succès !")
        
        # Return the form data and a flag indicating successful submission
        return [surface, num_people, housing_type, heating_type, has_ecs], 1
    else:
        # Return the current session state data without submission flag
        return [st.session_state['surface'], st.session_state['num_people'], 
                st.session_state['housing_type'], st.session_state['heating_type'],
                st.session_state['has_ecs']], 0
    

def display_user_am_form():
    # Initialize session state for form fields if not already set
    if 'surface_am' not in st.session_state:
        st.session_state['surface_am'] = 30
    if 'type_am' not in st.session_state:
        st.session_state['type_am'] = "Collège"

    # CSS personnalisé pour augmenter la taille du texte dans les champs de saisie
    st.markdown("""
    <style>
        .stNumberInput input, .stSelectbox select, .row-widget.stRadio > div {
            font-size: 1.1rem !important;
        }
        .stNumberInput label, .stSelectbox label, .stRadio label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    #st.markdown("<h3 style='text-align: center; color: #818081; margin: 20px 0 5px 0; padding-bottom: 8px; border-bottom: 2px solid #e6321e;'>Formulaire pour l'utilisateur</h3>", unsafe_allow_html=True)
    
    # Brief explanation of the form purpose
    #st.markdown("<p style='text-align: center; color: #888888; margin-top: 0; margin-bottom: 25px;'>Ces informations nous permettent de personnaliser l'analyse de votre consommation</p>", unsafe_allow_html=True)

    # Create the form with styled elements
    with st.form(key='user_form'):
        st.markdown("<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
        surface = st.number_input("Surface du batîment (m²)", min_value=30, value=st.session_state['surface_am'], help="Surface habitable totale de votre logement")
        
        type = st.selectbox("Type de bâtiment", options=["Collège", "Autre"],
                            index=["Collège", "Autre"].index(st.session_state['type_am']) if st.session_state['type_am'] in ["Collège", "Autre"] else 0,
                            help="Type de bâtiment pour lequel vous souhaitez une analyse")

        st.markdown("</div>", unsafe_allow_html=True)
        
        # Centrer le bouton correctement
        st.markdown("<div style='display: flex; justify-content: center; margin: 20px 0;'>", unsafe_allow_html=True)
        submit_button = st.form_submit_button(label='Valider les informations', use_container_width=False)
        st.markdown("</div>", unsafe_allow_html=True)

    # Update session state with the form data if submitted
    if submit_button:
        st.session_state['surface_am'] = surface
        st.session_state['type_am'] = type

        # Confirmation message when form is submitted
        st.success("Informations entrées avec succès !")
        
        # Return the form data and a flag indicating successful submission
        return [surface, type], 1
    else:
        # Return the current session state data without submission flag
        return [st.session_state['surface_am'], 
                st.session_state['type_am']], 0
    
def display_user_corp_form():
    # Initialize session state for form fields if not already set
    if 'surface_c' not in st.session_state:
        st.session_state['surface_c'] = 30

    # CSS personnalisé pour augmenter la taille du texte dans les champs de saisie
    st.markdown("""
    <style>
        .stNumberInput input, .stSelectbox select, .row-widget.stRadio > div {
            font-size: 1.1rem !important;
        }
        .stNumberInput label, .stSelectbox label, .stRadio label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    #st.markdown("<h3 style='text-align: center; color: #818081; margin: 20px 0 5px 0; padding-bottom: 8px; border-bottom: 2px solid #e6321e;'>Formulaire pour l'utilisateur</h3>", unsafe_allow_html=True)
    
    # Brief explanation of the form purpose
    #st.markdown("<p style='text-align: center; color: #888888; margin-top: 0; margin-bottom: 25px;'>Ces informations nous permettent de personnaliser l'analyse de votre consommation</p>", unsafe_allow_html=True)

    # Create the form with styled elements
    with st.form(key='user_form'):
        st.markdown("<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
        surface = st.number_input("Surface du bâtiment (m²)", min_value=30, value=st.session_state['surface_c'], help="Surface habitable totale du bâtiment")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Centrer le bouton correctement
        st.markdown("<div style='display: flex; justify-content: center; margin: 20px 0;'>", unsafe_allow_html=True)
        submit_button = st.form_submit_button(label='Valider les informations', use_container_width=False)
        st.markdown("</div>", unsafe_allow_html=True)

    # Update session state with the form data if submitted
    if submit_button:
        st.session_state['surface_c'] = surface

        # Confirmation message when form is submitted
        st.success("Informations entrées avec succès !")
        
        # Return the form data and a flag indicating successful submission
        return [surface], 1
    else:
        # Return the current session state data without submission flag
        return [st.session_state['surface_c']], 0