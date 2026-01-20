import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# --- 1. CONFIGURATION & CONSTANTES ---
def setup_page():
    st.set_page_config(page_title="Junior_Doctor V6 (Chat)", page_icon="👨‍⚕️", layout="wide")
    st.markdown("""
    <style>
        .reportview-container { background: #0e1117; }
        h1 { color: #64B5F6; }
        .stChatMessage { background-color: #262730; border-radius: 10px; padding: 10px; margin-bottom: 10px;}
    </style>
    """, unsafe_allow_html=True)

def check_api_key():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("⚠️ Clé API manquante dans le fichier .env")
        st.stop()
    return api_key

def init_session_state():
    # Historique global des sessions (liste de dossiers patients)
    if "history" not in st.session_state:
        st.session_state.history = []
    # Vue actuelle (Session active)
    if "current_view" not in st.session_state:
        st.session_state.current_view = None

# --- 2. SIDEBAR (Navigation) ---
def render_sidebar():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3774/3774299.png", width=80)
        st.title("Configuration")
        
        mode = st.radio("Mode :", ["Diagnostic 🩺", "Traduction 🔀"])
        source_lang = st.selectbox("Langage Source :", ["Python", "JS", "C++", "Java", "Bash", "SQL", "Go"])
        
        target_lang = None
        niveau = "Expert"
        
        if mode == "Traduction 🔀":
            target_lang = st.selectbox("Vers :", ["C++", "Python", "Rust", "Go", "JS"])
        else:
            niveau = st.radio("Niveau :", ["Débutant", "Expert"])

        st.markdown("---")
        st.markdown("### 📜 Dossiers Patients")
        
        if st.button("➕ Nouveau Patient"):
            st.session_state.current_view = None
            st.rerun()
            
        if st.button("🗑️ Tout effacer"):
            st.session_state.history = []
            st.session_state.current_view = None
            st.rerun()

        # Liste des sessions passées
        for i, session in enumerate(reversed(st.session_state.history)):
            label = f"{session['time']} - {session['summary']}"
            if st.button(label, key=f"hist_{i}"):
                st.session_state.current_view = session
                st.rerun()
                
    return mode, source_lang, target_lang, niveau

# --- 3. MOTEUR IA (Chat) ---
def get_ai_response(messages, api_key):
    """Envoie tout l'historique de chat à Groq"""
    llm = ChatGroq(temperature=0.1, model_name="llama-3.3-70b-versatile", api_key=api_key)
    response = llm.invoke(messages)
    return response.content

# --- 4. INTERFACE PRINCIPALE ---
def main():
    api_key = check_api_key()
    setup_page()
    init_session_state()
    
    mode, source_lang, target_lang, niveau = render_sidebar()
    
    st.title("👨‍⚕️ Junior_Doctor : Consultation")

    # --- SCÉNARIO 1 : Consultation Active (Chat ouvert) ---
    if st.session_state.current_view:
        session = st.session_state.current_view
        
        # Layout : Code à gauche (fixe), Chat à droite (interactif)
        col_code, col_chat = st.columns([1, 1])
        
        with col_code:
            st.subheader(f"Code du Patient ({session['lang']})")
            st.code(session['code_input'], language=session['lang'].lower())
            st.info("💡 Le code est affiché ici pour référence pendant le chat.")

        with col_chat:
            st.subheader(f"Discussion : {session['summary']}")
            
            # 1. Afficher l'historique du chat
            for msg in session['messages']:
                # On saute le message système pour l'affichage
                if isinstance(msg, SystemMessage):
                    continue
                
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                avatar = "👤" if role == "user" else "👨‍⚕️"
                with st.chat_message(role, avatar=avatar):
                    st.markdown(msg.content)

            # 2. Zone de saisie pour poser une nouvelle question
            if user_input := st.chat_input("Pose une question au docteur..."):
                # Ajout message utilisateur
                session['messages'].append(HumanMessage(content=user_input))
                
                # Affichage immédiat (pour la réactivité)
                with st.chat_message("user", avatar="👤"):
                    st.markdown(user_input)

                # Réponse IA
                with st.chat_message("assistant", avatar="👨‍⚕️"):
                    with st.spinner("Réflexion..."):
                        ai_reply = get_ai_response(session['messages'], api_key)
                        st.markdown(ai_reply)
                
                # Sauvegarde réponse IA
                session['messages'].append(AIMessage(content=ai_reply))
                # Streamlit gère le rafraichissement auto avec chat_input, 
                # mais on force pour être sûr de la synchro si besoin.

    # --- SCÉNARIO 2 : Accueil (Nouveau Patient) ---
    else:
        st.subheader(f"Démarrer une consultation ({mode})")
        code_input = st.text_area("Colle le code ici...", height=400)
        
        btn_text = f"Lancer {mode}"
        if st.button(btn_text, type="primary"):
            if code_input:
                # 1. Préparation du Prompt Système (Le contexte initial)
                if mode == "Traduction 🔀":
                    sys_prompt = f"""Tu es un expert développeur.
                    TA MISSION : Traduire le code suivant du {source_lang} vers le {target_lang}.
                    CODE PATIENT : \n```{source_lang}\n{code_input}\n```
                    Agis comme un collègue expert. Donne le code traduit et explique."""
                    summary = f"{source_lang} ➔ {target_lang}"
                else:
                    sys_prompt = f"""Tu es Junior_Doctor, un expert {source_lang}.
                    Niveau: {niveau}.
                    TA MISSION : Analyser et corriger ce code.
                    CODE PATIENT : \n```{source_lang}\n{code_input}\n```
                    Commence par donner le diagnostic et la correction."""
                    summary = f"Debug {source_lang}"

                # 2. Création de la session avec le premier message système
                initial_messages = [
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content="Docteur, quel est votre diagnostic ?")
                ]
                
                # 3. Premier appel IA pour lancer la conversation
                with st.spinner("Analyse initiale..."):
                    first_response = get_ai_response(initial_messages, api_key)
                    initial_messages.append(AIMessage(content=first_response))

                # 4. Sauvegarde dans l'historique
                new_session = {
                    "time": datetime.now().strftime("%H:%M"),
                    "summary": summary,
                    "lang": source_lang,
                    "code_input": code_input,
                    "messages": initial_messages # On stocke toute la conversation ici
                }
                
                st.session_state.history.append(new_session)
                st.session_state.current_view = new_session
                st.rerun()

if __name__ == "__main__":
    main()
