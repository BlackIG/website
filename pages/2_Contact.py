import streamlit as st
from PIL import Image
from pathlib import Path

# === Page Config ===
def set_page_config():
    favicon_path = "assets/icons/favicon.png"
    favicon = Image.open(favicon_path) if Path(favicon_path).is_file() else "🤖"
    st.set_page_config(
        page_title="BrokeTechBro",
        page_icon=favicon,
        layout="centered"
    )

# === Render Contact Info Section ===
def render_contact_section():
    st.title("✉️ Contact")
    col1, col2 = st.columns([1.2, 2])

    # Left: Profile Image
    with col1:
        profile_path = "assets/photos/about_photo/photo_working.jpeg"
        if Path(profile_path).is_file():
            profile_img = Image.open(profile_path)
            st.image(profile_img, width=250, caption="Ikechukwu Chilaka")

    # Right: Contact Details
    with col2:
        st.markdown("""
            <div style='font-size:16px; line-height:1.8'>
                <p><strong>LinkedIn:</strong> <a href='https://www.linkedin.com/in/chilakaig/' target='_blank'>chilakaig</a></p>
                <p><strong>Email:</strong> <a href='mailto:chilaka.ig@gmail.com'>chilaka.ig@gmail.com</a></p>
            </div>
        """, unsafe_allow_html=True)

# === Main Entry ===
def contact():
    set_page_config()
    render_contact_section()

if __name__ == "__main__":
    contact()
