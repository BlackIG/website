import streamlit as st
from PIL import Image
import os
from pathlib import Path
import time

# === Page Configuration ===
favicon_path = "assets/icons/favicon.png"
favicon = Image.open(favicon_path) if Path(favicon_path).is_file() else "🤖"

st.set_page_config(
    page_title="BrokeTechBro",
    page_icon=favicon,
    layout="centered"
)

# === Constants ===
EVENT_PHOTO_DIR = "assets/photos/event_photo"
IMAGE_WIDTH = 350
SLIDESHOW_INTERVAL = 3  # seconds

# === Render About Text ===
def render_about():
    st.title("👤 About")
    st.markdown("""
    <div style='font-size:14px; line-height:1.6'>
    Hi, I’m Ikechukwu Chilaka, a data engineer and technology strategist with more than seven years of professional experience in customer experience, data analytics, and data engineering.<br><br>

    My career has been centered around solving real-world business problems through scalable data systems, automation, and analytics that inform impactful decisions. Over the years, I have worked with prominent financial institutions such as United Bank for Africa (UBA) and Carbon Microfinance Bank, where I led and contributed to key projects that improved operational efficiency, enhanced customer outcomes, and drove data-informed strategies across teams.<br><br>

    In addition to my roles in the corporate sector, I am the Chief Data Strategist and Co-founder of contactOZ, a startup dedicated to enabling organizations across Nigeria to build truly customer-centric workforces.
    I also hold membership with the British Computer Society (BCS), the Chartered Institute for IT, where I continue to engage in global conversations around professionalism, ethics, and emerging best practices in data and technology.<br><br>

    At the core of everything I do is a desire to bridge the gap between technology and people. Whether I’m building automated systems, designing scalable data workflows, or mentoring others in tech, I’m driven by the belief that people should always come first.
    </div>
    """, unsafe_allow_html=True)


# === Load Image Paths ===
def load_event_images():
    valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    all_files = os.listdir(EVENT_PHOTO_DIR)
    valid_images = [f for f in sorted(all_files) if Path(f).suffix.lower() in valid_extensions]
    return [os.path.join(EVENT_PHOTO_DIR, img) for img in valid_images]


# === Display Slideshow in Two Columns ===
def render_event_slideshow(img_paths):
    total = len(img_paths)
    if total == 0:
        st.warning("No event images found.")
        return

    # Initialize index
    if "slideshow_index" not in st.session_state:
        st.session_state.slideshow_index = 0

    idx1 = st.session_state.slideshow_index % total
    idx2 = (st.session_state.slideshow_index + 1) % total

    col1, col2 = st.columns(2)
    with col1:
        st.image(Image.open(img_paths[idx1]), width=IMAGE_WIDTH)
    with col2:
        st.image(Image.open(img_paths[idx2]), width=IMAGE_WIDTH)

    # Cycle index and rerun
    time.sleep(SLIDESHOW_INTERVAL)
    st.session_state.slideshow_index = (st.session_state.slideshow_index + 1) % total
    st.rerun()


# === Run Page ===
def about():
    render_about()
    render_event_slideshow(load_event_images())


if __name__ == "__main__":
    about()
