import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
from datetime import datetime
import os

# --- 1. ASETUKSET JA API ---
# Varmista, että Streamlit Secretsissä on: GEMINI_API_KEY = "AIza..."
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("API-avain puuttuu Streamlit Secretsistä!")
    st.stop()

genai.configure(api_key=API_KEY)

# Käytetään varmuuden vuoksi tätä nimeämistapaa 404-virheen välttämiseksi
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. TIETOKANTAFUNKTIOT ---
def init_db():
    conn = sqlite3.connect('gemical_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meals 
                 (date TEXT, food TEXT, calories INT, protein INT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs 
                 (date TEXT, weight REAL)''')
    conn.commit()
    conn.close()

def save_meal(food, cal, prot):
    conn = sqlite3.connect('gemical_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO meals VALUES (?, ?, ?, ?)", 
              (datetime.now().strftime("%Y-%m-%d"), food, int(cal), int(prot)))
    conn.commit()
    conn.close()

def save_weight(weight):
    conn = sqlite3.connect('gemical_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO weight_logs VALUES (?, ?)", 
              (datetime.now().strftime("%Y-%m-%d"), weight))
    conn.commit()
    conn.close()

init_db()

# --- 3. KÄYTTÖLIITTYMÄ (UI) ---
st.set_page_config(page_title="GemiCal Pro", page_icon="🥗", layout="centered")

st.title("🥗 GemiCal Pro")
st.write("Tavoite: 90kg & 100kg Penkki")

# --- SIVUPALKKI: EDISTYMINEN & HUOLTO ---
with st.sidebar:
    st.header("📊 Kehitys")
    current_weight = st.number_input("Päivän paino (
