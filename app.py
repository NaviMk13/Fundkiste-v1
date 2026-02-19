import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
from datetime import datetime

# --- KONFIGURATION & DESIGN ---
st.set_page_config(page_title="Schul-Fundbüro KI", layout="centered")
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

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

# --- KI MODELL LADEN ---
@st.cache_resource
def load_found_model():
    # Wichtig: Nutze tensorflow.keras für Kompatibilität
    model = tf.keras.models.load_model("keras_model.h5", compile=False)
    with open("labels.txt", "r") as f:
        labels = [line.strip().split(" ", 1)[1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- NAVIGATION ---
menu = ["🏠 Startseite", "📤 Fundstück melden", "🔍 Nach Verlorenem suchen"]
choice = st.sidebar.selectbox("Menü", menu)

# --- LOGIK: STARTSEITE ---
if choice == "🏠 Startseite":
    st.title("🏫 Digitales Schul-Fundbüro")
    st.write("Willkommen! Hier kannst du gefundene Gegenstände mit Hilfe von KI registrieren oder nach deinen verlorenen Sachen suchen.")
    st.image("https://images.unsplash.com/photo-1588072432836-e10032774350?auto=format&fit=crop&q=80&w=800", caption="Lass uns Ordnung in das Chaos bringen!")

# --- LOGIK: FUNDSTÜCK MELDEN ---
elif choice == "📤 Fundstück melden":
    st.header("Neues Fundstück registrieren")
    img_file = st.camera_input("Foto des Fundstücks machen") or st.file_uploader("Oder Bild hochladen", type=["jpg", "png", "jpeg"])

    if img_file is not None:
        image = Image.open(img_file)
        st.image(image, caption="Hochgeladenes Bild", width=300)
        
        if st.button("Gegenstand analysieren & speichern"):
            # Bildvorverarbeitung für KI
            size = (224, 224)
            image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
            img_array = np.asarray(image_resized).astype(np.float32) / 127.5 - 1
            img_array = np.expand_dims(img_array, axis=0)

            # Vorhersage
            prediction = model.predict(img_array)
            index = np.argmax(prediction)
            detected_cat = labels[index]
            confidence = prediction[0][index]

            # Speichern
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = f"uploads/item_{timestamp}.jpg"
            image.save(img_path)
            
            c.execute("INSERT INTO items (category, image_path, date) VALUES (?, ?, ?)", 
                      (detected_cat, img_path, datetime.now().strftime("%d.%m.%Y, %H:%M")))
            conn.commit()

            st.success(f"Erkannt als: **{detected_cat}** ({confidence:.1%})")
            st.info("Das Fundstück wurde erfolgreich in der Datenbank gespeichert.")
            st.balloons()

# --- LOGIK: SUCHEN ---
elif choice == "🔍 Nach Verlorenem suchen":
    st.header("Suche in Kategorien")
    search_cat = st.selectbox("Welche Kategorie suchst du?", labels)
    
    results = c.execute("SELECT image_path, date FROM items WHERE category = ? ORDER BY id DESC", (search_cat,)).fetchall()
    
    if results:
        st.write(f"Gefundene {search_cat}:")
        cols = st.columns(2)
        for i, res in enumerate(results):
            with cols[i % 2]:
                st.image(res[0], caption=f"Gefunden am: {res[1]}")
    else:
        st.warning(f"Bisher wurden keine Gegenstände in der Kategorie '{search_cat}' gefunden.")
