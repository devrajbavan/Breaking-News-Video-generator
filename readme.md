# 📰 News → Video Generator

A Python pipeline that converts news articles from a Google Sheet into engaging videos with headline overlays and AI-generated voice narration. Users can navigate through articles using a simple Gradio interface.

---

## Features

- Fetches news articles (title + URL) from a Google Sheet.
- Extracts article text and top image.
- Summarizes articles using a short rule-based summary.
- Generates text-to-speech narration using gTTS.
- Builds a video with:
  - A header (`BREAKING NEWS`)
  - Highlighted title overlay
  - Background image
- Gradio UI with **Previous / Next / Generate Current** navigation.

---

## Demo Screenshot

![Demo Screenshot](demo_screenshot.png)
*Replace with your own screenshot of the Gradio app.*

---

## Getting Started

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd breaking-news
```

### 2. Set up a virtual environment
```bash
python -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate       # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Google Sheets Setup
1. Create a Google Sheet with columns:  
   - `Title`  
   - `URL`
2. Create a **Service Account** in Google Cloud and download `service_account.json`.
3. Share the Google Sheet with the service account email.
4. Update `news_video_pipeline.py` with your:
```python
SHEET_KEY = "<YOUR_GOOGLE_SHEET_ID>"
CREDS_FILE = "service_account.json"
```

### 5. Run the application
```bash
python news_video_pipeline.py --gradio
```
- Open the Gradio link in your browser.
- Use the **Previous / Next / Generate Current** buttons to navigate and generate videos.

---

## Project Structure
```
breaking-news/
├── news_video_pipeline.py   # Main pipeline script
├── requirements.txt         # Dependencies
├── service_account.json     # Google Sheets credentials
├── README.md                # Project documentation
└── demo_screenshot.png      # Optional: Gradio screenshot
```

---

## Dependencies
Key libraries used:

- `newspaper3k` – Article extraction
- `nltk` – Sentence tokenization
- `gTTS` – Text-to-speech
- `moviepy` – Video generation
- `Pillow` – Image processing
- `gspread` & `oauth2client` – Google Sheets API
- `gradio` – UI interface
- `requests` & `beautifulsoup4` – Web scraping

All dependencies are listed in `requirements.txt`.

---

## Notes
- Videos are saved temporarily in your system’s temp folder.  
- If an article has no top image, the script automatically fetches one using DuckDuckGo search.  
- The title overlay has a highlighted background for better visibility.

---

## License
This project is for educational purposes. You may freely use or modify it for non-commercial purposes.

