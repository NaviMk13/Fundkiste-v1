import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
from datetime import datetime

# --- KONFIGURATION & DESIGN ---
st.set_page_config(page_title="Schul-Fundbüro PRO", layout="centered")

st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- DATENBANK SETUP (Erweitert um Fundort und Beschreibung) ---
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              category TEXT, 
              location TEXT,
              description TEXT,
              image_path TEXT, 
              date TEXT)''')
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

# --- NAVIGATION ---
choice = st.sidebar.radio("Navigation", ["🏠 Home", "📤 Fundstück melden", "🔍 Suchen"])

if choice == "🏠 Home":
    st.title("🏫 Digitales Fundbüro")
    st.write("Registriere Fundstücke präzise mit KI-Unterstützung.")
    # Übersicht über aktuelle Funde
    total = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    st.metric("Registrierte Fundstücke", total)

elif choice == "📤 Fundstück melden":
    st.header("Neues Fundstück aufnehmen")
    
    img_file = st.camera_input("Foto aufnehmen")
    
    if img_file:
        image = Image.open(img_file)
        
        # --- KI ANALYSE BEREICH ---
        st.subheader("🤖 KI-Analyse")
        size = (224, 224)
        image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        img_array = np.asarray(image_resized).astype(np.float32) / 127.5 - 1
        img_array = np.expand_dims(img_array, axis=0)

        prediction = model.predict(img_array)
        idx = np.argmax(prediction)
        conf = prediction[0][idx]
        detected_cat = labels[idx]

        # Übersicht der Analyse anzeigen
        col_a, col_b = st.columns(2)
        col_a.metric("Kategorie", detected_cat)
        col_b.metric("Sicherheit", f"{conf:.1%}")

        st.divider()
        
        # --- ZUSÄTZLICHE INFOS ---
        st.subheader("📝 Details zum Fund")
        fundort = st.text_input("Fundort (z.B. Turnhalle, Mensa, Raum 204)")
        beschreibung = st.text_area("Zusätzliche Beschreibung (Farbe, Marke, Besonderheiten)")

        if st.button("Endgültig speichern"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"uploads/item_{ts}.jpg"
            image.save(path)
            
            c.execute("INSERT INTO items (category, location, description, image_path, date) VALUES (?, ?, ?, ?, ?)", 
                      (detected_cat, fundort, beschreibung, path, datetime.now().strftime("%d.%m.%Y, %H:%M")))
            conn.commit()
            st.success("Erfolgreich gespeichert!")
            st.balloons()

elif choice == "🔍 Suchen":
    st.header("Fundstücke durchsuchen")
    search_cat = st.selectbox("Kategorie filtern", ["Alle"] + labels)
    
    query = "SELECT * FROM items" if search_cat == "Alle" else f"SELECT * FROM items WHERE category = '{search_cat}'"
    results = c.execute(query + " ORDER BY id DESC").fetchall()
    
    for res in results:
        with st.expander(f"{res[1]} - Gefunden am {res[5]}"):
            c1, c2 = st.columns([1, 2])
            c1.image(res[4], use_container_width=True)
            c2.write(f"**📍 Fundort:** {res[2]}")
            c2.write(f"**📄 Beschreibung:** {res[3]}")
            c2.write(f"**ID:** {res[0]}")
            if st.button(f"Löschen (ID {res[0]})", key=f"btn_{res[0]}"):
                if os.path.exists(res[4]): os.remove(res[4])
                c.execute("DELETE FROM items WHERE id = ?", (res[0],))
                conn.commit()
                st.rerun()
