"""
Home Page for BrokeTechBro Streamlit App

This module renders the homepage UI with:
- Logo and favicon
- Knowledge Base browser
- Footer navigation
- Floating chat icon

Author: Ikechukwu Chilaka
"""

import streamlit as st
from PIL import Image
from pathlib import Path
import json

# === Page Configuration ===
favicon_path = "assets/icons/favicon.png"
favicon = Image.open(favicon_path) if Path(favicon_path).is_file() else "🤖"

st.set_page_config(
    page_title="BrokeTechBro",
    page_icon=favicon,
    layout="centered"
)

# === Hero Section ===
logo_path = "assets/icons/logo.png"
if Path(logo_path).is_file():
    st.image(logo_path, width=250)
else:
    st.markdown(":robot:")


def initialize_session_state():
    """Initialize session state with default values."""
    defaults = {
        "selected_category": "FAQs",  # Open FAQs by default
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_kb():
    """Render knowledge base with category buttons and expandable entries."""
    with open("assets/docs/kb.json", "r") as f:
        kb = json.load(f)

    cols = st.columns(len(kb["knowledge_base"]))
    for idx, section in enumerate(kb["knowledge_base"]):
        with cols[idx]:
            if st.button(section["category"]):
                st.session_state.selected_category = section["category"]

    selected = st.session_state.selected_category
    section_data = next((s for s in kb["knowledge_base"] if s["category"] == selected), None)
    if section_data:
        st.markdown(f"##### {selected}")
        for entry in section_data["entries"]:
            with st.expander(entry["title"]):
                st.markdown(entry["description"])


def footer():
    """Render footer with navigation links and blog reference."""
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.page_link("pages/1_About.py", label="👤 About")

    with col2:
        st.page_link("pages/2_Contact.py", label="✉️ Contact")

    with col3:
        st.page_link("pages/3_Projects.py", label="📂 Projects")

    with col4:
        st.markdown(
            '<a href="https://medium.com/@brokeTechBro" target="_blank">📝 Blog</a>',
            unsafe_allow_html=True
        )


def create_chat_icon():
    """Render floating chat icon button that links to Chat page."""
    chat_icon = """
        <style>
            .chat-button {
                position: fixed;
                bottom: 40px;
                right: 40px;
                z-index: 9999;
            }
            .chat-button a {
                border-radius: 50%;
                width: 60px;
                height: 60px;
                background-color: #DE7E5D;
                color: white;
                font-size: 28px;
                border: none;
                text-decoration: none;
                display: flex;
                align-items: center;
                justify-content: center;
            }
        </style>
        <div class="chat-button">
            <a href="/Chat" target="_self">💬</a>
        </div>
    """
    st.markdown(chat_icon, unsafe_allow_html=True)


def home():
    """Run the homepage application."""
    initialize_session_state()
    render_kb()
    footer()
    create_chat_icon()


if __name__ == "__main__":
    home()
