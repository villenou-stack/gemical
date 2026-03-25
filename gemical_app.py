import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
from datetime import datetime
import os

# --- 1. ASETUKSET JA API ---
# Streamlit Cloudissa aseta 'GEMINI_API_KEY' Advanced Settings -> Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "LAITA_OMA_AVAIN_TÄHÄN_JOS_AJAT_PAIKALLISESTI"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. TIETOKANTAFUNKTIOT ---
def init_db():
    conn = sqlite3.connect('gemical_v2.db')
    c = conn.cursor()
    # Taulukko ruuille
    c.execute('''CREATE TABLE IF NOT EXISTS meals 
                 (date TEXT, food TEXT, calories INT, protein INT)''')
    # Taulukko painolle
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs 
                 (date TEXT, weight REAL)''')
    conn.commit()
    conn.close()

def save_meal(food, cal, prot):
    conn = sqlite3.connect('gemical_v2.db')
    c = conn.cursor()
    c.execute("INSERT INTO meals VALUES (?, ?, ?, ?)", 
              (datetime.now().strftime("%Y-%m-%d"), food, cal, prot))
    conn.commit()
    conn.close()

def save_weight(weight):
    conn = sqlite3.connect('gemical_v2.db')
    c = conn.cursor()
    c.execute("INSERT INTO weight_logs VALUES (?, ?)", 
              (datetime.now().strftime("%Y-%m-%d"), weight))
    conn.commit()
    conn.close()

init_db()

# --- 3. KÄYTTÖLIITTYMÄ (UI) ---
st.set_page_config(page_title="GemiCal Pro", page_icon="🥗", layout="centered")

st.title("🥗 GemiCal Pro")
st.write("183cm | Tavoite: 90kg & 100kg Penkki")

# --- SIVUPALKKI: RYHTI & PAINO ---
with st.sidebar:
    st.header("📊 Edistyminen")
    current_weight = st.number_input("Tämän päivän paino (kg):", 80.0, 110.0, 100.0, 0.1)
    if st.button("Tallenna paino"):
        save_weight(current_weight)
        st.success("Paino tallennettu!")
    
    st.write("---")
    st.header("🧘 Ryhtihuolto")
    st.checkbox("Couch Stretch (1 min/puoli)")
    st.checkbox("Chin Tucks (15x)")
    st.checkbox("Wall Slides (15x)")
    st.write("---")
    st.caption("GemiCal v2.0 | 2700 kcal target")

# --- PÄIVÄN TILANNE ---
today_str = datetime.now().strftime("%Y-%m-%d")
conn = sqlite3.connect('gemical_v2.db')
res = conn.execute("SELECT SUM(calories), SUM(protein) FROM meals WHERE date=?", (today_str,)).fetchone()
conn.close()

consumed_cal = res[0] if res[0] else 0
consumed_prot = res[1] if res[1] else 0

col1, col2 = st.columns(2)
col1.metric("Syöty tänään", f"{consumed_cal} kcal", f"{2700 - consumed_cal} jäljellä")
col2.metric("Proteiini", f"{consumed_prot} g", "Tavoite >180g")

# --- KAMERA JA ANALYYSI ---
st.write("---")
img_file = st.camera_input("Kuvaa annos (esim. Usva-lounas)")

if img_file:
    img = Image.open(img_file)
    with st.spinner('AI analysoi annosta...'):
        prompt = """
        Toimi kokeneena ravitsemusasiantuntijana. Analysoi kuvan ruoka.
        Käyttäjä on 100kg mies, joka treenaa kovaa. Arvioi kalorit ja proteiinit.
        Palauta VAIN JSON:
        {"ruoka": "nimi", "kalorit": 0, "proteiini": 0, "vinkki": "lyhyt terveysvinkki"}
        """
        response = model.generate_content([prompt, img])
        
        try:
            # Puhdistetaan vastaus JSON-muotoon
            raw_text = response.text.strip().replace("```json", "").replace("```", "")
            data = json.loads(raw_text)
            
            st.success(f"Tunnistettu: {data['ruoka']}")
            st.write(f"**Arvio:** {data['kalorit']} kcal | {data['proteiini']}g prot")
            st.info(f"💡 {data['vinkki']}")
            
            if st.button("Lisää päiväkirjaan"):
                save_meal(data['ruoka'], data['calories' if 'calories' in data else 'kalorit'], data['protein_g' if 'protein_g' in data else 'proteiini'])
                st.success("Tallennettu!")
                st.rerun()
        except:
            st.error("AI:n vastausta ei voitu lukea. Yritä uudelleen.")

# --- HISTORIA ---
if st.checkbox("Näytä päivän syömiset"):
    conn = sqlite3.connect('gemical_v2.db')
    history = conn.execute("SELECT food, calories, protein FROM meals WHERE date=? ORDER BY rowid DESC", (today_str,)).fetchall()
    conn.close()
    for f, c, p in history:
        st.text(f"- {f}: {c} kcal, {p}g prot")