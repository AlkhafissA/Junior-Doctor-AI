import streamlit as st
import os
import base64
from datetime import datetime
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# --- 1. CONFIGURATION & OUTILS ---
def setup_page():
    st.set_page_config(page_title="Junior_Doctor V7 (Vision)", page_icon="👁️", layout="wide")
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
    if "history" not in st.session_state:
        st.session_state.history = []
    if "current_view" not in st.session_state:
        st.session_state.current_view = None

def encode_image(image_file):
    """Convertit l'image en format lisible pour l'IA (Base64)"""
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 2. SIDEBAR ---
def render_sidebar():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3774/3774299.png", width=80)
        st.title("Menu")
        
        mode = st.radio("Mode :", ["Diagnostic 🩺", "Traduction 🔀", "Explication 🎓"])
        
        # Options contextuelles
        if mode == "Traduction 🔀":
            target_lang = st.selectbox("Vers :", ["Python", "C++", "JS", "Go", "Rust"])
            lang_label = f"Traduction vers {target_lang}"
        else:
            target_lang = None
            lang_label = mode

        st.markdown("---")
        if st.button("➕ Nouvelle Consultation"):
            st.session_state.current_view = None
            st.rerun()
            
        if st.button("🗑️ Tout effacer"):
            st.session_state.history = []
            st.session_state.current_view = None
            st.rerun()

        st.markdown("### 📂 Dossiers")
        for i, session in enumerate(reversed(st.session_state.history)):
            label = f"{session['time']} - {session['summary']}"
            if st.button(label, key=f"hist_{i}"):
                st.session_state.current_view = session
                st.rerun()
                
    return mode, target_lang, lang_label

# --- 3. MOTEUR IA HYBRIDE (TEXTE + VISION) ---
def get_ai_response(messages, api_key, has_image=False):
    """Choisit le bon cerveau selon qu'il y a une image ou non"""
    
    # Si on a une image dans l'historique récent, on utilise le modèle VISION
    if has_image:
        model = "llama-3.2-11b-vision-preview" # Modèle qui "voit"
    else:
        model = "llama-3.3-70b-versatile" # Modèle qui "pense" fort
        
    llm = ChatGroq(temperature=0.1, model_name=model, api_key=api_key)
    response = llm.invoke(messages)
    return response.content

# --- 4. INTERFACE PRINCIPALE ---
def main():
    api_key = check_api_key()
    setup_page()
    init_session_state()
    
    mode, target_lang, summary_label = render_sidebar()
    
    st.title("👁️ Junior_Doctor : Vision")

    # --- CAS 1 : Consultation en cours (Chat) ---
    if st.session_state.current_view:
        session = st.session_state.current_view
        
        # Affichage (Image ou Code) à gauche, Chat à droite
        col_ref, col_chat = st.columns([1, 1])
        
        with col_ref:
            st.subheader("Pièce à conviction")
            if session.get('image_data'):
                st.image(session['image_data'], caption="Photo analysée", use_container_width=True)
            elif session.get('code_input'):
                st.code(session['code_input'])
            else:
                st.info("Aucun document de référence.")

        with col_chat:
            st.subheader("Discussion")
            
            # Historique
            for msg in session['messages']:
                if isinstance(msg, SystemMessage): continue
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                avatar = "👤" if role == "user" else "👨‍⚕️"
                with st.chat_message(role, avatar=avatar):
                    # On évite d'afficher le bloc binaire de l'image dans le chat
                    if isinstance(msg.content, list):
                        st.markdown(msg.content[0]['text']) 
                    else:
                        st.markdown(msg.content)

            # Input Chat
            if user_input := st.chat_input("Répondre au docteur..."):
                session['messages'].append(HumanMessage(content=user_input))
                with st.chat_message("user", avatar="👤"):
                    st.markdown(user_input)
                
                with st.chat_message("assistant", avatar="👨‍⚕️"):
                    with st.spinner("Analyse..."):
                        # On garde le mode vision si la session a une image
                        has_img = session.get('image_data') is not None
                        ai_reply = get_ai_response(session['messages'], api_key, has_image=has_img)
                        st.markdown(ai_reply)
                
                session['messages'].append(AIMessage(content=ai_reply))

    # --- CAS 2 : Nouvelle Consultation (Accueil) ---
    else:
        st.subheader("Comment veux-tu transmettre le code ?")
        
        tab_text, tab_cam = st.tabs(["✍️ Copier-Coller", "📸 Caméra (Vision)"])
        
        # OPTION A : TEXTE CLASSIQUE
        with tab_text:
            code_input = st.text_area("Colle ton code ici...", height=300)
            if st.button("Lancer l'analyse (Texte)", type="primary"):
                sys_msg = f"Tu es expert. Mode: {mode}. Analyse ce code."
                initial_msgs = [
                    SystemMessage(content=sys_msg),
                    HumanMessage(content=f"Voici le code : \n```\n{code_input}\n```")
                ]
                
                with st.spinner("Analyse texte..."):
                    resp = get_ai_response(initial_msgs, api_key, has_image=False)
                
                initial_msgs.append(AIMessage(content=resp))
                new_session = {
                    "time": datetime.now().strftime("%H:%M"),
                    "summary": f"{summary_label} (Txt)",
                    "code_input": code_input,
                    "image_data": None,
                    "messages": initial_msgs
                }
                st.session_state.history.append(new_session)
                st.session_state.current_view = new_session
                st.rerun()

        # OPTION B : VISION (CAMÉRA)
        with tab_cam:
            img_file = st.camera_input("Prends une photo nette du code")
            
            if img_file is not None:
                if st.button("Lancer l'analyse (Vision) 👁️", type="primary"):
                    with st.spinner("Lecture de l'image et analyse..."):
                        # 1. Encodage
                        base64_image = encode_image(img_file)
                        
                        # 2. Prompt Spécial Vision
                        prompt_text = f"""
                        Regarde cette image attentivement. Elle contient du code informatique.
                        TA MISSION :
                        1. Extrais le code présent sur l'image.
                        2. Exécute la requête suivante : {mode}.
                        {f'Si Traduction, traduis vers {target_lang}.' if target_lang else ''}
                        """
                        
                        # 3. Message Multimodal (Texte + Image)
                        msg_content = [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                        
                        initial_msgs = [HumanMessage(content=msg_content)]
                        
                        # 4. Appel API Vision
                        resp = get_ai_response(initial_msgs, api_key, has_image=True)
                        
                        # 5. On ajoute la réponse (mais on nettoie le message user pour éviter de stocker le base64 lourd en double)
                        # Pour l'historique, on garde une version simplifiée du message user
                        clean_msgs = [HumanMessage(content="[Photo du code envoyée]")]
                        clean_msgs.append(AIMessage(content=resp))

                        new_session = {
                            "time": datetime.now().strftime("%H:%M"),
                            "summary": f"{summary_label} (Cam)",
                            "code_input": None,
                            "image_data": img_file.getvalue(), # On garde l'image brute pour l'affichage
                            "messages": clean_msgs
                        }
                        st.session_state.history.append(new_session)
                        st.session_state.current_view = new_session
                        st.rerun()

if __name__ == "__main__":
    main()
