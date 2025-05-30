import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

# --- Page Configuration (set early) ---
st.set_page_config(layout="wide") # Use wide layout



# --- Load environment variables ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# --- Configure Gemini ---
if not api_key:
    st.error("GEMINI_API_KEY not found in .env file! Please create a .env file with your API key.")
    st.stop()
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Failed to configure Gemini API: {e}")
    st.stop()

st.title("💬 Gemini Chatbot") # Title and caption will scroll with chat messages



# --- Initialize session state variables ---
if "chats" not in st.session_state:
    st.session_state.chats = {
        "Chat 1": [{"role": "model", "content": "Hello! How can I assist you today?"}]
    }
if "chat_titles" not in st.session_state:
    st.session_state.chat_titles = {"Chat 1": "Chat 1"}
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Chat 1"
if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = 1
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# --- Utility functions ---
def get_active_chat_history():
    return st.session_state.chats.get(st.session_state.active_chat, [])

def save_chat_history(chat_id, messages):
    st.session_state.chats[chat_id] = messages

def delete_chat(chat_id):
    if chat_id in st.session_state.chats:
        del st.session_state.chats[chat_id]
        if chat_id in st.session_state.chat_titles:
            del st.session_state.chat_titles[chat_id]
        if chat_id == st.session_state.active_chat:
            if st.session_state.chats:
                st.session_state.active_chat = list(st.session_state.chats.keys())[0]
            else: # No chats left, create a new default one
                st.session_state.chat_counter = 1
                new_chat_id = "Chat 1"
                st.session_state.chats[new_chat_id] = [
                    {"role": "model", "content": "Hello! How can I assist you today?"}
                ]
                st.session_state.chat_titles[new_chat_id] = new_chat_id
                st.session_state.active_chat = new_chat_id
        st.rerun()


model_name = "gemini-2.5-pro-preview-05-06"
try:
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"Error initializing model '{model_name}': {e}")
    st.sidebar.error(f"Selected model '{model_name}' might be unavailable or invalid.")
    st.stop()

def generate_title_from_summary(text_content: str, original_prompt: str):
    try:
        title_model_name = "gemini-1.5-flash-latest"
        title_gen_model = genai.GenerativeModel(title_model_name)
        context_for_title = f"User: {original_prompt}\nAssistant: {text_content}"
        response = title_gen_model.generate_content(
            f"Generate a very short title (3-5 words) for this conversation snippet:\n\n{context_for_title}"
        )
        title = response.text.strip().split("\n")[0]
        title = title.replace("*", "").replace("\"", "").strip()
        return title[:50]
    except Exception as e:
        st.warning(f"Could not generate title automatically: {e}")
        return (" ".join(original_prompt.split()[:5]) + "...") if original_prompt else "New Chat"

# --- Chat Management (Left Sidebar) ---
with st.sidebar:
    st.markdown("## 💬 Chats")
    if st.button("➕ New Chat", use_container_width=True, key="new_chat_button"):
        st.session_state.chat_counter += 1
        new_id = f"Chat {st.session_state.chat_counter}"
        st.session_state.chats[new_id] = [
            {"role": "model", "content": "Hello! How can I assist you today?"}
        ]
        st.session_state.chat_titles[new_id] = new_id
        st.session_state.active_chat = new_id
        st.rerun()

    sorted_chat_ids = sorted(st.session_state.chats.keys(), reverse=True)
    for chat_id in sorted_chat_ids:
        s_col1, s_col2 = st.columns([4, 1]) # Sidebar columns for chat title and delete button
        with s_col1:
            chat_title = st.session_state.chat_titles.get(chat_id, chat_id)
            if st.button(
                chat_title,
                key=f"select_{chat_id}",
                use_container_width=True,
                type="secondary" if st.session_state.active_chat != chat_id else "primary"
            ):
                st.session_state.active_chat = chat_id
                st.rerun()
        with s_col2:
            if st.button("🗑️", key=f"delete_{chat_id}", help="Delete this chat"):
                delete_chat(chat_id)


main_container=st.container(border=True,height=400)

# --- Function to process input ---
def handle_chat_submission(prompt_text):
    if not prompt_text:
        return

    active_chat_history = get_active_chat_history()
    active_chat_history.append({"role": "user", "content": prompt_text})

    try:
        api_history = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in active_chat_history]
        with main_container:
            with st.spinner(f"Thinking with {model_name}"):
                response = model.generate_content(api_history)
                reply_text = response.text

        active_chat_history.append({"role": "model", "content": reply_text})

        current_chat_id = st.session_state.active_chat
        is_default_title = st.session_state.chat_titles.get(current_chat_id, "") == current_chat_id
        if is_default_title and len(active_chat_history) >= 2: # User prompt + model reply
            user_prompt_for_title = active_chat_history[-2]['content']
            new_title = generate_title_from_summary(reply_text, user_prompt_for_title)
            st.session_state.chat_titles[current_chat_id] = new_title
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        st.error(error_message) # Show error in main interface
        active_chat_history.append({"role": "model", "content": f"Error: {error_message}"})

    save_chat_history(st.session_state.active_chat, active_chat_history)
    st.session_state.user_input = "" # Clear the processed input
    st.rerun()

# Display chat messages
# The entire content of chat_col (within its stBlock) will be scrollable due to CSS
active_chat_history_display = get_active_chat_history()
with main_container: 
    for msg in active_chat_history_display:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.write(msg["content"])

    # Chat input will be at the bottom of the scrollable chat_col

prompt_from_input = st.chat_input("What would you like to ask?", key="chat_input_main")
if prompt_from_input:
    st.session_state.user_input = prompt_from_input


# --- Process user input (from chat_input or FAQ click) ---
if st.session_state.user_input:
    handle_chat_submission(st.session_state.user_input)