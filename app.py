import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
import time
from datetime import datetime

# --- DESIGN & DISKO ---
st.set_page_config(page_title="AI Fund-Arena: Empire", layout="wide")

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
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; background: linear-gradient(45deg, #00dbde, #fc00ff); color: white; border: none; transition: 0.3s; height: 3em; }
    .stButton>button:hover { transform: scale(1.05); box-shadow: 0px 0px 15px #fc00ff; }
    .stat-box { padding: 10px; border-radius: 10px; background: #262730; border-left: 5px solid #fc00ff; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATENBANK ---
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              category TEXT, image_path TEXT, date TEXT, location TEXT, description TEXT)''')
conn.commit()

# --- KI LADEN ---
@st.cache_resource
def load_found_model():
    model = tf.keras.models.load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- COOKIE CLICKER EMPIRE LOGIK ---
if 'credits' not in st.session_state: st.session_state.credits = 0
if 'click_power' not in st.session_state: st.session_state.click_power = 1
if 'last_tick' not in st.session_state: st.session_state.last_tick = time.time()

# Helfer-Stufen im Session State initialisieren
helpers = {
    "bäcker": {"name": "👨‍🍳 Bäcker", "power": 1, "base_cost": 50},
    "ki_helfer": {"name": "🤖 KI-Assistent", "power": 5, "base_cost": 250},
    "roboter": {"name": "🦾 Roboter-Arm", "power": 25, "base_cost": 1200},
    "fabrik": {"name": "🏭 Fund-Fabrik", "power": 100, "base_cost": 5000}
}

for h_id in helpers:
    if f"count_{h_id}" not in st.session_state:
        st.session_state[f"count_{h_id}"] = 0

# Passives Einkommen berechnen
tps = sum(st.session_state[f"count_{h_id}"] * helpers[h_id]["power"] for h_id in helpers)
now = time.time()
dt = now - st.session_state.last_tick
if dt >= 1:
    st.session_state.credits += tps * int(dt)
    st.session_state.last_tick = now

# --- SIDEBAR: DAS GAME ---
st.sidebar.title("🍪 FUND-EMPIRE")
st.sidebar.markdown(f"""<div class="stat-box">
    <b>Credits: {int(st.session_state.credits)} 💰</b><br>
    Pro Klick: +{st.session_state.click_power}<br>
    Pro Sekunde (TPS): {tps}
</div>""", unsafe_allow_html=True)

if st.sidebar.button("🍪 KLICK FÜR CREDITS!"):
    st.session_state.credits += st
