import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import sqlite3
import os
import time
from datetime import datetime

# --- KONFIGURATION & DESIGN ---
st.set_page_config(page_title="Schul-Fundbüro KI", layout="wide")

# Ordner für Bilder erstellen
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- DATENBANK SETUP ---
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
        st.error("⚠️ Dateien fehlen! Bitte keras_model.h5 und labels.txt hochladen.")
        st.stop()
    model = tf.keras.models.load_model(model_path, compile=False)
    with open(label_path, "r") as f:
        labels = [line.strip().split(maxsplit=1)[-1] for line in f.readlines()]
    return model, labels

model, labels = load_found_model()

# --- SIDEBAR STATS ---
st.sidebar.title("🎮 Fundbüro Menü")
total_items = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
st.sidebar.metric("Gegenstände gesamt", total_items)

menu = ["🏠 Startseite", "📤 Fundstück melden", "🔍 Suchen"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- STARTSEITE ---
if choice == "🏠 Startseite":
    st.title("🏫 Digitales Schul-Fundbüro")
    st.write("Willkommen! Registriere Fundstücke oder finde deine verlorenen Sachen.")
    st.image("https://images.unsplash.com/photo-1588072432836-e10032774350?w=800", caption="Zusammen finden wir alles wieder!")

# --- FUNDSTÜCK MELDEN ---
elif choice == "📤 Fundstück melden":
    st.header("Neues Fundstück registrieren")
    
    col_input, col_preview = st.columns([1, 1])
    
    with col_input:
        img_file = st.camera_input("Foto des Fundstücks")
        fundort = st.text_input("📍 Wo wurde es gefunden?", placeholder="z.B. Schulhof, Mensa...")
        beschreibung = st.text_area("📝 Kurze Beschreibung", placeholder="Farbe, Marke, Besonderheiten...")

    if img_file is not None:
        image = Image.open(img_file)
        
        if st.button("Analyse starten & Speichern"):
            # --- WARTESPIEL / ANIMATION ---
            with st.status("🤖 KI arbeitet...", expanded=True) as status:
                st.write("Verkleinere Bild...")
                time.sleep(1)
                st.write("Suche nach Mustern...")
                # Kleines Mini-Spiel/Interaktion während des Wartens
                st.toast("Wusstest du? Die meisten Sachen werden in der Sporthalle vergessen!")
                time.sleep(1)
                st.write("Vergleiche mit Datenbank...")
                
                # Tatsächliche KI-Analyse
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
                status.update(label="✅ Analyse abgeschlossen!", state="complete", expanded=False)

            # --- ERGEBNIS ÜBERSICHT ---
            st.divider()
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.metric("Erkannte Kategorie", detected_cat)
            with res_col2:
                st.metric("KI-Sicherheit", f"{conf:.1%}")
            
            st.success(f"Gegenstand erfolgreich unter '{detected_cat}' gespeichert!")
            st.balloons()

# --- SUCHEN ---
elif choice == "🔍 Suchen":
    st.header("Nach Verlorenem suchen")
    search_cat = st.selectbox("Kategorie wählen", labels)
    
    results = c.execute("SELECT id, image_path, date, location, description FROM items WHERE category = ? ORDER BY id DESC", (search_cat,)).fetchall()
    
    if results:
        for res in results:
            with st.container():
                c1, c2 = st.columns([1, 2])
                c1.image(res[1], width=200)
                c2.write(f"**Datum:** {res[2]}")
                c2.write(f"**Ort:** {res[3]}")
                c2.write(f"**Info:** {res[4]}")
                if st.button(f"Abgeholt (Lösche ID {res[0]})", key=f"del_{res[0]}"):
                    if os.path.exists(res[1]): os.remove(res[1])
                    c.execute("DELETE FROM items WHERE id = ?", (res[0],))
                    conn.commit()
                    st.rerun()
                st.divider()
    else:
        st.warning(f"Keine Einträge für '{search_cat}' gefunden.")
