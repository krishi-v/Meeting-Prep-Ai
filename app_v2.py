import streamlit as st
import os
import json
import tomllib
from google import genai

# --- 1. CONFIGURATION & PERSISTENCE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "meeting_history.json")
SECRETS_PATH = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_to_history(topic, strategy, notes=""):
    history = load_history()
    history.append({
        "topic": topic, 
        "strategy": strategy, 
        "notes": notes 
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# --- 2. SECURE API LOADING ---
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif os.path.exists(SECRETS_PATH):
    with open(SECRETS_PATH, "rb") as f:
        data = tomllib.load(f)
        api_key = data.get("GEMINI_API_KEY")

if not api_key:
    st.error("🔑 API Key not found. Please check .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 3. UI SETUP ---
st.set_page_config(page_title="Meeting Prep AI Assistant", page_icon="🎯", layout="wide")

# Custom CSS for a cleaner, professional look
st.markdown("""
    <style>
    .stApp { background-color: #fdfdfd; }
    .stButton>button { border-radius: 8px; height: 3em; transition: 0.3s; }
    .stExpander { border-radius: 10px; border: 1px solid #e1e4e8 !important; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar: Project Memory
with st.sidebar:
    st.title(" Project Memory")
    history = load_history()
    if not history:
        st.write("No past meetings recorded.")
    
    for i, entry in enumerate(reversed(history)):
        h_topic = entry.get('topic', 'Untitled')
        h_notes = entry.get('notes', "")

        with st.expander(f"Ref: {h_topic}"):
            if h_notes:
                st.caption("Meeting Outcome:")
                st.info(h_notes)
            else:
                st.caption("Status:")
                st.write("Outcome not recorded yet.")
    
    if st.button("Reset All History", type="secondary"):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            st.rerun()

# --- 4. MAIN APP INTERFACE ---
st.title("🎯 Meeting Prep AI Assistant")
st.markdown("Generates smart questions, risks, and decision points based on your project history.")

tab1, tab2 = st.tabs(["New Plan", "Update Outcome"])

with tab1:
    col1, col2 = st.columns([4, 1])
    with col1:
        new_topic = st.text_input("What is the meeting about?", placeholder="e.g., Report delays with the Ops team")
    with col2:
        st.write(" ") 
        style = st.selectbox("Tone", ["Analytical", "Direct", "Creative"])

    if st.button("Generate Strategic Brief", type="primary"):
        if new_topic:
            with st.spinner("Reviewing history and calculating risks..."):
                # BUILD CONTEXT FROM HISTORY
                context_block = "PROJECT HISTORY AND PAST OUTCOMES:\n"
                for entry in history:
                    context_block += f"- Topic: {entry.get('topic')}\n  Outcome: {entry.get('notes', 'No notes recorded.')}\n"
                
                # TARGETED PROMPT
                full_prompt = (
                    f"{context_block}\n\n"
                    f"New Meeting Title/Agenda: {new_topic}\n"
                    f"Tone Style: {style}\n\n"
                    f"TASK: Provide a strategic brief that specifically covers the following sections:\n"
                    f"1. 5 SMART QUESTIONS to ask during this meeting.\n"
                    f"2. 3 LIKELY RISKS or root causes to watch for.\n"
                    f"3. 2 CRITICAL DECISIONS to push the team toward."
                )

                try:
                    # SPECIFIC SYSTEM INSTRUCTION
                    sys_instr = (
                        "You are a Senior Strategic Consultant. "
                        "Do NOT give a general agenda. "
                        "ONLY provide the 5 questions, 3 risks, and 2 decision points requested. "
                        "Use concise, bulleted markdown. "
                        "Link your advice to the project history if relevant."
                    )

                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=full_prompt,
                        config={"system_instruction": sys_instr}
                    )
                    
                    st.divider()
                    st.subheader(f"Strategy: {new_topic}")
                    st.markdown(response.text)
                    
                    # Save record
                    save_to_history(new_topic, response.text)
                    st.toast("Strategy saved!")
                    
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.warning("Please enter a meeting topic.")

with tab2:
    st.subheader("What was the outcome?")
    if history:
        last_item = history[-1]
        st.write(f"**Current Context:** {last_item.get('topic')}")
        outcome_notes = st.text_area("Update the memory with what was actually decided:", 
                                     placeholder="e.g., Ops team agreed to hire a contractor to fix the delay by next Friday.")
        
        if st.button("Commit to Memory"):
            all_history = load_history()
            if all_history:
                all_history[-1]['notes'] = outcome_notes
                with open(HISTORY_FILE, "w") as f:
                    json.dump(all_history, f, indent=4)
                st.success("History updated. AI will reference this in the next session!")
                st.rerun()
    else:
        st.info("Start a new plan in Tab 1 to build your project memory.")
