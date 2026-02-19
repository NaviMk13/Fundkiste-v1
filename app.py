import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
import time
from datetime import datetime

# --- DESIGN & DISKO ---
st.set_page_config(page_title="AI Fund-Arena: Empire Edition", layout="wide")

st.markdown("""
    <style>
    @keyframes disco {
        0% { background-color: #ff00ff; }
        25% { background-color: #00ffff; }
        50% { background-color: #ffff00; }
        75% { background-color: #00ff00; }
        100% { background-color: #ff0000; }
    }
    .disco-bg { animation: disco 0.3s infinite; padding: 25px; border-radius: 15px; text-align: center; color: white; font-weight: bold; font-size: 35px; text-shadow: 2px 2px #000; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; background: linear-gradient(45deg, #00dbde, #fc00ff); color: white; border: none; transition: 0.3s; height: 3.5em; }
    .stButton>button:hover { transform: scale(1.05); box-shadow: 0px 0px 20px #fc00ff; }
    .stat-box { padding: 15px; border-radius: 10px; background: #1E1E1E; border-left: 5px solid #00dbde; margin-bottom: 10px; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- DATENBANK ---
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              category TEXT, image_path TEXT, date TEXT, location TEXT, description TEXT)''')
conn.commit()

# --- KI MODELL ---
@st.cache_resource
def load_found_model():
    if not os.path.exists("keras_model.h5"):
        st.error("Datei keras_model.h5 fehlt!")
        st.stop()
    model = tf.keras.models.load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- EMPIRE GAME LOGIK ---
if 'credits' not in st.session_state: st.session_state.credits = 0
if 'click_power' not in st.session_state: st.session_state.click_power = 1
if 'last_tick' not in st.session_state: st.session_state.last_tick = time.time()

# Alle Upgrade-Figuren
upgrades = {
    "bäcker": {"name": "👨‍🍳 Fleißiger Bäcker", "power": 1, "cost": 50},
    "ki_bot": {"name": "🤖 KI-Suchbot", "power": 8, "cost": 400},
    "detektiv": {"name": "🕵️‍♂️ Meister-Detektiv", "power": 40, "cost": 2000},
    "satellit": {"name": "🛰️ Fund-Satellit", "power": 150, "cost": 10000},
    "alien": {"name": "👽 Intergalaktischer Finder", "power": 500, "cost": 50000}
}

for uid in upgrades:
    if f"count_{uid}" not in st.session_state: st.session_state[f"count_{uid}"] = 0

# Passives Einkommen (TPS) berechnen
tps = sum(st.session_state[f"count_{u}"] * upgrades[u]["power"] for u in upgrades)
now = time.time()
diff = now - st.session_state.last_tick

if diff >= 1:
    st.session_state.credits += tps * int(diff)
    st.session_state.last_tick = now

# --- SIDEBAR GAME CENTER
