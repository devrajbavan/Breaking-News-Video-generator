#!/usr/bin/env python3
"""
News Video Pipeline
- Reads news articles from Google Sheet (Title + URL)
- Generates TTS, fetches images, and creates video
- Gradio UI with Previous / Next navigation
"""

import os
import re
import argparse
import requests
import textwrap
import tempfile
import nltk
from newspaper import Article
from bs4 import BeautifulSoup
from gtts import gTTS
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip, ColorClip
from PIL import Image, ImageOps
import gspread
from google.oauth2.service_account import Credentials
import gradio as gr

# Download NLTK punkt tokenizer if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

#  CONFIG 
SHEET_KEY = "1NroZCjXYE9s9uiLAtDeaM2T6FeKdF0C2PNrpk5WqS7g"
WORKSHEET_NAME = "Sheet1"
CREDS_FILE = "service_account.json"

#  GOOGLE SHEETS 
def load_google_sheet(sheet_key, worksheet_name="Sheet1", creds_file="service_account.json"):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_key).worksheet(worksheet_name)
    return sheet.get_all_records()

#  IMAGE UTILITIES 
def download_and_fit_image(url, size=(1280, 720), timeout=12):
    """
    Download an image from a URL and resize it to the given dimensions.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, timeout=timeout, headers=headers, stream=True)
        resp.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        with open(tmp.name, "wb") as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)
        im = Image.open(tmp.name).convert("RGB")
        im = ImageOps.fit(im, size, Image.Resampling.LANCZOS)
        im.save(tmp.name, format="JPEG", quality=85)
        return tmp.name
    except Exception:
        return None

def duckduckgo_image_search_and_download(query, size=(1280, 720)):
    """
    Fallback image search on DuckDuckGo when article doesn't have an image.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://duckduckgo.com/", params={"q": query}, headers=headers, timeout=10)
        token_m = re.search(r"vqd='([^\']+)'", r.text) or re.search(r'vqd="([^"]+)"', r.text)
        if not token_m: return None
        vqd = token_m.group(1)
        params = {"l": "us-en", "o": "json", "q": query, "vqd": vqd}
        jsr = requests.get("https://duckduckgo.com/i.js", params=params, headers=headers, timeout=10)
        jsr.raise_for_status()
        results = jsr.json().get("results") or []
        image_url = next((r["image"] for r in results if r.get("image")), None)
        return download_and_fit_image(image_url, size=size) if image_url else None
    except Exception:
        return None

#  ARTICLE UTILITIES 
def extract_article(url):
    """
    Extract title, text, and top image from a given news URL.
    """
    art = Article(url)
    art.download()
    art.parse()
    title, text, top_image = art.title or "", art.text or "", art.top_image or ""
    if not top_image:
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            og = soup.find("meta", property="og:image")
            if og and og.get("content"): top_image = og["content"]
        except Exception:
            top_image = ""
    return {"title": title, "text": text, "top_image": top_image, "url": url}

def rule_based_summary(text, max_sentences=3):
    """
    Simple summary: take the first 'max_sentences' sentences from the article.
    """
    if not text: return ""
    sents = nltk.tokenize.sent_tokenize(text)
    return " ".join(sents[:max_sentences])

#  TTS 
def tts_save_gtts(text, out_path, lang="en"):
    """
    Convert text to speech using gTTS and save to output path.
    """
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(out_path)
    return out_path

#  VIDEO 
def build_news_video(title, audio_path, out_path, resolution=(1280,720), header_text="BREAKING NEWS", image_path=None):
    """
    Build a video using MoviePy with background image, header, and highlighted title.
    """
    audio_clip = AudioFileClip(audio_path)
    duration = max(5.0, audio_clip.duration)
    W, H = resolution
    clips = []

    # Background
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path).resize((W, H), Image.Resampling.LANCZOS)
            tmp_img_path = os.path.join(tempfile.gettempdir(), "bg_resized.jpg")
            img.save(tmp_img_path)
            clips.append(ImageClip(tmp_img_path).set_duration(duration))
        except Exception:
            clips.append(ColorClip(size=(W,H), color=(20,20,20)).set_duration(duration))
    else:
        clips.append(ColorClip(size=(W,H), color=(20,20,20)).set_duration(duration))

    # Title with highlighted box
    wrapped_title = "\n".join(textwrap.wrap(title, width=50))
    title_clip = TextClip(wrapped_title, fontsize=40, font="Arial-Bold", color="white", method="label")
    text_w, text_h = title_clip.size
    box = ColorClip(size=(text_w+40, text_h+120), color=(150,0,0)).set_opacity(1).set_duration(duration)
    box = box.set_position(("center", H-120))
    clips.append(box)
    title_clip = title_clip.set_position(("center", H-120)).set_duration(duration)
    clips.append(title_clip)

    # Header
    header = TextClip(header_text, fontsize=50, font="Arial-Bold", color="white", method="label")
    header = header.on_color(size=(W, header.h + 20), color=(200,0,0), col_opacity=1)
    header = header.set_position(("center","top")).set_duration(duration)
    clips.append(header)

    # Combine and export
    final = CompositeVideoClip(clips, size=(W,H)).set_duration(duration).set_audio(audio_clip)
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac")
    final.close()
    audio_clip.close()
    return out_path

#  PIPELINE 
def run_pipeline(url, title=None, out_video_path="news_output.mp4"):
    art = extract_article(url)
    title = title or art["title"]

    print(f"[DEBUG] Running pipeline for: {title}")
    print(f"[DEBUG] Top Image Found: {art['top_image']}")

    summary = rule_based_summary(art["text"])
    audio_path = os.path.join(tempfile.gettempdir(), "tts.mp3")
    tts_save_gtts(summary or title, audio_path)

    image_path = None
    if art["top_image"]:
        image_path = download_and_fit_image(art["top_image"])
    if not image_path:
        print("[DEBUG] No valid article image, trying DuckDuckGo...")
        image_path = duckduckgo_image_search_and_download(title)

    print(f"[DEBUG] Final Image Path: {image_path}")

    build_news_video(title, audio_path, out_video_path, image_path=image_path)
    return {"title": title, "out_path": out_video_path}


#  NAVIGATION 
class NewsNavigator:
    """
    Maintain index to navigate between news articles from Google Sheet.
    """
    def __init__(self, sheet_key=SHEET_KEY, worksheet=WORKSHEET_NAME, creds=CREDS_FILE):
        self.data = load_google_sheet(sheet_key, worksheet, creds)
        self.index = 0
    def get_current(self): return self.data[self.index] if self.data else None
    def next(self):
        if self.index < len(self.data)-1: self.index += 1
        return self.get_current()
    def prev(self):
        if self.index > 0: self.index -= 1
        return self.get_current()

#  GRADIO UI 
def gradio_main(sheet_key=SHEET_KEY, worksheet=WORKSHEET_NAME, creds=CREDS_FILE):
    nav = NewsNavigator(sheet_key, worksheet, creds)
    def generate(direction="current"):
        row = {"Title":"News","URL":None}
        if direction=="next": row = nav.next()
        elif direction=="prev": row = nav.prev()
        else: row = nav.get_current()
        if not row: return None
        return run_pipeline(row.get("URL"), title=row.get("Title"))["out_path"]

    with gr.Blocks() as demo:
        gr.Markdown("# 📰 News → Video Generator")
        with gr.Row():
            prev_btn = gr.Button("⬅️ Previous")
            gen_btn = gr.Button("🔄 Generate Current")
            next_btn = gr.Button("➡️ Next")
        video_out = gr.Video(label="Generated Video")
        prev_btn.click(fn=lambda: generate("prev"), outputs=[video_out])
        gen_btn.click(fn=lambda: generate("current"), outputs=[video_out])
        next_btn.click(fn=lambda: generate("next"), outputs=[video_out])
    demo.launch()

#  CLI 
def cli_main():
    parser = argparse.ArgumentParser(description="News->Video pipeline with Sheets")
    parser.add_argument("--gradio", action="store_true")
    parser.add_argument("--sheet_key", help="Google Sheet key")
    parser.add_argument("--worksheet", default=WORKSHEET_NAME)
    parser.add_argument("--creds", default=CREDS_FILE)
    args = parser.parse_args()
    sheet_key = args.sheet_key or SHEET_KEY
    if args.gradio: gradio_main(sheet_key, args.worksheet, args.creds)

if __name__ == "__main__":
    cli_main()
