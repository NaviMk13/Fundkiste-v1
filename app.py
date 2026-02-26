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
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; background: linear-gradient(45deg, #00dbde, #fc00ff); color: white; border: none; height: 3.5em; }
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

# --- KI MODELL LADEN ---
@st.cache_resource
def load_found_model():
    model_path, label_path = "keras_model.h5", "labels.txt"
    if not os.path.exists(model_path):
        st.error("⚠️ Datei keras_model.h5 fehlt!")
        st.stop()
    # Check ob Datei heil ist (mind. 1MB)
    if os.path.getsize(model_path) < 1000000:
        st.error("⚠️ Modell-Datei ist beschädigt (zu klein). Bitte neu hochladen!")
        st.stop()
        
    model = tf.keras.models.load_model(model_path, compile=False)
    with open(label_path, "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- EMPIRE GAME LOGIK ---
if 'credits' not in st.session_state: st.session_state.credits = 0
if 'click_power' not in st.session_state: st.session_state.click_power = 1
if 'last_tick' not in st.session_state: st.session_state.last_tick = time.time()

upgrades = {
    "bäcker": {"name": "👨‍🍳 Bäcker", "power": 1, "cost": 50},
    "ki_bot": {"name": "🤖 KI-Bot", "power": 10, "cost": 500},
    "detektiv": {"name": "🕵️‍♂️ Detektiv", "power": 50, "cost": 2500},
    "roboter": {"name": "🦾 Greifarm", "power": 200, "cost": 10000},
    "alien": {"name": "👽 Alien-Finder", "power": 1000, "cost": 50000}
}

for uid in upgrades:
    if f"count_{uid}" not in st.session_state: st.session_state[f"count_{uid}"] = 0

# Passives Einkommen
tps = sum(st.session_state[f"count_{u}"] * upgrades[u]["power"] for u in upgrades)
now = time.time()
if now - st.session_state.last_tick >= 1:
    st.session_state.credits += tps * int(now - st.session_state.last_tick)
    st.session_state.last_tick = now

# --- SIDEBAR ---
st.sidebar.title("🍪 FUND-EMPIRE")
st.sidebar.markdown(f'<div class="stat-box"><b>Credits: {int(st.session_state.credits)} 💰</b><br>TPS: {tps}</div>', unsafe_allow_html=True)

if st.sidebar.button("🍪 KLICKEN!"):
    st.session_state.credits += st.session_state.click_power
    st.rerun()

st.sidebar.subheader("🛒 Shop")
c_cost = int(25 * (st.session_state.click_power ** 1.8))
if st.sidebar.button(f"🔍 Lupe ({c_cost} 💰)"):
    if st.session_state.credits >= c_cost:
        st.session_state.credits -= c_cost
        st.session_state.click_power += 1
        st.rerun()

for uid, data in upgrades.items():
    cnt = st.session_state[f"count_{uid}"]
    cost = int(data["cost"] * (1.15 ** cnt))
    if st.sidebar.button(f"{data['name']} ({cost} 💰) | x{cnt}"):
        if st.session_state.credits >= cost:
            st.session_state.credits -= cost
            st.session_state[f"count_{uid}"] += 1
            st.rerun()

choice = st.sidebar.selectbox("Menü", ["🏠 Home", "📤 Melden", "🔍 Suchen"])

# --- SEITEN ---
if choice == "🏠 Home":
    st.title("🚀 AI Fund-Arena")
    st.write("Baue dein Imperium auf!")
    st.image("https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800")

elif choice == "📤 Melden":
    st.header("📤 Fundstück registrieren")
    col1, col2 = st.columns(2)
    with col1:
        src = st.camera_input("Foto") or st.file_uploader("Upload")
        loc = st.text_input("📍 Fundort")
        txt = st.text_area("📝 Beschreibung")

    if src:
        img = Image.open(src)
        with col2: st.image(img, width=250)
        if st.button("🔥 ANALYSE"):
            box = st.empty()
            for _ in range(8):
                box.markdown('<div class="disco-bg">🕺 KI ANALYSIERT... 💃</div>', unsafe_allow_html=True)
                time.sleep(0.1)
            box.empty()
            
            res = ImageOps.fit(img, (224, 224), Image.Resampling.LANCZOS)
            arr = np.asarray(res).astype(np.float32) / 127.5 - 1
            pred = model.predict(np.expand_dims(arr, axis=0))
            label = labels[np.argmax(pred)]
            
            path = f"uploads/{time.time()}.jpg"
            if not os.path.exists("uploads"): os.makedirs("uploads")
            img.save(path)
            c.execute("INSERT INTO items (category, image_path, date, location, description) VALUES (?, ?, ?, ?, ?)", 
                      (label, path, datetime.now().strftime("%d.%m.%Y"), loc, txt))
            conn.commit()
            st.session_state.credits += 1000
            st.success(f"Gefunden: {label}! +1000 Credits!")
            st.balloons()

elif choice == "🔍 Suchen":
    st.header("🔍 Suchen")
    cat = st.selectbox("Kategorie", labels)
    data = c.execute("SELECT * FROM items WHERE category=?", (cat,)).fetchall()
    for item in data:
        with st.expander(f"Fund ID {item[0]}"):
            st.image(item[2], width=200)
            st.write(f"**Ort:** {item[4]} | **Info:** {item[5]}")
            if st.button("Löschen", key=f"del{item[0]}"):
                c.execute("DELETE FROM items WHERE id=?", (item[0],))
                conn.commit()
                st.rerun()
