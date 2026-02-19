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
st.set_page_config(page_title="AI Fund-Arena 3000", layout="wide")

# CSS für Disko-Effekte und Animationen
st.markdown("""
    <style>
    @keyframes disco {
        0% { background-color: #ff00ff; }
        25% { background-color: #00ffff; }
        50% { background-color: #ffff00; }
        75% { background-color: #00ff00; }
        100% { background-color: #ff0000; }
    }
    .disco-bg { animation: disco 0.5s infinite; padding: 20px; border-radius: 15px; text-align: center; color: white; font-weight: bold; font-size: 30px; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background: linear-gradient(45deg, #6200ea, #03dac5); color: white; border: none; }
    .stSidebar { background-image: linear-gradient(#1a1a1a, #2d3436); color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- DATENBANK & KI (wie bisher) ---
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

# --- SIDEBAR: GAME CENTER ---
st.sidebar.title("🕹️ GAME CENTER")
game_choice = st.sidebar.selectbox("Wähle ein Pausenspiel:", ["---", "🚀 Star Clicker", "🔢 Zahlen-Raten"])

if game_choice == "🚀 Star Clicker":
    st.sidebar.subheader("Klick die Sterne!")
    if 'clicks' not in st.session_state: st.session_state.clicks = 0
    if st.sidebar.button("✨ KLICK!"): st.session_state.clicks += 1
    st.sidebar.write(f"Score: {st.session_state.clicks}")
    if st.sidebar.button("Reset"): st.session_state.clicks = 0

elif game_choice == "🔢 Zahlen-Raten":
    st.sidebar.subheader("Rate (1-10):")
    secret = random.randint(1, 10)
    guess = st.sidebar.number_input("Deine Zahl", 1, 10)
    if st.sidebar.button("Check"):
        if guess == secret: st.sidebar.success("Richtig! 🎉")
        else: st.sidebar.error(f"Falsch! Es war {secret}")

st.sidebar.divider()
menu = ["🏠 Startseite", "📤 Fundstück melden", "🔍 Suchen"]
choice = st.sidebar.selectbox("Hauptmenü", menu)

# --- LOGIK ---
if choice == "🏠 Startseite":
    st.title("🏫 Willkommen in der AI Fund-Arena")
    st.write("Registriere Dinge mit Style oder finde Verlorenes.")
    st.image("https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=800", caption="Der coolste Fundort der Schule")

elif choice == "📤 Fundstück melden":
    st.header("📤 Neues Fundstück registrieren")
    
    col_in, col_pre = st.columns([1, 1])
    with col_in:
        img_file = st.camera_input("Foto machen")
        uploaded_file = st.file_uploader("Oder Datei hochladen", type=["jpg", "png", "jpeg"])
        final_file = img_file if img_file else uploaded_file
        fundort = st.text_input("📍 Fundort")
        beschreibung = st.text_area("📝 Beschreibung")

    if final_file is not None:
        image = Image.open(final_file)
        with col_pre: st.image(image, width=300)
        
        if st.button("🔥 ANALYSE STARTEN (DISKO-MODUS!)"):
            # DISKO EFFEKT
            disco_placeholder = st.empty()
            for _ in range(10):
                disco_placeholder.markdown('<div class="disco-bg">🕺 DISKO-ANALYSE LÄUFT... 💃</div>', unsafe_allow_html=True)
                time.sleep(0.2)
            disco_placeholder.empty()

            # KI Logik
            size = (224, 224)
            image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
            img_array = np.asarray(image_resized).astype(np.float32) / 127.5 - 1
            img_array = np.expand_dims(img_array, axis=0)
            prediction = model.predict(img_array)
            idx = np.argmax(prediction)
            detected_cat = labels[idx]

            # Speichern
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"uploads/item_{ts}.jpg"
            image.save(path)
            c.execute("INSERT INTO items (category, location, description, image_path, date) VALUES (?, ?, ?, ?, ?)", 
                      (detected_cat, fundort, beschreibung, path, datetime.now().strftime("%d.%m.%Y, %H:%M")))
            conn.commit()
            
            st.success(f"🤖 KI sagt: Das ist eine **{detected_cat}**!")
            st.balloons()

elif choice == "🔍 Suchen":
    st.header("🔍 Fundstücke durchsuchen")
    search_cat = st.selectbox("Kategorie", labels)
    results = c.execute("SELECT id, image_path, date, location, description FROM items WHERE category = ? ORDER BY id DESC", (search_cat,)).fetchall()
    
    for res in results:
        with st.container():
            ca, cb = st.columns([1, 2])
            ca.image(res[1], width=200)
            cb.write(f"**📍 Ort:** {res[3]} | **📅 Wann:** {res[2]}")
            cb.info(f"Info: {res[4]}")
            if st.button(f"Abgeholt (ID {res[0]})", key=f"d_{res[0]}"):
                c.execute("DELETE FROM items WHERE id = ?", (res[0],))
                conn.commit()
                st.rerun()
            st.divider()
