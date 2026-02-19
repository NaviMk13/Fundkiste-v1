import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
import time
from datetime import datetime

# --- KONFIGURATION & LAYOUT (Erste Version Style) ---
st.set_page_config(page_title="Schul-Fundbüro KI", layout="wide")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- DATENBANK SETUP (Mit automatischer Reparatur) ---
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              category TEXT, image_path TEXT, date TEXT)''')

# Sicherstellen, dass neue Spalten existieren (verhindert den OperationalError)
try:
    c.execute("ALTER TABLE items ADD COLUMN location TEXT")
    c.execute("ALTER TABLE items ADD COLUMN description TEXT")
except:
    pass # Spalten existieren bereits
conn.commit()

# --- KI MODELL LADEN ---
@st.cache_resource
def load_found_model():
    model_path, label_path = "keras_model.h5", "labels.txt"
    if not os.path.exists(model_path) or not os.path.exists(label_path):
        st.error("⚠️ Dateien fehlen im Hauptverzeichnis!")
        st.stop()
    model = tf.keras.models.load_model(model_path, compile=False)
    with open(label_path, "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- SIDEBAR ---
st.sidebar.title("🎮 Fundbüro Menü")
menu = ["🏠 Startseite", "📤 Fundstück melden", "🔍 Suchen"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "🏠 Startseite":
    st.title("🏫 Digitales Schul-Fundbüro")
    st.write("Registriere Fundstücke oder finde deine Sachen wieder.")
    st.image("https://images.unsplash.com/photo-1588072432836-e10032774350?w=800")

elif choice == "📤 Fundstück melden":
    st.header("Neues Fundstück registrieren")
    
    col_in, col_pre = st.columns([1, 1])
    
    with col_in:
        # Foto oder Datei
        img_file = st.camera_input("Foto machen")
        uploaded_file = st.file_uploader("Oder Datei hochladen", type=["jpg", "png", "jpeg"])
        
        final_file = img_file if img_file else uploaded_file
        
        fundort = st.text_input("📍 Fundort", placeholder="Wo wurde es gefunden?")
        beschreibung = st.text_area("📝 Beschreibung", placeholder="Farbe, Marke, Besonderheiten...")

    if final_file is not None:
        image = Image.open(final_file)
        with col_pre:
            st.image(image, caption="Vorschau deines Fundstücks", width=300)
        
        if st.button("🚀 Analyse starten & Speichern"):
            # --- WARTESPIEL ---
            with st.status("🤖 KI analysiert das Fundstück...", expanded=True) as status:
                st.write("Initialisiere neuronale Netze...")
                time.sleep(1)
                st.write("Extrahiere Merkmale...")
                st.toast("Kleiner Tipp: Saubere Linsen machen bessere Fotos! 📸")
                time.sleep(1.5)
                
                # KI Logik
                size = (224, 224)
                image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
                img_array = np.asarray(image_resized).astype(np.float32) / 127.5 - 1
                img_array = np.expand_dims(img_array, axis=0)
                prediction = model.predict(img_array)
                idx = np.argmax(prediction)
                conf = prediction[0][idx]
                detected_cat = labels[idx]

                # Speichern
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"uploads/item_{ts}.jpg"
                image.save(path)
                c.execute("INSERT INTO items (category, location, description, image_path, date) VALUES (?, ?, ?, ?, ?)", 
                          (detected_cat, fundort, beschreibung, path, datetime.now().strftime("%d.%m.%Y, %H:%M")))
                conn.commit()
                status.update(label="✅ Analyse erfolgreich!", state="complete")

            # --- KI ÜBERSICHT ---
            st.divider()
            res1, res2 = st.columns(2)
            res1.metric("KI-Kategorie", detected_cat)
            res2.metric("Sicherheit", f"{conf:.1%}")
            st.success(f"Gegenstand wurde als '{detected_cat}' registriert!")
            st.balloons()

elif choice == "🔍 Suchen":
    st.header("Fundstücke durchsuchen")
    search_cat = st.selectbox("Nach Kategorie filtern", labels)
    results = c.execute("SELECT id, image_path, date, location, description FROM items WHERE category = ? ORDER BY id DESC", (search_cat,)).fetchall()
    
    for res in results:
        with st.container():
            ca, cb = st.columns([1, 2])
            ca.image(res[1], width=200)
            cb.write(f"**📅 Datum:** {res[2]}")
            cb.write(f"**📍 Ort:** {res[3]}")
            cb.write(f"**📝 Info:** {res[4]}")
            cb.write(f"**🆔 ID:** {res[0]}")
            if st.button(f"Abgeholt (Löschen {res[0]})", key=f"d_{res[0]}"):
                if os.path.exists(res[1]): os.remove(res[1])
                c.execute("DELETE FROM items WHERE id = ?", (res[0],))
                conn.commit()
                st.rerun()
            st.divider()
