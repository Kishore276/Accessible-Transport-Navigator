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
def create_map(location, zoom_start=13, markers=None, polyline=None):
    m = folium.Map(location=location, zoom_start=zoom_start)
    if markers:
        for marker in markers:
            folium.Marker(marker[0], popup=marker[1], icon=folium.Icon(color=marker[2])).add_to(m)
    if polyline:
        folium.PolyLine(polyline, color="blue", weight=2.5, opacity=1).add_to(m)
    return m

# Function to find nearby hospitals
def find_nearby_hospitals(lat, lon, radius=5000):
    url = f"https://nominatim.openstreetmap.org/search?q=hospital&format=json&lat={lat}&lon={lon}&radius={radius}"
    headers = {"User-Agent": "RouteFinder/1.0"}
    response = requests.get(url, headers=headers)
    data = response.json()
    hospitals = []
    for item in data:
        hospitals.append((float(item['lat']), float(item['lon'])))
    return hospitals

# Function to calculate fare based on distance and vehicle type
def calculate_fare(distance, vehicle_type):
    # Fixed fare rates per km (for demonstration purposes)
    fare_rates = {
        "Car": 10,  # ₹10 per km
        "Motorcycle": 5,  # ₹5 per km
        "Bus": 2,  # ₹2 per km
        "Train": 1,  # ₹1 per km (approximate fare for trains)
        "Walking": 0,  # Free
    }
    return distance * fare_rates.get(vehicle_type, 0)

# Function to handle voice input
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            st.error("Sorry, I could not understand the audio.")
        except sr.RequestError as e:
            st.error(f"Could not request results from Google Speech Recognition service; {e}")
    return None

# Streamlit UI
st.set_page_config(page_title="Route Finder with AI", layout="wide")
st.title("Route Finder with AI and Voice Input")

# Initialize session state for voice input
if "start_place" not in st.session_state:
    st.session_state.start_place = ""
if "end_place" not in st.session_state:
    st.session_state.end_place = ""

# Input fields
col1, col2 = st.columns(2)
with col1:
    start_place = st.text_input("Start Location:", placeholder="Enter start location", value=st.session_state.start_place, key="start_input")
    start_voice = st.button("🎤 Start Location Voice Input")
with col2:
    end_place = st.text_input("End Location:", placeholder="Enter destination", value=st.session_state.end_place, key="end_input")
    end_voice = st.button("🎤 End Location Voice Input")

# Handle voice input
if start_voice:
    voice_input = get_voice_input()
    if voice_input:
        st.session_state.start_place = voice_input
        st.rerun()  # Refresh the app to update the input field

if end_voice:
    voice_input = get_voice_input()
    if voice_input:
        st.session_state.end_place = voice_input
        st.rerun()  # Refresh the app to update the input field

# Vehicle type selection
vehicle_type = st.selectbox(
    "Select Mode of Transport",
    ["Car", "Motorcycle", "Bus", "Train", "Walking"],  # Added Train
    index=0,  # Default to Car
)

# Language selection
target_language = st.selectbox("Choose language for translation", list(indian_languages.keys()))

# Emergency calling button
st.markdown("### Emergency Services")
st.markdown("Call emergency services at **112** in India.")
if st.button("🚨 Call Emergency Services"):
    st.write("Redirecting to emergency services...")

if st.button("Find Route"):
    if st.session_state.start_place and st.session_state.end_place:
        start_coords = get_coordinates(st.session_state.start_place)
        end_coords = get_coordinates(st.session_state.end_place)

        if start_coords and end_coords:
            # Calculate distance
            distance = geodesic(start_coords, end_coords).kilometers

            # Define speeds for different vehicle types (in km/h)
            speeds = {
                "Car": 60,
                "Motorcycle": 50,
                "Bus": 40,
                "Train": 60,  # Average speed for trains
                "Walking": 5,
            }

            # Calculate travel time based on selected vehicle type
            speed = speeds.get(vehicle_type, 60)  # Default to Car speed if vehicle type is not found
            time = (distance / speed) * 60  # Time in minutes

            # Calculate fare
            fare = calculate_fare(distance, vehicle_type)

            # Generate directions using AI
            directions = query_directions(st.session_state.start_place, st.session_state.end_place)
            language_code = indian_languages[target_language]
            translated_directions = translate_and_speak_text(directions, language_code)

            # Display directions
            st.subheader("Directions")
            st.write(translated_directions)

            # Display travel details
            st.subheader("Travel Details")
            st.write(f"Distance: {distance:.2f} km")
            st.write(f"Estimated Travel Time: {time:.2f} minutes (by {vehicle_type})")
            st.write(f"Estimated Fare: ₹{fare:.2f}")

            # Display route map
            st.subheader("Route Map")
            route_map = create_map(
                location=start_coords,
                markers=[
                    (start_coords, "Start Point", "green"),
                    (end_coords, "End Point", "red")
                ],
                polyline=[start_coords, end_coords]
            )
            folium_static(route_map)

            # Display nearby hospitals map
            st.subheader("Nearby Hospitals")
            hospitals = find_nearby_hospitals(start_coords[0], start_coords[1])
            if hospitals:
                hospital_map = create_map(
                    location=start_coords,
                    markers=[(hospital, "Hospital", "blue") for hospital in hospitals]
                )
                folium_static(hospital_map)
            else:
                st.warning("No nearby hospitals found.")
        else:
            st.error("Could not retrieve coordinates for the specified locations.")
    else:
        st.warning("Please enter both start and end locations.")