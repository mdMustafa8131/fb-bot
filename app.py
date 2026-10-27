import os, re, html, json, base64, random, time, threading, requests, feedparser
from io import BytesIO
from urllib.parse import quote, urljoin
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
from flask import Flask, render_template_string, request, jsonify, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")
CONFIG_FILE = os.path.join(BASE, "config.json")
os.makedirs(STATIC, exist_ok=True)
app = Flask(__name__, static_folder=STATIC, static_url_path="/static")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ====== APNI DETAILS ======
PAGE_ID   = "100737239401306"
TOKEN     = "EAAJEILYjdJ4BS1lYtyrRQQKkq0KbSkZCaiUfyL7j62P9Ymz6sxJX0cns6ZAuZC9AMepd0Wwg0wAIwIseTcqlEsZCaH5VJersZCjcZBLFRbAIsE41kbyKRsnssR7nBxO79JXtP3sZBlJj7emj8JhMtalpsnohUmoSQtVi8us6FyR6AFOkUMWR0nepHjIp7yZABHcS3SYZD"
PAGE_NAME = "@MalikaHafa"
# =========================

YELLOW = (255, 214, 0)
BLACK  = (12, 12, 12)

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

DEFAULT_CATEGORIES = {
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

DEFAULT_SETTINGS = {"fetch_min": 30, "post_min": 45, "post_max": 60, "per_fetch": 5}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                c = json.load(f)
            c.setdefault("categories", dict(DEFAULT_CATEGORIES))
            c.setdefault("settings", dict(DEFAULT_SETTINGS))
            c.setdefault("selected", [])
            c.setdefault("auto_on", False)
            return c
        except Exception as e:
            print("config load err:", e)
    return {"categories": dict(DEFAULT_CATEGORIES), "settings": dict(DEFAULT_SETTINGS),
            "selected": [], "auto_on": False}

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(CFG, f, ensure_ascii=False, indent=2)

CFG = load_config()

STATE = {"cats": list(CFG.get("selected", [])), "pool": [], "posted": [],
         "running": False, "last_post": None, "next_post": None}
LOCK = threading.Lock()

def is_dev(s):
    return any('\u0900' <= ch <= '\u097f' for ch in s)

def load_font(size, bold=False, dev=False):
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    if dev:
        cands += [os.path.join(here, "font_dev.ttf")]
    cands += [os.path.join(here, "font.ttf"),
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "C:/Windows/Fonts/NirmalaB.ttf", "C:/Windows/Fonts/Nirmala.ttf",
              "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]
    for c in cands:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()

def clean(t):
    return re.sub(r"\s+-\s+[^-]+$", "", t).strip()[:90]

def matches(title, keywords):
    tl = title.lower()
    return any(re.search(r"(?<![a-z])" + re.escape(k.lower()) + r"(?![a-z])", tl) for k in keywords)

def khit(title, keywords):
    tl = title.lower()
    return sum(1 for k in keywords if k.lower() in tl)

def img_from_entry(e):
    for a in ("media_content", "media_thumbnail"):
        v = getattr(e, a, None)
        if v:
            u = v[0].get("url")
            if u:
                return u
    for l in getattr(e, "links", []) or []:
        if l.get("type", "").startswith("image"):
            return l.get("href")
    for en in getattr(e, "enclosures", []) or []:
        if en.get("type", "").startswith("image"):
            return en.get("href")
    return None

def og_image(url):
    try:
        r = requests.get(url, headers=UA, timeout=15)
        for p in [r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
                  r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image']:
            m = re.search(p, r.text)
            if m:
                u = urljoin(r.url, html.unescape(m.group(1)))
                if "google" in u or "gstatic" in u:
                    continue
                return u
    except Exception:
        pass
    return None

def download(url, ref=None):
    try:
        h = dict(UA)
        if ref:
            h["Referer"] = ref
        r = requests.get(url, headers=h, timeout=30)
        if r.status_code == 200 and "image" in r.headers.get("content-type", "") and len(r.content) > 3000:
            im = Image.open(BytesIO(r.content))
            im.load()
            im = im.convert("RGB")
            if min(im.size) >= 200:
                return im
    except Exception:
        pass
    return None

def enhance(img):
    img = ImageEnhance.Color(img).enhance(1.18)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Brightness(img).enhance(1.04)
    return ImageEnhance.Sharpness(img).enhance(1.4)

def film_effect(img):
    W, H = img.size
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * 1.06)))
    b = b.point(lambda x: int(x * 0.94))
    img = Image.merge("RGB", (r, g, b))
    img = Image.blend(img, Image.new("RGB", (W, H), (22, 20, 28)), 0.07)
    img = Image.blend(img, Image.effect_noise((W, H), 16).convert("RGB"), 0.09)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W*0.15, -H*0.15, W*1.15, H*1.15], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(W // 8))
    return Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), vig)

def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def edit(img, topic, out):
    img = img.convert("RGB")
    scale = 1080 / max(img.size)
    if scale < 1:
        img = img.resize((int(img.size[0]*scale), int(img.size[1]*scale)), Image.LANCZOS)
    img = enhance(img)
    img = film_effect(img)
    W, H = img.size
    dev = is_dev(topic)
    fb = load_font(58, bold=True, dev=dev)
    fs = load_font(28, dev=dev)
    fh = load_font(62, dev=dev)
    line_h = 60
    lines = wrap(ImageDraw.Draw(img), topic, fb, W-110)[:3]
    band = 12 + len(lines) * line_h
    canvas = Image.new("RGB", (W, H + band), BLACK)
    canvas.paste(img, (0, 0))
    sh = 120
    grad = Image.new("L", (1, H), 0)
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        if y > H - sh:
            gd.point((0, y), fill=int(245 * (y - (H - sh)) / sh))
    photo = canvas.crop((0, 0, W, H))
    canvas.paste(Image.composite(Image.new("RGB", (W, H), BLACK), photo, grad.resize((W, H))), (0, 0))
    d = ImageDraw.Draw(canvas)
    y = H - 6
    for ln in lines:
        d.text((44, y), ln, font=fb, fill=YELLOW)
        y += line_h
    d.ellipse([22, 22, 116, 116], fill=(255, 105, 180))
    d.text((56, 36), "♥", font=fh, fill="white")
    d.text((W - 230, H + band - 32), PAGE_NAME, font=fs, fill=(180, 180, 180))
    mask = Image.new("L", (W, H + band), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, H + band], 40, fill=255)
    final = Image.new("RGB", (W, H + band), BLACK)
    final.paste(canvas, (0, 0), mask)
    final.save(out, format="JPEG", quality=90)

def to_b64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

def feed_entries():
    items = []
    for f in FEEDS:
        try:
            items += feedparser.parse(f).entries[:20]
        except Exception:
            pass
    return items

def gn_entries(q):
    return feedparser.parse("https://news.google.com/rss/search?q=" + quote(q) +
                            "&hl=en-IN&gl=IN&ceid=IN:en").entries

def real_link(e):
    m = re.search(r'href="([^"]+)"', getattr(e, "description", "") or "")
    return m.group(1) if m else e.link

def build(name, title, img_url, ref=None, eng=0, khits=0):
    img = download(img_url, ref)
    if img is None:
        return None
    fname = f"prev_{random.randint(100000,999999)}.jpg"
    full = os.path.join(STATIC, fname)
    edit(img, title, full)
    try:
        with Image.open(full) as v:
            v.verify()
    except Exception:
        return None
    return {"category": name, "title": title, "image": to_b64(full), "file": fname,
            "ts": time.time(), "eng": eng, "khits": khits}

def fetch_category(name, keywords, entries, need=2):
    out = []
    for e in entries:
        if len(out) >= need:
            break
        title = clean(e.title)
        if not matches(title, keywords):
            continue
        u = img_from_entry(e) or og_image(e.link)
        if not u:
            continue
        r = build(name, title, u, e.link, 0, khit(title, keywords))
        if r:
            out.append(r)
    return out

def search_keyword(kw, need=5):
    out = []
    for e in gn_entries(kw):
        if len(out) >= need:
            break
        title = clean(e.title)
        rl = real_link(e)
        u = img_from_entry(e) or og_image(rl)
        if not u:
            continue
        r = build("Search: " + kw, title, u, rl)
        if r:
            out.append(r)
    return out

def trending_hashtags(n=5):
    raw = []
    try:
        r = requests.get("https://trends24.in/india/", headers=UA, timeout=20)
        r.encoding = "utf-8"
        raw = [x.strip() for x in re.findall(r'trend-link[^>]*>([^<]+)<', r.text) if x.strip()]
    except Exception as e:
        print("trend err:", e)
    if not raw:
        try:
            d = feedparser.parse("https://trends.google.com/trending/rss?geo=IN")
            raw = [clean(e.title) for e in d.entries]
        except Exception:
            pass
    tags = []
    for t in raw:
        t = t.strip().strip('"\'').lstrip("#").strip()
        t = "".join(c for c in t if c.isalnum())
        if 3 <= len(t) <= 22:
            tags.append("#" + t)
    tags = list(dict.fromkeys(tags))
    random.shuffle(tags)
    return tags[:n]

def fetch_twitter(need=2):
    out = []
    for trend in trending_hashtags(20):
        if len(out) >= need:
            break
        for e in gn_entries(trend.lstrip("#")):
            title = clean(e.title)
            rl = real_link(e)
            u = img_from_entry(e) or og_image(rl)
            if not u:
                continue
            r = build("Twitter Trend: " + trend, title, u, rl)
            if r:
                out.append(r)
                break
    return out

SUBS = ["india", "IndianNews", "Cricket", "bollywood", "IndiaSpeaks"]

def reddit_top(sub, limit=25):
    try:
        r = requests.get(f"https://www.reddit.com/r/{sub}/top.json",
                         params={"t": "day", "limit": limit}, headers=UA, timeout=20)
        return r.json()["data"]["children"]
    except Exception as e:
        print("reddit err:", e)
        return []

def reddit_img(d):
    p = d.get("preview", {}).get("images", [])
    if p:
        return html.unescape(p[0]["source"]["url"])
    if d.get("post_hint") == "image":
        return d.get("url")
    return None

def fetch_viral(need=20):
    posts = []
    for s in SUBS:
        for c in reddit_top(s, 25):
            d = c["data"]
            img = reddit_img(d)
            if not img:
                continue
            posts.append({"title": clean(d["title"]), "img": img,
                          "eng": d.get("score", 0) + d.get("num_comments", 0) * 2,
                          "url": "https://reddit.com" + d.get("permalink", "")})
    posts.sort(key=lambda x: x["eng"], reverse=True)
    out, seen = [], set()
    for p in posts:
        if len(out) >= need:
            break
        if p["title"] in seen:
            continue
        seen.add(p["title"])
        r = build("Viral", p["title"], p["img"], p["url"], eng=p["eng"])
        if r:
            out.append(r)
    return out

def fetch_one(c, entries, need):
    if c == "Twitter Trending":
        return fetch_twitter(need)
    if c == "Viral India":
        return fetch_viral(need)
    if c in CFG["categories"]:
        return fetch_category(c, CFG["categories"][c], entries, need)
    return []

def make_caption(topic):
    hooks = ["Kya hua? 😳", "Badi khabar!", "Ye dekho!", "Aaj ki khabar!"]
    words = [w.strip(".,!?'\"").capitalize() for w in topic.split() if len(w) > 4][:3]
    extra = " ".join("#" + w for w in words)
    trend = " ".join(trending_hashtags(5))
    return (f"{random.choice(hooks)}\n\n{topic}\n\n"
            f"Aapki kya raay hai? Comment karo 👇\n\n#News #Trending #India {extra} {trend}")

def post_to_fb(image_path, caption):
    try:
        with open(image_path, "rb") as f:
            r = requests.post(f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos",
                              data={"caption": caption, "access_token": TOKEN},
                              files={"source": f}, timeout=60)
        print("  fb:", r.status_code, r.text[:150])
        return r.status_code == 200
    except Exception as e:
        print("  fb err:", e)
        return False

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

def fetch_worker():
    while STATE["running"]:
        try:
            cats = STATE.get("cats") or list(CFG["categories"].keys())
            n = CFG["settings"]["per_fetch"]
            tags = trending_hashtags(15)
            entries = feed_entries()
            new = []
            for c in cats:
                new += fetch_one(c, entries, n)
            with LOCK:
                have = [p["title"] for p in STATE["pool"]]
                for it in new:
                    if it["title"] not in have:
                        it["score"] = score_item(it, tags)
                        STATE["pool"].append(it)
                STATE["pool"] = STATE["pool"][-60:]
            print("fetched:", len(new), "| pool:", len(STATE["pool"]))
        except Exception as e:
            print("fetch err:", e)
        time.sleep(CFG["settings"]["fetch_min"] * 60)

def post_worker():
    while STATE["running"]:
        with LOCK:
            pool = [p for p in STATE["pool"] if p["title"] not in STATE["posted"]]
        if not pool:
            time.sleep(20)
            continue
        best = max(pool, key=lambda x: x["score"])
        ok = post_to_fb(os.path.join(STATIC, best["file"]), make_caption(best["title"]))
        if ok:
            with LOCK:
                STATE["posted"].append(best["title"])
                STATE["posted"] = STATE["posted"][-80:]
                STATE["last_post"] = time.strftime("%H:%M") + " | " + best["title"][:40]
            delay = random.randint(CFG["settings"]["post_min"], CFG["settings"]["post_max"]) * 60
        else:
            STATE["last_post"] = time.strftime("%H:%M") + " | FAILED, retry"
            delay = 120
        STATE["next_post"] = time.strftime("%H:%M", time.localtime(time.time() + delay))
        print("posted:", ok, "| score:", best["score"], "| next in", delay // 60, "min")
        time.sleep(delay)

def start_auto():
    if STATE["running"]:
        return
    STATE["running"] = True
    threading.Thread(target=fetch_worker, daemon=True).start()
    threading.Thread(target=post_worker, daemon=True).start()
    print("AUTO STARTED | cats:", STATE["cats"])

if CFG.get("auto_on") and STATE["cats"]:
    start_auto()

PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>FB Bot</title>
<style>
body{background:#111;color:#eee;font-family:system-ui;margin:0;padding:12px;font-size:13px}
h1{font-size:17px;margin:0 0 8px}
h3{font-size:13px;margin:12px 0 6px;color:#ff9dd0}
.cats{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0}
label{background:#1e1e2a;padding:3px 8px;border-radius:12px;cursor:pointer;
font-size:11.5px;white-space:nowrap;line-height:1.6}
label input{transform:scale(.8);margin:0 2px 0 0;vertical-align:middle}
button{background:#ff69b4;color:#111;border:0;padding:6px 12px;border-radius:7px;
font-weight:bold;cursor:pointer;margin:0 5px 5px 0;font-size:12px}
input,select{padding:6px 10px;border-radius:7px;border:0;font-size:12px;background:#222;color:#eee}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:14px}
.card{background:#1a1a24;border-radius:10px;overflow:hidden}
.card img{width:100%;display:block;background:#333}
.card .b{padding:8px}
.card small{color:#ff9dd0;font-size:11px}
.card .t{font-size:12px;margin:4px 0}
#auto{background:#1a1a24;padding:8px 10px;border-radius:8px;margin-top:8px;font-size:12px;line-height:1.5}
#mng{background:#1a1a24;padding:10px;border-radius:8px;margin-top:8px;font-size:12px}
.row{margin:6px 0;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
#kwBox{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0;min-height:22px}
.chip{background:#2a2a3a;padding:3px 8px;border-radius:10px;font-size:11px}
.chip b{color:#ff7f7f;cursor:pointer;margin-left:6px}
</style></head><body>
<h1>FB Bot Control Panel</h1>

<h3>Categories (tick karo)</h3>
<div class="cats" id="cats"></div>
<button onclick="all()">Select All</button>
<button onclick="fetchAll()">Fetch News</button>
<button onclick="startAuto()">Start Auto</button>
<button onclick="stopAuto()">Stop Auto</button>
<button onclick="postNow()">Post Now</button>

<div class="row"><input id="kw" placeholder="keyword search" style="width:200px">
<button onclick="searchKw()">Search Keyword</button></div>

<div id="auto">Auto: OFF</div>

<div id="mng">
  <h3>Manage</h3>
  <div class="row">
    <select id="catSel" onchange="showKw()" style="min-width:200px"></select>
    <button onclick="delCat()">Delete category</button>
  </div>
  <div id="kwBox"></div>
  <div class="row">
    <input id="newkw" placeholder="naya keyword" style="width:180px">
    <button onclick="addKw()">+ Keyword add</button>
  </div>
  <div class="row" style="border-top:1px solid #333;padding-top:8px">
    <input id="newname" placeholder="nayi category ka naam" style="width:180px">
    <input id="newkeys" placeholder="keywords comma separated" style="width:260px">
    <button onclick="addCat()">Create category</button>
  </div>
  <div class="row" style="border-top:1px solid #333;padding-top:8px">
    fetch(min) <input id="s_fetch" type="number" style="width:55px">
    post min <input id="s_pmin" type="number" style="width:55px">
    post max <input id="s_pmax" type="number" style="width:55px">
    per fetch <input id="s_pf" type="number" style="width:55px">
    <button onclick="saveSet()">Save</button>
  </div>
</div>

<div id="status" style="margin-top:12px;color:#9f9"></div>
<div id="grid"></div>

<script>
let CFG={};
function all(){document.querySelectorAll('.cat').forEach(c=>c.checked=true)}
function render(data){
  document.getElementById('status').textContent=data.length+' images ready';
  const g=document.getElementById('grid'); g.innerHTML='';
  data.forEach(it=>{
    const d=document.createElement('div'); d.className='card';
    d.innerHTML='<img src="'+it.image+'" onerror="this.replaceWith(document.createTextNode(\\'[no image]\\'))"><div class="b"><small>'+it.category+
      '</small><div class="t">'+it.title+'</div><button onclick="post(this)">Post to FB</button></div>';
    d.dataset.title=it.title; d.dataset.file=it.file;
    g.appendChild(d);
  });
}
async function loadCfg(keep){
  CFG=await (await fetch('/config')).json();
  const c=document.getElementById('cats'); c.innerHTML='';
  Object.keys(CFG.categories).forEach(n=>{
    const l=document.createElement('label');
    l.innerHTML='<input type="checkbox" class="cat" value="'+n+'"> '+n;
    l.querySelector('input').onchange=selChanged;
    if((CFG.selected||[]).includes(n)) l.querySelector('input').checked=true;
    c.appendChild(l);
  });
  const s=document.getElementById('catSel'); s.innerHTML='';
  Object.keys(CFG.categories).forEach(n=>{
    const o=document.createElement('option'); o.value=n; o.textContent=n; s.appendChild(o);
  });
  if(keep){ for(const o of s.options) if(o.value===keep) s.value=keep; }
  showKw();
  s_fetch.value=CFG.settings.fetch_min; s_pmin.value=CFG.settings.post_min;
  s_pmax.value=CFG.settings.post_max; s_pf.value=CFG.settings.per_fetch;
}
function showKw(){
  const n=document.getElementById('catSel').value;
  const box=document.getElementById('kwBox'); box.innerHTML='';
  if(!n){box.textContent='(koi category nahi)';return;}
  const list=CFG.categories[n]||[];
  if(!list.length){box.textContent='(koi keyword nahi — add karo)';return;}
  list.forEach((k,i)=>{
    const c=document.createElement('span'); c.className='chip'; c.textContent=k;
    const x=document.createElement('b'); x.textContent='x';
    x.onclick=()=>delKw(n,i);
    c.appendChild(x); box.appendChild(c);
  });
}
async function selChanged(){
  const cats=[...document.querySelectorAll('.cat:checked')].map(c=>c.value);
  await fetch('/select',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({categories:cats})});
}
async function addKw(){
  const n=document.getElementById('catSel').value, k=newkw.value.trim();
  if(!n||!k){alert('category aur keyword chuno');return;}
  await fetch('/config/keyword',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({category:n,keyword:k})});
  newkw.value=''; loadCfg(n);
}
async function delKw(cat,i){
  const k=CFG.categories[cat][i];
  await fetch('/config/keyword/del',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({category:cat,keyword:k})});
  loadCfg(cat);
}
async function addCat(){
  const name=newname.value.trim();
  if(!name){alert('naam likho');return;}
  await fetch('/config/category',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:name,keywords:newkeys.value.trim()})});
  newname.value=''; newkeys.value=''; loadCfg(name);
}
async function delCat(){
  const n=document.getElementById('catSel').value;
  if(!n) return;
  if(!confirm(n+' delete karun?')) return;
  await fetch('/config/category/'+encodeURIComponent(n),{method:'DELETE'}); loadCfg();
}
async function saveSet(){
  await fetch('/config/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({fetch_min:s_fetch.value,post_min:s_pmin.value,
      post_max:s_pmax.value,per_fetch:s_pf.value})});
  alert('saved'); loadCfg();
}
async function fetchAll(){
  const cats=[...document.querySelectorAll('.cat:checked')].map(c=>c.value);
  if(!cats.length){alert('category select karo');return;}
  document.getElementById('status').textContent='Fetching...';
  const r=await fetch('/fetch',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({categories:cats})});
  render(await r.json());
}
async function searchKw(){
  const kw=document.getElementById('kw').value.trim();
  if(!kw){alert('keyword likho');return;}
  document.getElementById('status').textContent='Searching...';
  const r=await fetch('/search',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({keyword:kw})});
  render(await r.json());
}
async function startAuto(){
  const cats=[...document.querySelectorAll('.cat:checked')].map(c=>c.value);
  if(!cats.length){alert('category select karo');return;}
  await fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({categories:cats})});
  poll();
}
async function stopAuto(){ await fetch('/stop',{method:'POST'}); poll(); }
async function postNow(){
  const r=await fetch('/postnow',{method:'POST'}); const d=await r.json();
  alert(d.ok?('Posted: '+d.title):'Fail: '+(d.msg||'')); poll();
}
async function poll(){
  const r=await fetch('/status'); const d=await r.json();
  document.getElementById('auto').innerHTML='<b>Auto: '+(d.running?'<span style="color:#7f7">ON</span>':'OFF')+
    '</b> | Pool: '+d.pool+' | Last: '+(d.last_post||'-')+' | Next: '+(d.next_post||'-')+
    '<br><small>Posted: '+(d.posted.join(' || ')||'-')+'</small>';
  if(d.running) setTimeout(poll, 15000);
}
async function post(btn){
  const c=btn.closest('.card'); btn.textContent='Posting...';
  const r=await fetch('/post',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({title:c.dataset.title,file:c.dataset.file})});
  const d=await r.json(); btn.textContent=d.ok?'Posted ✓':'Failed ✗';
}
loadCfg(); poll();
</script></body></html>
"""

@app.route("/img/<fn>")
def img(fn):
    return send_from_directory(STATIC, fn)

@app.route("/")
def home():
    return render_template_string(PAGE)

@app.route("/config")
def get_config():
    return jsonify(CFG)

@app.route("/config/category", methods=["POST"])
def add_category():
    d = request.json
    name = d.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "msg": "name khali"})
    CFG["categories"][name] = [k.strip() for k in d.get("keywords", "").split(",") if k.strip()]
    save_config()
    return jsonify({"ok": True})

@app.route("/config/category/<name>", methods=["DELETE"])
def del_category(name):
    CFG["categories"].pop(name, None)
    save_config()
    return jsonify({"ok": True})

@app.route("/config/keyword", methods=["POST"])
def add_keyword():
    d = request.json
    cat, kw = d.get("category"), d.get("keyword", "").strip()
    if cat in CFG["categories"] and kw and kw not in CFG["categories"][cat]:
        CFG["categories"][cat].append(kw)
        save_config()
    return jsonify({"ok": True})

@app.route("/config/keyword/del", methods=["POST"])
def del_keyword():
    d = request.json
    cat, kw = d.get("category"), d.get("keyword")
    if cat in CFG["categories"] and kw in CFG["categories"][cat]:
        CFG["categories"][cat].remove(kw)
        save_config()
    return jsonify({"ok": True})

@app.route("/config/settings", methods=["POST"])
def set_settings():
    for k in ("fetch_min", "post_min", "post_max", "per_fetch"):
        try:
            CFG["settings"][k] = int(request.json[k])
        except Exception:
            pass
    save_config()
    return jsonify({"ok": True})

@app.route("/fetch", methods=["POST"])
def fetch():
    cats = request.json.get("categories", [])
    entries = feed_entries()
    result = []
    for c in cats:
        result += fetch_one(c, entries, CFG["settings"]["per_fetch"])
    return jsonify(result)

@app.route("/search", methods=["POST"])
def search():
    kw = request.json.get("keyword", "").strip()
    return jsonify(search_keyword(kw, 5) if kw else [])

@app.route("/start", methods=["POST"])
def start():
    cats = request.json.get("categories", [])
    if not cats:
        return jsonify({"ok": False})
    STATE["cats"] = cats
    CFG["selected"] = cats
    CFG["auto_on"] = True
    save_config()
    start_auto()
    return jsonify({"ok": True})

@app.route("/stop", methods=["POST"])
def stop():
    STATE["running"] = False
    CFG["auto_on"] = False
    save_config()
    return jsonify({"ok": True})

@app.route("/select", methods=["POST"])
def select():
    STATE["cats"] = request.json.get("categories", [])
    CFG["selected"] = STATE["cats"]
    save_config()
    return jsonify({"ok": True})

@app.route("/postnow", methods=["POST"])
def postnow():
    with LOCK:
        pool = [p for p in STATE["pool"] if p["title"] not in STATE["posted"]]
    if not pool:
        return jsonify({"ok": False, "msg": "pool khali"})
    best = max(pool, key=lambda x: x["score"])
    ok = post_to_fb(os.path.join(STATIC, best["file"]), make_caption(best["title"]))
    if ok:
        with LOCK:
            STATE["posted"].append(best["title"])
    return jsonify({"ok": ok, "title": best["title"]})

@app.route("/status")
def status():
    with LOCK:
        return jsonify({"running": STATE["running"], "pool": len(STATE["pool"]),
                        "posted": STATE["posted"][-5:], "last_post": STATE["last_post"],
                        "next_post": STATE["next_post"]})

@app.route("/post", methods=["POST"])
def post():
    d = request.json
    path = os.path.join(STATIC, d["file"])
    return jsonify({"ok": post_to_fb(path, make_caption(d["title"]))})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))