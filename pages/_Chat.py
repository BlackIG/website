from PIL import Image
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta

import streamlit as st
import os
import base64
import logging
import time
import re

# === Page Config ===
favicon_path = "assets/icons/favicon.png"
favicon = Image.open(favicon_path) if Path(favicon_path).is_file() else "🤖"

st.set_page_config(
    page_title="BrokeTechBro",
    page_icon=favicon,
    layout="centered"
)


def load_image(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        logging.error(f"Error loading image {image_path}: {e}")
        return ""

# === Load Assets ===
logo_path = "assets/icons/logo.png"
logo = load_image(logo_path)
    
# Load environment variables
load_dotenv()
# === MongoDB Configs (placeholders) ===
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")
MONGODB_HOST = os.getenv("MONGODB_HOST")
DB_NAME = os.getenv("DB_NAME")
COLLECTION = os.getenv("COLLECTION")



# === OpenAI Setup with Error Handling ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY not found. Please set it in your .env file.")
    st.stop()

model = "gpt-4o"
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not ASSISTANT_ID:
    st.error("❌ ASSISTANT_ID not found. Please set it in your .env file.")
    st.stop()

# Create open client, save to cache to avoid recreating the client everytime
@st.cache_resource
def get_openai_client():
    """
    Initializes and returns an OpenAI client using the API key from environment variables."""
    return OpenAI(api_key=OPENAI_API_KEY)

client = get_openai_client()

# Connect to MongoDB 
@st.cache_resource
def get_mongo_collection():
        if not any([MONGODB_USERNAME, MONGODB_PASSWORD, MONGODB_HOST, DB_NAME, COLLECTION]):
            st.error("❌ MongoDB connection parameters are not fully set in environment variables.")
            logging.error("MongoDB connection parameters are not fully set in environment variables.")
                        
        else:       
            mongo_uri = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_HOST}/{DB_NAME}?retryWrites=true&w=majority"
            mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)  # 10s timeout

            return mongo_client[DB_NAME][COLLECTION]

collection = get_mongo_collection()

# Assistant should be instructed to use this words in closing a conversation. 
BOT_END_KEYWORDS = [
    "have a great day",  "goodbye"
]

# === Session Initialization ===
def initialize_session_state():
    defaults = {
        "messages": [],
        "chat_active": True,
        "cdn_injected": False,
        "thread_id": None,
        "chat_start_time": datetime.now(),
        "rating":  None,
        "show_rating": False,
        "mongo_id": None,
        "request_appointment": False,
        "appointment_phone":"",
        "appointment_email": "",
        "preferred_time": None,
        "chat_with_ai": True,  # Default to AI chat mode
        }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def click_close_chat():
    st.session_state.chat_active = False

def book_appointment_form():
    """
    Show an inline form to collect user's phone and email.
    Validates input and updates session state.
    Anchored using st.container to prevent top-page jump.
    """
    if st.session_state.request_appointment:
        # wrap form in container to anchor visually in-place relative to the button that triggered it, instead of showing at the top
        with st.container():
            with st.form("appointment_form", clear_on_submit=False):
                st.text_input("Phone Number:", placeholder="Enter phone number", key="input_phone")
                st.text_input("Email Address:", placeholder="Enter email", key="input_email")
                st.time_input("Preferred Time:", key="appointment_time")

                col1, col2 = st.columns([1, 1])
                close_button = col2.form_submit_button("Close")
                submit_button = col1.form_submit_button("Submit")

            if close_button:
                st.session_state.request_appointment = False
                st.toast("❌ Appointment cancelled")
                
                return

            if submit_button:
                phone = st.session_state.get("input_phone", "").strip()
                email = st.session_state.get("input_email", "").strip()
                booked_time = st.session_state.get("appointment_time").strftime("%H:%M:%S") if st.session_state.get("appointment_time") else ""

                if not phone or not email or not booked_time :
                    st.warning("⚠️ Please enter all required fields.")
                    return

                phone_pattern = re.compile(r"^\+?\d{10,15}$")
                if not phone_pattern.match(phone):
                    st.error("❌ Invalid phone number.")
                    return

                email_pattern = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
                if not email_pattern.match(email):
                    st.error("❌ Invalid email address.")
                    return

                # Save only after valid
                st.session_state["appointment_phone"] = phone
                st.session_state["appointment_email"] = email
                st.session_state["preferred_time"] = booked_time

                st.toast("✅ Appointment info saved")
                st.session_state.request_appointment = False
                click_close_chat() #sets chat active to false
                # Force main() to run manually after appointment booking
                st.rerun()


# === Chat Renderer === 
def render_chat():

    st.markdown("""
        <style>
            .chat-container {
                display: flex;
                flex-direction: column;
                gap: 10px;
                padding-top: 70px; /* Push chat below logo */
            }
            .bot-bubble {
                align-self: flex-start;
                background-color: #DE7E5D;
                color: #000;
                padding: 15px;
                border-radius: 15px 15px 15px 0px;
                max-width: 70%;
                font-size: 16px;
                margin-right: auto;
                margin-left: 0;
            }
            .user-bubble {
                align-self: flex-end;
                background-color: #6E2FD6;  
                color: white;
                padding: 10px 15px;
                border-radius: 15px 15px 0px 15px;
                max-width: 70%;
                font-size: 16px;
                margin-left: auto;
                margin-right: 0;
            }
            .bot-name {
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 4px;
                margin-left: 5px;
                color: #DE7E5D;
            }
                     
        </style>
        <div class="chat-container">
    """, unsafe_allow_html=True)



    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-name'>Broke Tech Bro</div><div class='bot-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


        # Show end chat after every user+assistant exchange
    if len(st.session_state.messages) >= 2 and st.session_state.messages[-1]["role"] == "assistant":
        col1, col2, col3 = st.columns([6, 2, 2])


        with col3:
            st.button("⛔ End", key="end_button", on_click=click_close_chat)
        

    # Show book appointment button if conversation is long enough
    if len(st.session_state.messages) >= 10 and st.session_state.messages[-1]["role"] == "assistant":
        with col1:
            if st.button("📅 Book", key="appointment_button"):
                st.session_state.request_appointment = True
                st.rerun()

    # Always show appointment form if toggled
    if st.session_state.get("request_appointment"):
        book_appointment_form()




# === Bot Response Logic ===
def generate_bot_reply(user_input):
    """
    Send user input to the OpenAI Assistant and return its response.

    Parameters:
        user_input (str): The message from the user.

    Returns:
        str: Assistant's response or an appropriate error/help message.
    """
    try:
        # Step 1: Create a new thread if one does not already exist in session
        if st.session_state.thread_id is None:
            thread = client.beta.threads.create()
            st.session_state.thread_id = thread.id
        else:
            # Retrieve the existing thread using the session's thread_id
            thread = client.beta.threads.retrieve(st.session_state.thread_id)

        # Step 2: Add the user's message to the assistant thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Step 3: Start the assistant run with thread and assistant ID
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            metadata={
                "assistant_name": "BROKETECHBRO",
                "assistant_id": ASSISTANT_ID
            }
        )

        # Step 4: Wait for assistant to complete response or timeout after 10 seconds
        timeout = 10  # seconds
        start_time = time.time()

        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )

            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                return ("brokeTechBro couldn’t generate a response — please try again")
            elif time.time() - start_time > timeout:
                return ("brokeTechBro is taking too long to respond - please try again")

            # pause the execution of the loop for n seconds during each iteration of the polling loop that checks the assistant's response status.
                time.sleep(0.5)

        # Step 5: Retrieve and return the assistant's most recent message
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_messages = [m for m in messages.data if m.role == "assistant"]
        assistant_messages.sort(key=lambda m: m.created_at, reverse=True)

        if assistant_messages:
            raw_reply = assistant_messages[0].content[0].text.value

            # Clean out LLM formatting artifacts and return clean message
            cleaned_reply = re.sub(r'【.*?】', '', raw_reply).strip()
            cleaned_reply = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                                   r'<a href="\2" target="_blank" style="color:#6A0DAD; text-decoration:underline;">\1</a>',
                                   cleaned_reply)
            return cleaned_reply

        return "No response from brokeTechBro at this time."

    except Exception as e:
        st.error("Error communicating with brokeTechBro.")
        logging.exception("Assistant API error")
        return "Oops, something went wrong. Check your network and try again at a later time"


def is_user_engaged() -> bool:
    # Check messages → is there any non-empty message?
    messages_engaged = any(
        msg.get("content", "").strip()
        for msg in st.session_state.get("messages", [])
    )

    # Final engagement flag
    return messages_engaged 



# === User Input Handler ===

def should_end_session(assistant_msg) -> bool:
    """
    Determines whether a session should end based on time elapsed or assistant response content.

    Parameters:
        assistant_msg (dict): The latest assistant message (must include "content").

    Returns:
        bool: True if session should end, False otherwise.
    """
    try:
        # Check time since last message
        if st.session_state.messages and "timestamp" in st.session_state.messages[-1]:
            elapsed = datetime.now() - st.session_state.messages[-1]["timestamp"]
        else:
            elapsed = timedelta(0)  # fallback if no messages or no timestamp
            logging.info("No timestamp found on last message. Defaulting elapsed to 0.")

        if elapsed > timedelta(minutes=15):
            return True

        # Check if assistant content contains any end keywords
        bot_text = assistant_msg.get("content", "").lower()
        return any(phrase in bot_text for phrase in BOT_END_KEYWORDS)

    except Exception as e:
        logging.warning(f"[should_end_session] Error: {e}")
        return False
    


def handle_user_input():
    """
    Handles user input from the Streamlit chat UI.

    - Captures user input and appends it to the session messages.
    - Sends the input to the assistant and appends the assistant's response.
    - Checks if the assistant's response should end the session.
    - Triggers a rerun to reflect new state (if session is still active).
    """
    if not st.session_state.chat_active:
        return
    if st.session_state.get("chat_with_ai"):
        with st.container():
            user_input = st.chat_input("Talk to me...", key="chat_input")
            if user_input:
                # Append user message
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input,
                    "created_at": datetime.now().isoformat()
                })
                # close the appointment if open
                st.session_state.request_appointment = False

                with st.spinner("brokeTechBro is typing..."):
                    bot_reply = generate_bot_reply(user_input)

                # Append bot reply
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": bot_reply,
                    "created_at": datetime.now().isoformat()
                })

                # End session if triggered by bot logic
                if should_end_session(st.session_state.messages[-1]):
                    st.session_state.chat_active = False
                    st.rerun()
                else:
                    st.rerun()

def create_mongo_id() -> bool:
    """
    Creates a new chat document in MongoDB if mongo_id does not exist in session.

    Returns:
        bool: True if a new document was created, False if mongo_id already exists.
    """
    try:
        if not st.session_state.get("mongo_id"):
            # First insert
            chat_data = {
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            result = collection.insert_one(chat_data)
            st.session_state.mongo_id = result.inserted_id
            logging.info(f"[create_mongo_id] Created new chat record with _id: {st.session_state.mongo_id}")
            return True
        else:
            # mongo_id already exists — no action needed
            logging.info(f"[create_mongo_id] mongo_id already exists: {st.session_state.mongo_id}")
            return False

    except PyMongoError:
        st.error("❌ Failed to create new chat record.")
        logging.exception("[create_mongo_id] MongoDB Error")
        return False

def update_chat_history() -> bool:
    """
    Updates the current chat session state in MongoDB.
    
    Chat data includes:
        - thread_id: OpenAI assistant thread identifier
        - chat_start_time: Timestamp of chat initiation
        - messages: Full user-assistant message log
        - appointment_phone, appointment_email: Captured appointment contact data
        - rating: User-provided session rating
        - updated_at: Save timestamp

    If this is the first update, inserts a new document and stores the generated _id in st.session_state.mongo_id.
    If the session already has mongo_id, updates the existing document with the latest session state.

    Returns:
        bool: True if update was successful, False otherwise.
    """
    try:
        if st.session_state.get("mongo_id"):
            chat_data = {
                "thread_id": st.session_state.get("thread_id"),
                "chat_start_time": st.session_state.get("chat_start_time"),
                "messages": st.session_state.get("messages", []),
                "appointment_phone": st.session_state.get("appointment_phone"),
                "appointment_email": st.session_state.get("appointment_email"),
                "preferred_time": st.session_state.get("preferred_time"),
                "rating": st.session_state.get("rating"),
                "updated_at": datetime.now()
            }

            result = collection.update_one(
                {"_id": st.session_state.mongo_id},
                {"$set": chat_data}
            )

            if result.modified_count == 1:
                logging.info(f"[update_chat_history] Successfully updated chat record _id: {st.session_state.mongo_id}")
                return True
            else:
 #               st.warning("⚠️ Chat history not saved.")
                logging.warning(f"[update_chat_history] No document modified for _id: {st.session_state.mongo_id}")
                return False
        else:
   #         st.warning("⚠️ No mongo_id available — skipping update.")
            logging.warning("[update_chat_history] No mongo_id in session after create_mongo_id().")
            return False

    except PyMongoError:
        st.error("❌ Failed to save chat history.")
        logging.exception("[update_chat_history] MongoDB Error")
        return False



# ===== Render Rating UI (Likert Scale) =====
def render_rating_ui(collection):
    """
    Render a Likert scale-based rating UI and save the result to MongoDB.
    """
    if not st.session_state.rating:
        col1, col2 = st.columns([9, 1])

        with col1:
            # Show Rate Chat button initially
            if not st.session_state.get("show_rating"):
                if st.button("⭐ Rate Chat", key="rate_button"):
                    st.session_state.show_rating = True

            if st.session_state.show_rating:
                # Display Likert scale options
                st.markdown("**How was your chat?**")
                likert_options = {
                    1: "Very Dissatisfied",
                    2: "Dissatisfied",
                    3: "Neutral",
                    4: "Satisfied",
                    5: "Very Satisfied"
                }
                selected = st.radio(
                    "Select a rating:",
                    options=list(likert_options.keys()),
                    format_func=lambda x: f"{x} - {likert_options[x]}",
                    key="likert_rating",
                    index=None
                )

                if selected is not None:
                    st.session_state.rating = selected
                    st.success(f"Thank you for rating us: {likert_options[selected]}")

                    if st.session_state.mongo_id:
                        collection.update_one(
                            {"_id": st.session_state.mongo_id},
                            {"$set": {"rating": selected}},
                            upsert=True
                        )
                        st.session_state.show_rating = False
                        st.rerun()
                    else:
                        st.write("No active conversation")
                        st.session_state.show_rating = False
    else:
        return

# === Closing Dashboard ===
def show_closing_dashboard():
    """
    Displays a closing dashboard with helpful video guides, support links,
    and social media handles after the chat session ends.
    """
    render_rating_ui(collection) #show rate button
    if st.session_state.rating == None:
        st.toast("Please rate me")
        st.success("Please rate this chat 🙏🙏🙏")

    # Declare image URLs and destination links
    tiles = [
        {"title": "LinkedIn", "link": "https://www.linkedin.com/in/chilakaig/", "img": "https://cdn-icons-png.flaticon.com/512/174/174857.png"},
        {"title": "Instagram", "link": "", "img": "https://cdn-icons-png.flaticon.com/512/174/174855.png"},
        {"title": "YouTube", "link": "", "img": "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"},
        {"title": "X", "link": "", "img": "https://freepnglogo.com/images/all_img/1691832581twitter-x-icon-png.png"},
        {"title": "GitHub", "link": "https://github.com/BlackIG/", "img": "https://cdn-icons-png.flaticon.com/512/25/25231.png"},
        {"title": "WhatsApp", "link": "", "img": "https://cdn-icons-png.flaticon.com/512/124/124034.png"},
        {"title": "Facebook", "link": "", "img": "https://cdn-icons-png.flaticon.com/512/124/124010.png"},
        {"title": "TikTok", "link": "", "img": "https://cdn-icons-png.flaticon.com/512/3670/3670358.png"},
        {"title": "Telegram", "link": "", "img": "https://cdn-icons-png.flaticon.com/512/2111/2111646.png"}
    ]

    html_tiles = "".join([
        f"<a href='{tile['link']}' target='_blank' class='tile' title='{tile['title']}'>"
        f"<img src='{tile['img']}' alt='{tile['title']}'>"
        f"<div class='tile-title'>{tile['title']}</div>"
        f"</a>"
        for tile in tiles
    ])

    st.markdown(f"""
    <style>
    .tile-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin-top: 2rem;
    }}
    .tile {{
        background: #FFFFFF;
        color: white;
        border-radius: 8px;
        overflow: hidden;
        text-align: center;
        text-decoration: none;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }}
    .tile:hover {{
        transform: scale(1.03);
    }}
    .tile img {{
        width: 100%;
        height: auto;
        aspect-ratio: 4 / 1;
        object-fit: contain;
        padding: 4px;
    }}
    .tile-title {{
        font-size: 16px;
        font-weight: 600;
        padding: 12px;
        color: #ff0475;
        text-decoration: underline;
    }}
    .tile:hover .tile-title {{
        color: #6E2FD6; 
    }}
    </style>
    <div class='tile-grid'>
        {html_tiles}
    </div>
    """, unsafe_allow_html=True)


# === Main App ===
def main():
    try:
        #Ensure state variables are existing or initialised if not existing
        initialize_session_state()

        # Check engagement
        has_engaged  = is_user_engaged()

        #create a mongo id if not created
        if has_engaged:
            create_mongo_id()
            #will update if mongo_id exists already
            update_chat_history()


        # If session is over, show only dashboard and exit
        if not st.session_state.chat_active:
            try:
                show_closing_dashboard()
            except Exception as e:
                st.error('⚠️ Closing dashboard failed to load.')
                logging.exception("Dashboard load error")
            return  #  prevent rest of app from rendering

        #  Create thread if needed
        if st.session_state.thread_id is None:
            try:
                thread = client.beta.threads.create()
                st.session_state.thread_id = thread.id
            except Exception as thread_error:
                st.error(f"❌ OpenAI cannot prepare thread for this conversation: {thread_error}")
                return

        # ✅ Header logo
        if logo:
            st.markdown(f"""
                <style>
                    .logo {{
                        position: absolute;
                        top: 1rem;
                        right: 1rem;
                        width: 100px;
                        z-index: 999;
                    }}
                    .block-container {{
                        position: relative;
                    }}
                </style>
                <a href="https://thebroketechbro.streamlit.app" target="_blank">
                    <img class='logo' src='data:image/png;base64,{logo}' alt="Logo">
                </a>
            """, unsafe_allow_html=True)

        render_chat()
        handle_user_input()
        #  save updated chat history AFTER possible new input!
        update_chat_history()


    except Exception as e:
        st.error("Oops, something went wrong loading the app, contact chilaka.ig@gmail.com")
        st.exception(e)
        logging.exception("Main block error")

main()


