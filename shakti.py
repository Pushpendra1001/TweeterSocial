import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid
import google.generativeai as genai
import requests
from requests_oauthlib import OAuth1

DATA_FILE = "posts.csv"
UPLOAD_FOLDER = "uploads"
GEMINI_API_KEY = "Hide"

API_KEY = "Hide"
API_SECRET = "Hide"
ACCESS_TOKEN = "Hide"
ACCESS_TOKEN_SECRET = "Hide"

# When creating the initial CSV file
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["id", "platform", "type", "text", "image", "status", "scheduled_time", "created_at"])
    df.to_csv(DATA_FILE, index=False, encoding="utf-8")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

df = pd.read_csv(DATA_FILE)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

if "ai_content" not in st.session_state:
    st.session_state.ai_content = ""

st.set_page_config(page_title="AI Social Media Scheduler", page_icon="📲")
st.title("Shakti-AI: Your AI Social Media Assistant")
st.write("📲 AI-Powered Social Media Post Scheduler + Twitter Uploader")

platform = st.selectbox("Select Platform", ["Twitter", "Instagram"])
post_type = st.selectbox("Post Type", ["Motivational", "Technical", "Funny", "Announcement", "Promotional"])
user_input = st.text_area("🔎 Describe your idea", placeholder="e.g. New product launch, Python tips, etc.")
word_limit = st.slider("🔢 Set Word Limit", min_value=20, max_value=300, value=100)
image = st.file_uploader("📷 Upload Image (optional)", type=["jpg", "jpeg", "png"])
post_time = st.time_input("⏰ Schedule Time")

def generate_ai_content():
    prompt = f"Write a {post_type.lower()} style post for {platform}. Limit it to {word_limit} words. Topic: {user_input}"
    try:
        response = model.generate_content(prompt)
        st.session_state.ai_content = response.text.strip()
        st.success("✅ Content generated!")
    except Exception as e:
        st.error(f"❌ Error: {e}")

col1, col2 = st.columns(2)
with col1:
    if st.button("✨ Generate Content"):
        generate_ai_content()

with col2:
    if st.button("🔁 Regenerate"):
        generate_ai_content()

if st.session_state.ai_content:
    st.subheader("✍️ Generated Content (Editable)")
    edited_content = st.text_area("Edit before scheduling/posting:", value=st.session_state.ai_content, height=150)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Schedule Post"):
            post_id = str(uuid.uuid4())
            image_name = None

            if image:
                image_name = f"{post_id}_{image.name}"
                with open(os.path.join(UPLOAD_FOLDER, image_name), "wb") as f:
                    f.write(image.getbuffer())

            new_post = {
                "id": post_id,
                "platform": platform,
                "type": post_type,
                "text": edited_content,
                "image": image_name,
                "status": "Pending",
                "scheduled_time": post_time.strftime("%H:%M"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            df = pd.concat([df, pd.DataFrame([new_post])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False, encoding="utf-8")
            st.success("✅ Post scheduled!")
            st.session_state.ai_content = ""

    with col2:
        if platform == "Twitter" and st.button("🚀 Post to Twitter"):
            mock_mode = False  
            
            if mock_mode:
                st.success("🚀 Tweet posted successfully! (MOCK MODE)")
                st.info(f"Tweet content: {edited_content}")
          
                with open("mock_tweets.txt", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] {edited_content}\n")
            else:
                try:
                    url = "https://api.twitter.com/2/tweets"
                    payload = {"text": edited_content}
                    
                    st.info("Sending request to Twitter API...")
                    
                    auth = OAuth1(
                        API_KEY, 
                        API_SECRET,
                        ACCESS_TOKEN, 
                        ACCESS_TOKEN_SECRET
                    )
                    
                    response = requests.post(url, json=payload, auth=auth)
                    
                    st.write(f"Response status code: {response.status_code}")
                    
                    if response.status_code == 201:
                        st.success("🚀 Tweet posted successfully!")
                    else:
                        st.error(f"❌ Failed to post tweet: {response.status_code}")
                        st.write("Error details:")
                        st.json(response.json() if response.content else {"message": "No response content"})
                        
                        if response.status_code == 403:
                            st.warning("""
                            This is likely a permissions issue. Please check:
                            1. Your Twitter Developer account has paid access (Basic tier minimum)
                            2. Your app has 'Write' permissions enabled
                            3. Your tokens are correctly configured with tweet.write scope
                            """)
                        elif response.status_code == 401:
                            st.warning("Authentication failed. Your API keys may be invalid or expired.")
                    
                except Exception as e:
                    st.error(f"❌ Exception when posting to Twitter: {str(e)}")

    with col3:
        if st.button("❌ Reject"):
            st.session_state.ai_content = ""
            st.info("🗑️ Content cleared.")

st.header("📟 Review Pending Posts")
pending_df = df[df["status"] == "Pending"]
for idx, row in pending_df.iterrows():
    st.markdown("---")
    st.write(f"*Platform:* {row['platform']}")
    st.write(f"*Type:* {row['type']}")
    st.write(f"*Content:* {row['text']}")
    st.write(f"*Scheduled at:* {row['scheduled_time']}")
    if pd.notna(row['image']):
        st.image(os.path.join(UPLOAD_FOLDER, row['image']), width=250)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve", key=f"approve_{row['id']}"):
            df.loc[df['id'] == row['id'], 'status'] = 'Approved'
            df.to_csv(DATA_FILE, index=False, encoding="utf-8")
            st.success(f"Post {row['id']} approved!")
    with col2:
        if st.button("❌ Reject", key=f"reject_{row['id']}"):
            df.loc[df['id'] == row['id'], 'status'] = 'Rejected'
            df.to_csv(DATA_FILE, index=False, encoding="utf-8")
            st.warning(f"Post {row['id']} rejected.")

st.markdown("---")
st.subheader("📊 Sample Scheduled Posts (Demo Only)")
dummy_data = pd.DataFrame([
    {
        "Username": "Pushpendra",
        "Platform": "Instagram",
        "Post Type": "Motivational",
        "Content": "Success doesn't come from what you do occasionally, it comes from what you do consistently.",
        "Time": "09:00 AM"
    },
    {
        "Username": "mohit_dev",
        "Platform": "Twitter",
        "Post Type": "Technical",
        "Content": "Use list comprehensions in Python for cleaner and faster code! 🐍 #PythonTips",
        "Time": "12:30 PM"
    },
    {
        "Username": "aryan_fun",
        "Platform": "Instagram",
        "Post Type": "Funny",
        "Content": "When the code works on the first try… suspicious but grateful 😂💻",
        "Time": "05:45 PM"
    }
])
st.dataframe(dummy_data, use_container_width=True)