import streamlit as st
import json
from PIL import Image
from pathlib import Path

# === Page Setup ===
def configure_page():
    """
    Set the Streamlit page configuration including favicon and layout.
    """
    favicon_path = "assets/icons/favicon.png"
    favicon = Image.open(favicon_path) if Path(favicon_path).is_file() else "🤖"

    st.set_page_config(
        page_title="BrokeTechBro",
        page_icon=favicon,
        layout="centered"
    )

# === Load Projects from JSON ===
def load_projects(json_path="assets/docs/projects.json"):
    """
    Load project data from a JSON file.

    Returns:
        list: A list of project dictionaries.
    """
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error("Failed to load project data.")
        return []

# === Render Each Project ===
def render_projects(projects):
    """
    Display all projects in the UI using containers and columns.

    Args:
        projects (list): List of project dictionaries.
    """
    st.title("📂 Projects")
    st.markdown("---")

    for project in projects:
        with st.container():
            col1, col2 = st.columns([1, 2])

            # Left Column: Project Image
            if project.get("img") and Path(project["img"]).is_file():
                img = Image.open(project["img"])
                col1.image(img, width=200)
            else:
                col1.markdown("📷 *No image*")

            # Right Column: Project Info
            title = project.get("title", "Untitled")
            url = project.get("url", "#")
            description = project.get("text", "")

            col2.markdown(f"### [{title}]({url})")
            col2.markdown(description)

        st.markdown("---")

# === Main Execution ===
def main():
    configure_page()
    projects = load_projects()
    render_projects(projects)

if __name__ == "__main__":
    main()
