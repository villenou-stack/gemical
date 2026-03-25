import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
import os

# --- 1. ASETUKSET JA API ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        st.error("API-avain puuttuu Secrets-osiosta!")
        st.stop()
except Exception as e:
    st.error(f"Virhe Secrets-luvussa: {e}")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. TIETOKANTAFUNKTIOT ---
def get_connection():
    return sqlite3.connect('gemical_v2.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meals 
                 (date TEXT, food TEXT, calories INT, protein INT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs 
                 (date TEXT, weight REAL)''')
    conn.commit()
    conn.close()

def save_meal(food, cal, prot):
    conn = get_connection()
    c = conn.cursor()
    # Käytetään SQLiten omaa date('now') -funktiota virheiden välttämiseksi
    c.execute("INSERT INTO meals (date, food, calories, protein) VALUES (date('now'), ?, ?, ?)", 
              (food, int(cal), int(prot)))
    conn.commit()
    conn.close()

def save_weight(weight):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO weight_logs (date, weight) VALUES (date('now'), ?)", 
              (weight,))
    conn.commit()
    conn.close()

init_db()

# --- 3. KÄYTTÖLIITTYMÄ (UI) ---
st.set_page_config(page_title="GemiCal Pro", page_icon="🥗", layout="centered")

st.title("🥗 GemiCal Pro")
st.write("Tavoite: 90 kg & 100 kg Penkkipunnerrus")

# ---
