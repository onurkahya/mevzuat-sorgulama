from flask import Flask, render_template, jsonify
import requests, re, json, io, os
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
BASE = "https://www.mevzuat.gov.tr"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

MEVZUATLAR = {
    "mesafeli-sozlesmeler": {
        "ad": "MESAFELİ SÖZLEŞMELER YÖNETMELİĞİ",
        "no": "20237",
        "tur": "7",
        "tertip": "5",
        "kaynak": "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20237&MevzuatTur=7&MevzuatTertip=5"
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.mevzuat.gov.tr/"
}


def safe_get(url, timeout=30):
    """
    Önce normal SSL doğrulamasıyla bağlanır.
    Yalnızca sertifika doğrulama hatasında mevzuat.gov.tr için verify=False ile tekrar dener.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r, False
    except requests.exceptions.SSLError:
        # Yalnızca resmi mevzuat.gov.tr alan adı için kontrollü fallback
        if not url.lower().startswith("https://www.mevzuat.gov.tr/"):
            raise
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        return r, True

def now():
    return datetime.now().isoformat(timespec="seconds")

def cache_path(key):
    return CACHE_DIR / f"{key}.json"

def save_cache(key, data):
    payload = dict(data)
    payload["cache_time"] = now()
    cache_path(key).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def load_cache(key):
    p = cache_path(key)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def normalize_text(s):
    s = s.replace("\xa0", " ")
    s = re.sub(r"\r\n?", "\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

SECTION_WORDS = (
    "BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|"
    "DOKUZUNCU|ONUNCU|ON BİRİNCİ|ON İKİNCİ|ON ÜÇÜNCÜ|ON DÖRDÜNCÜ|"
    "ON BEŞİNCİ|ON ALTINCI|ON YEDİNCİ|ON SEKİZİNCİ|ON DOKUZUNCU|YİRMİNCİ"
)

SECTION_RE = re.compile(
    rf"(?im)^[ \t]*(?:{SECTION_WORDS})\s+BÖLÜM(?:\s*$|\s+.*$)"
)

ARTICLE_RE = re.compile(
    r"(?im)^[ \t]*(?P<title>(?:GEÇİCİ\s+)?MADDE\s+(?P<num>\d+(?:/[A-ZÇĞİÖŞÜ])?))"
    r"\s*[-–—:]?\s*"
)

def clean_line(line):
    return re.sub(r"\s+", " ", line.replace("\xa0", " ")).strip()

def extract_heading_before_article(text, article_start):
    """
    MADDE satırının hemen önündeki madde başlığını alır.
    Bölüm başlıklarını veya önceki maddenin son cümlesini başlık olarak kabul etmez.
    """
    prefix = text[:article_start]
    lines = [clean_line(x) for x in prefix.splitlines()]
    lines = [x for x in lines if x]

    if not lines:
        return ""

    candidate = lines[-1]

    # "ÜÇÜNCÜ BÖLÜM" gibi yapısal başlıklar madde başlığı değildir.
    if re.fullmatch(rf"(?:{SECTION_WORDS})\s+BÖLÜM", candidate, flags=re.I):
        return ""

    # Resmî Gazete / sayfa dipnotu gibi satırları başlık yapma.
    bad_prefixes = ("RESMÎ GAZETE", "RESMI GAZETE", "SAYFA ", "EK-")
    if candidate.upper().startswith(bad_prefixes):
        return ""

    # Önceki maddenin uzun bitiş cümlesini yanlışlıkla başlık alma.
    # Madde başlıkları genellikle kısa ve nokta ile bitmez.
    if len(candidate) > 160 or candidate.endswith("."):
        return ""

    return candidate

def trim_structural_tail(raw):
    """
    Bir maddenin sonuna sarkan 'ÜÇÜNCÜ BÖLÜM' vb. yapısal başlıkları
    ve onlardan sonraki metni maddenin dışına çıkarır.
    """
    m = SECTION_RE.search(raw)
    if m:
        raw = raw[:m.start()]
    return raw.strip()

def format_article_text(raw):
    """
    HTML/PDF kaynaklı gereksiz satır kırılmalarını temizler.
    Fıkraları ve bentleri okunabilir biçimde ayrı satırlarda tutar.
    """
    raw = trim_structural_tail(raw)
    raw = raw.replace("\xa0", " ")

    # Önce bütün yapay satır kırılmalarını boşluğa çevir.
    raw = re.sub(r"\s+", " ", raw).strip()

    # MADDE başlığından sonra ilk fıkrayı aynı satır düzeninde bırak.
    raw = re.sub(r"\s+(?=\(\d+\)\s)", "\n\n", raw)

    # Bentleri ayrı satıra al: a), b), c)...
    raw = re.sub(
        r"\s+(?=(?:[a-zçğıöşü])\)\s)",
        "\n",
        raw,
        flags=re.I
    )

    # Alt bentleri ayrı satıra al: 1), 2), 3)...
    raw = re.sub(r"\s+(?=\d+\)\s)", "\n", raw)

    # Değişiklik notlarını metinden koparmadan önceki boşlukları normalize et.
    raw = re.sub(r"[ \t]{2,}", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()

def split_articles(text):
    text = normalize_text(text)
    matches = list(ARTICLE_RE.finditer(text))
    articles = []

    for i, m in enumerate(matches):
        raw_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_chunk = text[m.start():raw_end]

        # Sonraki bölüm başlığını mevcut maddeye dahil etme.
        raw_chunk = trim_structural_tail(raw_chunk)

        madde_title = re.sub(r"\s+", " ", m.group("title")).strip()
        num = m.group("num")
        is_temp = madde_title.upper().startswith("GEÇİCİ")

        heading = extract_heading_before_article(text, m.start())

        formatted = format_article_text(raw_chunk)

        articles.append({
            "id": ("g-" if is_temp else "") + num,
            "etiket": ("Geçici Madde " if is_temp else "Madde ") + num,
            "baslik": heading,
            "metin": formatted
        })

    return articles

def fetch_live_html(item):
    url = (
        f"{BASE}/anasayfa/MevzuatFihristDetayIframe"
        f"?MevzuatTur={item['tur']}&MevzuatNo={item['no']}&MevzuatTertip={item['tertip']}"
    )
    r, ssl_fallback = safe_get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    articles = split_articles(soup.get_text("\n"))
    if not articles:
        raise RuntimeError("Canlı HTML geldi ancak madde başlıkları ayrıştırılamadı.")
    return {
        "articles": articles,
        "source_type": "canli_html",
        "source_url": url,
        "fetched_at": now(),
        "ssl_fallback": ssl_fallback
    }

def fetch_official_pdf(item):
    url = (
        f"{BASE}/File/GeneratePdf"
        f"?mevzuatNo={item['no']}&mevzuatTur={item['tur']}&mevzuatTertip={item['tertip']}"
    )
    r, ssl_fallback = safe_get(url, timeout=45)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise RuntimeError("Resmî PDF adresi PDF döndürmedi.")
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(r.content))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    articles = split_articles(text)
    if not articles:
        raise RuntimeError("Resmî PDF geldi ancak madde başlıkları ayrıştırılamadı.")
    return {
        "articles": articles,
        "source_type": "canli_pdf",
        "source_url": url,
        "fetched_at": now(),
        "ssl_fallback": ssl_fallback
    }

def get_legislation(key):
    item = MEVZUATLAR[key]
    errors = []

    for getter in (fetch_live_html, fetch_official_pdf):
        try:
            data = getter(item)
            data["ad"] = item["ad"]
            data["kaynak"] = item["kaynak"]
            data["from_cache"] = False
            save_cache(key, data)
            return data
        except Exception as e:
            errors.append(str(e))

    cached = load_cache(key)
    if cached:
        cached["from_cache"] = True
        cached["live_errors"] = errors
        return cached

    raise RuntimeError(" | ".join(errors) if errors else "Mevzuat verisi alınamadı.")

@app.route("/")
def index():
    return render_template("index.html", mevzuatlar=MEVZUATLAR)

@app.route("/api/mevzuat/<key>")
def api_mevzuat(key):
    if key not in MEVZUATLAR:
        return jsonify({"ok": False, "error": "Mevzuat bulunamadı."}), 404
    try:
        return jsonify({"ok": True, **get_legislation(key)})
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "source": "mevzuat.gov.tr"
        }), 502

@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "mevzuat-sorgulama", "time": now()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port)
