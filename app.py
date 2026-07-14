import streamlit as st
import yt_dlp
import os
import google.genai as genai
import subprocess
import re
from static_ffmpeg import run
# Import für die Google Sheets Verbindung
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# FFmpeg-Pfad registrieren
ffmpeg_bin, ffprobe_bin = run.get_or_fetch_platform_executables_else_raise()

# --- DEIN GEHEIMER API-KEY (Wird vor den Nutzern versteckt!) ---
# Wir holen uns den Key gleich über die sicheren "Secrets" von Streamlit im Internet!
DEIN_GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

st.set_page_config(page_title="ShortCut AI", page_icon="🎬", layout="centered")

st.title("🎬 ShortCut AI")
st.subheader("Der vollautomatische Short-Generator")
st.write("Schneide deine Videos mit KI direkt ins 9:16 Format.")

st.markdown("---")

# 1. SCHRITT: E-Mail-Abfrage für das Limit
st.write("### 🔑 Anmeldung")
user_email = st.text_input("Trage deine E-Mail-Adresse ein, um deine 2 Gratis-Videos freizuschalten:", placeholder="name@beispiel.de").strip().lower()

if user_email:
    # Überprüfen, ob die E-Mail ein gültiges Format hat
    if not re.match(r"[^@]+@[^@]+\.[^@]+", user_email):
        st.error("Bitte gib eine gültige E-Mail-Adresse ein!")
    else:
        try:
            # Verbindung zum Google Sheet herstellen
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0) # ttl=0 sorgt dafür, dass die Daten immer live geladen werden
            
            # Überprüfen, ob der Nutzer schon in der Tabelle existiert
            if user_email in df['email'].values:
                # Nutzer existiert -> verbleibende Videos auslesen
                user_row = df[df['email'] == user_email]
                videos_left = int(user_row['videos_left'].values[0])
            else:
                # Neuer Nutzer -> Im Datensatz mit 2 Videos hinzufügen
                new_user = pd.DataFrame([{"email": user_email, "videos_left": 2}])
                df = pd.concat([df, new_user], ignore_index=True)
                conn.update(data=df)
                videos_left = 2
                st.balloons()
                st.success(f"Willkommen! Deine E-Mail wurde registriert. Du hast **{videos_left} Gratis-Videos** übrig.")

            # Status-Anzeige für den Nutzer
            if videos_left > 0:
                st.info(f"🎈 Du hast noch **{videos_left} von 2** Gratis-Videos übrig.")
                
                # --- HIER STARTET DIE EIGENTLICHE APP ---
                st.markdown("---")
                video_url = st.text_input("🔗 Dein YouTube-Video-Link:", placeholder="https://www.youtube.com/watch?v=...")

                if st.button("🚀 Short generieren", type="primary"):
                    if not video_url:
                        st.warning("Bitte gib einen gültigen YouTube-Link ein!")
                    else:
                        with st.spinner("KI analysiert das Video und schneidet deinen Short..."):
                            audio_filename = "temp_audio.m4a"
                            video_filename = "input_video.mp4"
                            output_filename = "output_short.mp4"
                            
                            try:
                                # 1. Audio laden
                                st.write("⏳ Extrahiere Tonspur...")
                                ydl_opts_audio = {
                                    'format': 'bestaudio[ext=m4a]/bestaudio', 
                                    'outtmpl': 'temp_audio.%(ext)s',
                                    'noplaylist': True,
                                    'overwrites': True,
                                }
                                with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                                    ydl.download([video_url])
                                
                                # 2. Gemini 3.5 Analyse (Nutzt jetzt deinen versteckten Key!)
                                st.write("🧠 KI sucht das Highlight und schreibt die Caption...")
                                client = genai.Client(api_key=DEIN_GEMINI_API_KEY)
                                audio_file = client.files.upload(file=audio_filename)
                                
                                prompt = (
                                    "Analysiere dieses Audio. Finde die absolut beste Sequenz (Länge exakt zwischen 30 und 50 Sekunden).\n"
                                    "Generiere zusätzlich eine extrem packende, virale Social-Media-Beschreibung (Caption) mit Emojis für TikTok/Reels/Shorts "
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

                                # 3. Video laden
                                st.write("📥 Lade Video-Spur herunter...")
                                ydl_opts_video = {
                                    'format': 'best[ext=mp4]', 
                                    'outtmpl': video_filename,
                                    'noplaylist': True,
                                    'overwrites': True,
                                }
                                with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                                    ydl.download([video_url])

                                # 4. FFmpeg Schnitt & Zoom
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
                # Hier kannst du später deinen Stripe- oder Copecart-Link einfügen
                st.link_button("💎 Jetzt unbegrenzten Premium-Zugang sichern", "https://deine-seite.de/checkout", type="primary")

        except Exception as database_error:
            st.error(f"Fehler bei der Verbindung zur Benutzer-Datenbank. Bitte versuche es später noch einmal. ({database_error})")

st.markdown("---")
st.caption("© 2026 ShortCut AI - Dein Content-Recycling-Tool")