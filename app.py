import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
import time
import random
from datetime import datetime

# --- DISKO & ARCADE DESIGN ---
st.set_page_config(page_title="AI Fund-Arena: Cookie Edition", layout="wide")

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
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; background: linear-gradient(45deg, #00dbde, #fc00ff); color: white; border: none; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.05); box-shadow: 0px 0px 15px #fc00ff; }
    </style>
    """, unsafe_allow_html=True)

# --- DATENBANK & KI SETUP ---
if not os.path.exists("uploads"): os.makedirs("uploads")
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, location TEXT, description TEXT, image_path TEXT, date TEXT)''')
try:
    c.execute("ALTER TABLE items ADD COLUMN location TEXT")
    c.execute("ALTER TABLE items ADD COLUMN description TEXT")
except: pass
conn.commit()

@st.cache_resource
def load_found_model():
    model = tf.keras.models.load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- SIDEBAR: FOUND-IT COOKIE CLICKER ---
st.sidebar.title("🍪 FUND-CLICKER PRO")

# Session State für das Spiel
if 'credits' not in st.session_state: st.session_state.credits = 0
if 'click_power' not in st.session_state: st.session_state.click_power = 1
if 'auto_clickers' not in st.session_state: st.session_state.auto_clickers = 0
if 'last_tick' not in st.session_state: st.session_state.last_tick = time.time()

# Auto-Clicker Logik (basiert auf Zeitdifferenz)
current_time = time.time()
elapsed = current_time - st.session_state.last_tick
if elapsed > 1:
    st.session_state.credits += st.session_state.auto_clickers * int(elapsed)
    st.session_state.last_tick = current_time

# Anzeige Stats
st.sidebar.metric("Deine Credits 💰", f"{st.session_state.credits:.0f}")
st.sidebar.write(f"Click-Power: {st.session_state.click_power} | Auto-TPS: {st.session_state.auto_clickers}")

if st.sidebar.button("🍪 GEGENSTAND FINDEN (KLICK!)"):
    st.
