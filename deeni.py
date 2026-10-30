import os, sys, json, time, random, threading

from flask import Blueprint, jsonify, request, render_template_string
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

bp = Blueprint("deeni", __name__)
BASE = os.path.dirname(os.path.abspath(__file__))
ITEMS_FILE = os.path.join(BASE, "deeni.json")
BG_DIR = os.path.join(BASE, "deeni_bg")
LOCK = threading.Lock()
STARTED = False
NEXT = {}

GOLD = (212, 175, 55)
FOOT = "Follow to get daily new hadiths"

CATS = ("jahannam", "jannat", "qabr", "aam")

FALLBACK = {
    "jahannam": ((38, 8, 4), (8, 2, 2)),
    "jannat": ((10, 42, 26), (4, 14, 10)),
    "qabr": ((28, 28, 32), (6, 6, 8)),
    "aam": ((14, 26, 34), (4, 8, 12)),
}

KEY = {
    "jahannam": ("jahannam", "aag", "azab", "halaak", "paseena", "sakht",
                 "zulm", "andhera", "hisaab", "qayamat", "dozakh", "sood",
                 "halka", "wazan", "qatl", "gheebat"),
    "jannat": ("jannat", "bahisht", "bahaar", "baagh", "khushbu", "hoor",
               "nemat", "neki", "sadqa", "reham", "muskura"),
    "qabr": ("qabr", "maut", "kafan", "dafan", "qabristan", "marne", "murdar",
             "marhoom"),
}


def A():
    m = sys.modules.get("__main__")
    if m and hasattr(m, "get_page"):
        return m
    import app
    return app


def items():
    try:
        with open(ITEMS_FILE, encoding="utf-8") as f:
            return json.load(f).get("items", [])
    except Exception:
        return []


def pick(pool, used):
    left = [x for x in pool if x["id"] not in used]
    return random.choice(left) if left else random.choice(pool)


def category(text):
    t = text.lower()
    for c in ("jahannam", "jannat", "qabr"):
        if any(k in t for k in KEY[c]):
            return c
    return "aam"


def bg_files(cat):
    out = []
    for c in (cat, "aam"):
        d = os.path.join(BG_DIR, c)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                out.append(os.path.join(d, f))
        if out:
            break
    return out


def wrap(d, text, fnt, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def background(cat):
    files = bg_files(cat)
    if files:
        try:
            im = Image.open(random.choice(files)).convert("RGB")
            s = 1080 / min(im.size)
            im = im.resize((max(1080, int(im.size[0] * s)),
                            max(1080, int(im.size[1] * s))), Image.LANCZOS)
            w, h = im.size
            x = random.randint(0, max(0, w - 1080))
            y = random.randint(0, max(0, h - 1080))
            im = im.crop((x, y, x + 1080, y + 1080))
            im = ImageEnhance.Brightness(im).enhance(0.78)
            im = ImageEnhance.Color(im).enhance(1.05)
            return im
        except Exception:
            pass

    top, bot = FALLBACK[cat]
    im = Image.new("RGB", (1080, 1080), top)
    d = ImageDraw.Draw(im)
    for y in range(1080):
        t = y / 1080
        d.line([(0, y), (1080, y)],
               fill=(int(top[0] + (bot[0] - top[0]) * t),
                     int(top[1] + (bot[1] - top[1]) * t),
                     int(top[2] + (bot[2] - top[2]) * t)))

    if cat == "jahannam":
        for _ in range(320):
            x, y = random.randint(0, 1080), random.randint(500, 1080)
            r = random.randint(1, 4)
            d.ellipse([x, y, x + r, y + r],
                      fill=(random.randint(180, 255),
                            random.randint(70, 170),
                            random.randint(0, 50)))
        im = im.filter(ImageFilter.GaussianBlur(0.6))
    elif cat == "jannat":
        for _ in range(180):
            x, y = random.randint(0, 1080), random.randint(0, 1080)
            r = random.randint(2, 7)
            d.ellipse([x, y, x + r, y + r],
                      fill=(random.randint(80, 170),
                            random.randint(150, 230),
                            random.randint(80, 150)))
        im = im.filter(ImageFilter.GaussianBlur(0.8))
    elif cat == "qabr":
        for _ in range(60):
            x = random.randint(0, 1080)
            h = random.randint(80, 300)
            w = random.randint(30, 80)
            d.rectangle([x, 1080 - h, x + w, 1080],
                        fill=(random.randint(18, 34),) * 3)
        im = im.filter(ImageFilter.GaussianBlur(1.0))
    else:
        for _ in range(120):
            x, y = random.randint(0, 1080), random.randint(0, 500)
            r = random.randint(1, 2)
            d.ellipse([x, y, x + r, y + r], fill=(220, 225, 240))
    return im


def build(path, used=None):
    a = A()
    pool = items()
    if not pool:
        return False, "deeni.json khali hai"
    it = pick(pool, used or [])
    cat = category(it["text"])

    img = background(cat)

    scrim = Image.new("L", (1080, 1080), 0)
    sd = ImageDraw.Draw(scrim)
    for y in range(1080):
        v = int(120 + 95 * (abs(y - 540) / 540))
        sd.line([(0, y), (1080, y)], fill=v)
    img = Image.composite(Image.new("RGB", (1080, 1080), (0, 0, 0)), img, scrim)

    d = ImageDraw.Draw(img)
    m = 46
    d.rounded_rectangle([m, m, 1080 - m, 1080 - m], 26, outline=GOLD, width=3)
    d.rounded_rectangle([m + 12, m + 12, 1080 - m - 12, 1080 - m - 12], 20,
                        outline=(120, 100, 40), width=1)

    body = a.font(56, True, False)
    ref = a.font(28, False, False)
    head = a.font(30, True, False)
    foot = a.font(23, False, False)

    d.text((540, m + 58), "HADEES-E-NABAWI", font=head, fill=GOLD, anchor="mm")

    lines = wrap(d, it["text"], body, 1080 - 2 * m - 90)[:8]
    lh = 74
    y = (1080 - len(lines) * lh) // 2 - 6
    for ln in lines:
        d.text((540, y + 2), ln, font=body, fill=(0, 0, 0), anchor="mm")
        d.text((540, y), ln, font=body, fill=(250, 248, 242), anchor="mm")
        y += lh

    d.line([(540 - 70, y + 24), (540 + 70, y + 24)], fill=GOLD, width=2)
    d.text((540, y + 70), it.get("ref", ""), font=ref, fill=GOLD, anchor="mm")

    fy = 1080 - m - 42
    d.line([(540 - 120, fy - 26), (540 + 120, fy - 26)], fill=(110, 95, 45), width=1)
    d.text((540, fy), FOOT, font=foot, fill=(196, 186, 158), anchor="mm")

    if path:
        img.save(path, quality=93, subsampling=0, optimize=True)
    return True, it


def caption(it):
    return (f"{it['text']}\n\n— {it.get('ref', '')}\n\n"
            f"Roz nayi hadith ke liye page follow karo 🤲\n\n"
            f"#Hadith #Hadees #Islam #Deen #Sunnah #Jannat #Jahannam #Hikmah")


def post_one(pid):
    a = A()
    p = a.get_page(pid)
    if not p or not p.get("token") or not p.get("page_id"):
        return False, "token ya page_id nahi"
    fn = f"deeni_{pid}_{random.randint(100000, 999999)}.jpg"
    full = os.path.join(a.OUT, fn)
    ok, it = build(full, list(p.get("deeni_used") or []))
    if not ok:
        return False, it
    sent, res = a.fb_post(p, full, caption(it))
    with LOCK:
        if sent:
            u = list(p.get("deeni_used") or [])
            u.append(it["id"])
            p["deeni_used"] = u[-80:]
            p["deeni_msg"] = "Posted: " + it.get("ref", "")
            p["deeni_last"] = time.strftime("%d-%m %H:%M")
        else:
            p["deeni_msg"] = "Fail: " + str(res)[:60]
        a.cfg_save(a.CFG)
    return sent, (res if not sent else it.get("ref", ""))


def gap(p):
    lo = max(1, int(p.get("deeni_min") or 45))
    hi = max(lo, int(p.get("deeni_max") or 60))
    return random.randint(lo, hi)


def loop():
    while True:
        try:
            a = A()
            now = time.time()
            for p in list(a.CFG["pages"]):
                if not p.get("deeni"):
                    continue
                pid = p["id"]
                nxt = NEXT.get(pid)
                if nxt is None:
                    NEXT[pid] = now + gap(p) * 60
                    continue
                if now < nxt:
                    continue
                ok, msg = post_one(pid)
                NEXT[pid] = time.time() + gap(p) * 60
                p["deeni_next"] = time.strftime("%H:%M", time.localtime(NEXT[pid]))
                a.cfg_save(a.CFG)
                print("[deeni]", p["name"], ok, msg)
        except Exception as e:
            print("[deeni err]", repr(e)[:120])
        time.sleep(20)


def boot():
    global STARTED
    if STARTED:
        return
    STARTED = True
    threading.Thread(target=loop, daemon=True).start()
    print("[deeni] scheduler chalu")


@bp.route("/deeni")
def page():
    a = A()
    return render_template_string(TPL, cfg=a.CFG)


@bp.route("/deeni/preview")
def preview():
    a = A()
    fn = f"deeni_prev_{random.randint(100000, 999999)}.jpg"
    ok, it = build(os.path.join(a.OUT, fn))
    if not ok:
        return jsonify({"ok": False, "msg": it})
    return jsonify({"ok": True, "file": fn, "ref": it.get("ref", ""),
                    "cat": category(it["text"])})


@bp.route("/deeni/<pid>/toggle", methods=["POST"])
def toggle(pid):
    a = A()
    p = a.get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    if not p.get("token"):
        return jsonify({"ok": False, "msg": "❌ pehle is page pe token save karo"})
    p["deeni"] = not p.get("deeni")
    p.setdefault("deeni_min", 45)
    p.setdefault("deeni_max", 60)
    if p["deeni"]:
        NEXT[pid] = time.time() + gap(p) * 60
    else:
        NEXT.pop(pid, None)
    a.cfg_save(a.CFG)
    return jsonify({"ok": True, "msg": "deeni " + ("ON" if p["deeni"] else "OFF")})


@bp.route("/deeni/<pid>/gap", methods=["POST"])
def set_gap(pid):
    a = A()
    p = a.get_page(pid)
    if not p:
        return jsonify({"ok": False, "msg": "page nahi mila"})
    d = request.json or {}
    try:
        lo = max(1, min(720, int(d.get("min", 45))))
        hi = max(lo, min(720, int(d.get("max", 60))))
    except Exception:
        lo, hi = 45, 60
    p["deeni_min"], p["deeni_max"] = lo, hi
    if p.get("deeni"):
        NEXT[pid] = time.time() + gap(p) * 60
    a.cfg_save(a.CFG)
    return jsonify({"ok": True, "msg": f"random {lo}-{hi} min"})


@bp.route("/deeni/<pid>/post", methods=["POST"])
def post_now(pid):
    ok, msg = post_one(pid)
    return jsonify({"ok": ok, "msg": msg})


@bp.route("/deeni/bg")
def bg_info():
    out = {}
    for c in CATS:
        d = os.path.join(BG_DIR, c)
        n = 0
        if os.path.isdir(d):
            n = len([f for f in os.listdir(d)
                     if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])
        out[c] = n
    return jsonify(out)


TPL = """<!doctype html><html><head><meta charset="utf-8"><title>Deeni</title>
<style>
body{background:#0b120e;color:#e8e4d8;font-family:system-ui;margin:0;padding:16px;max-width:780px}
h1{font-size:17px;color:#d4af37}
.p{background:#121a14;border:1px solid #2a3520;border-radius:10px;padding:10px;margin-top:10px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0}
button{background:#1d2a20;color:#e8e4d8;border:1px solid #3a4a30;padding:6px 11px;
border-radius:7px;font-size:12px;cursor:pointer}
button.on{background:#6b2f2f;border-color:#8f4a4a}
input{background:#0e150f;border:1px solid #2a3520;color:#e8e4d8;padding:6px;border-radius:6px}
.st{font-size:11px;color:#9f9;min-height:14px}
.nx{font-size:11px;color:#c9a44a}
a{color:#d4af37;font-size:12px}
img{max-width:100%;border-radius:8px;margin-top:8px}
#log{font-size:11px;font-family:monospace;background:#0e150f;border:1px solid #2a3520;
border-radius:8px;padding:8px;max-height:150px;overflow:auto;margin-top:10px;white-space:pre-wrap}
.bg{font-size:11px;color:#8a9a80}
</style></head><body>
<h1>Deeni — random interval hadith post</h1>
<div style="font-size:12px;color:#8a9a80">ON karo → min-max ke beech random gap pe post,
jab tak OFF na karo. <a href="/">← main panel</a></div>

{% for p in cfg.pages %}
<div class="p">
  <b>{{p.name}}</b> <span style="font-size:11px;color:#666">{{p.page_id or "no token"}}</span>
  <div class="row">
    <button class="{{'on' if p.deeni}}" onclick="tog('{{p.id}}')">
      Deeni {{'ON' if p.deeni else 'OFF'}}</button>
    <input type="number" class="mn" value="{{p.deeni_min or 45}}" style="width:64px">-
    <input type="number" class="mx" value="{{p.deeni_max or 60}}" style="width:64px"> min
    <button onclick="saveG('{{p.id}}')">Set</button>
    <button onclick="postN('{{p.id}}',this)">Post now</button>
  </div>
  <div class="nx">last: {{p.deeni_last or '-'}} · next: {{p.deeni_next or '-'}}</div>
  <div class="st" data-st="{{p.id}}">{{p.deeni_msg or ''}}</div>
</div>
{% endfor %}

<div class="row" style="margin-top:14px">
  <button onclick="prev()">Preview card</button>
  <button onclick="bgInfo()">BG files</button>
</div>
<div class="bg" id="bgstat"></div>
<div id="pv"></div>
<div id="log"></div>

<script>
const J={'Content-Type':'application/json'};
function L(m){const l=document.getElementById('log');
  l.textContent='['+new Date().toLocaleTimeString()+'] '+m+'\\n'+l.textContent;}
async function call(u,m,b){
  try{
    const r=await fetch(u,{method:m||'POST',headers:J,body:b?JSON.stringify(b):null});
    const t=await r.text();let d=null;try{d=JSON.parse(t);}catch(e){}
    if(!d){L(u+' HTTP '+r.status+' '+t.slice(0,120));return{ok:false,msg:'HTTP '+r.status};}
    L(u+' -> '+r.status+' '+JSON.stringify(d).slice(0,120));
    return d;
  }catch(e){L(u+' NET '+e.name);return{ok:false,msg:'NET '+e.name};}
}
async function tog(id){const d=await call('/deeni/'+id+'/toggle');
  if(d.ok)location.reload();else alert(d.msg);}
async function saveG(id){
  const box=document.querySelector('.mn').closest('.p');
  const d=await call('/deeni/'+id+'/gap','POST',
    {min:box.querySelector('.mn').value,max:box.querySelector('.mx').value});
  document.querySelector('[data-st="'+id+'"]').textContent=d.msg;}
async function postN(id,b){
  b.disabled=true;b.textContent='...';
  const d=await call('/deeni/'+id+'/post');
  b.disabled=false;b.textContent='Post now';
  document.querySelector('[data-st="'+id+'"]').textContent=(d.ok?'✅ ':'❌ ')+d.msg;}
async function prev(){
  const r=await fetch('/deeni/preview');const d=await r.json();
  if(d.ok)document.getElementById('pv').innerHTML=
    '<img src="/img/'+d.file+'"><div class="bg">cat: '+d.cat+'</div>';
  else L('preview fail '+d.msg);}
async function bgInfo(){
  const r=await fetch('/deeni/bg');const d=await r.json();
  document.getElementById('bgstat').textContent=
    Object.entries(d).map(([k,v])=>k+': '+v).join(' · ');}
L('ready');
</script></body></html>"""

boot()
