import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
from datetime import datetime

# --- KONFIGURATION & DESIGN ---
st.set_page_config(page_title="Schul-Fundbüro KI", layout="centered")

# CSS für ein schöneres UI
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #4CAF50; color: white; }
    .reportview-container { background: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# Ordner für Bilder erstellen, falls er fehlt
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
    
    # Fehlerprüfung: Existieren die Dateien im Hauptverzeichnis?
    if not os.path.exists(model_path) or not os.path.exists(label_path):
        st.error(f"❌ KRITISCHER FEHLER: Dateien nicht gefunden!")
        st.write(f"Gesuchte Dateien: {model_path}, {label_path}")
        st.write(f"Vorhandene Dateien im Ordner: {os.listdir('.')}")
        st.stop()
        
    # Modell laden (TensorFlow 2.15 kompatibel)
    model = tf.keras.models.load_model(model_path, compile=False)
    
    # Labels laden
    with open(label_path, "r") as f:
        # Extrahiert den Namen (z.B. 'Jacke') aus '0 Jacke'
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

# Laden starten
model, labels = load_found_model()

# --- NAVIGATION ---
st.sidebar.title("🏫 Fund-Manager")
menu = ["🏠 Startseite", "📤 Fundstück melden", "🔍 Nach Verlorenem suchen"]
choice = st.sidebar.selectbox("Menü", menu)

# --- LOGIK: STARTSEITE ---
if choice == "🏠 Startseite":
    st.title("Digitales Schul-Fundbüro")
    st.write("Registriere Fundstücke per KI oder suche nach deinen verlorenen Sachen.")
    st.info(f"Aktuell unterstützte Kategorien: {', '.join(labels)}")
    st.image("https://images.unsplash.com/photo-1540317580384-e5d43616b9aa?q=80&w=800", caption="Verlorene Schätze warten auf ihre Besitzer")

# --- LOGIK: FUNDSTÜCK MELDEN ---
elif choice == "📤 Fundstück melden":
    st.header("Neues Fundstück registrieren")
    img_file = st.camera_input("Foto machen") or st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])

    if img_file is not None:
        image = Image.open(img_file)
        st.image(image, caption="Vorschau", width=300)
        
        if st.button("Gegenstand analysieren & speichern"):
            with st.spinner('KI analysiert das Bild...'):
                # Bildvorverarbeitung
                size = (224, 224)
                image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
                img_array = np.asarray(image_resized).astype(np.float32) / 127.5 - 1
                img_array = np.expand_dims(img_array, axis=0)

                # Vorhersage
                prediction = model.predict(img_array)
                index = np.argmax(prediction)
                detected_cat = labels[index]
                confidence = prediction[0][index]

                # Bild physisch speichern
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                img_path = f"uploads/item_{timestamp}.jpg"
                image.save(img_path)
                
                # In Datenbank schreiben
                c.execute("INSERT INTO items (category, image_path, date) VALUES (?, ?, ?)", 
                          (detected_cat, img_path, datetime.now().strftime("%d.%m.%Y, %H:%M")))
                conn.commit()

                st.success(f"Erkannt: **{detected_cat}** ({confidence:.1%})")
                st.balloons()

# --- LOGIK: SUCHEN & ADMIN ---
elif choice == "🔍 Nach Verlorenem suchen":
    st.header("Suche in Kategorien")
    search_cat = st.selectbox("Was hast du verloren?", labels)
    
    results = c.execute("SELECT id, image_path, date FROM items WHERE category = ? ORDER BY id DESC", (search_cat,)).fetchall()
    
    if results:
        for res in results:
            with st.container():
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    st.image(res[1], width=150)
                with col_info:
                    st.write(f"**ID:** {res[0]}")
                    st.write(f"**Gefunden am:** {res[2]}")
                st.divider()
    else:
        st.warning(f"Keine Fundstücke in der Kategorie '{search_cat}' vorhanden.")

    # --- ADMIN BEREICH (LÖSCHEN) ---
    st.sidebar.divider()
    if st.sidebar.checkbox("Admin-Modus (Abgeholt)"):
        pw = st.sidebar.text_input("Admin-Passwort", type="password")
        if pw == "schule123":
            st.subheader("🗑️ Gegenstand entfernen")
            del_id = st.number_input("ID des abgeholten Gegenstands", min_value=1, step=1)
            if st.button("Aus Datenbank löschen"):
                # Bildpfad holen um auch die Datei zu löschen
                item = c.execute("SELECT image_path FROM items WHERE id = ?", (del_id,)).fetchone()
                if item:
                    if os.path.exists(item[0]):
                        os.remove(item[0])
                    c.execute("DELETE FROM items WHERE id = ?", (del_id,))
                    conn.commit()
                    st.success(f"Gegenstand {del_id} wurde gelöscht.")
                    st.rerun()
                else:
                    st.error("ID nicht gefunden.")
