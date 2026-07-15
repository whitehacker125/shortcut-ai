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

# --- SPRACH-AUSWAHL ---
# Wir packen einen eleganten Sprachumschalter in die Seitenleiste (Sidebar)
with st.sidebar:
    language = st.selectbox("🌐 Language / Sprache", ["English 🇬🇧", "Deutsch 🇩🇪"])

# Wörterbuch für die Lokalisierung
if language == "Deutsch 🇩🇪":
    t = {
        "title": "🎬 ShortCut AI",
        "subheader": "Der intelligente All-in-One Video-zu-Short-Generator",
        "description": """
        **ShortCut AI nimmt dir die komplette Arbeit ab:** 
        1. **Intelligente Analyse:** Unsere KI durchsucht dein hochgeladenes Video und findet den spannendsten und viralsten Moment.
        2. **Automatischer Zuschnitt:** Der Clip wird vollautomatisch in das perfekte vertikale **9:16-Format** geschnitten (ideal für TikTok, Instagram Reels & YouTube Shorts).
        3. **Copywriting & Hashtags:** Du erhältst eine packende, virale Beschreibung (Caption) sowie handverlesene Trend-Hashtags direkt zum Kopieren.
        """,
        "login": "### 🔑 Anmeldung",
        "email_placeholder": "name@beispiel.de",
        "email_label": "Trage deine E-Mail-Adresse ein, um deine 2 Gratis-Videos freizuschalten:",
        "email_error": "Bitte gib eine gültige E-Mail-Adresse ein!",
        "welcome": "Willkommen! Deine E-Mail wurde registriert. Du hast **{0} Gratis-Videos** übrig.",
        "credits_left": "🎈 Du hast noch **{0} von 2** Gratis-Videos übrig.",
        "upload_section": "### 📤 Lade dein Video hoch",
        "upload_label": "Wähle ein Video von deinem Gerät aus:",
        "upload_success": "Video erfolgreich geladen!",
        "btn_generate": "🚀 Short generieren",
        "spinner_msg": "KI analysiert das Video und schneidet deinen Short...",
        "status_audio": "⏳ Extrahiere Tonspur...",
        "status_ai": "🧠 KI sucht das Highlight und schreibt die Caption...",
        "status_crop": "✂️ Schneide Video und zoome auf 9:16 Hochformat...",
        "success_msg": "🎉 Dein Short im Hochformat (9:16) ist fertig!",
        "result_header": "### 📝 Textvorlage für deinen Post",
        "caption_lbl": "**Beschreibung (Caption):**",
        "hashtag_lbl": "**Hashtags:**",
        "why_viral": "💡 **Warum das viral geht:** {0}",
        "btn_download": "📥 Short jetzt herunterladen (MP4)",
        "ip_block": "🔒 Schutz-Sperre aktiv: Dieses Gerät hat das Limit an Gratis-Videos bereits erreicht.",
        "paywall_title": "⚠️ **Dein Gratis-Limit ist erreicht!**",
        "paywall_text": "Du hast deine 2 freien Videos für dieses Gerät oder diese E-Mail bereits generiert. Sichern dir jetzt deinen Zugang, um ShortCut AI unbegrenzt weiterzunutzen!",
        "paywall_btn_de": "💎 Zugang sichern via CopeCart (Deutschland/PayPal/SEPA)",
        "paywall_btn_en": "💎 Get Access via Lemon Squeezy (International/Card)",
        "db_error": "Fehler bei der Verbindung zur Benutzer-Datenbank. Bitte versuche es später noch einmal.",
        "prompt_lang": "Deutsch"
    }
else:
    t = {
        "title": "🎬 ShortCut AI",
        "subheader": "The Intelligent All-in-One Video-to-Short Generator",
        "description": """
        **ShortCut AI does all the heavy lifting for you:** 
        1. **AI Analysis:** Our artificial intelligence scans your uploaded video to find the most exciting and viral moment.
        2. **Auto-Cropping:** The clip is automatically cropped into the perfect vertical **9:16 aspect ratio** (ideal for TikTok, Instagram Reels & YouTube Shorts).
        3. **Copywriting & Hashtags:** You get an engaging, viral description (caption) and hand-picked trending hashtags ready to copy.
        """,
        "login": "### 🔑 Login",
        "email_placeholder": "name@example.com",
        "email_label": "Enter your email address to unlock your 2 free videos:",
        "email_error": "Please enter a valid email address!",
        "welcome": "Welcome! Your email has been registered. You have **{0} free videos** left.",
        "credits_left": "🎈 You have **{0} out of 2** free videos left.",
        "upload_section": "### 📤 Upload your video",
        "upload_label": "Select a video from your device:",
        "upload_success": "Video successfully loaded!",
        "btn_generate": "🚀 Generate Short",
        "spinner_msg": "AI is analyzing the video and cropping your short...",
        "status_audio": "⏳ Extracting audio track...",
        "status_ai": "🧠 AI is finding the highlight and writing the caption...",
        "status_crop": "✂️ Cutting video and zooming to 9:16 vertical format...",
        "success_msg": "🎉 Your vertical short (9:16) is ready!",
        "result_header": "### 📝 Copy/Paste Templates for your post",
        "caption_lbl": "**Caption:**",
        "hashtag_lbl": "**Hashtags:**",
        "why_viral": "💡 **Why this will go viral:** {0}",
        "btn_download": "📥 Download Short Now (MP4)",
        "ip_block": "🔒 Security Lock: This device has reached the limit for free videos.",
        "paywall_title": "⚠️ **Your Free Limit has been reached!**",
        "paywall_text": "You have successfully generated your 2 free videos for this device or email. Upgrade to premium now to keep using ShortCut AI without limits!",
        "paywall_btn_de": "💎 Get Access via CopeCart (German/PayPal/SEPA)",
        "paywall_btn_en": "💎 Get Access via Lemon Squeezy (International/Card)",
        "db_error": "Database connection error. Please try again later.",
        "prompt_lang": "English"
    }

# --- SESSION STATE INITIALISIERUNG ---
if "generation_results" not in st.session_state:
    st.session_state.generation_results = None

st.title(t["title"])
st.subheader(t["subheader"])

# Beschreibung anzeigen
st.markdown(t["description"])

st.markdown("---")

# IP-Adresse des Nutzers auslesen
user_ip = st.context.ip_address
if user_ip is None:
    user_ip = "127.0.0.1"

# 1. SCHRITT: E-Mail-Abfrage für das Limit
st.write(t["login"])
user_email = st.text_input(t["email_label"], placeholder=t["email_placeholder"]).strip().lower()

if user_email:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", user_email):
        st.error(t["email_error"])
    else:
        try:
            # Verbindung zum Google Sheet herstellen
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0) # Immer live laden
            
            # Falls die Spalte 'ip_address' noch nicht existiert
            if 'ip_address' not in df.columns:
                df['ip_address'] = ""
                conn.update(data=df)

            # --- SICHERHEITS-CHECK ---
            ip_exists = user_ip in df['ip_address'].values
            email_exists = user_email in df['email'].values

            if ip_exists:
                ip_row = df[df['ip_address'] == user_ip]
                videos_left = int(ip_row['videos_left'].values[0])
                if videos_left <= 0 and not email_exists:
                    st.warning(t["ip_block"])
            
            elif email_exists:
                email_row = df[df['email'] == user_email]
                videos_left = int(email_row['videos_left'].values[0])
            
            else:
                # Neuer Nutzer
                new_user = pd.DataFrame([{"email": user_email, "videos_left": 2, "ip_address": user_ip}])
                df = pd.concat([df, new_user], ignore_index=True)
                conn.update(data=df)
                videos_left = 2
                st.balloons()
                st.success(t["welcome"].format(videos_left))

            # Status-Anzeige & App-Freigabe
            if videos_left > 0:
                st.info(t["credits_left"].format(videos_left))
                
                # --- APP-BEREICH ---
                st.markdown("---")
                st.write(t["upload_section"])
                
                # Datei-Uploader
                uploaded_file = st.file_uploader(t["upload_label"], type=["mp4", "mov", "avi"])

                if uploaded_file is not None:
                    st.success(t["upload_success"])
                    
                    if st.button(t["btn_generate"], type="primary"):
                        with st.spinner(t["spinner_msg"]):
                            audio_filename = "temp_audio.m4a"
                            video_filename = "input_video.mp4"
                            output_filename = "output_short.mp4"
                            
                            try:
                                with open(video_filename, "wb") as f:
                                    f.write(uploaded_file.read())
                                            
                                # 1. Audio extrahieren
                                st.write(t["status_audio"])
                                audio_extract_cmd = [
                                    ffmpeg_bin, "-y",
                                    "-i", video_filename,
                                    "-vn", "-acodec", "aac",
                                    audio_filename
                                ]
                                subprocess.run(audio_extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                                
                                # 2. Gemini Analyse
                                st.write(t["status_ai"])
                                client = genai.Client(api_key=DEIN_GEMINI_API_KEY)
                                audio_file = client.files.upload(file=audio_filename)
                                
                                # Der Prompt passt sich dynamisch an die gewählte Sprache an!
                                prompt = (
                                    f"Analyze this audio. Find the absolute best sequence (duration strictly between 30 and 50 seconds).\n"
                                    f"Generate an extremely engaging, viral social media description (caption) with emojis for TikTok/Reels/Shorts "
                                    f"as well as 5-8 highly relevant, viral hashtags.\n"
                                    f"Write the caption, hashtags, and explanation entirely in {t['prompt_lang']}!\n\n"
                                    f"Respond EXCLUSIVELY in the following format, replace values in brackets. Do not write anything else!\n"
                                    f"START: [Start second as a raw number, e.g. 45]\n"
                                    f"END: [End second as a raw number, e.g. 85]\n"
                                    f"CAPTION: [Captivating description with emojis]\n"
                                    f"HASHTAGS: [#viral #typ #shortcut etc.]\n"
                                    f"BEGRUENDUNG: [Short explanation in the chosen language why this will go viral]"
                                )
                                
                                response = client.models.generate_content(
                                    model='gemini-3.5-flash', 
                                    contents=[audio_file, prompt]
                                )
                                
                                ki_text = response.text
                                
                                start_sec, end_sec = 10, 40
                                caption = "Check this out! 😱🔥"
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

                                # 3. FFmpeg Schnitt & Zoom
                                st.write(t["status_crop"])
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
                                
                                with open(output_filename, "rb") as video_file:
                                    video_bytes = video_file.read()
                                
                                st.session_state.generation_results = {
                                    "caption": caption,
                                    "hashtags": hashtags,
                                    "begruendung": begruendung,
                                    "video_bytes": video_bytes
                                }
                                
                                if ip_exists:
                                    df.loc[df['ip_address'] == user_ip, 'videos_left'] = videos_left - 1
                                elif email_exists:
                                    df.loc[df['email'] == user_email, 'videos_left'] = videos_left - 1
                                else:
                                    df.loc[df['email'] == user_email, 'videos_left'] = videos_left - 1
                                
                                conn.update(data=df)
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error: {e}")
                            
                            finally:
                                for temp_file in [audio_filename, video_filename, output_filename]:
                                    if os.path.exists(temp_file):
                                        try: os.remove(temp_file)
                                        except: pass
                
                # --- ERGEBNIS-ANZEIGE ---
                if st.session_state.generation_results is not None:
                    res = st.session_state.generation_results
                    
                    st.markdown("---")
                    st.success(t["success_msg"])
                    
                    st.video(res["video_bytes"])
                    
                    st.markdown(t["result_header"])
                    st.write(t["caption_lbl"])
                    st.code(res["caption"], language="text")
                    
                    st.write(t["hashtag_lbl"])
                    st.code(res["hashtags"], language="text")
                    
                    st.info(t["why_viral"].format(res['begruendung']))
                    st.markdown("---")
                    
                    st.download_button(
                        label=t["btn_download"],
                        data=res["video_bytes"],
                        file_name="shortcut_ai_short.mp4",
                        mime="video/mp4"
                    )
            else:
                # --- DIE PAYWALLS (FÜR DEUTSCH UND ENGLISCH) ---
                st.markdown("---")
                st.error(t["paywall_title"])
                st.markdown(t["paywall_text"])
                
                col1, col2 = st.columns(2)
                with col1:
                    # HIER DEINEN COPECART/DIGISTORE-LINK EINTRAGEN
                    st.link_button(t["paywall_btn_de"], "https://www.copecart.com/products/DEIN_PRODUKT_ID/checkout", type="primary")
                with col2:
                    # HIER DEINEN LEMON SQUEEZY LINK EINTRAGEN
                    st.link_button(t["paywall_btn_en"], "https://deinefirmade.lemonsqueezy.com/checkout/buy/PRODUKT_ID", type="secondary")

        except Exception as database_error:
            st.error(f"{t['db_error']} ({database_error})")

st.markdown("---")
st.caption("© 2026 ShortCut AI - Your Content Recycling Tool")
