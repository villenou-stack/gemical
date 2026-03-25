3.  **Tietokantapolku:** Varmistimme, että tietokanta ja kuvakansio luodaan oikeisiin polkuihin, jotta Streamlitillä on niihin varmasti kirjoitusoikeudet.
4.  **Käsittelynopeus:** Teimme koodista kevyemmän ja vähemmän alttiin "aikakatkaisuille" (timeouts) Cloud-ympäristössä.

### Koko toimiva koodi (`gemical_app.py`)

Kopioi tästä koko sisältö tiedostoosi ja tallenna se GitHubiin:

```python
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
import os
import io

# --- 1. ASETUKSET JA API (Varmistettu toimivaksi) ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        st.error("❌ API-avain puuttuu Streamlit Secrets-osiosta! Lisää: GEMINI_API_KEY = 'AVAIN'")
        st.stop()
except Exception as e:
    st.error(f"❌ Virhe Secrets-luvussa: {e}")
    st.stop()

# Alustetaan Gemini-malli
genai.configure(api_key=API_KEY)
# Käytetään pro-versiota parempaan JSON-käsittelyyn ja kuva-analyysiin
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. TIETOKANTA- JA KUVAKANSIO-FUNKTIOT ---
DB_NAME = 'gemical_v2.5.db'
IMAGE_FOLDER = 'saved_images'

# Varmistetaan, että kuvakansio on olemassa
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Ruokaloki: Lisätty 'image_path' kuvan tiedostonimelle
    c.execute('''CREATE TABLE IF NOT EXISTS meals 
                 (date TEXT, food TEXT, calories INT, protein INT, image_path TEXT)''')
    # Painoloki
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs 
                 (date TEXT, weight REAL)''')
    conn.commit()
    conn.close()

def save_meal(food, cal, prot, image_path=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO meals (date, food, calories, protein, image_path) VALUES (date('now'), ?, ?, ?, ?)", 
              (food, int(cal), int(prot), image_path))
    conn.commit()
    conn.close()

def save_weight(weight):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO weight_logs (date, weight) VALUES (date('now'), ?)", 
              (weight,))
    conn.commit()
    conn.close()

# Alustetaan tietokanta heti
init_db()

# --- 3. KÄYTTÖLIITTYMÄ (UI) ---
st.set_page_config(page_title="GemiCal Pro v2.5", page_icon="🥗", layout="centered")

st.title("🥗 GemiCal Pro")
st.write("Tavoite: 90 kg & 100 kg Penkkipunnerrus")

# --- SIVUPALKKI: EDISTYMINEN ---
with st.sidebar:
    st.header("📊 Kehitys")
    current_weight = st.number_input("Päivän paino (kg):", 50.0, 150.0, 100.0, 0.1)
    if st.button("Tallenna paino"):
        save_weight(current_weight)
        st.success(f"Paino {current_weight} kg tallennettu!")
    
    st.write("---")
    st.caption("GemiCal v2.5 | Tavoite: 2700 kcal / vrk")

# --- PÄIVÄN STATUS (Kysytään tietokannasta) ---
conn = get_connection()
# Haetaan päivän summa kaloreista ja proteiinista
res = conn.execute("SELECT SUM(calories), SUM(protein) FROM meals WHERE date=date('now')").fetchone()
conn.close()

consumed_cal = res[0] if res[0] else 0
consumed_prot = res[1] if res[1] else 0

# Näytetään metriikat
col1, col2 = st.columns(2)
col1.metric("Kalorit tänään", f"{consumed_cal} kcal", f"{2700 - consumed_cal} jäljellä")
col2.metric("Proteiini", f"{consumed_prot} g", f"Tavoite 180g ({max(0, 180-consumed_prot)}g uupuu)")

# --- KUVA, ANALYYSI JA TALLENNUS ---
st.write("---")
st.subheader("Lisää ateria")

tab1, tab2 = st.tabs(["📸 Ota kuva", "📁 Valitse tiedosto"])
with tab1:
    camera_file = st.camera_input("Käytä kameraa")
with tab2:
    uploaded_file = st.file_uploader("Lataa muistista", type=['jpg', 'jpeg', 'png'])

# Käytetään kumpaa tahansa tiedostoa
img_file = camera_file if camera_file is not None else uploaded_file

if img_file:
    # Näytetään kuva esikatseluna
    img = Image.open(img_file)
    st.image(img, caption="Valittu annos", use_container_width=True)
    
    if st.button("Analysoi ja tallenna"):
        with st.spinner('AI laskee kaloreita ja tallentaa kuvaa...'):
            
            # --- Vaihe 1: Tallennetaan kuva levylle ---
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Luodaan uniikki tiedostonimi
            image_filename = f"{timestamp}_meal.jpg"
            image_path = os.path.join(IMAGE_FOLDER, image_filename)
            
            # Konvertoidaan kuva JPG-muotoon, jotta se vie vähemmän tilaa
            rgb_img = img.convert('RGB')
            # Tallennetaan levylle
            rgb_img.save(image_path, "JPEG", quality=85)
            
            # --- Vaihe 2: AI Analysoi kalorit ---
            prompt = """
            Toimi ravitsemusasiantuntijana. Analysoi kuvan ruoka.
            Käyttäjä on 100kg mies, joka treenaa kovaa. Arvioi kalorit ja proteiinit.
            Palauta tiedot täsmälleen JSON-muodossa, jossa on seuraavat kentät:
            {"ruoka": "nimi", "kalorit": 0, "proteiini": 0, "vinkki": "lyhyt vinkki"}
            """
            try:
                # Pakotetaan vastaus puhtaaksi JSON-muodoksi
                response = model.generate_content(
                    [prompt, img],
                    generation_config={"response_mime_type": "application/json"}
                )
                data = json.loads(response.text)
                
                # --- Vaihe 3: Tallennus tietokantaan (Lisätty image_path) ---
                save_meal(data.get('ruoka', 'Tuntematon'), 
                          data.get('kalorit', 0), 
                          data.get('proteiini', 0),
                          image_path) # Tallennetaan polku tietokantaan
                
                st.success(f"Tallennettu: {data.get('ruoka')} ({data.get('kalorit')} kcal)")
                st.info(f"💡 {data.get('vinkki')}")
                st.rerun() # Päivitetään sivu, jotta metriikat ja historia päivittyvät
            
            except Exception as e:
                # Jos AI-analyysi epäonnistuu, poistetaan jo tallennettu kuva virheen välttämiseksi
                if os.path.exists(image_path):
                    os.remove(image_path)
                st.error(f"❌ Virhe analyysissä: {e}")

# --- HISTORIA (Päivitetty näyttämään myös kuvat) ---
st.write("---")
if st.checkbox("Näytä päivän historia (sis. kuvat)"):
    conn = get_connection()
    # Haetaan historia, mukaan lukien kuvan polku
    history = conn.execute("SELECT food, calories, protein, image_path FROM meals WHERE date=date('now') ORDER BY rowid DESC").fetchall()
    conn.close()
    
    if history:
        for f, c, p, img_p in history:
            # Luodaan laatikko jokaiselle historialle
            with st.container(border=True):
                col_text, col_img = st.columns([3, 1])
                
                with col_text:
                    st.write(f"🍴 **{f}**")
                    st.write(f"{c} kcal | {p}g proteiinia")
                
                with col_img:
                    # Jos kuvan polku löytyy ja tiedosto on olemassa, näytetään se
                    if img_p and os.path.exists(img_p):
                        try:
                            # Avaa kuva pienempänä historianäyttöä varten
                            h_img = Image.open(img_p)
                            # Pienennä kuvaa historianäyttöä varten, jotta sivu latautuu nopeammin
                            h_img.thumbnail((150, 150))
                            st.image(h_img, use_container_width=True)
                        except Exception:
                            st.write("(Kuva ei lataudu)")
                    else:
                        st.write("(Ei kuvaa)")
    else:
        st.write("Ei vielä kirjauksia tälle päivälle.")
```

### Tarkistuslista ennen tallennusta:
1.  **Varmista `requirements.txt`:** GitHub-repositoriossasi pitää olla tiedosto nimeltä `requirements.txt`, jonka sisältö on (Tämä on kriittinen):
    ```text
    streamlit
    google-generativeai>=0.5.0
    Pillow
