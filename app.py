import streamlit as st
import os
import google.genai as genai
import subprocess
import re
# Import für die Google Sheets Verbindung
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# FFmpeg-Pfad
ffmpeg_bin = "ffmpeg"

# API-Key aus den Secrets laden
DEIN_GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

st.set_page_config(page_title="ShortCut AI", page_icon="🎬", layout="centered")

st.title("🎬 ShortCut AI")
st.subheader("Der vollautomatische Short-Generator")
st.write("Erstelle virale Shorts im 9:16 Format aus deinen Videos.")

st.markdown("---")

# 1. SCHRITT: E-Mail-Abfrage für das Limit
st.write("### 🔑 Anmeldung")
user_email = st.text_input("Trage deine E-Mail-Adresse ein, um deine 2 Gratis-Videos freizuschalten:", placeholder="name@beispiel.de").strip().lower()

if user_email:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", user_email):
        st.error("Bitte gib eine gültige E-Mail-Adresse ein!")
    else:
        try:
            # Verbindung zum Google Sheet herstellen
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0) # Immer live laden
            
            # Überprüfen, ob der Nutzer schon existiert
            if user_email in df['email'].values:
                user_row = df[df['email'] == user_email]
                videos_left = int(user_row['videos_left'].values[0])
            else:
                # Neuer Nutzer -> Registrieren
                new_user = pd.DataFrame([{"email": user_email, "videos_left": 2}])
                df = pd.concat([df, new_user], ignore_index=True)
                conn.update(data=df)
                videos_left = 2
                st.balloons()
                st.success(f"Willkommen! Deine E-Mail wurde registriert. Du hast **{videos_left} Gratis-Videos** übrig.")

            # Status-Anzeige für den Nutzer
            if videos_left > 0:
                st.info(f"🎈 Du hast noch **{videos_left} von 2** Gratis-Videos übrig.")
                
                # --- APP-BEREICH ---
                st.markdown("---")
                st.write("### 📤 Lade dein Video hoch")
                
                # Datei-Uploader (Unterstützt MP4, MOV, AVI bis 200MB auf Streamlit)
                uploaded_file = st.file_uploader("Wähle ein Video von deinem Gerät aus:", type=["mp4", "mov", "avi"])

                if uploaded_file is not None:
                    st.success("Video erfolgreich geladen!")
                    
                    if st.button("🚀 Short generieren", type="primary"):
                        with st.spinner("KI analysiert das Video und schneidet deinen Short..."):
                            audio_filename = "temp_audio.m4a"
                            video_filename = "input_video.mp4"
                            output_filename = "output_short.mp4"
                            
                            try:
                                # Das hochgeladene Video temporär auf dem Server speichern
                                with open(video_filename, "wb") as f:
                                    f.write(uploaded_file.read())
                                            
                                # 1. Die Tonspur lokal mit FFmpeg extrahieren
                                st.write("⏳ Extrahiere Tonspur...")
                                audio_extract_cmd = [
                                    ffmpeg_bin, "-y",
                                    "-i", video_filename,
                                    "-vn", "-acodec", "aac",
                                    audio_filename
                                ]
                                subprocess.run(audio_extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                                
                                # 2. Gemini 3.5 Analyse
                                st.write("🧠 KI sucht das Highlight und schreibt die Caption...")
                                client = genai.Client(api_key=DEIN_GEMINI_API_KEY)
                                audio_file = client.files.upload(file=audio_filename)
                                
                                prompt = (
                                    "Analysiere dieses Audio. Finde die absolut beste Sequenz (Länge exakt zwischen 30 und 50 Sekunden).\n"
                                    "Generiere zusätzlich eine extrem packende, virale Social-Media-Beschreibung (caption) mit Emojis für TikTok/Reels/Shorts "
                                    "sowie 5-8 hochrelevante, virale Hashtags.\n\n"
                                    "Antworte mir AUSSCHLIESSLICH im folgenden Format, ersetze die Werte in den Klammern. Keine anderen Sätze drumherum!\n"
                                    "START: [Startsekunde als reine Zahl, z.B. 45]\n"
                                    "END: [Endsekunde als reine Zahl, z.B. 85]\n"
                                    "CAPTION: [Fesselnde Beschreibung, die Neugier weckt und Emojis enthält]\n"
                                    "HASHTAGS: [#viral #typ #shortcut etc.]\n"
                                    "BEGRUENDUNG: [Kurze Begründung auf Deutsch, warum das viral gehen wird]"
                                )
                                
                                response = client.models.generate_content(
                                    model='gemini-3.5-flash', 
                                    contents=[audio_file, prompt]
                                )
                                
                                ki_text = response.text
                                
                                start_sec, end_sec = 10, 40
                                caption = "Schau dir das an! 😱🔥"
                                hashtags = "#viral #shorts #ai"
                                begruendung = ""
                                
                                for line in ki_text.split("\n"):
                                    if line.startswith("START:"):
                                        try: start_sec = int(line.replace("START:", "").strip())
                                        except: pass
                                    elif line.startswith("END:"):
                                        try: end_sec = int(line.replace("END:", "").strip())
                                        except: pass
                                    elif line.startswith("CAPTION:"):
                                        caption = line.replace("CAPTION:", "").strip()
                                    elif line.startswith("HASHTAGS:"):
                                        hashtags = line.replace("HASHTAGS:", "").strip()
                                    elif line.startswith("BEGRUENDUNG:"):
                                        begruendung = line.replace("BEGRUENDUNG:", "").strip()

                                duration = end_sec - start_sec

                                # 3. FFmpeg Schnitt & Zoom (Lokal)
                                st.write("✂️ Schneide Video und zoome auf 9:16 Hochformat...")
                                ffmpeg_command = [
                                    ffmpeg_bin, "-y",
                                    "-ss", str(start_sec),
                                    "-i", video_filename,
                                    "-t", str(duration),
                                    "-vf", "crop=ih*(9/16):ih", 
                                    "-c:v", "libx264", "-profile:v", "main", "-level", "3.0",
                                    "-pix_fmt", "yuv420p",
                                    "-c:a", "aac",
                                    output_filename
                                ]
                                subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                                
                                st.success("🎉 Dein Short im Hochformat (9:16) ist fertig!")
                                
                                # Dem Nutzer ein Video abziehen und im Google Sheet speichern!
                                df.loc[df['email'] == user_email, 'videos_left'] = videos_left - 1
                                conn.update(data=df)
                                
                                # Ergebnisse anzeigen
                                st.markdown("### 📝 Textvorlage für deinen Post")
                                st.write("**Beschreibung (Caption):**")
                                st.code(caption, language="text")
                                st.write("**Hashtags:**")
                                st.code(hashtags, language="text")
                                st.info(f"💡 **Warum das viral geht:** {begruendung}")
                                st.markdown("---")
                                
                                # Download-Button
                                with open(output_filename, "rb") as file:
                                    st.download_button(
                                        label="📥 Short jetzt herunterladen (MP4)",
                                        data=file,
                                        file_name="mein_viraler_short.mp4",
                                        mime="video/mp4"
                                    )

                            except Exception as e:
                                st.error(f"Fehler bei der Verarbeitung: {e}")
                            
                            finally:
                                # Sicheres Löschen aller temporären Dateien
                                for temp_file in [audio_filename, video_filename, output_filename]:
                                    if os.path.exists(temp_file):
                                        try: os.remove(temp_file)
                                        except: pass
            else:
                # --- DIE PAYWALL ---
                st.markdown("---")
                st.error("⚠️ **Dein Gratis-Limit ist erreicht!**")
                st.markdown(
                    "Du hast deine 2 freien Videos für diesen Account bereits erfolgreich generiert. "
                    "Um ShortCut AI unbegrenzt weiterzunutzen und noch mehr virale Clips zu erstellen, "
                    "sichere dir jetzt deinen Premium-Zugang!"
                )
                st.link_button("💎 Jetzt unbegrenzten Premium-Zugang sichern", "https://deine-seite.de/checkout", type="primary")

        except Exception as database_error:
            st.error(f"Fehler bei der Verbindung zur Benutzer-Datenbank. Bitte versuche es später noch einmal. ({database_error})")

st.markdown("---")
st.caption("© 2026 ShortCut AI - Dein Content-Recycling-Tool")
