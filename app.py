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
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 15px #fc00ff; }
    </style>
    """, unsafe_allow_html=True)

# --- DATENBANK SETUP ---
if not os.path.exists("uploads"): os.makedirs("uploads")
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              category TEXT, image_path TEXT, date TEXT)''')
try:
    c.execute("ALTER TABLE items ADD COLUMN location TEXT")
    c.execute("ALTER TABLE items ADD COLUMN description TEXT")
except: pass
conn.commit()

# --- KI MODELL LADEN ---
@st.cache_resource
def load_found_model():
    model_path, label_path = "keras_model.h5", "labels.txt"
    if not os.path.exists(model_path) or not os.path.exists(label_path):
        st.error("⚠️ Dateien fehlen! Bitte keras_model.h5 und labels.txt hochladen.")
        st.stop()
    model = tf.keras.models.load_model(model_path, compile=False)
    with open(label_path, "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- SIDEBAR: FOUND-IT COOKIE CLICKER ---
st.sidebar.title("🍪 FUND-CLICKER PRO")

if 'credits' not in st.session_state: st.session_state.credits = 0
if 'click_power' not in st.session_state: st.session_state.click_power = 1
if 'auto_clickers' not in st.session_state: st.session_state.auto_clickers = 0
if 'last_tick' not in st.session_state: st.session_state.last_tick = time.time()

# Auto-Clicker Logik
cur_time = time.time()
elapsed = cur_time - st.session_state.last_tick
if elapsed > 1:
    st.session_state.credits += st.session_state.auto_clickers * int(elapsed)
    st.session_state.last_tick = cur_time

st.sidebar.metric("Deine Credits 💰", f"{st.session_state.credits:.0f}")
if st.sidebar.button("🍪 GEGENSTAND FINDEN (KLICK!)"):
    st.session_state.credits += st.session_state.click_power

st.sidebar.divider()
st.sidebar.subheader("🛒 Shop")
lupe_cost = 10 * (st.session_state.click_power ** 2)
if st.sidebar.button(f"🔍 Lupe ({lupe_cost} 💰)"):
    if st.session_state.credits >= lupe_cost:
        st.session_state.credits -= lupe_cost
        st.session_state.click_power += 1
        st.sidebar.success("Power Up!")
    else: st.sidebar.error("Zu wenig!")

auto_cost = 50 + (st.session_state.auto_clickers * 20)
if st.sidebar.button(f"🤖 KI-Helfer ({auto_cost} 💰)"):
    if st.session_state.credits >= auto_cost:
        st.session_state.credits -= auto_cost
        st.session_state.auto_clickers += 1
        st.sidebar.success("Helfer aktiv!")
    else: st.sidebar.error("Zu wenig!")

st.sidebar.divider()
menu = ["🏠 Startseite", "📤 Fundstück melden", "🔍 Suchen"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- HAUPTBEREICH ---
if choice == "🏠 Startseite":
    st.title("🚀 AI Fund-Arena")
    st.write("Registriere Fundstücke oder sammle Credits im Clicker-Game!")
    st.image("
