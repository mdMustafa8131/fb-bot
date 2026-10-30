import os, re, json, html, time, random, threading
from io import BytesIO
from urllib.parse import urljoin, quote
from functools import lru_cache

import requests, feedparser
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
from flask import (Flask, request, jsonify, render_template_string,
                   send_from_directory, Response)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", BASE)
OUT = os.path.join(DATA, "out")
FONTDIR = os.path.join(BASE, "fonts")
os.makedirs(OUT, exist_ok=True)
os.makedirs(FONTDIR, exist_ok=True)
CFG_FILE = os.path.join(DATA, "config.json")

app = Flask(__name__, static_folder=OUT, static_url_path="/out")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
      "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8"}

GRAPH = "https://graph.facebook.com/v21.0"
REQ_PERMS = ["pages_show_list", "pages_read_engagement", "pages_manage_posts"]
VERSION = "7.0"


# ============================================================ defaults
FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://feeds.feedburner.com/ndtvnews-india-news",
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms",
    "https://feeds.feedburner.com/ndtvmovies-latest",
    "https://indianexpress.com/section/entertainment/feed/",
    "https://www.thehindu.com/entertainment/feeder/default.rss",
    "https://www.hindustantimes.com/feeds/rss/entertainment/rssfeed.xml",
    "https://indianexpress.com/section/politics/feed/",
    "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
    "https://feeds.feedburner.com/ndtvnews-sports-news",
    "https://www.scoopwhoop.com/rss/",
    "https://storypick.com/feed/",
    "https://www.thebetterindia.com/feed/",
    "https://www.bollywoodlife.com/feed/",
    "https://www.filmibeat.com/rss/",
    "https://navbharattimes.indiatimes.com/rssfeedstopstories.cms",
    "https://www.aajtak.in/rssfeeds/?id=home",
    "https://hindi.news18.com/rss/khabar/national.xml",
    "https://theislamicinformation.com/feed/",
    "https://aboutislam.net/feed/",
    "https://www.islamicity.org/feed/",
    "https://www.ummid.com/rss/latest-news.xml",
]

DEFAULT_CATS = {
    "BJP Support": ["bjp", "bharatiya janata", "narendra modi", "modi", "amit shah", "yogi",
                    "nadda", "fadnavis", "rajnath", "smriti", "gadkari", "hindutva", "nda",
                    "ram mandir", "ayodhya", "भाजपा", "मोदी", "योगी", "हिंदुत्व", "अयोध्या"],
    "Congress Support": ["congress", "indian national congress", "rahul", "rahul gandhi",
                         "priyanka", "sonia", "kharge", "upa", "indian alliance", "gehlot",
                         "tharoor", "कांग्रेस", "राहुल", "प्रियंका", "सोनिया", "खड़गे"],
    "BJP Propaganda": ["bjp", "modi", "hindutva", "ram mandir", "vishwaguru", "nda",
                       "vikas", "gujarat model", "new india", "digital india", "chandrayaan",
                       "amrit kaal", "भाजपा", "मोदी सरकार", "विकास", "हिंदुत्व"],
    "Congress Propaganda": ["congress", "rahul", "bharat jodo", "indian alliance", "upa",
                            "opposition", "gathbandhan", "caste census", "kisan", "mgnrega",
                            "कांग्रेस सरकार", "विपक्ष", "गठबंधन", "किसान", "महंगाई"],
    "18+ Bold": ["bold", "glamour", "glamorous", "sizzling", "bikini", "curvy", "hot",
                 "bombshell", "masala", "stunning", "photoshoot", "बोल्ड", "ग्लैमर"],
    "Movies": ["movie", "film", "bollywood", "hollywood", "trailer", "teaser", "box office",
               "release", "review", "cinema", "director", "sequel", "remake", "ott",
               "netflix", "web series", "song", "blockbuster", "फिल्म", "बॉलीवुड", "सिनेमा"],
    "Actress": ["actress", "heroine", "diva", "glamour", "beauty", "nayika",
                "अभिनेत्री", "हीरोइन", "नायिका"],
    "Pakistani Actress": ["pakistani actress", "pakistan actress", "mahira", "sajal",
                          "hania", "ayeza", "saba qamar", "maya ali", "esha gupta",
                          "neelam muneer", "mehwish hayat", "iqra aziz", "yumna zaidi",
                          "पाकिस्तानी", "महिरा", "हानिया"],
    "World Top News": ["world", "global", "international", "usa", "america", "china", "russia",
                       "putin", "israel", "gaza", "palestine", "ukraine", "britain", "japan",
                       "nato", "iran", "saudi", "canada", "दुनिया", "विदेश", "अमेरिका", "रूस"],
    "India Top News": ["india", "delhi", "mumbai", "bengaluru", "chennai", "kolkata",
                       "hyderabad", "pune", "bihar", "maharashtra", "tamil nadu", "kerala",
                       "rajasthan", "uttar pradesh", "gujarat", "assam", "punjab",
                       "भारत", "देश", "दिल्ली", "मुंबई", "बिहार"],
    "Cricket": ["cricket", "ipl", "virat", "kohli", "rohit", "dhoni", "bcci", "world cup",
                "t20", "odi", "team india", "sachin", "tendulkar", "gambhir", "bumrah",
                "jadeja", "hardik", "shubman", "gill", "rishabh", "mandhana",
                "क्रिकेट", "विराट", "आईपीएल", "रोहित", "धोनी", "बीसीसीआई"],
    "Sports": ["sports", "football", "fifa", "olympics", "hockey", "tennis", "kabaddi",
               "badminton", "neeraj", "chopra", "medal", "wwe", "boxing", "wrestling",
               "खेल", "मैच", "फुटबॉल", "ओलंपिक", "कबड्डी", "मेडल"],
    "Islam": ["islam", "islamic", "quran", "hadith", "sunnah", "dua", "namaz", "ramzan",
              "ramadan", "eid", "hajj", "umrah", "masjid", "muslim", "prophet", "jummah",
              "allah", "muharram", "halal", "इस्लाम", "दुआ", "नमाज़", "रमज़ान", "कुरान",
              "ईद", "हज", "मस्जिद", "मुस्लिम", "अल्लाह"],
    "Twitter Trending": [],
    "Viral India": [],
}

PAGE_DEFAULTS = {"fetch_min": 30, "post_min": 45, "post_max": 60, "per_fetch": 2}

DEFAULT = {
    "categories": DEFAULT_CATS,
    "settings": dict(PAGE_DEFAULTS),
    "app": {"id": "", "secret": "", "verified": 0},
    "auth": {"user": "", "pass": ""},
    "pages": [{
        "id": "pg1", "name": "Page 1", "page_id": "", "token": "",
        "token_exp": None, "mode": "news", "auto": False,
        "selected": ["India Top News"], "link": "", "count": 20,
        **PAGE_DEFAULTS,
    }],
}

RT = {}
RT_LOCK = threading.RLock()
FEED_ERR = []


# ============================================================ config
def cfg_load():
    c = {}
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, encoding="utf-8") as f:
                c = json.load(f)
        except Exception:
            c = {}
    if not isinstance(c, dict):
        c = {}

    c.setdefault("categories", dict(DEFAULT_CATS))
    c.setdefault("settings", dict(PAGE_DEFAULTS))
    c.setdefault("app", dict(DEFAULT["app"]))
    c.setdefault("auth", dict(DEFAULT["auth"]))
    c.setdefault("pages", [])

    for k in DEFAULT_CATS:
        c["categories"].setdefault(k, list(DEFAULT_CATS[k]))
    for k, v in PAGE_DEFAULTS.items():
        c["settings"].setdefault(k, v)
    for k in ("id", "secret", "verified"):
        c["app"].setdefault(k, DEFAULT["app"][k])
    for k in ("user", "pass"):
        c["auth"].setdefault(k, "")

    c["app"]["id"] = c["app"]["id"] or os.environ.get("FB_APP_ID", "")
    c["app"]["secret"] = c["app"]["secret"] or os.environ.get("FB_APP_SECRET", "")

    if not c["pages"]:
        c["pages"] = [json.loads(json.dumps(DEFAULT["pages"][0]))]

    for p in c["pages"]:
        p.setdefault("id", "pg" + str(random.randint(100000, 999999)))
        p.setdefault("mode", "news")
        p.setdefault("selected", ["India Top News"])
        p.setdefault("link", "")
        p.setdefault("count", 20)
        p.setdefault("auto", False)
        p.setdefault("token", "")
        p.setdefault("token_exp", None)
        p.setdefault("deeni", False)
        p.setdefault("deeni_min", 45)
        p.setdefault("deeni_max", 60)
        p.setdefault("deeni_msg", "")
        for k, v in PAGE_DEFAULTS.items():
            p.setdefault(k, c["settings"].get(k, v))
    return c


def cfg_save(c):
    tmp = CFG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CFG_FILE)


CFG = cfg_load()
cfg_save(CFG)


# ============================================================ cache + auth
@app.after_request
def no_cache(r):
    if request.path == "/" or request.path.startswith(
            ("/pages", "/pool", "/cats", "/diag", "/ping")):
        r.headers["Cache-Control"] = "no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
    return r


@app.before_request
def _auth():
    u = CFG["auth"].get("user")
    pw = CFG["auth"].get("pass")
    if not u or not pw:
        return
    if request.path.startswith("/out/"):
        return
    a = request.authorization
    if not a or a.username != u or a.password != pw:
        return Response("login required", 401,
                        {"WWW-Authenticate": 'Basic realm="fb-bot"'})


def rts(pid):
    with RT_LOCK:
        return RT.setdefault(pid, {"pool": [], "seen": set(), "posted": [],
                                   "running": False, "fill": False,
                                   "last": "-", "next": "-", "msg": ""})


def get_page(pid):
    for p in CFG["pages"]:
        if p["id"] == pid:
            return p
    return None


def clamp(v, lo, hi, dflt):
    try:
        return max(lo, min(hi, int(v)))
    except Exception:
        return dflt


def mask(t):
    t = t or ""
    return t[:10] + "…" + t[-4:] if len(t) > 18 else ("—" if not t else t)


# ============================================================ text
def is_dev(s):
    return any("\u0900" <= ch <= "\u097f" for ch in s)


def clean(t):
    t = re.sub(r"\s+-\s+[^-]+$", "", t or "").strip()
    return re.sub(r"\s{2,}", " ", t)[:110]


def khit(title, keys):
    tl = title.lower()
    return sum(1 for k in keys if k.lower() in tl)


# ============================================================ fonts
DEV_FONTS = ["font_dev.ttf", "NotoSansDevanagari-Bold.ttf",
             "NotoSansDevanagari-Regular.ttf", "NirmalaB.ttf", "Nirmala.ttf", "mangalb.ttf"]
LAT_FONTS_B = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
LAT_FONTS_R = ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]


@lru_cache(maxsize=96)
def font(sz, bold=False, dev=False):
    names = DEV_FONTS if dev else (LAT_FONTS_B if bold else LAT_FONTS_R)
    dirs = [FONTDIR, BASE, "/usr/share/fonts/truetype/noto",
            "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
            "C:/Windows/Fonts", "/System/Library/Fonts/Supplemental"]
    for n in names:
        for d in dirs:
            try:
                return ImageFont.truetype(os.path.join(d, n), sz)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap(d, text, fnt, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            while d.textlength(w, font=fnt) > maxw and len(w) > 4:
                cut = len(w)
                while cut > 2 and d.textlength(w[:cut], font=fnt) > maxw:
                    cut -= 1
                lines.append(w[:cut])
                w = w[cut:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ============================================================ graph
def app_creds():
    return CFG["app"].get("id", ""), CFG["app"].get("secret", "")


def graph_get(path, tok, **params):
    params["access_token"] = tok
    try:
        return requests.get(f"{GRAPH}/{path}", params=params, timeout=25).json()
    except Exception as e:
        return {"error": {"message": "net: " + str(e)[:60]}}


def long_lived(tok):
    aid, sec = app_creds()
    if not (aid and sec):
        return tok, None, "app credentials missing"
    try:
        j = requests.get(f"{GRAPH}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": aid,
            "client_secret": sec, "fb_exchange_token": tok}, timeout=25).json()
        if j.get("access_token"):
            exp = j.get("expires_in") or 5184000
            return j["access_token"], time.time() + exp, ""
        return tok, None, j.get("error", {}).get("message", "exchange fail")[:80]
    except Exception as e:
        return tok, None, "net: " + str(e)[:60]


def missing_perms(tok):
    j = graph_get("me/permissions", tok)
    if "error" in j:
        return []
    have = {p.get("permission") for p in j.get("data", [])
            if p.get("status") == "granted"}
    return [p for p in REQ_PERMS if p not in have]


def resolve_token(tok):
    j = graph_get("me", tok, fields="id,name")
    if "error" in j:
        return "bad", j["error"].get("message", "invalid token")[:90]

    acc = graph_get("me/accounts", tok, fields="id,name,access_token", limit=200)
    pages = [p for p in (acc.get("data") or []) if p.get("access_token")]
    if pages:
        return "pages", pages

    return "pages", [{"id": j["id"], "name": j.get("name"), "token": tok}]


def add_page_rec(page_id, name, tok, mode, exp=None):
    if any(p["page_id"] == page_id for p in CFG["pages"]):
        return False
    CFG["pages"] = [p for p in CFG["pages"] if p.get("page_id")]
    CFG["pages"].append({
        "id": "pg" + str(int(time.time()))[-6:] + str(random.randint(10, 99)),
        "name": name or "Page", "page_id": page_id, "token": tok, "token_exp": exp,
        "mode": mode if mode in ("news", "fb", "deeni") else "news", "auto": False,
        "selected": ["India Top News"], "link": "", "count": 20,
        "deeni": mode == "deeni", "deeni_min": 45, "deeni_max": 60, "deeni_msg": "",
        **{k: CFG["settings"].get(k, v) for k, v in PAGE_DEFAULTS.items()},
    })
    return True


# ============================================================ fetch helpers
def img_from_entry(e):
    for a in ("media_content", "media_thumbnail"):
        v = getattr(e, a, None)
        if v and isinstance(v, list):
            u = v[0].get("url")
            if u:
                return u
    for l in getattr(e, "links", []) or []:
        t = (l.get("type") or "")
        if t.startswith("image") or l.get("rel") == "enclosure":
            if l.get("href"):
                return l.get("href")
    for en in getattr(e, "enclosures", []) or []:
        if (en.get("type") or "").startswith("image") and en.get("href"):
            return en.get("href")
    d = getattr(e, "description", "") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', d)
    return html.unescape(m.group(1)) if m else None


OG_CACHE = {}


def og_image(link, ttl=3600):
    now = time.time()
    hit = OG_CACHE.get(link)
    if hit and now - hit[1] < ttl:
        return hit[0]
    url = None
    try:
        r = requests.get(link, headers=UA, timeout=20)
        for m in re.finditer(
                r'<meta[^>]+(?:property|name)=["\']og:image(?::secure_url)?["\'][^>]+'
                r'content=["\']([^"\']+)', r.text, re.I):
            u = urljoin(link, html.unescape(m.group(1)))
            if "gstatic" in u or "google.com/images" in u:
                continue
            url = u
            break
    except Exception:
        pass
    OG_CACHE[link] = (url, now)
    return url


def download(url, ref=None, min_side=180, min_bytes=2500):
    if not url:
        return None
    h = dict(UA)
    if ref:
        h["Referer"] = ref
    try:
        r = requests.get(url, headers=h, timeout=35)
        if r.status_code != 200 or "image" not in r.headers.get("content-type", ""):
            return None
        if len(r.content) < min_bytes:
            return None
        im = Image.open(BytesIO(r.content))
        im.load()
        im = im.convert("RGB")
        if min(im.size) < min_side:
            return None
        return im
    except Exception:
        return None


# ============================================================ fb hi-res
FB_STP = re.compile(r"stp=dst-jpg[a-z0-9_\-]*", re.I)
SIZES = ["dst-jpg_p2048x2048", "dst-jpg_s2048x2048", "dst-jpg_p1680x1680",
         "dst-jpg_p1080x1080", "dst-jpg_s1080x1080", "dst-jpg_p960x960",
         "dst-jpg_s960x960", "dst-jpg_p720x720"]


def url_variants(u):
    u = html.unescape(u).replace("&amp;", "&")
    if "scontent" not in u:
        return [u]
    u = re.sub(r"[?&]dl=1", "", u)
    out = []
    for s in SIZES:
        out.append(FB_STP.sub("stp=" + s, u) if FB_STP.search(u)
                   else u + ("&" if "?" in u else "?") + "stp=" + s)
    out.append(FB_STP.sub("", u).replace("?&", "?").replace("&&", "&").rstrip("?&"))
    o = re.sub(r"_n\.jpg", "_o.jpg", u)
    if o != u:
        out.append(o)
    return list(dict.fromkeys(out))


def download_best(urls, ref=None, want=1080):
    best = None
    for u in urls:
        im = download(u, ref)
        if im is None:
            continue
        if best is None or im.size[0] * im.size[1] > best.size[0] * best.size[1]:
            best = im
        if min(best.size) >= want:
            break
    return best


# ============================================================ readers
def _direct(url, timeout):
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""


def _jina(url, timeout):
    try:
        r = requests.get("https://r.jina.ai/" + url, headers=UA, timeout=timeout)
        return r.text.replace("\\/", "/") if r.status_code == 200 else ""
    except Exception:
        return ""


def _allorigins(url, timeout):
    try:
        r = requests.get("https://api.allorigins.win/raw?url=" + quote(url, safe=""),
                         headers=UA, timeout=timeout)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""


def fetch_html(url, timeout=45):
    for fn in (_jina, _allorigins, _direct):
        t = fn(url, timeout)
        if t and len(t) > 600:
            return t
    return ""


SCONTENT = re.compile(r"https://scontent[^)\s\"'\]]+")


def scontent_urls(text):
    return [html.unescape(m.group(0)).rstrip(").,") for m in SCONTENT.finditer(text)]


def fb_link(url):
    url = url.strip()
    if "facebook.com" not in url:
        return url
    if "fbid=" in url:
        return url.split("&")[0]
    if re.search(r"/(photos|photo|media|albums)/", url):
        return url.split("?")[0]
    return url.split("?")[0].rstrip("/") + "/photos"


def jina_photos(link, count):
    url = fb_link(link)
    txt = fetch_html(url)
    pairs = [(u, None) for u in scontent_urls(txt)]

    fids = list(dict.fromkeys(re.findall(r"fbid=(\d+)", txt)))
    for f in fids[:min(count, 15)]:
        if len(pairs) >= count * 2:
            break
        t2 = fetch_html("https://www.facebook.com/photo/?fbid=" + f)
        pairs += [(u, f) for u in scontent_urls(t2)]

    if len(pairs) < count:
        slug = url.split("facebook.com/")[-1]
        for alt in ("https://mbasic.facebook.com/" + slug,
                    "https://m.facebook.com/" + slug):
            pairs += [(u, None) for u in scontent_urls(fetch_html(alt))]
            if len(pairs) >= count:
                break

    seen, out = set(), []
    for u, f in pairs:
        m = re.search(r"/(\d+_\d+_\d+_n)\.jpg", u)
        k = f or (m.group(1) if m else u.split("?")[0])
        if k in seen:
            continue
        seen.add(k)
        out.append((u, f))
    return out[:count]


# ============================================================ image
TARGET = 1080


def enhance(img):
    img = ImageEnhance.Color(img).enhance(1.16)
    img = ImageEnhance.Contrast(img).enhance(1.14)
    img = ImageEnhance.Brightness(img).enhance(1.03)
    return img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=118, threshold=3))


def film_effect(img):
    W, H = img.size
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * 1.04)))
    b = b.point(lambda x: int(x * 0.96))
    img = Image.merge("RGB", (r, g, b))
    img = Image.blend(img, Image.new("RGB", (W, H), (24, 22, 30)), 0.05)
    noise = Image.effect_noise((W, H), 12).convert("RGB")
    noise = noise.filter(ImageFilter.GaussianBlur(0.4))
    img = Image.blend(img, noise, 0.055)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * .28, -H * .28, W * 1.28, H * 1.28], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(max(2, W // 7)))
    return Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), vig)


def prepare(img):
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    s = min(3.2, TARGET / max(w, h))
    if abs(s - 1) > 0.02:
        img = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        if s > 1:
            img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=150, threshold=2))
    img = film_effect(enhance(img))
    W, H = img.size
    ss = 4
    mask = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W * ss - 1, H * ss - 1],
                                           int(W * .026) * ss, fill=255)
    mask = mask.resize((W, H), Image.LANCZOS)
    photo = Image.new("RGB", (W, H), (12, 12, 12))
    photo.paste(img, (0, 0), mask)
    return photo


def save(img, out):
    img.save(out, quality=95, subsampling=0, optimize=True, progressive=True)


def edit_news(img, topic, out, wm=""):
    photo = prepare(img)
    W, H = photo.size
    dev = is_dev(topic)
    fs = max(30, W // 24)
    fb, fw = font(fs, True, dev), font(max(16, W // 62), False, dev)
    probe = ImageDraw.Draw(photo)
    lines = wrap(probe, topic, fb, W - int(W * .08))[:3]
    lh = int(fs * 1.24)
    band = int(fs * .7) + len(lines) * lh
    canvas = Image.new("RGB", (W, H + band), (12, 12, 12))
    canvas.paste(photo, (0, 0))
    d = ImageDraw.Draw(canvas)
    y = H + int(fs * .32)
    for ln in lines:
        d.text((int(W * .045) + 2, y + 2), ln, font=fb, fill=(0, 0, 0))
        d.text((int(W * .045), y), ln, font=fb, fill=(255, 214, 10))
        y += lh
    if wm:
        d.text((W - int(W * .03) - probe.textlength("@" + wm, font=fw),
                H + band - int(fs * .55)), "@" + wm, font=fw, fill=(150, 150, 150))
    save(canvas, out)


def edit_photo(img, out, wm=""):
    photo = prepare(img)
    W, H = photo.size
    if wm:
        d = ImageDraw.Draw(photo)
        fw = font(max(16, W // 62))
        d.text((W - int(W * .03) - d.textlength("@" + wm, font=fw), H - int(W * .045)),
               "@" + wm, font=fw, fill=(255, 255, 255),
               stroke_width=2, stroke_fill=(0, 0, 0))
    save(photo, out)


# ============================================================ trends
TREND = {"ts": 0, "tags": []}


def trending_hashtags(n=8, ttl=900):
    if TREND["tags"] and time.time() - TREND["ts"] < ttl:
        return TREND["tags"][:n]
    raw = []
    try:
        r = requests.get("https://trends24.in/india/", headers=UA, timeout=15)
        r.encoding = "utf-8"
        raw = [x.strip() for x in re.findall(r"trend-link[^>]*>([^<]+)<", r.text) if x.strip()]
    except Exception:
        pass
    if not raw:
        try:
            d = feedparser.parse("https://trends.google.com/trending/rss?geo=IN")
            raw = [clean(e.title) for e in d.entries]
        except Exception:
            pass
    tags = []
    for t in raw:
        t = "".join(c for c in t.strip().strip("\"'").lstrip("#") if c.isalnum())
        if 3 <= len(t) <= 22:
            tags.append("#" + t)
    tags = list(dict.fromkeys(tags))
    random.shuffle(tags)
    TREND["tags"], TREND["ts"] = tags, time.time()
    return tags[:n]


# ============================================================ reddit
SUBS = ["india", "IndianNews", "Cricket", "bollywood", "IndiaSpeaks"]


def reddit_top(sub, limit=25):
    try:
        r = requests.get(f"https://www.reddit.com/r/{sub}/top.json",
                         params={"t": "day", "limit": limit}, headers=UA, timeout=20)
        return r.json()["data"]["children"]
    except Exception:
        return []


def reddit_img(d):
    p = d.get("preview", {}).get("images", [])
    if p:
        return html.unescape(p[0]["source"]["url"])
    if d.get("post_hint") == "image":
        return d.get("url")
    return None


# ============================================================ sourcing
def gn_entries(q):
    try:
        return feedparser.parse(
            "https://news.google.com/rss/search?q=" + quote(q) +
            "&hl=en-IN&gl=IN&ceid=IN:en").entries
    except Exception:
        return []


def real_link(e):
    m = re.search(r'href="([^"]+)"', getattr(e, "description", "") or "")
    return m.group(1) if m else e.link


def feed_entries(record=False):
    items = []
    errs = []
    feeds = list(FEEDS)
    random.shuffle(feeds)
    for f in feeds:
        try:
            d = feedparser.parse(f)
            n = len(d.entries)
            if n == 0:
                errs.append({"feed": f, "n": 0,
                             "exc": repr(d.get("bozo_exception"))[:160],
                             "status": getattr(d, "status", "-")})
            items += d.entries[:25]
        except Exception as e:
            errs.append({"feed": f, "n": -1, "exc": repr(e)[:160], "status": "-"})
    if record:
        FEED_ERR.clear()
        FEED_ERR.extend(errs)
        print(f"[feeds] items={len(items)} bad={len(errs)}")
        for e in errs[:8]:
            print("   ", e["feed"], e["n"], e["exc"])
    return items


def score_item(it, tags):
    s = 0.0
    tl = it["title"].lower()
    s += sum(4 for t in tags if t.lstrip("#").lower() in tl)
    age_min = (time.time() - it.get("ts", time.time())) / 60
    s += max(0, 3 - age_min / 60)
    if 40 <= len(it["title"]) <= 110:
        s += 2
    s += min(5, it.get("eng", 0) / 200)
    s += min(3, it.get("khits", 0))
    s += random.random()
    return round(s, 2)


def make_item(pid, kind, title, url, ref=None, eng=0, khits=0, fbid=None):
    p = get_page(pid)
    if not p:
        return None
    im = download_best(url_variants(url), ref) if url else None
    if im is None and fbid:
        im = download_best(
            url_variants("https://www.facebook.com/photo/?fbid=" + fbid), ref)
    if im is None:
        return None
    fn = f"{pid}_{random.randint(100000, 999999)}.jpg"
    try:
        if kind == "news":
            edit_news(im, title, os.path.join(OUT, fn), p["name"].replace(" ", ""))
        else:
            edit_photo(im, os.path.join(OUT, fn), p["name"].replace(" ", ""))
    except Exception as e:
        print("[edit fail]", repr(e)[:80])
        return None
    return {"title": title, "file": fn, "kind": kind, "fbid": fbid, "link": ref,
            "ts": time.time(), "eng": eng, "khits": khits}


def add_item(pid, it, tags):
    if not it:
        return False
    r = rts(pid)
    with RT_LOCK:
        if it["title"] in r["seen"]:
            return False
        r["seen"].add(it["title"])
        it["score"] = score_item(it, tags)
        r["pool"].append(it)
        if len(r["pool"]) > 80:
            old = r["pool"].pop(0)
            try:
                os.remove(os.path.join(OUT, old["file"]))
            except Exception:
                pass
    return True


def fetch_category(pid, name, need):
    keys = CFG["categories"].get(name, [])
    if not keys:
        return 0
    tags = trending_hashtags(12)
    n = 0
    for e in feed_entries():
        if n >= need:
            break
        title = clean(e.title)
        if not any(k.lower() in title.lower() for k in keys):
            continue
        u = img_from_entry(e) or og_image(e.link)
        if not u:
            continue
        if add_item(pid, make_item(pid, "news", title, u, e.link, 0, khit(title, keys)), tags):
            n += 1
    return n


def fetch_twitter(pid, need):
    n = 0
    for trend in trending_hashtags(20):
        if n >= need:
            break
        for e in gn_entries(trend.lstrip("#")):
            title = clean(e.title)
            rl = real_link(e)
            u = img_from_entry(e) or og_image(rl)
            if not u:
                continue
            if add_item(pid, make_item(pid, "news", title, u, rl, 0, 1),
                        trending_hashtags(12)):
                n += 1
            break
    return n


def fetch_viral(pid, need):
    posts = []
    for s in SUBS:
        for c in reddit_top(s, 25):
            d = c["data"]
            img = reddit_img(d)
            if img:
                posts.append({"title": clean(d["title"]), "img": img,
                              "eng": d.get("score", 0) + d.get("num_comments", 0) * 2})
    posts.sort(key=lambda x: x["eng"], reverse=True)
    n = 0
    for p in posts:
        if n >= need:
            break
        if add_item(pid, make_item(pid, "news", p["title"], p["img"],
                                   "https://reddit.com", p["eng"]), trending_hashtags(12)):
            n += 1
    return n


def fetch_page(pid):
    p = get_page(pid)
    if not p:
        return 0
    per = clamp(p.get("per_fetch"), 1, 10, 2)
    added = 0
    cats = list(p.get("selected") or [])
    random.shuffle(cats)
    for cat in cats:
        if cat == "Twitter Trending":
            added += fetch_twitter(pid, per)
        elif cat == "Viral India":
            added += fetch_viral(pid, per)
        else:
            added += fetch_category(pid, cat, per)
    rts(pid)["msg"] = f"{added} nayi image mili"
    print(f"[fetch {pid}] cats={cats} per={per} added={added}")
    return added


def search_keyword(pid, kw, need=5):
    n = 0
    for e in gn_entries(kw):
        if n >= need:
            break
        title = clean(e.title)
        rl = real_link(e)
        u = img_from_entry(e) or og_image(rl)
        if not u:
            continue
        if add_item(pid, make_item(pid, "news", title, u, rl), trending_hashtags(12)):
            n += 1
    return n


# ============================================================ posting
TAGS = ["#news", "#india", "#trending", "#viral", "#breaking", "#daily", "#update",
        "#khabar", "#aajki", "#desh"]
HOOKS = ["Kya hua? 😳", "Badi khabar!", "Ye dekho!", "Aaj ki khabar!",
         "Sabse bada update!", "Dekh lo yaar!"]


def caption(item):
    title = item["title"]
    link = item.get("link") or ""
    words = [w.strip(".,!?'\"").capitalize() for w in title.split() if len(w) > 4][:3]
    extra = " ".join("#" + w for w in words if w.replace(".", "").isalpha())
    out = [random.choice(HOOKS), "", title, ""]
    if link and "reddit.com" not in link:
        out += ["Is khabar ki poori jankari aur detail yahan padho 👇", link, ""]
    out += ["Aapko ye khabar kaisi lagi? Comment me batao 👇", "",
            f"{' '.join(random.sample(TAGS, 5))} {extra} "
            f"{' '.join(trending_hashtags(4))}"]
    return "\n".join(out)


def caption_photo(page):
    return (f"{page['name']} 📸\n\n"
            f"{' '.join(random.sample(TAGS, 5))} {' '.join(trending_hashtags(4))}")


def fb_post(page, path, text):
    if not page.get("page_id") or not page.get("token"):
        return False, "page_id ya token missing"
    try:
        with open(path, "rb") as f:
            r = requests.post(
                f"{GRAPH}/{page['page_id']}/photos",
                data={"caption": text, "access_token": page["token"]},
                files={"source": f}, timeout=90)
        j = r.json()
        if "error" in j:
            print("[post err]", page["name"], j["error"])
            return False, j["error"].get("message", "error")
        print("[posted]", page["name"], j.get("id"))
        return True, j.get("id", "ok")
    except Exception as e:
        print("[post exc]", repr(e))
        return False, str(e)


def pick(r):
    with RT_LOCK:
        pool = [x for x in r["pool"] if x["title"] not in r["posted"]]
        if not pool:
            return None
        best = max(pool, key=lambda x: x.get("score", 0))
        r["pool"].remove(best)
        return best


def post_page(pid):
    p = get_page(pid)
    if not p:
        return False
    r = rts(pid)
    item = pick(r)
    if not item:
        r["msg"] = "queue khaali hai"
        print(f"[post {pid}] pool empty")
        return False
    text = caption(item) if item.get("kind") == "news" else caption_photo(p)
    ok, res = fb_post(p, os.path.join(OUT, item["file"]), text)
    with RT_LOCK:
        if ok:
            r["posted"].append(item["title"])
            r["posted"] = r["posted"][-120:]
        else:
            r["pool"].append(item)
        r["msg"] = ("Posted: " + item["title"][:40]) if ok else ("Fail: " + res[:70])
        r["last"] = time.strftime("%H:%M")
    return ok


# ============================================================ filler
def filler(pid):
    r = rts(pid)
    while r["fill"]:
        p = get_page(pid)
        if not p or p.get("mode") != "fb" or not p.get("link"):
            time.sleep(6)
            continue
        target = clamp(p.get("count"), 3, 200, 20)
        if len(r["pool"]) >= target:
            time.sleep(10)
            continue
        got = 0
        for u, f in jina_photos(p["link"], target):
            if not r["fill"] or len(r["pool"]) >= target:
                break
            key = f or u.split("?")[0]
            if key in r["seen"]:
                continue
            r["seen"].add(key)
            it = make_item(pid, "photo", "FB photo", u, p["link"], fbid=f)
            if not it:
                continue
            with RT_LOCK:
                r["pool"].append(it)
            r["msg"] = f"auto: pool {len(r['pool'])}/{target}"
            got += 1
            time.sleep(random.randint(6, 12))
        if got == 0:
            time.sleep(30)


# ============================================================ worker
def worker(pid):
    r = rts(pid)
    if r["running"]:
        return
    r["running"] = True
    next_fetch = 0.0
    print("[worker start]", pid)
    while r["running"]:
        p = get_page(pid)
        if not p:
            break
        try:
            now = time.time()
            if p["mode"] == "news" and now >= next_fetch:
                fetch_page(pid)
                next_fetch = now + clamp(p.get("fetch_min"), 2, 720, 30) * 60
            if p["mode"] in ("news", "fb") and r["pool"]:
                post_page(pid)
            elif p["mode"] == "deeni":
                r["msg"] = "deeni apna scheduler chalata hai"
        except Exception as e:
            r["msg"] = "err: " + str(e)[:70]
            print("[worker err]", repr(e))
        pmin = clamp(p.get("post_min"), 1, 720, 45)
        wait = random.randint(pmin, max(pmin, clamp(p.get("post_max"), 1, 720, 60))) * 60
        r["next"] = time.strftime("%H:%M", time.localtime(time.time() + wait))
        for _ in range(wait):
            if not r["running"]:
                break
            time.sleep(1)
    r["running"] = False
    print("[worker stop]", pid)


def start_worker(pid):
    p = get_page(pid)
    if not p:
        return
    r = rts(pid)
    if p["mode"] == "fb" and p.get("link") and not r["fill"]:
        r["fill"] = True
        threading.Thread(target=filler, args=(pid,), daemon=True).start()
    if not r["running"]:
        threading.Thread(target=worker, args=(pid,), daemon=True).start()


# ============================================================ routes
@app.route("/img/<fn>")
def img(fn):
    return send_from_directory(OUT, fn)


@app.route("/ping")
def ping():
    return jsonify({"ok": True, "t": time.time(), "v": VERSION,
                    "pages": len(CFG["pages"]),
                    "app": bool(CFG["app"].get("id"))})


@app.route("/diag/feeds")
def diag_feeds():
    items = feed_entries(record=True)
    return jsonify({"items": len(items), "bad": len(FEED_ERR),
                    "errs": FEED_ERR[:25]})


@app.route("/diag/pipeline/<pid>")
def diag_pipeline(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    t0 = time.time()
    es = feed_entries(record=True)
    keys = CFG["categories"].get((p.get("selected") or ["?"])[0], [])
    matched = [e for e in es if any(k.lower() in clean(e.title).lower() for k in keys)]
    sample = []
    for e in matched[:3]:
        u = img_from_entry(e) or og_image(e.link)
        im = download_best(url_variants(u), e.link) if u else None
        sample.append({"title": clean(e.title)[:60], "url": (u or "")[:90],
                       "ok": bool(im), "size": im.size if im else None})
    return jsonify({"entries": len(es), "bad_feeds": len(FEED_ERR),
                    "cat": (p.get("selected") or [])[:1], "keys": len(keys),
                    "matched": len(matched), "sample": sample,
                    "secs": round(time.time() - t0, 1)})


@app.route("/")
def home():
    return render_template_string(TPL, cfg=CFG, mask=mask, ver=VERSION)


@app.route("/pages/<pid>/settings", methods=["POST"])
def set_page_settings(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    d = request.json or {}
    p["fetch_min"] = clamp(d.get("fetch_min"), 2, 720, 30)
    p["post_min"] = clamp(d.get("post_min"), 1, 720, 45)
    p["post_max"] = max(p["post_min"], clamp(d.get("post_max"), 1, 720, 60))
    p["per_fetch"] = clamp(d.get("per_fetch"), 1, 10, 2)
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": f"✅ saved: fetch {p['fetch_min']}m · "
                                       f"post {p['post_min']}-{p['post_max']}m · "
                                       f"per {p['per_fetch']}"})


@app.route("/settings", methods=["POST"])
def set_settings():
    d = request.json or {}
    CFG["settings"]["fetch_min"] = clamp(d.get("fetch_min"), 2, 720, 30)
    CFG["settings"]["post_min"] = clamp(d.get("post_min"), 1, 720, 45)
    CFG["settings"]["post_max"] = clamp(d.get("post_max"), 1, 720, 60)
    CFG["settings"]["per_fetch"] = clamp(d.get("per_fetch"), 1, 10, 2)
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": "defaults saved"})


@app.route("/app", methods=["POST"])
def set_app():
    d = request.json or {}
    aid = (d.get("id") or "").strip()
    sec = (d.get("secret") or "").strip()
    if not aid or not sec:
        return jsonify({"ok": False, "msg": "❌ App ID aur Secret dono daalo"})
    print("[app] verifying", aid)
    try:
        j = requests.get(f"{GRAPH}/oauth/access_token", params={
            "client_id": aid, "client_secret": sec,
            "grant_type": "client_credentials"}, timeout=25).json()
    except Exception as e:
        print("[app] net fail", repr(e))
        return jsonify({"ok": False, "msg": "❌ net: " + str(e)[:50]})
    if "error" in j:
        print("[app] fb err", j["error"])
        return jsonify({"ok": False, "msg": "❌ " + j["error"].get("message", "invalid")[:80]})
    CFG["app"]["id"] = aid
    CFG["app"]["secret"] = sec
    CFG["app"]["verified"] = time.time()
    cfg_save(CFG)
    print("[app] ok")
    return jsonify({"ok": True, "msg": "✅ credentials verified & saved"})


@app.route("/auth", methods=["POST"])
def set_auth():
    d = request.json or {}
    CFG["auth"]["user"] = (d.get("user") or "").strip()
    CFG["auth"]["pass"] = (d.get("pass") or "").strip()
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": "✅ panel lock updated"})


@app.route("/pages/discover", methods=["POST"])
def discover():
    t0 = time.time()
    aid, sec = app_creds()
    if not (aid and sec):
        return jsonify({"ok": False, "msg": "❌ pehle App ID + Secret save karo"})
    tok = (request.json or {}).get("token", "").strip()
    if not tok:
        return jsonify({"ok": False, "msg": "❌ token daalo"})
    try:
        ll, exp, err = long_lived(tok)
        print(f"[discover] exchange {time.time()-t0:.1f}s err={err!r}")
        if err:
            return jsonify({"ok": False, "msg": "❌ exchange fail: " + err})
        kind, data = resolve_token(ll)
        print(f"[discover] resolve {time.time()-t0:.1f}s kind={kind} "
              f"n={len(data) if isinstance(data, list) else '-'}")
        if kind == "bad":
            return jsonify({"ok": False, "msg": "❌ " + str(data)})
        miss = missing_perms(ll)
        print(f"[discover] perms {time.time()-t0:.1f}s missing={miss}")
        out = []
        for p in data:
            out.append({"id": p.get("id"), "name": p.get("name", "Page"),
                        "token": p.get("token") or p.get("access_token") or ll,
                        "exists": any(x["page_id"] == p.get("id") for x in CFG["pages"])})
        return jsonify({"ok": True, "token": ll, "long_lived": bool(exp),
                        "missing": miss, "pages": out})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "msg": "❌ server err: " + repr(e)[:120]})


@app.route("/pages", methods=["POST"])
def add_page():
    d = request.json or {}
    tok = (d.get("token") or "").strip()
    mode = d.get("mode", "news")
    sel = d.get("pages") or []
    if not tok:
        return jsonify({"ok": False, "msg": "❌ token daalo"})
    if not sel:
        return jsonify({"ok": False, "msg": "❌ kam se kam ek page chuno"})
    _, exp, _ = long_lived(tok)
    okn, skip = [], []
    for item in sel:
        pid = (item.get("id") or "").strip()
        ptok = (item.get("token") or "").strip() or tok
        if not pid:
            continue
        (okn if add_page_rec(pid, item.get("name"), ptok, mode, exp) else skip).append(
            item.get("name") or pid)
    cfg_save(CFG)
    m = []
    if okn:
        m.append("✅ added: " + ", ".join(okn))
    if skip:
        m.append("⏭ already: " + ", ".join(skip))
    return jsonify({"ok": bool(okn), "msg": " | ".join(m) or "kuch add nahi hua"})


@app.route("/pages/<pid>/token", methods=["POST"])
def set_token(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    tok = (request.json or {}).get("token", "").strip()
    if not tok:
        return jsonify({"ok": False, "msg": "token daalo"})
    ll, exp, err = long_lived(tok)
    if err:
        return jsonify({"ok": False, "msg": "❌ " + err})
    kind, data = resolve_token(ll)
    if kind == "bad":
        return jsonify({"ok": False, "msg": "❌ " + str(data)})
    match = [x for x in data if x.get("id") == p["page_id"]]
    if not p.get("page_id"):
        nm = [x for x in data
              if (x.get("name") or "").strip().lower() == (p.get("name") or "").strip().lower()]
        pick2 = nm or data[:1]
        p["page_id"] = pick2[0]["id"]
        p["name"] = pick2[0].get("name") or p["name"]
        match = pick2
    if not match:
        return jsonify({"ok": False, "msg": "❌ is token me is page ka access nahi"})
    p["token"] = match[0].get("token") or match[0].get("access_token") or ll
    p["token_exp"] = exp
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": "✅ token save"})


@app.route("/pages/<pid>/link", methods=["POST"])
def set_link(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    if p["mode"] != "fb":
        return jsonify({"ok": False, "msg": "❌ ye page news mode me hai"})
    d = request.json or {}
    p["link"] = (d.get("link") or "").strip()
    p["count"] = clamp(d.get("count"), 3, 200, 20)
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": "link save"})


@app.route("/pages/<pid>/auto", methods=["POST"])
def auto_on(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    if not p.get("page_id") or not p.get("token"):
        return jsonify({"ok": False, "msg": "❌ pehle token save karo"})
    if p["mode"] == "deeni":
        p["deeni"] = True
        p.setdefault("deeni_min", 45)
        p.setdefault("deeni_max", 60)
    if p["mode"] == "fb" and not p.get("link"):
        return jsonify({"ok": False, "msg": "❌ pehle link save karo"})
    if p["mode"] == "news" and not (p.get("selected") or []):
        return jsonify({"ok": False, "msg": "❌ koi category select karo"})
    p["auto"] = True
    cfg_save(CFG)
    start_worker(pid)
    return jsonify({"ok": True, "msg": "auto chalu"})


@app.route("/pages/<pid>", methods=["DELETE"])
def del_page(pid):
    r = rts(pid)
    r["running"] = False
    r["fill"] = False
    for it in list(r["pool"]):
        try:
            os.remove(os.path.join(OUT, it["file"]))
        except Exception:
            pass
    r["pool"].clear()
    CFG["pages"] = [p for p in CFG["pages"] if p["id"] != pid]
    cfg_save(CFG)
    RT.pop(pid, None)
    return jsonify({"ok": True})


@app.route("/pages/<pid>/mode", methods=["POST"])
def set_mode(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False})
    p["mode"] = (request.json or {}).get("mode", "news")
    p["auto"] = False
    r = rts(pid)
    r["running"] = False
    r["fill"] = False
    cfg_save(CFG)
    return jsonify({"ok": True})


@app.route("/pages/<pid>/select", methods=["POST"])
def set_sel(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False})
    p["selected"] = (request.json or {}).get("categories", [])
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": f"{len(p['selected'])} categories"})


@app.route("/pages/<pid>/stop", methods=["POST"])
def stop(pid):
    p = get_page(pid)
    if p:
        p["auto"] = False
        cfg_save(CFG)
    r = rts(pid)
    r["running"] = False
    r["fill"] = False
    return jsonify({"ok": True, "msg": "stop"})


@app.route("/pages/<pid>/fetch", methods=["POST"])
def do_fetch(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    if p["mode"] != "news":
        return jsonify({"ok": False, "msg": "❌ news mode me hi fetch hota hai"})
    if not (p.get("selected") or []):
        return jsonify({"ok": False, "msg": "❌ koi category tick karo"})
    threading.Thread(target=fetch_page, args=(pid,), daemon=True).start()
    return jsonify({"ok": True, "msg": "fetch chalu — 20-40s"})


@app.route("/pages/<pid>/search", methods=["POST"])
def do_search(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False})
    kw = (request.json or {}).get("keyword", "").strip()
    if not kw:
        return jsonify({"ok": False, "msg": "❌ keyword daalo"})
    threading.Thread(target=search_keyword, args=(pid, kw, 5), daemon=True).start()
    return jsonify({"ok": True, "msg": "search chalu"})


@app.route("/pages/<pid>/postnow", methods=["POST"])
def post_now(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    if not p.get("token"):
        return jsonify({"ok": False, "msg": "❌ pehle token save karo"})
    threading.Thread(target=post_page, args=(pid,), daemon=True).start()
    return jsonify({"ok": True, "msg": "post chalu"})


@app.route("/pages/<pid>/fbdl", methods=["POST"])
def fb_dl(pid):
    p = get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    if p["mode"] != "fb":
        return jsonify({"ok": False, "msg": "❌ sirf fb mode ke liye"})
    d = request.json or {}
    link, cnt = (d.get("link") or "").strip(), clamp(d.get("count"), 1, 60, 10)
    if not link:
        return jsonify({"ok": False, "msg": "❌ link daalo"})
    p["link"], p["count"] = link, cnt
    cfg_save(CFG)
    r = rts(pid)
    n = 0
    for u, f in jina_photos(link, cnt):
        key = f or u.split("?")[0]
        if key in r["seen"]:
            continue
        r["seen"].add(key)
        it = make_item(pid, "photo", "FB photo", u, link, fbid=f)
        if not it:
            continue
        with RT_LOCK:
            r["pool"].append(it)
        n += 1
    if n == 0:
        return jsonify({"ok": False, "msg": "❌ koi nayi photo nahi mili"})
    return jsonify({"ok": True, "msg": f"✅ {n} photo mili (hi-res)"})


@app.route("/pages/<pid>/status")
def status(pid):
    r = rts(pid)
    p = get_page(pid) or {}
    exp = p.get("token_exp")
    h = "token —"
    if exp:
        left = int((exp - time.time()) / 86400)
        h = f"token {left}d" if left > 0 else "token EXPIRED"
    elif p.get("token"):
        h = "token ok"
    return jsonify({"pool": len(r["pool"]), "running": r["running"], "fill": r["fill"],
                    "last": r["last"], "next": r["next"], "msg": r["msg"],
                    "posted": len(r["posted"]), "health": h,
                    "page_id": p.get("page_id", ""), "name": p.get("name", ""),
                    "per_fetch": p.get("per_fetch", 2)})


@app.route("/pool/<pid>")
def pool(pid):
    items = rts(pid)["pool"]
    return jsonify({"items": list(items)})


@app.route("/pool/<pid>/<int:i>", methods=["DELETE"])
def drop(pid, i):
    r = rts(pid)
    with RT_LOCK:
        if 0 <= i < len(r["pool"]):
            it = r["pool"].pop(i)
            try:
                os.remove(os.path.join(OUT, it["file"]))
            except Exception:
                pass
    return jsonify({"ok": True})


@app.route("/cats", methods=["POST"])
def add_cat():
    d = request.json or {}
    n, k = (d.get("name") or "").strip(), d.get("keys") or []
    if not n:
        return jsonify({"ok": False, "msg": "naam daalo"})
    CFG["categories"][n] = [x for x in k if x]
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": f"category {n} ({len(k)} keys)"})


@app.route("/cats/<name>", methods=["DELETE"])
def del_cat(name):
    CFG["categories"].pop(name, None)
    for p in CFG["pages"]:
        p["selected"] = [c for c in p.get("selected", []) if c != name]
    cfg_save(CFG)
    return jsonify({"ok": True, "msg": "deleted"})


@app.route("/cats/<name>/keys", methods=["POST"])
def add_kw(name):
    k = (request.json or {}).get("key", "").strip()
    if name in CFG["categories"] and k and k not in CFG["categories"][name]:
        CFG["categories"][name].append(k)
        cfg_save(CFG)
        return jsonify({"ok": True, "msg": f"+{k}"})
    return jsonify({"ok": False, "msg": "already ya khali"})


@app.route("/cats/<name>/keys/<key>", methods=["DELETE"])
def del_kw(name, key):
    if name in CFG["categories"]:
        CFG["categories"][name] = [x for x in CFG["categories"][name] if x != key]
        cfg_save(CFG)
    return jsonify({"ok": True, "msg": "removed"})


# ============================================================ template
TPL = """<!doctype html><html><head><meta charset="utf-8">
<title>FB Bot</title><style>
*{box-sizing:border-box}
body{background:#101018;color:#eee;font-family:system-ui,sans-serif;margin:0;padding:16px;max-width:1060px}
h1{font-size:18px;margin:0 0 10px}
.pg{background:#1a1a24;border-radius:10px;padding:10px;margin-top:10px}
.pg h4{margin:0 0 6px;font-size:14px;color:#ff9dd0}
.pid{color:#777;font-size:11px;font-weight:400}
.cats{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}
.cats label{background:#2a2a3a;padding:2px 7px;border-radius:10px;font-size:11px;cursor:pointer}
.row{margin:6px 0;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
button{background:#2b2b3a;color:#eee;border:0;padding:6px 11px;border-radius:7px;
font-size:12px;cursor:pointer}
button:hover{background:#3a3a4d}
button.on{background:#2f7d4f}
button.auto{background:#7a5c1e}
button.del{background:#7d2f2f}
button.sm{padding:4px 8px;font-size:11px}
input,select{background:#222;border:1px solid #333;color:#eee;padding:6px 9px;border-radius:7px;font-size:12px}
.st{font-size:11px;color:#9f9;min-height:16px;white-space:pre-wrap;word-break:break-all}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:10px}
.card{background:#1a1a24;border-radius:10px;overflow:hidden;position:relative}
.card img{width:100%;display:block;background:#333}
.card .t{font-size:11px;padding:6px}
.card .sc{font-size:10px;color:#ff9dd0;padding:0 6px 6px}
.card .x{position:absolute;top:5px;right:5px;background:#e33;border:0;color:#fff;
border-radius:50%;width:22px;height:22px;font-weight:bold;cursor:pointer;padding:0}
.mask{position:fixed;inset:0;background:#000a;display:none;align-items:center;
justify-content:center;z-index:9}
.mask.show{display:flex}
.modal{background:#1c1c27;border-radius:12px;padding:16px;width:500px;max-width:92vw}
.modal h3{margin:0 0 10px;font-size:15px;color:#ff9dd0}
.modal input,.modal select{width:100%;margin-bottom:8px}
.warn{background:#4a1f1f;border:1px solid #7d2f2f;padding:9px 12px;border-radius:8px;
font-size:12px;margin-bottom:12px;line-height:1.5}
.ok{background:#1f4a2f;border:1px solid #2f7d4f;padding:9px 12px;border-radius:8px;
font-size:12px;margin-bottom:12px}
.pg[data-mode="fb"] .cats,.pg[data-mode="fb"] .news-only{display:none}
.pg[data-mode="news"] .fb-only{display:none}
.pg[data-mode="deeni"] .cats,.pg[data-mode="deeni"] .news-only{display:none}
.pg[data-mode="deeni"] .fb-only{display:none}
.drow{background:#141b16;border:1px solid #2a3520;border-radius:8px;padding:6px}
.drow button{background:#1d2a20}
.drow button.on{background:#6b2f2f}
.tokline{font-size:11px;color:#888}
details summary{cursor:pointer;font-size:12px;color:#ff9dd0;margin:4px 0}
#errbar{background:#2a1010;border:1px solid #7d2f2f;border-radius:8px;padding:8px 10px;
font-size:11px;font-family:monospace;max-height:200px;overflow:auto;margin-bottom:12px;
white-space:pre-wrap;word-break:break-all}
#errbar b{color:#ff8a8a}
#diag{font-size:11px;font-family:monospace;color:#888;margin-bottom:8px}
.small{font-size:11px;color:#888}
</style></head><body>
<h1>FB Bot — Multi Page <span class="pid">v{{ver}}</span></h1>
<div class="row"><a href="/deeni" style="color:#d4af37;font-size:12px">
Deeni page (preview / BG files) →</a></div>

<div id="diag">diagnostics: checking...</div>
<div id="errbar"><b>EVENT LOG</b> <button class="sm" onclick="CLR()">clear</button>
<div id="errlist"></div></div>

{% if not cfg.app.id or not cfg.app.secret %}
<div class="warn"><b>Setup baaki hai.</b> App credentials me App ID + Secret daal ke Save karo.</div>
{% else %}
<div class="ok">App configured — ID {{cfg.app.id}} · Secret {{mask(cfg.app.secret)}}</div>
{% endif %}

<div class="pg">
  <h4>App credentials</h4>
  <div class="row">
    <input id="appid" value="{{cfg.app.id}}" placeholder="App ID" style="width:180px">
    <input id="appsec" type="password" value="{{cfg.app.secret}}"
      placeholder="App Secret" style="width:260px">
    <button onclick="saveApp(this)">Verify &amp; Save</button>
  </div>
  <div class="st" id="appstat"></div>
  <details><summary>Panel lock (optional)</summary>
    <div class="row">
      <input id="authu" value="{{cfg.auth.user}}" placeholder="username" style="width:140px">
      <input id="authp" type="password" value="{{cfg.auth.pass}}"
        placeholder="password" style="width:140px">
      <button onclick="saveAuth()">Save lock</button>
    </div>
    <div class="st" id="authstat"></div>
  </details>
</div>

<div id="pages">
{% for p in cfg.pages %}
<div class="pg" data-id="{{p.id}}" data-mode="{{p.mode}}">
  <h4>{{p.name}} <span class="pid">{{p.page_id or "not connected"}}</span></h4>
  <div class="row">
    <button class="{{'on' if p.mode=='news'}}" onclick="setMode('{{p.id}}','news')">News</button>
    <button class="{{'on' if p.mode=='fb'}}" onclick="setMode('{{p.id}}','fb')">FB photos</button>
    <button class="{{'on' if p.mode=='deeni'}}" onclick="setMode('{{p.id}}','deeni')">Deeni</button>
    <button class="auto" onclick="autoP('{{p.id}}',this)">Auto</button>
    <button onclick="stopP('{{p.id}}')">Stop</button>
    <button onclick="postNow('{{p.id}}')">Post Now</button>
    <button class="news-only" onclick="fetchP('{{p.id}}')">Fetch</button>
    <button class="del" onclick="delPage('{{p.id}}')">Remove</button>
  </div>
  <div class="row">
    <input class="ptok" type="password" placeholder="naya token (khali = purana)" style="width:290px">
    <button class="sm" onclick="saveTok('{{p.id}}',this)">Save token</button>
    <span class="tokline" data-tok></span>
  </div>
  <div class="row drow">
    <button class="{{'on' if p.deeni}}" onclick="dTog('{{p.id}}')">
      Deeni {{'ON' if p.deeni else 'OFF'}}</button>
    <input class="dmn" type="number" value="{{p.deeni_min or 45}}" style="width:50px">-
    <input class="dmx" type="number" value="{{p.deeni_max or 60}}" style="width:50px">min
    <button class="sm" onclick="dSet('{{p.id}}')">Set</button>
    <button class="sm" onclick="dPost('{{p.id}}',this)">Post now</button>
    <span class="tokline" data-dn>{{p.deeni_msg or ''}}</span>
  </div>
  <div class="row news-only">
    <input class="kw" placeholder="keyword search" style="width:170px">
    <button onclick="searchKw('{{p.id}}',this)">Search</button>
  </div>
  <div class="row small">
    fetch <input class="s_fetch" type="number" value="{{p.fetch_min}}" style="width:52px">min
    · post <input class="s_pmin" type="number" value="{{p.post_min}}" style="width:52px">-
    <input class="s_pmax" type="number" value="{{p.post_max}}" style="width:52px">min
    · per fetch <input class="s_per" type="number" value="{{p.per_fetch}}" style="width:44px">
    <button class="sm" onclick="savePageSet('{{p.id}}',this)">Save</button>
  </div>
  <div class="cats">
    {% for c in cfg.categories %}
    <label><input type="checkbox" value="{{c}}" {{'checked' if c in p.selected}}
      onchange="saveSel('{{p.id}}')"> {{c}}</label>
    {% endfor %}
  </div>
  <div class="row fb-only">
    <input class="lnk" value="{{p.link}}" placeholder="facebook page/photo link" style="width:260px">
    <input class="cnt" type="number" value="{{p.count}}" style="width:70px">
    <button onclick="dlFb('{{p.id}}',this)">Download photos</button>
  </div>
  <div class="st" data-st></div>
  <div class="grid" data-grid></div>
</div>
{% endfor %}
</div>

<div class="row" style="margin-top:14px">
  <button onclick="openAdd()">＋ Connect page</button>
</div>

<div class="mask" id="mask">
  <div class="modal">
    <h3>Page connect karo</h3>
    <input id="newtok" placeholder="User token ya Page token (EAA...)">
    <select id="newmode">
      <option value="news">Engine: News</option>
      <option value="fb">Engine: Facebook photos</option>
      <option value="deeni">Engine: Deeni (hadith)</option>
    </select>
    <button onclick="discover(this)">Pages fetch karo</button>
    <div class="st" id="addstat" style="margin:8px 0"></div>
    <div id="pglist" style="max-height:230px;overflow:auto"></div>
    <div class="row" style="margin-top:10px">
      <button onclick="addPicked(this)">Save / Connect</button>
      <button onclick="closeAdd()">Cancel</button>
    </div>
  </div>
</div>

<div class="pg">
  <h4>Categories</h4>
  <div class="row">
    <input id="newname" placeholder="category" style="width:130px">
    <input id="newkeys" placeholder="keywords comma separated" style="width:230px">
    <button onclick="addCat()">Create</button>
  </div>
  <div class="row">
    <select id="catSel" style="min-width:170px">
      {% for c in cfg.categories %}<option>{{c}}</option>{% endfor %}
    </select>
    <input id="newkw" placeholder="keyword" style="width:140px">
    <button onclick="addKw()">+ Keyword</button>
    <button class="del" onclick="delCat()">Delete category</button>
  </div>
  <div class="row small">
    <button class="sm" onclick="diagFeeds()">Feed test</button>
    <span id="feedstat"></span>
  </div>
</div>

<script>
const J={'Content-Type':'application/json'};
const SIG={};
let PICK={token:'',pages:[]};
const EB=document.getElementById('errbar');
const EL=document.getElementById('errlist');
function LOG(m,c){
  const d=document.createElement('div');
  d.textContent='['+new Date().toLocaleTimeString()+'] '+m;
  if(c)d.style.color=c;
  EL.appendChild(d);EB.scrollTop=EB.scrollHeight;
  while(EL.childNodes.length>150)EL.removeChild(EL.firstChild);
}
function CLR(){EL.innerHTML='';}
window.onerror=(m,s,l)=>LOG('JS ERROR: '+m+' @'+l,'#ff8a8a');
window.addEventListener('unhandledrejection',e=>LOG('PROMISE: '+(e.reason&&e.reason.message||e.reason),'#ff8a8a'));
function st(id,msg,color){
  const el=document.querySelector('[data-id="'+id+'"] [data-st]');
  if(el){el.textContent=msg;el.style.color=color||'#9f9';}
  LOG('['+id+'] '+msg,color);
}
async function call(u,m,b){
  const t0=Date.now();
  try{
    const r=await fetch(u,{method:m||'POST',headers:J,body:b?JSON.stringify(b):null});
    const txt=await r.text();
    let d=null;try{d=JSON.parse(txt);}catch(e){}
    if(!r.ok||!d){
      LOG((m||'POST')+' '+u+' -> HTTP '+r.status+' '+txt.slice(0,200),'#ff8a8a');
      return {ok:false,msg:'HTTP '+r.status+' '+(txt.slice(0,140)||'empty')};
    }
    LOG((m||'POST')+' '+u+' -> '+r.status+' ('+(Date.now()-t0)+'ms)');
    return d;
  }catch(e){
    LOG((m||'POST')+' '+u+' -> NET FAIL '+e.name,'#ff8a8a');
    return {ok:false,msg:'NET FAIL '+e.name+' — server band?'};
  }
}
async function saveApp(btn){
  const s=document.getElementById('appstat');
  const id=document.getElementById('appid').value.trim();
  const sec=document.getElementById('appsec').value.trim();
  if(!id||!sec){s.textContent='❌ dono daalo';return;}
  btn.disabled=true;s.textContent='checking...';
  const d=await call('/app','POST',{id,secret:sec});
  btn.disabled=false;s.textContent=d.msg;
  if(d.ok)setTimeout(()=>location.reload(),900);
}
async function saveAuth(){
  const d=await call('/auth','POST',{user:document.getElementById('authu').value,
    pass:document.getElementById('authp').value});
  document.getElementById('authstat').textContent=d.msg;
}
function openAdd(){document.getElementById('addstat').textContent='';
  document.getElementById('newtok').value='';document.getElementById('pglist').innerHTML='';
  document.getElementById('mask').classList.add('show');}
function closeAdd(){document.getElementById('mask').classList.remove('show');}
async function discover(btn){
  const t=document.getElementById('newtok').value.trim();
  const s=document.getElementById('addstat');
  if(!t){s.textContent='❌ token daalo';return;}
  btn.disabled=true;s.textContent='checking...';
  const d=await call('/pages/discover','POST',{token:t});
  btn.disabled=false;
  if(!d.ok){s.textContent=d.msg;return;}
  PICK.token=d.token;PICK.pages=d.pages;
  let m=[];if(d.missing.length)m.push('⚠ '+d.missing.join(', '));
  m.push(d.long_lived?'✅ long-lived':'⚠ short-lived');
  s.textContent=m.join(' | ');
  document.getElementById('pglist').innerHTML=d.pages.map((p,i)=>
    '<label style="display:flex;gap:8px;padding:5px 0"><input type="checkbox" '+
    (p.exists?'disabled ':'checked ')+'data-i="'+i+'"> <span>'+p.name+
    ' <span class="pid">'+p.id+'</span>'+(p.exists?' — already':'')+'</span></label>').join('');
}
async function addPicked(btn){
  const s=document.getElementById('addstat');
  const sel=[...document.querySelectorAll('#pglist input:checked')].map(x=>PICK.pages[+x.dataset.i]);
  if(!sel.length){s.textContent='❌ koi page chuno';return;}
  btn.disabled=true;
  const d=await call('/pages','POST',{token:PICK.token,pages:sel,
    mode:document.getElementById('newmode').value});
  btn.disabled=false;s.textContent=d.msg;
  if(d.ok)setTimeout(()=>location.reload(),1200);
}
async function saveTok(id,btn){
  const d0=document.querySelector('[data-id="'+id+'"]');
  const t=d0.querySelector('.ptok').value.trim();
  if(!t){st(id,'token daalo','#ff8a8a');return;}
  btn.disabled=true;btn.textContent='...';
  const d=await call('/pages/'+id+'/token','POST',{token:t});
  btn.disabled=false;btn.textContent='Save token';
  st(id,d.msg,d.ok?'#9f9':'#ff8a8a');
  if(d.ok)setTimeout(()=>location.reload(),700);
}
async function savePageSet(id,btn){
  const d0=document.querySelector('[data-id="'+id+'"]');
  btn.disabled=true;
  const d=await call('/pages/'+id+'/settings','POST',{
    fetch_min:+d0.querySelector('.s_fetch').value,
    post_min:+d0.querySelector('.s_pmin').value,
    post_max:+d0.querySelector('.s_pmax').value,
    per_fetch:+d0.querySelector('.s_per').value});
  btn.disabled=false;
  st(id,d.msg,d.ok?'#9f9':'#ff8a8a');
}
async function dTog(id){
  const d=await call('/deeni/'+id+'/toggle');
  st(id,'deeni: '+d.msg,d.ok?'#9f9':'#ff8a8a');
  if(d.ok)setTimeout(()=>location.reload(),700);
}
async function dSet(id){
  const d0=document.querySelector('[data-id="'+id+'"]');
  const d=await call('/deeni/'+id+'/gap','POST',
    {min:d0.querySelector('.dmn').value,max:d0.querySelector('.dmx').value});
  const el=d0.querySelector('[data-dn]');
  if(el)el.textContent=d.msg;
  LOG('deeni gap: '+d.msg,d.ok?'#9f9':'#ff8a8a');
}
async function dPost(id,btn){
  btn.disabled=true;btn.textContent='...';
  const d=await call('/deeni/'+id+'/post');
  btn.disabled=false;btn.textContent='Post now';
  const el=document.querySelector('[data-id="'+id+'"] [data-dn]');
  if(el)el.textContent=(d.ok?'✅ ':'❌ ')+d.msg;
  LOG('deeni post: '+d.msg,d.ok?'#9f9':'#ff8a8a');
}
async function delPage(id){
  if(!confirm('page remove karun?'))return;
  const d=await call('/pages/'+id,'DELETE');LOG('remove '+id+' '+JSON.stringify(d));
  location.reload();
}
async function setMode(id,m){
  const d=await call('/pages/'+id+'/mode','POST',{mode:m});
  LOG('mode '+id+' '+m+' '+JSON.stringify(d));location.reload();
}
async function saveSel(id){
  const d0=document.querySelector('[data-id="'+id+'"]');
  const c=[...d0.querySelectorAll('.cats input:checked')].map(x=>x.value);
  const d=await call('/pages/'+id+'/select','POST',{categories:c});
  st(id,'cats: '+d.msg,d.ok?'#888':'#ff8a8a');
}
async function autoP(id,btn){
  const d0=document.querySelector('[data-id="'+id+'"]');
  if(d0.dataset.mode==='fb'){
    const s=await call('/pages/'+id+'/link','POST',{
      link:d0.querySelector('.lnk').value.trim(),count:d0.querySelector('.cnt').value});
    st(id,'link: '+s.msg,s.ok?'#888':'#ff8a8a');
    if(!s.ok)return;
  }
  btn.disabled=true;
  const d=await call('/pages/'+id+'/auto','POST');
  btn.disabled=false;
  st(id,'auto: '+d.msg,d.ok?'#9f9':'#ff8a8a');
  if(!d.ok)alert(d.msg);
  tick();
}
async function stopP(id){const d=await call('/pages/'+id+'/stop');st(id,'stop: '+d.msg,'#888');tick();}
async function postNow(id){const d=await call('/pages/'+id+'/postnow');st(id,'post: '+d.msg,d.ok?'#9f9':'#ff8a8a');setTimeout(tick,3000);}
async function fetchP(id){const d=await call('/pages/'+id+'/fetch');st(id,'fetch: '+d.msg,d.ok?'#9f9':'#ff8a8a');setTimeout(tick,6000);}
async function searchKw(id,btn){
  const d0=document.querySelector('[data-id="'+id+'"]');
  const kw=d0.querySelector('.kw').value.trim();
  if(!kw){st(id,'keyword likho','#ff8a8a');return;}
  btn.disabled=true;btn.textContent='...';
  const d=await call('/pages/'+id+'/search','POST',{keyword:kw});
  btn.disabled=false;btn.textContent='Search';
  st(id,'search: '+d.msg,d.ok?'#9f9':'#ff8a8a');
}
async function dlFb(id,btn){
  const d0=document.querySelector('[data-id="'+id+'"]');
  const link=d0.querySelector('.lnk').value.trim();
  if(!link){st(id,'link daalo','#ff8a8a');return;}
  btn.disabled=true;btn.textContent='...';st(id,'download chalu...','#888');
  const d=await call('/pages/'+id+'/fbdl','POST',{link,count:d0.querySelector('.cnt').value});
  btn.disabled=false;btn.textContent='Download photos';
  st(id,'download: '+d.msg,d.ok?'#9f9':'#ff8a8a');
  loadPool(id);
}
async function addCat(){
  const n=document.getElementById('newname').value.trim();
  const k=document.getElementById('newkeys').value.split(',').map(x=>x.trim()).filter(Boolean);
  if(!n){LOG('naam khali','#ff8a8a');return;}
  const d=await call('/cats','POST',{name:n,keys:k});
  LOG('add cat '+n+' '+d.msg);
  if(d.ok)location.reload();
}
async function delCat(){
  const n=document.getElementById('catSel').value;
  if(!confirm('category delete?'))return;
  const d=await call('/cats/'+encodeURIComponent(n),'DELETE');
  LOG('del cat '+n+' '+d.msg);location.reload();
}
async function addKw(){
  const n=document.getElementById('catSel').value;
  const k=document.getElementById('newkw').value.trim();
  if(!k)return;
  const d=await call('/cats/'+encodeURIComponent(n)+'/keys','POST',{key:k});
  LOG('kw '+k+': '+d.msg);
  if(d.ok)document.getElementById('newkw').value='';
}
async function diagFeeds(){
  document.getElementById('feedstat').textContent=' testing...';
  const r=await fetch('/diag/feeds');const d=await r.json();
  document.getElementById('feedstat').textContent=
    ' items '+d.items+' · bad '+d.bad;
  d.errs.slice(0,8).forEach(e=>LOG('FEED '+e.feed+' n='+e.n+' '+e.exc,'#ff8a8a'));
}
async function loadPool(id){
  const r=await fetch('/pool/'+id);const d=await r.json();
  const s=d.items.map(x=>x.file).join(',');
  if(SIG[id]===s)return;
  SIG[id]=s;
  const g=document.querySelector('[data-id="'+id+'"] [data-grid]');
  if(!g)return;
  g.innerHTML=d.items.map((it,i)=>
    '<div class="card"><img src="/img/'+it.file+'"><div class="t">'+
    it.title.slice(0,42)+'</div><div class="sc">score '+(it.score||0)+
    '</div><button class="x" onclick="drop(\\''+id+'\\','+i+')">×</button></div>').join('');
}
async function drop(id,i){const d=await call('/pool/'+id+'/'+i,'DELETE');LOG('drop '+i+' '+JSON.stringify(d));loadPool(id);}
async function tick(){
  for(const el of document.querySelectorAll('.pg[data-id]')){
    const id=el.dataset.id;
    loadPool(id);
    try{
      const s=await (await fetch('/pages/'+id+'/status')).json();
      el.querySelector('[data-st]').textContent=
        'pool '+s.pool+' | posted '+s.posted+' | '+(s.fill?'AUTO-FILL ':'')+
        (s.running?'RUNNING':'stopped')+' | '+s.health+' | last '+s.last+
        ' | next '+s.next+' | '+s.msg;
    }catch(e){LOG('tick fail '+id+': '+e.message,'#ff8a8a');}
  }
}
async function diag(){
  const el=document.getElementById('diag');
  try{
    const r=await fetch('/ping');const d=await r.json();
    el.innerHTML='server OK · v'+d.v+' · pages '+d.pages+' · app '+
      (d.app?'set':'MISSING')+' · <span style="color:#9f9">JS chal raha</span>';
    el.style.color='#9f9';
  }catch(e){
    el.textContent='SERVER SE CONNECT NAHI — '+e.name;
    el.style.color='#ff8a8a';LOG('PING FAIL '+e.message,'#ff8a8a');
  }
}
diag();setInterval(diag,10000);
tick();setInterval(tick,4000);
LOG('panel ready v{{ver}}');
</script></body></html>"""


# ============================================================ boot
def boot_resume():
    aid, sec = app_creds()
    if not (aid and sec):
        print("!! App ID / Secret set nahi — panel se daalo")
    if not os.environ.get("DATA_DIR"):
        print("!! DATA_DIR set nahi — config.json deploy pe mit jayega")
    for p in CFG["pages"]:
        exp = p.get("token_exp")
        if exp and exp < time.time():
            print("TOKEN EXPIRED:", p["name"])
        if not p.get("auto"):
            continue
        if not p.get("token"):
            continue
        if p["mode"] == "fb" and not p.get("link"):
            continue
        if p["mode"] == "news" and not (p.get("selected") or []):
            continue
        start_worker(p["id"])
        print("resumed:", p["name"])


import deeni
app.register_blueprint(deeni.bp)


if __name__ == "__main__":
    boot_resume()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=True, use_reloader=False)
else:
    boot_resume()
