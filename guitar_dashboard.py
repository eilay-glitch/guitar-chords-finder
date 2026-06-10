import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json
import os
import tempfile
import subprocess
from pathlib import Path

# ── Optional heavy deps ────────────────────────────────────────────────────────
try:
    import yt_dlp
    YT_DLP_OK = True
except ImportError:
    YT_DLP_OK = False

try:
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

st.set_page_config(page_title="Guitar Chords Finder", page_icon="🎸", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 100%); }
.stTextInput > div > div > input {
    background: #1e1e2e !important; color: #ffffff !important;
    border: 2px solid #f0c040 !important; border-radius: 10px !important; font-size: 1.1rem !important;
}
.stButton > button {
    background: linear-gradient(135deg, #f0c040, #e67e22) !important;
    color: #000 !important; font-weight: bold !important;
    border-radius: 10px !important; font-size: 1rem !important; border: none !important; width: 100%;
}
.stCheckbox > label { color: #f0c040 !important; font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ── CHORD DATABASE ─────────────────────────────────────────────────────────────
CHORDS = {
    "C":     {"diagram": "x32010", "ascii": "e|--0-|\nB|--1-|\nG|--0-|\nD|--2-|\nA|--3-|\nE|--x-|", "level": "beginner"},
    "G":     {"diagram": "320003", "ascii": "e|--3-|\nB|--0-|\nG|--0-|\nD|--0-|\nA|--2-|\nE|--3-|", "level": "beginner"},
    "Am":    {"diagram": "x02210", "ascii": "e|--0-|\nB|--1-|\nG|--2-|\nD|--2-|\nA|--0-|\nE|--x-|", "level": "beginner"},
    "Em":    {"diagram": "022000", "ascii": "e|--0-|\nB|--0-|\nG|--0-|\nD|--2-|\nA|--2-|\nE|--0-|", "level": "beginner"},
    "D":     {"diagram": "xx0232", "ascii": "e|--2-|\nB|--3-|\nG|--2-|\nD|--0-|\nA|--x-|\nE|--x-|", "level": "beginner"},
    "Dm":    {"diagram": "xx0231", "ascii": "e|--1-|\nB|--3-|\nG|--2-|\nD|--0-|\nA|--x-|\nE|--x-|", "level": "beginner"},
    "E":     {"diagram": "022100", "ascii": "e|--0-|\nB|--0-|\nG|--1-|\nD|--2-|\nA|--2-|\nE|--0-|", "level": "beginner"},
    "A":     {"diagram": "x02220", "ascii": "e|--0-|\nB|--2-|\nG|--2-|\nD|--2-|\nA|--0-|\nE|--x-|", "level": "beginner"},
    "F":     {"diagram": "133211", "ascii": "e|--1-|\nB|--1-|\nG|--2-|\nD|--3-|\nA|--3-|\nE|--1-|", "level": "intermediate"},
    "Bm":    {"diagram": "x24432", "ascii": "e|--2-|\nB|--3-|\nG|--4-|\nD|--4-|\nA|--2-|\nE|--x-|", "level": "intermediate"},
    "G7":    {"diagram": "320001", "ascii": "e|--1-|\nB|--0-|\nG|--0-|\nD|--0-|\nA|--2-|\nE|--3-|", "level": "intermediate"},
    "C7":    {"diagram": "x32310", "ascii": "e|--0-|\nB|--1-|\nG|--3-|\nD|--2-|\nA|--3-|\nE|--x-|", "level": "intermediate"},
    "Am7":   {"diagram": "x02010", "ascii": "e|--0-|\nB|--1-|\nG|--0-|\nD|--2-|\nA|--0-|\nE|--x-|", "level": "intermediate"},
    "Em7":   {"diagram": "020000", "ascii": "e|--0-|\nB|--0-|\nG|--0-|\nD|--2-|\nA|--0-|\nE|--0-|", "level": "intermediate"},
    "Fmaj7": {"diagram": "x33210", "ascii": "e|--0-|\nB|--1-|\nG|--2-|\nD|--3-|\nA|--3-|\nE|--x-|", "level": "intermediate"},
    "D7":    {"diagram": "xx0212", "ascii": "e|--2-|\nB|--1-|\nG|--2-|\nD|--0-|\nA|--x-|\nE|--x-|", "level": "intermediate"},
    "Cadd9": {"diagram": "x32033", "ascii": "e|--3-|\nB|--3-|\nG|--0-|\nD|--2-|\nA|--3-|\nE|--x-|", "level": "intermediate"},
    "Gmaj7": {"diagram": "320002", "ascii": "e|--2-|\nB|--0-|\nG|--0-|\nD|--0-|\nA|--2-|\nE|--3-|", "level": "extreme"},
    "F#m":   {"diagram": "244222", "ascii": "e|--2-|\nB|--2-|\nG|--2-|\nD|--4-|\nA|--4-|\nE|--2-|", "level": "extreme"},
    "B":     {"diagram": "x24442", "ascii": "e|--2-|\nB|--4-|\nG|--4-|\nD|--4-|\nA|--2-|\nE|--x-|", "level": "extreme"},
    "Bb":    {"diagram": "x13331", "ascii": "e|--1-|\nB|--3-|\nG|--3-|\nD|--3-|\nA|--1-|\nE|--x-|", "level": "extreme"},
    "Dm7":   {"diagram": "xx0211", "ascii": "e|--1-|\nB|--1-|\nG|--2-|\nD|--0-|\nA|--x-|\nE|--x-|", "level": "extreme"},
    "G#m":   {"diagram": "466444", "ascii": "e|--4-|\nB|--4-|\nG|--4-|\nD|--6-|\nA|--6-|\nE|--4-|", "level": "extreme"},
    "Eb":    {"diagram": "x68886", "ascii": "e|--6-|\nB|--8-|\nG|--8-|\nD|--8-|\nA|--6-|\nE|--x-|", "level": "extreme"},
}

KEY_PROGRESSIONS = {
    "C": ["C","Am","F","G"], "G": ["G","Em","C","D"],
    "D": ["D","Bm","G","A"], "A": ["A","F#m","D","E"],
    "E": ["E","C#m","A","B"], "Am": ["Am","F","C","G"], "Em": ["Em","C","G","D"],
}
BEGINNER_SUBS    = {"F#m":"Em","C#m":"Am","B":"G","Eb":"E","Bb":"A","G#m":"Em","Bm":"Am"}
EXTREME_UPGRADES = {"C":"Cadd9","G":"Gmaj7","Am":"Am7","Em":"Em7","F":"Fmaj7","D":"D7"}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}

CHORD_RE = re.compile(
    r'[A-G][b#]?(?:m|maj7?|min|7|sus[24]?|add9|dim|aug|6|9)?(?:/[A-G][b#]?)?'
)
CHORD_LINE_RE = re.compile(
    r'^[\s]*([A-G][b#]?(?:m|maj7?|min|7|sus[24]?|add9|dim|aug|6|9)?(?:/[A-G][b#]?)?)'
    r'(?:\s+[A-G][b#]?(?:m|maj7?|min|7|sus[24]?|add9|dim|aug|6|9)?(?:/[A-G][b#]?)?)*\s*$'
)


def adapt_chords(chords, level):
    out = []
    for ch in chords:
        if level == "beginner":
            ch = BEGINNER_SUBS.get(ch, ch)
            if CHORDS.get(ch, {}).get("level") in ("intermediate", "extreme"):
                ch = "C"
        elif level == "extreme":
            ch = EXTREME_UPGRADES.get(ch, ch)
        out.append(ch)
    return out


def is_hebrew(text):
    return bool(re.search(r'[֐-׿]', text))


# ── YOUTUBE SEARCH ─────────────────────────────────────────────────────────────
def youtube_search(query):
    for search_q in [query + " מילים", query + " lyrics", query + " guitar chords"]:
        try:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(search_q)
            r = requests.get(url, headers=HEADERS, timeout=10)
            ids    = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
            titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"', r.text)
            if ids:
                return {"video_id": ids[0], "title": titles[0] if titles else query}
        except Exception:
            pass
    return None


def get_youtube_description(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        match = re.search(r'"description":\{"runs":\[(.*?)\]\}', r.text, re.DOTALL)
        if match:
            texts = re.findall(r'"text":"((?:[^"\\]|\\.)*)"', match.group(1))
            desc = "".join(t.encode().decode("unicode_escape", errors="replace") for t in texts)
            if len(desc) > 80:
                return desc
        match2 = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', r.text)
        if match2:
            desc = match2.group(1).replace("\\n", "\n").replace('\\"', '"')
            if len(desc) > 80:
                return desc
    except Exception:
        pass
    return ""


# ── LYRICS EXTRACTION ──────────────────────────────────────────────────────────
def _is_lyric_line(line):
    s = line.strip()
    if not s:
        return False
    if re.search(r'https?://|www\.', s, re.IGNORECASE):
        return False
    if re.search(r'0\d[\d\-]{7,}', s):
        return False
    if re.match(r'^\s*\d{1,2}:\d{2}', s):
        return False
    colon_pos = s.find(':')
    if colon_pos != -1 and colon_pos < len(s) * 0.6:
        return False
    if re.search(r'[@#]\w', s):
        return False
    credit_kw = re.compile(
        r'(ניהול|הפצה|יחסי\s*ציבור|להזמנת|ייצוג|הפקות|הפקה\s*דיגיטלית|'
        r'מיקס|מאסטר|עיבוד\s*מוסיקלי|עיבוד\s*והפקה|'
        r'subscribe|copyright|℗|©|all rights|'
        r'spotify|apple\s*music|itunes|soundcloud|deezer|'
        r'instagram|facebook|tiktok|twitter|whatsapp|'
        r'produced\s*by|mixed\s*by|mastered\s*by|'
        r'follow\s*us|stream\s*now|download|available\s*on)',
        re.IGNORECASE
    )
    if credit_kw.search(s):
        return False
    if re.match(r'^[\-–—=*~_•\s]{3,}$', s):
        return False
    if len(s) > 85 or len(s) < 3:
        return False
    return True


def extract_lyrics_from_description(desc):
    raw_lines = desc.splitlines()
    is_lyric = []
    for line in raw_lines:
        if not line.strip():
            is_lyric.append(None)
        else:
            is_lyric.append(_is_lyric_line(line))

    best_start, best_end = 0, 0
    cur_start = None
    consecutive = 0
    for i, val in enumerate(is_lyric):
        if val is True:
            if cur_start is None:
                cur_start = i
            consecutive += 1
        elif val is None and cur_start is not None:
            pass
        else:
            if cur_start is not None and consecutive > (best_end - best_start):
                best_start, best_end = cur_start, i
            cur_start = None
            consecutive = 0
    if cur_start is not None and consecutive > (best_end - best_start):
        best_start, best_end = cur_start, len(raw_lines)

    block = raw_lines[best_start:best_end]
    while block and not block[0].strip():
        block.pop(0)
    while block and not block[-1].strip():
        block.pop()
    text = "\n".join(block).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def get_lyrics_only(song, video_id=None):
    if video_id:
        desc = get_youtube_description(video_id)
        if desc:
            clean = extract_lyrics_from_description(desc)
            if len(clean.splitlines()) >= 4:
                return clean
    try:
        for suffix in [" מילים", " lyrics official"]:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(song + suffix)
            r = requests.get(url, headers=HEADERS, timeout=8)
            ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
            if ids:
                desc = get_youtube_description(ids[0])
                if desc:
                    clean = extract_lyrics_from_description(desc)
                    if len(clean.splitlines()) >= 4:
                        return clean
                break
    except Exception:
        pass
    try:
        google_url = f"https://www.google.com/search?q={urllib.parse.quote(song + ' site:genius.com lyrics')}"
        r = requests.get(google_url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        genius_links = [
            a["href"] for a in soup.find_all("a", href=True)
            if "genius.com" in a["href"] and "/lyrics/" in a["href"]
        ]
        if genius_links:
            link = genius_links[0].split("&")[0].replace("/url?q=", "")
            r2 = requests.get(link, headers=HEADERS, timeout=10)
            soup2 = BeautifulSoup(r2.text, "html.parser")
            containers = soup2.find_all("div", {"data-lyrics-container": "true"})
            if containers:
                lines = []
                for c in containers:
                    for br in c.find_all("br"):
                        br.replace_with("\n")
                    lines.append(c.get_text())
                return "\n".join(lines)
    except Exception:
        pass
    return ""


# ── CHORD SCRAPING ─────────────────────────────────────────────────────────────
def parse_chord_lyric_text(text):
    """Parse alternating chord/lyric lines from plain text."""
    lines = [l for l in text.splitlines() if l.strip()]
    paired = []
    all_chords = []
    i = 0
    while i < len(lines) - 1:
        line = lines[i].rstrip()
        if CHORD_LINE_RE.match(line) and len(line.strip()) <= 60:
            chords_in_line = CHORD_RE.findall(line)
            lyric = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if lyric and not CHORD_LINE_RE.match(lyric):
                paired.append({"chord_line": line, "lyric_line": lyric, "chords": chords_in_line})
                all_chords.extend(chords_in_line)
                i += 2
                continue
        i += 1
    if len(paired) < 3:
        return None, []
    unique = list(dict.fromkeys(all_chords))
    return unique[:8], paired[:40]


def parse_tab_html(html):
    """Parse HTML from any tab site — extract chord+lyric pairs."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    return parse_chord_lyric_text(text)


def get_chords_from_tab4u(song):
    """Scrape tab4u.com — primary source for Hebrew songs."""
    try:
        q = urllib.parse.quote(song)
        r = requests.get(
            f"https://www.tab4u.com/resultsSimple?tab=songs&q={q}",
            headers=HEADERS, timeout=8
        )
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if "/tabs/songs/" in a["href"]:
                song_url = "https://www.tab4u.com" + a["href"]
                r2 = requests.get(song_url, headers=HEADERS, timeout=8)
                # tab4u stores chords in <span class="chord">
                soup2 = BeautifulSoup(r2.text, "html.parser")
                # Rebuild text with chord markers
                content = soup2.find("pre") or soup2.find("div", class_=re.compile(r'song|tab|chord'))
                if content:
                    result = parse_chord_lyric_text(content.get_text("\n"))
                    if result[0]:
                        return result
                # Fallback: full page parse
                result = parse_tab_html(r2.text)
                if result[0]:
                    return result
                break
    except Exception:
        pass
    return None, []


def get_chords_from_e_chords(song):
    """Try e-chords.com."""
    try:
        q = urllib.parse.quote(song + " chords")
        r = requests.get(
            f"https://www.e-chords.com/search-chord/{q}",
            headers=HEADERS, timeout=8
        )
        soup = BeautifulSoup(r.text, "html.parser")
        # Get first result
        for a in soup.find_all("a", href=re.compile(r'/chords/')):
            r2 = requests.get("https://www.e-chords.com" + a["href"], headers=HEADERS, timeout=8)
            result = parse_tab_html(r2.text)
            if result[0]:
                return result
            break
    except Exception:
        pass
    return None, []


def get_chords_and_lyrics_from_web(song):
    """
    Try multiple sources in order of reliability.
    Hebrew songs: tab4u first.
    English songs: chordu → e-chords → Google.
    """
    # Hebrew songs → tab4u first
    if is_hebrew(song):
        result = get_chords_from_tab4u(song)
        if result[0]:
            return result

    # Try chordu.com
    try:
        slug = song.replace(" ", "-").lower()
        r = requests.get(f"https://chordu.com/chords-tabs-{slug}", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            result = parse_tab_html(r.text)
            if result[0]:
                return result
    except Exception:
        pass

    # Try e-chords
    result = get_chords_from_e_chords(song)
    if result[0]:
        return result

    # Google → chord sites
    try:
        q = urllib.parse.quote(song + " guitar chords tab site:chordu.com OR site:e-chords.com OR site:mychordbook.com")
        r = requests.get(f"https://www.google.com/search?q={q}", headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            for domain in ["chordu.com", "e-chords.com", "mychordbook.com", "tab4u.com"]:
                if domain in href:
                    link = href.split("&")[0].replace("/url?q=", "")
                    try:
                        r2 = requests.get(link, headers=HEADERS, timeout=8)
                        result = parse_tab_html(r2.text)
                        if result[0]:
                            return result
                    except Exception:
                        pass
    except Exception:
        pass

    # English songs → tab4u as last resort
    if not is_hebrew(song):
        result = get_chords_from_tab4u(song)
        if result[0]:
            return result

    return None, []


def get_basic_chords(song):
    """
    Search Google specifically for this song's chords.
    Require at least 2 of the same chord to appear — avoids picking up random mentions.
    """
    try:
        r = requests.get(
            f"https://www.google.com/search?q={urllib.parse.quote(song + ' guitar chords')}",
            headers=HEADERS, timeout=8
        )
        found = CHORD_RE.findall(r.text)
        # Count occurrences — only keep chords that appear 2+ times in context
        counts = {}
        for c in found:
            if c in CHORDS:
                counts[c] = counts.get(c, 0) + 1
        # Sort by frequency, take top 6
        ranked = sorted(counts, key=lambda x: -counts[x])
        result = [c for c in ranked if counts[c] >= 2][:6]
        if len(result) >= 3:
            return result
    except Exception:
        pass
    return []


# ── YOUTUBE CAPTIONS (for karaoke sync) ───────────────────────────────────────
def parse_vtt_time(t):
    parts = t.split(":")
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2].replace(",", "."))
    return h * 3600 + m * 60 + s


def parse_vtt(vtt_text):
    """Parse VTT captions → list of (start_sec, end_sec, text)."""
    cues = []
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r'(\d+:\d+:\d+[\.,]\d+)\s*-->\s*(\d+:\d+:\d+[\.,]\d+)', lines[i].strip())
        if m:
            start = parse_vtt_time(m.group(1))
            end   = parse_vtt_time(m.group(2))
            i += 1
            text_parts = []
            while i < len(lines) and lines[i].strip():
                clean = re.sub(r'<[^>]+>', '', lines[i]).strip()
                if clean:
                    text_parts.append(clean)
                i += 1
            if text_parts:
                cues.append((start, end, " ".join(text_parts)))
        else:
            i += 1
    return cues


def get_captions_from_youtube(video_id):
    """
    Fetch auto-captions directly from YouTube's timedtext API — no yt-dlp needed.
    Tries Hebrew then English.
    """
    for lang in ["iw", "he", "en"]:
        try:
            url = f"https://www.youtube.com/api/timedtext?v={video_id}&lang={lang}&fmt=vtt"
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200 and "-->)" not in r.text and len(r.text) > 100:
                cues = parse_vtt(r.text)
                if cues:
                    return cues
        except Exception:
            pass
    # Fallback: try fetching caption tracks list
    try:
        r = requests.get(
            f"https://www.youtube.com/watch?v={video_id}", headers=HEADERS, timeout=10
        )
        tracks = re.findall(r'"captionTracks":\[(.*?)\]', r.text)
        if tracks:
            urls = re.findall(r'"baseUrl":"([^"]+)"', tracks[0])
            for u in urls[:3]:
                u = u.replace("\\u0026", "&") + "&fmt=vtt"
                r2 = requests.get(u, headers=HEADERS, timeout=8)
                if r2.status_code == 200:
                    cues = parse_vtt(r2.text)
                    if cues:
                        return cues
    except Exception:
        pass
    return []


def get_captions_yt_dlp(video_id):
    """Download auto-generated captions via yt-dlp. Returns list of (start, end, text)."""
    if not YT_DLP_OK:
        return []
    with tempfile.TemporaryDirectory() as tmpdir:
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {
            "writeautomaticsub": True,
            "subtitleslangs": ["he", "iw", "en", "en-US"],
            "subtitlesformat": "vtt",
            "skip_download": True,
            "outtmpl": os.path.join(tmpdir, "cap"),
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            for f in Path(tmpdir).glob("cap*.vtt"):
                return parse_vtt(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


# ── VOCAL SEPARATION ───────────────────────────────────────────────────────────
def download_audio_yt_dlp(video_id, out_dir):
    """Download audio as WAV. Returns path or None."""
    if not YT_DLP_OK:
        return None, "יש להתקין yt-dlp:  pip install yt-dlp"
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "audio.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        for f in Path(out_dir).glob("audio.wav"):
            return str(f), None
        # Some formats keep original ext
        for f in Path(out_dir).glob("audio.*"):
            return str(f), None
        return None, "לא נמצא קובץ אודיו לאחר ההורדה"
    except Exception as e:
        return None, f"שגיאת הורדה: {e}"


def separate_vocals_demucs(audio_path, out_dir):
    """
    Run demucs --two-stems=vocals on the audio.
    Returns (no_vocals_path, error_str).
    """
    try:
        result = subprocess.run(
            ["python", "-m", "demucs", "--two-stems=vocals", "-o", out_dir, audio_path],
            capture_output=True, timeout=600, text=True
        )
        if result.returncode != 0:
            return None, "demucs לא מותקן. הרץ:  pip install demucs"
        for f in Path(out_dir).rglob("no_vocals.wav"):
            return str(f), None
        return None, "לא מצאנו את פלט demucs"
    except FileNotFoundError:
        return None, "demucs לא מותקן. הרץ:  pip install demucs"
    except subprocess.TimeoutExpired:
        return None, "העיבוד לקח יותר מדי זמן (timeout)"
    except Exception as e:
        return None, str(e)


# ── KARAOKE VIDEO CREATION ─────────────────────────────────────────────────────
def _make_frame(W, H, bg, prev_text, curr_text, next_text):
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    font_curr = font_ctx = None
    for name in ["arial.ttf", "ArialUnicode.ttf", "NotoSans-Regular.ttf"]:
        try:
            font_curr = ImageFont.truetype(name, 56)
            font_ctx  = ImageFont.truetype(name, 34)
            break
        except Exception:
            pass
    if font_curr is None:
        font_curr = font_ctx = ImageFont.load_default()

    if prev_text:
        draw.text((W // 2, H // 2 - 100), prev_text, font=font_ctx,
                  fill=(90, 90, 110), anchor="mm")
    if curr_text:
        draw.text((W // 2, H // 2), curr_text, font=font_curr,
                  fill=(240, 192, 64), anchor="mm")
    if next_text:
        draw.text((W // 2, H // 2 + 100), next_text, font=font_ctx,
                  fill=(90, 90, 110), anchor="mm")

    return np.array(img)


def create_karaoke_video(captions, audio_path, output_path):
    """
    Create an MP4 karaoke video: instrumental audio + animated lyrics.
    captions: list of (start, end, text)
    Returns output_path on success, None on failure.
    """
    if not MOVIEPY_OK:
        return None
    try:
        W, H = 1280, 720
        BG = (13, 13, 26)
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        clips = []
        prev_end = 0.0

        for idx, (start, end, text) in enumerate(captions):
            if start > prev_end + 0.05:
                img = _make_frame(W, H, BG, "", "", "")
                clips.append(ImageClip(img).set_duration(start - prev_end))

            prev_t = captions[idx - 1][2] if idx > 0 else ""
            next_t = captions[idx + 1][2] if idx < len(captions) - 1 else ""
            img = _make_frame(W, H, BG, prev_t, text, next_t)
            clips.append(ImageClip(img).set_duration(max(end - start, 0.1)))
            prev_end = end

        if prev_end < duration:
            img = _make_frame(W, H, BG, "", "", "")
            clips.append(ImageClip(img).set_duration(duration - prev_end))

        video = concatenate_videoclips(clips).set_audio(audio)
        video.write_videofile(output_path, fps=24, codec="libx264",
                              audio_codec="aac", verbose=False, logger=None)
        return output_path
    except Exception as e:
        st.error(f"שגיאה ביצירת הווידאו: {e}")
        return None


# ── KARAOKE BROWSER PLAYER (YouTube IFrame API + JS sync) ─────────────────────
def karaoke_player_html(video_id, captions):
    """
    Returns an HTML string that:
    - Embeds the YouTube player (or plays instrumental if provided)
    - Shows three lines of lyrics in real-time via YouTube IFrame API
    """
    caps_json = json.dumps([
        {"s": round(s, 2), "e": round(e, 2), "t": t}
        for s, e, t in captions
    ])
    return f"""
<div style="background:#0d0d1a;padding:16px;border-radius:14px;font-family:Arial,sans-serif">
  <div id="ytplayer-{video_id}"></div>
  <div id="lyric-box" style="
    text-align:center;padding:28px 20px;margin-top:18px;
    background:#111827;border-radius:12px;border-left:4px solid #f0c040;
    min-height:140px;display:flex;flex-direction:column;
    justify-content:center;align-items:center;gap:14px;">
    <div id="prev-l" style="color:#555;font-size:1.1rem;font-style:italic;min-height:1.4em"></div>
    <div id="curr-l" style="color:#f0c040;font-size:2rem;font-weight:bold;min-height:2.4em;
         text-shadow:0 0 20px rgba(240,192,64,0.5)"></div>
    <div id="next-l" style="color:#555;font-size:1.1rem;font-style:italic;min-height:1.4em"></div>
  </div>
  <div style="text-align:center;margin-top:10px;color:#666;font-size:0.8rem">
    ▶ לחץ Play בנגן כדי להפעיל את הסנכרון
  </div>
</div>
<script>
(function() {{
  var captions = {caps_json};
  var player;
  var syncInterval = null;
  var lastIdx = -1;

  function onYouTubeIframeAPIReady() {{
    player = new YT.Player('ytplayer-{video_id}', {{
      height: '340', width: '100%',
      videoId: '{video_id}',
      playerVars: {{rel: 0, modestbranding: 1}},
      events: {{onStateChange: onStateChange}}
    }});
  }}
  window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady;

  function onStateChange(e) {{
    if (e.data === 1) {{  // PLAYING
      if (!syncInterval) syncInterval = setInterval(sync, 80);
    }} else {{
      clearInterval(syncInterval); syncInterval = null;
    }}
  }}

  function sync() {{
    if (!player || !player.getCurrentTime) return;
    var t = player.getCurrentTime();
    var idx = -1;
    for (var i = 0; i < captions.length; i++) {{
      if (captions[i].s <= t && captions[i].e >= t) {{ idx = i; break; }}
    }}
    if (idx === lastIdx) return;
    lastIdx = idx;
    document.getElementById('curr-l').textContent = idx >= 0 ? captions[idx].t : '';
    document.getElementById('prev-l').textContent = idx > 0 ? captions[idx-1].t : '';
    document.getElementById('next-l').textContent =
      (idx >= 0 && idx < captions.length-1) ? captions[idx+1].t : '';
  }}

  if (!window.YT) {{
    var tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
  }} else {{
    onYouTubeIframeAPIReady();
  }}
}})();
</script>
"""


def karaoke_lyrics_animated_html(lyrics_lines, total_duration_estimate=240):
    """
    Fallback karaoke display when no caption timestamps are available.
    Words cycle with a CSS animation based on estimated timing.
    """
    lines = [l for l in lyrics_lines if l.strip()]
    if not lines:
        return ""
    sec_per_line = max(2.0, total_duration_estimate / max(len(lines), 1))
    items_html = ""
    for i, line in enumerate(lines):
        delay = i * sec_per_line
        items_html += f"""
        <div class="kline" style="animation-delay:{delay:.1f}s;animation-duration:{sec_per_line:.1f}s">
          {line}
        </div>"""
    return f"""
<style>
@keyframes kfade {{
  0%   {{ opacity:0; color:#555; font-size:1rem; }}
  10%  {{ opacity:1; color:#f0c040; font-size:2rem; text-shadow:0 0 20px rgba(240,192,64,.6); }}
  70%  {{ opacity:1; color:#f0c040; font-size:2rem; }}
  100% {{ opacity:0; color:#555; font-size:1rem; }}
}}
.kline {{
  position:absolute; left:0; right:0; text-align:center;
  font-family:Arial,sans-serif; font-weight:bold;
  opacity:0; animation: kfade linear 1 both;
  top:50%; transform:translateY(-50%);
}}
</style>
<div style="
  background:#0d0d1a; border-left:4px solid #f0c040; border-radius:12px;
  height:180px; position:relative; overflow:hidden; margin-top:16px;">
  {items_html}
</div>
<p style="color:#666;font-size:0.8rem;margin-top:6px;text-align:center">
  * הצגת מילים משוערת — ללא כתוביות מ-YouTube
</p>
"""


# ── CHORD BOX RENDERER ─────────────────────────────────────────────────────────
def chord_box_html(name):
    data = CHORDS.get(name)
    if not data:
        return ""
    ascii_escaped = data["ascii"].replace("\n", "<br>")
    return f"""
<div style="background:#1e1e2e;border:2px solid #f0c040;border-radius:12px;
    padding:14px 18px;margin:6px 4px;text-align:center;
    font-family:monospace;color:#fff;display:inline-block;min-width:120px;vertical-align:top;">
  <div style="font-size:1.3rem;font-weight:bold;color:#f0c040;margin-bottom:8px">{name}</div>
  <div style="font-size:0.72rem;color:#aaa;line-height:1.5;text-align:left">{ascii_escaped}</div>
  <div style="font-size:0.65rem;color:#666;margin-top:6px">{data['diagram']}</div>
</div>"""


# ── CHORD SHEET RENDERER ───────────────────────────────────────────────────────
def render_chord_sheet(paired_lines, known_chords):
    html_parts = ["""
<div style="background:#111827;border-left:4px solid #f0c040;border-radius:10px;
    padding:24px 28px;font-family:'Courier New',monospace;
    max-height:600px;overflow-y:auto;line-height:1.4;">
"""]
    for item in paired_lines:
        def color_chord(m):
            ch = m.group(0)
            color = "#f0c040" if ch in known_chords else "#e07020"
            return f'<span style="color:{color};font-weight:bold">{ch}</span>'
        colored = re.sub(CHORD_RE, color_chord, item["chord_line"])
        html_parts.append(
            f'<div style="white-space:pre;min-height:1.4em">{colored}</div>'
            f'<div style="white-space:pre;color:#e0e0e0;margin-bottom:10px">{item["lyric_line"]}</div>'
        )
    html_parts.append("</div>")
    return "".join(html_parts)


# ══════════════════════════════════════════════════════════════════════════════
# ── UI ─────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    "<h1 style='color:#f0c040;text-align:center;font-size:2.6rem'>🎸 Guitar Chords Finder</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#aaa;font-size:1.05rem'>"
    "הקלד שם שיר ► אקורדים מעל המילים + YouTube + קריוקי</p>",
    unsafe_allow_html=True,
)

# ── KARAOKE TOGGLE (before everything else) ────────────────────────────────────
st.markdown(
    "<div style='background:#1a1a2e;border:2px solid #9b59b6;border-radius:12px;"
    "padding:14px 20px;margin-bottom:18px'>",
    unsafe_allow_html=True,
)
karaoke_mode = st.checkbox(
    "🎤 מצב קריוקי — הסר את קול הזמר והצג מילים מסונכרנות",
    value=False,
)
if karaoke_mode:
    st.markdown(
        "<p style='color:#9b59b6;font-size:0.9rem;margin:4px 0 0 28px'>"
        "יוריד את האודיו, יפריד את הווקאל ויצור תצוגת קריוקי + וידאו להורדה</p>",
        unsafe_allow_html=True,
    )
    if not YT_DLP_OK:
        st.warning("⚠️ yt-dlp לא מותקן — הסרת הווקאל לא תעבוד. הרץ:  pip install yt-dlp")
st.markdown("</div>", unsafe_allow_html=True)

col_search, col_level = st.columns([3, 1])
with col_search:
    song_input = st.text_input(
        "", placeholder="🎵  שם שיר + אמן  (לדוגמה: Wonderwall Oasis)",
        label_visibility="collapsed",
    )
with col_level:
    level_map   = {"🟢 מתחיל": "beginner", "🟠 מתקדם": "intermediate", "🔴 אקסטרים": "extreme"}
    level_label = st.radio("רמת קושי", list(level_map.keys()), horizontal=False)
    level       = level_map[level_label]

search_btn = st.button("🔍 חפש אקורדים")

if search_btn and song_input.strip():
    song = song_input.strip()

    with st.spinner("מחפש אקורדים ומילים..."):
        yt = youtube_search(song)
        video_id = yt["video_id"] if yt else None

        chords_raw, paired = get_chords_and_lyrics_from_web(song)
        if not chords_raw:
            chords_raw = get_basic_chords(song)
        if not chords_raw:
            # Last resort — detect key from song name clues or default
            chords_raw = KEY_PROGRESSIONS.get("Am", ["Am", "F", "C", "G"])

        chords = adapt_chords(chords_raw, level)

        # Adapt chords inside paired lines
        adapted_paired = []
        for item in paired:
            new_chords = adapt_chords(item["chords"], level)
            counter = [0]
            def replacer(m, _nc=new_chords, _c=counter):
                replacement = _nc[_c[0]] if _c[0] < len(_nc) else m.group(0)
                _c[0] += 1
                return replacement
            new_chord_line = re.sub(CHORD_RE, replacer, item["chord_line"])
            adapted_paired.append({
                "chord_line": new_chord_line,
                "lyric_line": item["lyric_line"],
                "chords": new_chords,
            })

        lyrics = ""
        if not adapted_paired:
            lyrics = get_lyrics_only(song, video_id=video_id)

    # ── KARAOKE PROCESSING ─────────────────────────────────────────────────────
    instrumental_path = None
    captions = []

    if karaoke_mode and video_id:
        with st.spinner("🎤 מביא כתוביות לסנכרון מילים..."):
            captions = get_captions_from_youtube(video_id)
            if not captions:
                captions = get_captions_yt_dlp(video_id)

        if YT_DLP_OK:
            tmpdir = tempfile.mkdtemp()
            with st.spinner("🎵 מוריד אודיו מ-YouTube..."):
                audio_path, err = download_audio_yt_dlp(video_id, tmpdir)

            if audio_path:
                with st.spinner("🤖 מפריד את הווקאל (demucs AI) — עשוי לקחת 2-5 דקות..."):
                    instrumental_path, sep_err = separate_vocals_demucs(audio_path, tmpdir)
                if sep_err:
                    st.info(f"💡 הסרת ווקאל לא זמינה בענן: {sep_err}")
            elif err:
                st.info("💡 הורדת אודיו חסומה בענן — הקריוקי יעבוד עם הנגן הרגיל")

    # ── YOUTUBE / KARAOKE PLAYER ───────────────────────────────────────────────
    st.markdown("---")

    if karaoke_mode and video_id:
        st.markdown("<h3 style='color:#9b59b6'>🎤 קריוקי — מילים מסונכרנות</h3>",
                    unsafe_allow_html=True)

        if captions:
            # Full sync via YouTube IFrame API
            components.html(karaoke_player_html(video_id, captions), height=570)
        else:
            # No captions — show the YouTube video + animated fallback
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            st.markdown(
                f'<iframe width="100%" height="340" src="{embed_url}" '
                f'frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>',
                unsafe_allow_html=True,
            )
            st.caption("⚠️ לא נמצאו כתוביות — מוצגות המילים ללא סנכרון מדויק")
            lyric_source = [l["lyric_line"] for l in adapted_paired] if adapted_paired else (lyrics.splitlines() if lyrics else [])
            if lyric_source:
                components.html(karaoke_lyrics_animated_html(lyric_source), height=220)

        # Instrumental download
        if instrumental_path and os.path.exists(instrumental_path):
            st.markdown("<h4 style='color:#9b59b6'>🎵 מוזיקה ללא ווקאל</h4>",
                        unsafe_allow_html=True)
            with open(instrumental_path, "rb") as f:
                st.download_button(
                    "⬇️ הורד מוזיקה (ללא זמר)",
                    data=f.read(),
                    file_name=f"{song}_instrumental.wav",
                    mime="audio/wav",
                )

            # Create karaoke video
            if captions and MOVIEPY_OK:
                video_path = os.path.join(tempfile.mkdtemp(), "karaoke.mp4")
                with st.spinner("🎬 יוצר וידאו קריוקי..."):
                    result_path = create_karaoke_video(captions, instrumental_path, video_path)
                if result_path and os.path.exists(result_path):
                    with open(result_path, "rb") as f:
                        st.download_button(
                            "⬇️ הורד וידאו קריוקי (MP4)",
                            data=f.read(),
                            file_name=f"{song}_karaoke.mp4",
                            mime="video/mp4",
                        )
            elif captions and not MOVIEPY_OK:
                st.info("💡 להורדת וידאו קריוקי התקן:  pip install moviepy pillow")

    else:
        # Normal YouTube embed
        col_vid, col_info = st.columns([2, 1])
        with col_vid:
            st.markdown("<h3 style='color:#f0c040'>📺 YouTube</h3>", unsafe_allow_html=True)
            if yt:
                embed_url = f"https://www.youtube.com/embed/{yt['video_id']}"
                st.markdown(
                    f'<iframe width="100%" height="340" src="{embed_url}" '
                    f'frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>',
                    unsafe_allow_html=True,
                )
                st.caption(yt["title"])
            else:
                yt_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(song + " guitar chords")
                st.markdown(f"[🔗 חפש ב-YouTube]({yt_url})")

        with col_info:
            st.markdown("<h3 style='color:#f0c040'>ℹ️ מידע</h3>", unsafe_allow_html=True)
            st.markdown(f"**שיר:** {song}")
            badge_color = {"beginner": "#2ecc71", "intermediate": "#f39c12", "extreme": "#e74c3c"}[level]
            badge_text  = {"beginner": "🟢 מתחיל", "intermediate": "🟠 מתקדם", "extreme": "🔴 אקסטרים"}[level]
            st.markdown(
                f'<span style="background:{badge_color};color:#000;padding:4px 14px;'
                f'border-radius:20px;font-weight:bold;font-size:0.85rem">{badge_text}</span>',
                unsafe_allow_html=True,
            )
            st.markdown("")
            tips = {
                "beginner":     "💡 לך לאט בין האקורדים, תתרגל כל מעבר בנפרד.",
                "intermediate": "💡 השתמש ב-capo להקל על barre chords.",
                "extreme":      "💡 שים לב לאצבעות — אקורדים מורכבים דורשים סבלנות.",
            }
            st.info(tips[level])
            ug_url = "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + urllib.parse.quote(song)
            st.markdown(f"[🎸 Ultimate Guitar]({ug_url})")

    # ── CHORD DIAGRAMS ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("<h3 style='color:#f0c040'>🎸 דיאגרמות אקורדים</h3>", unsafe_allow_html=True)
    boxes_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">'
    for ch in chords:
        boxes_html += chord_box_html(ch)
    boxes_html += "</div>"
    st.markdown(boxes_html, unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#aaa;font-family:monospace'>סדר: &nbsp;"
        f"<span style='color:#f0c040;font-weight:bold'>{'  →  '.join(chords)}</span></p>",
        unsafe_allow_html=True,
    )

    # ── CHORD + LYRICS SHEET ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("<h3 style='color:#f0c040'>📝 מילים עם אקורדים</h3>", unsafe_allow_html=True)

    if adapted_paired:
        st.markdown(render_chord_sheet(adapted_paired, chords), unsafe_allow_html=True)

    elif lyrics and lyrics.strip():
        lyric_lines = lyrics.splitlines()
        chord_cycle = chords * 40
        chord_idx = 0
        non_empty_count = 0

        sheet = [
            '<div style="background:#111827;border-left:4px solid #f0c040;border-radius:10px;'
            'padding:24px 28px;font-family:\'Courier New\',monospace;'
            'max-height:650px;overflow-y:auto;line-height:1.5">'
        ]
        for line in lyric_lines:
            stripped = line.strip()
            if not stripped:
                sheet.append('<div style="height:14px"></div>')
                non_empty_count = 0
                continue
            if non_empty_count % 2 == 0:
                c = chord_cycle[chord_idx % len(chord_cycle)]
                chord_idx += 1
                sheet.append(
                    f'<div style="color:#f0c040;font-weight:bold;font-size:0.9rem;'
                    f'letter-spacing:1px;white-space:pre">{c}</div>'
                )
            sheet.append(
                f'<div style="color:#e0e0e0;white-space:pre-wrap;margin-bottom:2px">{stripped}</div>'
            )
            non_empty_count += 1
        sheet.append("</div>")
        st.markdown("".join(sheet), unsafe_allow_html=True)

    else:
        genius_url = "https://genius.com/search?q=" + urllib.parse.quote(song)
        st.warning("לא הצלחנו לשלוף מילים. נסה לחפש ידנית:")
        st.markdown(f"[🔗 חפש מילים ב-Genius]({genius_url})")

elif search_btn:
    st.warning("אנא הכנס שם שיר.")

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#555;font-size:0.8rem'>"
    "🎸 Guitar Chords Finder | Streamlit + YouTube + Genius + Karaoke</p>",
    unsafe_allow_html=True,
)
