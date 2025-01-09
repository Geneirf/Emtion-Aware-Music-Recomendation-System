import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
 
# Streamlit Page Config
st.set_page_config(page_title="Spotify Mood-Based Song Player", page_icon="🎵", layout="centered")
 
# Custom CSS for styling
st.markdown(
    """
<style>
    .main {
        background-color: #f4f6f8;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
    }
    .reportview-container {
        background: linear-gradient(to right, #ffecd2, #fcb69f);
    }
    h1, h2, h3, p, label {
        font-family: 'Arial', sans-serif;
    }
    .spotify-header {
        text-align: center;
        color: #1db954;
        font-weight: bold;
    }
    .track-details {
        background-color: #fff;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        margin-top: 20px;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        font-size: 14px;
        color: #666;
    }
</style>
    """,
    unsafe_allow_html=True,
)
 
# API Keys and Config
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://localhost:8501/" 
 
# Google Gemini API Setup
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
 
# Spotify OAuth Setup
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-modify-playback-state user-read-playback-state",
    cache_path=".spotify_cache"
)
 
# Helper function to get Spotify client
def get_spotify_client():
    url_params = st.experimental_get_query_params()  
 
    # Store the authorization code in session state
    if "code" in url_params and "auth_code" not in st.session_state:
        st.session_state["auth_code"] = url_params["code"][0]
 
    # Display the authorization link if not authenticated
    if "auth_code" not in st.session_state:
        auth_url = sp_oauth.get_authorize_url()
        st.markdown(f"[Click here to authorize Spotify]({auth_url})", unsafe_allow_html=True)
        return None
 
    try:
        token_info = sp_oauth.get_cached_token()
        if not token_info:
            token_info = sp_oauth.get_access_token(st.session_state["auth_code"])
        if token_info and sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        return spotipy.Spotify(auth=token_info["access_token"])
    except spotipy.oauth2.SpotifyOauthError as e:
        st.error(f"Spotify OAuth Error: {e}")
        st.markdown(f"[Reauthorize Spotify]({sp_oauth.get_authorize_url()})", unsafe_allow_html=True)
    return None
 
# Helper function to list available Spotify devices
def list_available_devices(spotify_client):
    try:
        devices = spotify_client.devices().get("devices", [])
        return {device["id"]: device["name"] for device in devices}
    except Exception as e:
        st.error(f"Error listing devices: {e}")
        return {}
 
# Autoplay Track on Device
def autoplay_track(spotify_client, track_uri, device_id):
    try:
        spotify_client.start_playback(device_id=device_id, uris=[track_uri])
        st.success("🎶 Hope you enjoy the song. 🎶")
    except Exception as e:
        st.error(f"Failed to start playback: {e}")
 
# Main Function
def main():
    st.markdown("<h1 class='spotify-header'>🎧 Spotify Mood-Based Song Player</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter your mood or message, and we'll recommend and play a song for you!</p>", unsafe_allow_html=True)
 
    # Authenticate Spotify
    spotify_client = get_spotify_client()
    if spotify_client:
        st.success("✅ Successfully authenticated with Spotify! 🎶")
 
        # User Input
        user_input = st.text_input("✨ How are you feeling today? (e.g., 'happy', 'relaxed')", "")
 
        # Refresh device list before allowing user to select a device
        devices = list_available_devices(spotify_client)
        if devices:
            selected_device_id = st.selectbox(
                "🎵 Select a Spotify device:",
                options=list(devices.keys()),
                format_func=lambda x: devices[x]
            )
        else:
            st.warning("⚠️ No active Spotify devices detected. Please open Spotify on a device.")
            return
 
        if user_input and selected_device_id:
            with st.spinner("🎤 Finding the perfect song for your mood..."):
                try:
                    prompt = f"Recommend a song based on the mood: '{user_input}'. Please respond with 'song name - artist'."
                    ai_response = model.generate_content(prompt).text.strip()
 
                    if " - " not in ai_response:
                        st.error("❌ Invalid AI response format. Please try again.")
                        return
 
                    st.markdown(f"<h6 class='spotify-header'>🎶 AI recommendation: {ai_response}</h6>", unsafe_allow_html=True)
 
                    # Search Spotify for the recommended song
                    search_results = spotify_client.search(q=ai_response, type="track", limit=1)
                    if search_results["tracks"]["items"]:
                        track = search_results["tracks"]["items"][0]
                        track_name = track["name"]
                        artist_name = ", ".join([artist["name"] for artist in track["artists"]])
                        track_uri = track["uri"]
 
                        st.markdown(f"### Now playing: {track_name} by {artist_name}")
                        st.markdown(
                            f'<iframe src="https://open.spotify.com/embed/track/{track["id"]}" width="300" height="80" frameborder="0" allow="encrypted-media"></iframe>',
                            unsafe_allow_html=True
                        )
                        # Autoplay track
                        autoplay_track(spotify_client, track_uri, selected_device_id)
                    else:
                        st.error("🚫 Couldn't find a song based on the recommendation.")
                except Exception as e:
                    st.error(f"Error generating song recommendation: {e}")
    else:
        st.warning("🔐 Please authorize Spotify to continue.")
 
    # Footer
    st.markdown("<div class='footer'>Built with ❤️ by GSAS Nida student group</div>", unsafe_allow_html=True)
 
if __name__ == "__main__":
    main()
