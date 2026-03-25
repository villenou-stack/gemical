import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
from datetime import datetime
import os

# --- 1. ASETUKSET JA API ---
# Muista asettaa Streamlit Cloudissa: Settings -> Secrets -> GEMINI_API_KEY = "AVAIN"
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "MÄÄRITÄ_AVAIN_SECRETS_OSIOSSA"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. TIETOKANTAFUNKTIOT ---
def init_db():
    conn = sqlite3.connect('gemical_v2.db')
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
st.write("Tavoite: 90kg & 100kg Penkki")

# --- SIVUPALKKI: EDISTYMINEN & HUOLTO ---
with st.sidebar:
    st.header("📊 Kehitys")
    current_weight = st.number_input("Päivän paino (kg):", 70.0, 120.0, 100.0, 0.1)
    if st.button("Tallenna paino"):
        save_weight(current_weight)
        st.success(f"Paino {current_weight}kg tallennettu!")
    
    st.write("---")
    st.header("🧘 Ryhtihuolto")
    st.checkbox("Couch Stretch (1 min/puoli)")
    st.checkbox("Chin Tucks (15 toistoa)")
    st.checkbox("Wall Slides (15 toistoa)")
    st.write("---")
    st.caption("GemiCal v2.1 | 2700 kcal / vrk")

# --- PÄIVÄN STATUS ---
today_str = datetime.now().strftime("%Y-%m-%d")
conn = sqlite3.connect('gemical_v2.db')
res = conn.execute("SELECT SUM(calories), SUM(protein) FROM meals WHERE date=?", (today_str,)).fetchone()
conn.close()

consumed_cal = res[0] if res[0] else 0
consumed_prot = res[1] if res[1] else 0

col1, col2 = st.columns(2)
col1.metric("Kalorit tänään", f"{consumed_cal} kcal", f"{2700 - consumed_cal} jäljellä")
col2.metric("Proteiini", f"{consumed_prot} g", "Tavoite >180g")

# --- KUVA JA ANALYYSI ---
st.write("---")
st.subheader("Lisää ateria")

tab1, tab2 = st.tabs(["📸 Ota kuva", "📁 Valitse tiedosto"])

with tab1:
    camera_file = st.camera_input("Käytä kameraa")

with tab2:
    uploaded_file = st.file_uploader("Lataa muistista", type=['jpg', 'jpeg', 'png'])

# Käytetään kumpaa tahansa saatavilla olevaa tiedostoa
img_file = camera_file if camera_file is not None else uploaded_file

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="Valittu annos", use_container_width=True)
    
    if st.button("Analysoi ja tallenna"):
        with st.spinner('AI laskee kaloreita...'):
            prompt = """
            Toimi ravitsemusasiantuntijana. Analysoi kuvan ruoka.
            Käyttäjä on 100kg mies, joka treenaa kovaa. Arvioi kalorit ja proteiinit.
            Palauta VAIN JSON-muodossa:
            {"ruoka": "nimi", "kalorit": 0, "proteiini": 0, "vinkki": "lyhyt vinkki"}
            """
            
            try:
                response = model.generate_content([prompt, img])
                # Puhdistetaan AI:n vastaus JSON-yhteensopivaksi
                raw_text = response.text.strip().replace("```json", "").replace("```", "")
                data = json.loads(raw_text)
                
                # Tallennus tietokantaan
                save_meal(data.get('ruoka', 'Tuntematon'), 
                          data.get('kalorit', 0), 
                          data.get('proteiini', 0))
                
                st.success(f"Tallennettu: {data.get('ruoka')} ({data.get('kalorit')} kcal)")
                st.info(f"💡 {data.get('vinkki')}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Virhe analyysissä: {e}")
                st.write("Varmista, että API-avain on asetettu oikein Secrets-osioon.")

# --- HISTORIA ---
if st.checkbox("Näytä päivän historia"):
    conn = sqlite3.connect('gemical_v2.db')
    history = conn.execute("SELECT food, calories, protein FROM meals WHERE date=? ORDER BY rowid DESC", (today_str,)).fetchall()
    conn.close()
    if history:
        for f, c, p in history:
            st.write(f"🍴 **{f}**: {c} kcal | {p}g prot")
    else:
        st.write("Ei vielä kirjauksia tälle päivälle.")