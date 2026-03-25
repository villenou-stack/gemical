import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
from datetime import datetime

# --- TIETOKANTA-ASETUKSET ---
def init_db():
    conn = sqlite3.connect('gemical_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (date TEXT, food TEXT, calories INT, protein INT)''')
    conn.commit()
    conn.close()

def add_entry(food, cal, prot):
    conn = sqlite3.connect('gemical_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs VALUES (?, ?, ?, ?)", 
              (datetime.now().strftime("%Y-%m-%d"), food, cal, prot))
    conn.commit()
    conn.close()

init_db()

# --- UI ---
st.title("🥗 GemiCal Pro")

# Kalorilaskuri tälle päivälle
conn = sqlite3.connect('gemical_data.db')
today = datetime.now().strftime("%Y-%m-%d")
rows = conn.execute("SELECT SUM(calories) FROM logs WHERE date=?", (today,)).fetchone()
consumed = rows[0] if rows[0] else 0
conn.close()

st.metric("Päivän saldo", f"{consumed} / 2700 kcal", f"{2700 - consumed} jäljellä")

# Kamera ja analyysi
uploaded_file = st.camera_input("Kuvaa annos")

if uploaded_file:
    img = Image.open(uploaded_file)
    # ... (tähän väliin aiempi Gemini-analyysikoodi) ...
    
    # Napin painalluksella tallennus
    if st.button("Tallenna päiväkirjaan"):
        add_entry(data['ruoka'], data['kalorit'], data['proteiini'])
        st.success("Tallennettu!")
        st.rerun()