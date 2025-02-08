import streamlit as st
import google.generativeai as genai
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import logging
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic
import requests
import streamlit.components.v1 as components
import speech_recognition as sr

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Gemini AI API
os.environ['GOOGLE_API_KEY'] = 'AIzaSyB3lpyL0wgEWj4a_pkXpfYvR3jotXbJfAU'
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Language options
indian_languages = {
    "Hindi": "hi", "English": "en", "Telugu": "te", "Tamil": "ta",
    "Marathi": "mr", "Gujarati": "gu", "Kannada": "kn", "Malayalam": "ml",
    "Odia": "or", "Bengali": "bn", "Assamese": "as", "Punjabi": "pa", "Urdu": "ur"
}

# Function to translate and speak text
def translate_and_speak_text(text, language_code):
    try:
        translated_text = GoogleTranslator(source='auto', target=language_code).translate(text)
        tts = gTTS(text=translated_text, lang=language_code)
        tts.save("response.mp3")
        st.audio("response.mp3", format="audio/mp3")
        os.remove("response.mp3")  # Cleanup
        return translated_text
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return text

# Function to query Gemini AI for directions
def query_directions(start, end):
    prompt = f"Provide detailed directions from {start} to {end}."
    model = genai.GenerativeModel('gemini-pro')
    try:
        response = model.generate_content(prompt)
        if response and response.parts:
            return response.text
        else:
            logging.error("No response parts found.")
            return "Sorry, there was an error generating the directions."
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return "Sorry, there was an error generating the directions."

# Function to get coordinates from a place name
def get_coordinates(place):
    url = f"https://nominatim.openstreetmap.org/search?q={place}&format=json&limit=1"
    headers = {"User-Agent": "RouteFinder/1.0"}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data:
        return (float(data[0]['lat']), float(data[0]['lon']))
    else:
        return None

# Function to create a map
def create_map(start_coords, end_coords):
    m = folium.Map(location=start_coords, zoom_start=13)
    folium.Marker(start_coords, popup="Start Point", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(end_coords, popup="End Point", icon=folium.Icon(color='red')).add_to(m)
    folium.PolyLine([start_coords, end_coords], color="blue", weight=2.5, opacity=1).add_to(m)
    return m

# Function to convert speech to text
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            st.error("Could not understand the audio")
        except sr.RequestError as e:
            st.error(f"Could not request results; {e}")
    return None

# Streamlit UI
st.set_page_config(page_title="Accessible Transport Navigator", layout="wide")
st.title("Accessible Transport Navigator")

# Initialize session state for voice input
if 'start_place' not in st.session_state:
    st.session_state['start_place'] = ""
if 'end_place' not in st.session_state:
    st.session_state['end_place'] = ""

# Input fields
col1, col2 = st.columns(2)
with col1:
    start_place = st.text_input("Start Location:", placeholder="Enter start location", value=st.session_state['start_place'])
    if st.button("🎤 Start Location Voice Input"):
        voice_text = speech_to_text()
        if voice_text:
            st.session_state['start_place'] = voice_text
            start_place = voice_text
with col2:
    end_place = st.text_input("End Location:", placeholder="Enter destination", value=st.session_state['end_place'])
    if st.button("🎤 End Location Voice Input"):
        voice_text = speech_to_text()
        if voice_text:
            st.session_state['end_place'] = voice_text
            end_place = voice_text

# Vehicle type selection and fare calculation
vehicle_types = {"Car": 60, "Motorcycle": 50, "Bus": 40, "Walking": 5, "Train": 80, "Bike": 20}
vehicle_fares = {"Car": 10, "Motorcycle": 5, "Bus": 3, "Walking": 0, "Train": 8, "Bike": 2}
vehicle = st.selectbox("Choose your vehicle type", list(vehicle_types.keys()))

# Emergency calling slide
st.sidebar.title("Emergency Assistance")
if st.sidebar.button("Call Emergency Services"):
    st.sidebar.write("Calling emergency services...")
    st.sidebar.write("Please stay calm and provide your location to the operator.")
    st.sidebar.write("Emergency Numbers:")
    st.sidebar.write("Police: 100")
    st.sidebar.write("Ambulance: 102")
    st.sidebar.write("Fire: 101")

# Language selection
target_language = st.selectbox("Choose language for translation", list(indian_languages.keys()))

if st.button("Find Route"):
    if start_place and end_place:
        start_coords = get_coordinates(start_place)
        end_coords = get_coordinates(end_place)

        if start_coords and end_coords:
            # Calculate distance
            distance = geodesic(start_coords, end_coords).kilometers
            speed = vehicle_types[vehicle]
            time = (distance / speed) * 60  # Time in minutes
            fare = distance * vehicle_fares[vehicle]

            # Generate directions using AI
            directions = query_directions(start_place, end_place)
            language_code = indian_languages[target_language]
            translated_directions = translate_and_speak_text(directions, language_code)

            # Display directions
            st.subheader("Directions")
            st.write(translated_directions)

            # Display fare and time
            st.subheader("Fare and Time")
            st.write(f"Estimated Fare: ₹{fare:.2f}")
            st.write(f"Estimated Time: {time:.2f} minutes")

            # Display map
            st.subheader("Route Map")
            m = create_map(start_coords, end_coords)
            folium_static(m)

            # Embed JavaScript for map interactions
            components.html(
                f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Route Map</title>
                    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
                    <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.css" />
                    <style>
                        #map {{ height: 500px; }}
                    </style>
                </head>
                <body>
                    <div id="map"></div>
                    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
                    <script src="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.js"></script>
                    <script>
                        var map = L.map('map').setView([{start_coords[0]}, {start_coords[1]}], 13);
                        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenStreetMap contributors' }}).addTo(map);

                        var routeControl = L.Routing.control({{
                            waypoints: [
                                L.latLng({start_coords[0]}, {start_coords[1]}),
                                L.latLng({end_coords[0]}, {end_coords[1]})
                            ],
                            createMarker: function (i, waypoint) {{
                                const iconUrl = i === 0 ? 'https://cdn-icons-png.flaticon.com/512/1144/1144709.png' : 'https://cdn-icons-png.flaticon.com/512/10522/10522034.png';
                                return L.marker(waypoint.latLng, {{ icon: L.icon({{ iconUrl, iconSize: [50, 50], iconAnchor: [25, 50] }}) }});
                            }}
                        }}).addTo(map);
                    </script>
                </body>
                </html>
                """,
                height=550,
            )
        else:
            st.error("Could not retrieve coordinates for the specified locations.")
    else:
        st.warning("Please enter both start and end locations.")
