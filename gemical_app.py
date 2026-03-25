import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
from datetime import datetime
import os

# --- 1. ASETUKSET JA API ---
# Varmista Streamlit Cloudissa: Settings -> Secrets -> GEMINI_API_KEY = "AVAIN"
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        st.error("API-avainta ei löydy Secrets-osiosta!")
        st.stop()
except Exception as e:
    st.error(f"Virhe Secrets-luvussa: {e}")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. TIETOKANTAFUNKTIOT ---
def init_db():
    conn = sqlite3.connect('gemical_v2.db', check_same_thread=False)
    c = conn.cursor()
    # Ruokaloki
    c.execute('''CREATE TABLE IF NOT EXISTS meals 
                 (date TEXT, food TEXT, calories INT, protein INT)''')
    # Painoloki
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
              (datetime.now().strftime("%Y-%m
