import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Schul-Fundbüro KI", layout="centered")

# Ordner für Bilder erstellen
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- DATENBANK SETUP ---
conn = sqlite3.connect("lost_and_found.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS items 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              category TEXT, 
              image_path TEXT, 
              date TEXT)''')
conn.commit()

# --- KI MODELL & LABELS LADEN ---
@st.cache_resource
def load_found_model():
    model_path = "keras_model.h5"
    label_path = "labels.txt"
    
    # DEBUG-HILFE: Falls Dateien nicht gefunden werden
    if not os.path.exists(model_path) or not os.path.exists(label_path):
        st.error("⚠️ Dateien nicht im Hauptverzeichnis gefunden!")
        st.write("In deinem Repository befinden sich aktuell folgende Dateien:")
        st.code(os.listdir("."))
        st.info("Tipp: Die Dateien dürfen nicht in einem Ordner (wie 'converted_keras') liegen!")
        st.stop()
        
    model = tf.keras.models.load_model(model_path, compile=False)
    with open(label_path, "r") as f:
        # Extrahiert den Namen (z.B. 'Jacke') aus '0 Jacke'
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- NAVIGATION ---
st.sidebar.title("🏫 Menü")
choice = st.sidebar.selectbox("Navigation", ["🏠 Startseite", "📤 Fundstück melden", "🔍 Suchen & Abholen"])

if choice == "🏠 Startseite":
    st.title("Digitales Schul-Fundbüro")
    st.write("Willkommen! Nutze das Menü links, um Fundstücke zu verwalten.")
    st.info(f"KI erkennt: {', '.join(labels)}")

elif choice == "📤 Fundstück melden":
    st.header("Neues Fundstück")
    img_file = st.camera_input("Foto machen") or st.file_uploader("Bild wählen", type=["jpg", "png", "jpeg"])

    if img_file is not None:
        image = Image.open(img_file)
        if st.button("Analysieren & Speichern"):
            # KI Vorbereitung
            size = (224, 224)
            image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
            img_array = np.asarray(image_resized).astype(np.float32) / 127.5 - 1
            img_array = np.expand_dims(img_array, axis=0)

            prediction = model.predict(img_array)
            detected_cat = labels[np.argmax(prediction)]

            # Speichern
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"uploads/item_{ts}.jpg"
            image.save(path)
            
            c.execute("INSERT INTO items (category, image_path, date) VALUES (?, ?, ?)", 
                      (detected_cat, path, datetime.now().strftime("%d.%m.%Y, %H:%M")))
            conn.commit()
            st.success(f"Gegenstand als **{detected_cat}** gespeichert!")
            st.balloons()

elif choice == "🔍 Suchen & Abholen":
    st.header("Fundstücke durchsuchen")
    search_cat = st.selectbox("Kategorie", labels)
    results = c.execute("SELECT id, image_path, date FROM items WHERE category = ? ORDER BY id DESC", (search_cat,)).fetchall()
    
    for res in results:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(res[1], width=150)
        with col2:
            st.write(f"**ID:** {res[0]}")
            st.write(f"**Datum:** {res[2]}")
            if st.button(f"Als abgeholt markieren (Löschen ID {res[0]})", key=f"del_{res[0]}"):
                if os.path.exists(res[1]): os.remove(res[1])
                c.execute("DELETE FROM items WHERE id = ?", (res[0],))
                conn.commit()
                st.rerun()
