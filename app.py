import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
from supabase import create_client, Client
import os
import time
from datetime import datetime

# --- CLOUD VERBINDUNG (Step 5) ---
# Diese Daten ziehen wir sicher aus den Streamlit Secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("⚠️ Supabase Secrets fehlen oder sind falsch! Bitte in den Streamlit Settings prüfen.")
    st.stop()

# --- DESIGN ---
st.set_page_config(page_title="AI Fund-Arena: Cloud Edition", layout="wide")
st.markdown("""
    <style>
    @keyframes disco { 0% { background-color: #ff00ff; } 50% { background-color: #00ffff; } 100% { background-color: #ff00ff; } }
    .disco-bg { animation: disco 0.3s infinite; padding: 20px; border-radius: 15px; text-align: center; color: white; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 12px; background: linear-gradient(45deg, #00dbde, #fc00ff); color: white; border: none; height: 3.5em; }
    .stat-box { padding: 15px; border-radius: 10px; background: #1E1E1E; border-left: 5px solid #00dbde; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- KI MODELL LADEN ---
@st.cache_resource
def load_found_model():
    model_path = "keras_model.h5"
    if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000000:
        st.error("⚠️ Modell-Datei fehlt oder ist beschädigt!")
        st.stop()
    model = tf.keras.models.load_model(model_path, compile=False)
    with open("labels.txt", "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- CLOUD GAME LOGIK (Laden aus Supabase) ---
# Wir nutzen immer das Profil mit ID 1 (unser Standard-Spielstand)
def get_profile():
    res = supabase.table("profiles").select("*").eq("id", 1).execute()
    if len(res.data) == 0:
        # Falls kein Profil da ist, erstellen wir eines
        supabase.table("profiles").insert({"id": 1, "credits": 0, "click_power": 1}).execute()
        return {"id": 1, "credits": 0, "click_power": 1, "count_bäcker": 0, "count_ki_bot": 0, "count_detektiv": 0, "count_roboter": 0, "count_alien": 0}
    return res.data[0]

# Spielstand laden
prof = get_profile()
if 'last_tick' not in st.session_state: st.session_state.last_tick = time.time()

# Upgrades definieren
upgrades = {
    "bäcker": {"name": "👨‍🍳 Bäcker", "power": 1, "cost": 50},
    "ki_bot": {"name": "🤖 KI-Bot", "power": 10, "cost": 500},
    "detektiv": {"name": "🕵️‍♂️ Detektiv", "power": 50, "cost": 2500},
    "roboter": {"name": "🦾 Greifarm", "power": 200, "cost": 10000},
    "alien": {"name": "👽 Alien-Finder", "power": 1000, "cost": 50000}
}

# Passive Einnahmen berechnen (Live-Tick)
tps = sum(prof.get(f"count_{u}", 0) * upgrades[u]["power"] for u in upgrades)
now = time.time()
diff = int(now - st.session_state.last_tick)
if diff >= 1:
    new_credits = prof["credits"] + (tps * diff)
    supabase.table("profiles").update({"credits": new_credits}).eq("id", 1).execute()
    st.session_state.last_tick = now
    st.rerun()

# --- SIDEBAR ---
st.sidebar.title("🍪 CLOUD-EMPIRE")
st.sidebar.markdown(f'<div class="stat-box"><b>Credits: {prof["credits"]} 💰</b><br>TPS: {tps}</div>', unsafe_allow_html=True)

if st.sidebar.button("🍪 KLICKEN!"):
    supabase.table("profiles").update({"credits": prof["credits"] + prof["click_power"]}).eq("id", 1).execute()
    st.rerun()

st.sidebar.subheader("🛒 Cloud Shop")
c_cost = int(25 * (prof["click_power"] ** 1.8))
if st.sidebar.button(f"🔍 Lupe ({c_cost} 💰)"):
    if prof["credits"] >= c_cost:
        supabase.table("profiles").update({"credits": prof["credits"] - c_cost, "click_power": prof["click_power"] + 1}).eq("id", 1).execute()
        st.rerun()

for uid, data in upgrades.items():
    cnt = prof.get(f"count_{uid}", 0)
    cost = int(data["cost"] * (1.15 ** cnt))
    if st.sidebar.button(f"{data['name']} ({cost} 💰) | x{cnt}"):
        if prof["credits"] >= cost:
            supabase.table("profiles").update({"credits": prof["credits"] - cost, f"count_{uid}": cnt + 1}).eq("id", 1).execute()
            st.rerun()

choice = st.sidebar.selectbox("Menü", ["🏠 Home", "📤 Melden", "🔍 Suchen"])

# --- SEITEN-LOGIK ---
if choice == "🏠 Home":
    st.title("☁️ Die Cloud Fund-Arena")
    st.write("Dein Spielstand ist jetzt sicher in der Supabase-Cloud gespeichert!")
    st.image("https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800")

elif choice == "📤 Melden":
    st.header("📤 Fundstück in Cloud speichern")
    col1, col2 = st.columns(2)
    with col1:
        src = st.camera_input("Foto") or st.file_uploader("Upload")
        loc = st.text_input("📍 Fundort")
        txt = st.text_area("📝 Beschreibung")

    if src:
        img = Image.open(src)
        with col2: st.image(img, width=250)
        if st.button("🚀 CLOUD-ANALYSE"):
            # Disco-Effekt
            ph = st.empty()
            for _ in range(5):
                ph.markdown('<div class="disco-bg">🕺 CLOUD SYNC... 💃</div>', unsafe_allow_html=True)
                time.sleep(0.1)
            ph.empty()
            
            # KI Analyse
            res = ImageOps.fit(img, (224, 224), Image.Resampling.LANCZOS)
            arr = np.asarray(res).astype(np.float32) / 127.5 - 1
            pred = model.predict(np.expand_dims(arr, axis=0))
            label = labels[np.argmax(pred)]
            
            # Bild in Supabase Storage hochladen
            file_name = f"{time.time()}.jpg"
            img.save("temp.jpg")
            with open("temp.jpg", "rb") as f:
                supabase.storage.from_("fund-images").upload(file_name, f)
            img_url = supabase.storage.from_("fund-images").get_public_url(file_name)
            
            # Daten in Supabase Tabelle speichern
            supabase.table("items").insert({
                "category": label, "location": loc, "description": txt, "image_url": img_url
            }).execute()
            
            # Bonus Credits geben
            supabase.table("profiles").update({"credits": prof["credits"] + 1000}).eq("id", 1).execute()
            st.success(f"Gefunden: {label}! +1000 Credits Cloud-Bonus!")
            st.balloons()

elif choice == "🔍 Suchen":
    st.header("🔍 Cloud Suche")
    cat = st.selectbox("Kategorie", labels)
    res = supabase.table("items").select("*").eq("category", cat).execute()
    
    for item in res.data:
        with st.expander(f"Fundort: {item['location']}"):
            st.image(item['image_url'], width=300)
            st.write(f"**Beschreibung:** {item['description']}")
            if st.button("Löschen", key=f"del{item['id']}"):
                supabase.table("items").delete().eq("id", item['id']).execute()
                st.rerun()
