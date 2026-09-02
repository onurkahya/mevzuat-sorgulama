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
    "6502-tuketici-kanunu": {"ad":"6502 SAYILI TÜKETİCİNİN KORUNMASI HAKKINDA KANUN","no":"6502","tur":"1","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6502&MevzuatTur=1&MevzuatTertip=5"},
    "abonelik-sozlesmeleri": {"ad":"ABONELİK SÖZLEŞMELERİ YÖNETMELİĞİ","no":"20480","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20480&MevzuatTur=7&MevzuatTertip=5"},
    "devre-tatil": {"ad":"DEVRE TATİL VE UZUN SÜRELİ TATİL HİZMETİ SÖZLEŞMELERİ YÖNETMELİĞİ","no":"20442","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20442&MevzuatTur=7&MevzuatTertip=5"},
    "dogrudan-satislar": {"ad":"DOĞRUDAN SATIŞLAR HAKKINDA YÖNETMELİK","no":"42526","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=42526&MevzuatTur=7&MevzuatTertip=5"},
    "finansal-hizmetler-mesafeli": {"ad":"FİNANSAL HİZMETLERE İLİŞKİN MESAFELİ SÖZLEŞMELER YÖNETMELİĞİ","no":"20495","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20495&MevzuatTur=7&MevzuatTertip=5"},
    "fiyat-etiketi": {"ad":"FİYAT ETİKETİ YÖNETMELİĞİ","no":"19819","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19819&MevzuatTur=7&MevzuatTertip=5"},
    "garanti-belgesi": {"ad":"GARANTİ BELGESİ YÖNETMELİĞİ","no":"19782","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19782&MevzuatTur=7&MevzuatTertip=5"},
    "isyeri-disinda-kurulan": {"ad":"İŞ YERİ DIŞINDA KURULAN SÖZLEŞMELER YÖNETMELİĞİ","no":"20444","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20444&MevzuatTur=7&MevzuatTertip=5"},
    "konut-finansmani": {"ad":"KONUT FİNANSMANI SÖZLEŞMELERİ YÖNETMELİĞİ","no":"20793","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20793&MevzuatTur=7&MevzuatTertip=5"},
    "mesafeli-sozlesmeler": {"ad":"MESAFELİ SÖZLEŞMELER YÖNETMELİĞİ","no":"20237","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20237&MevzuatTur=7&MevzuatTertip=5"},
    "on-odemeli-konut": {"ad":"ÖN ÖDEMELİ KONUT SATIŞLARI HAKKINDA YÖNETMELİK","no":"20238","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20238&MevzuatTur=7&MevzuatTertip=5"},
    "paket-tur": {"ad":"PAKET TUR SÖZLEŞMELERİ YÖNETMELİĞİ","no":"20446","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20446&MevzuatTur=7&MevzuatTertip=5"},
    "satis-sonrasi-hizmetler": {"ad":"SATIŞ SONRASI HİZMETLER YÖNETMELİĞİ","no":"19783","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19783&MevzuatTur=7&MevzuatTertip=5"},
    "sureli-yayin-promosyon": {"ad":"SÜRELİ YAYIN KURULUŞLARINCA DÜZENLENEN PROMOSYON UYGULAMALARINA İLİŞKİN YÖNETMELİK","no":"19800","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19800&MevzuatTur=7&MevzuatTertip=5"},
    "taksitle-satis": {"ad":"TAKSİTLE SATIŞ SÖZLEŞMELERİ HAKKINDA YÖNETMELİK","no":"20447","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20447&MevzuatTur=7&MevzuatTertip=5"},
    "tanitma-kullanma-kilavuzu": {"ad":"TANITMA VE KULLANMA KILAVUZU YÖNETMELİĞİ","no":"19784","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19784&MevzuatTur=7&MevzuatTertip=5"},
    "ticari-reklam": {"ad":"TİCARİ REKLAM VE HAKSIZ TİCARİ UYGULAMALAR YÖNETMELİĞİ","no":"20435","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20435&MevzuatTur=7&MevzuatTertip=5"},
    "tuketici-kredisi": {"ad":"TÜKETİCİ KREDİSİ SÖZLEŞMELERİ YÖNETMELİĞİ","no":"20767","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20767&MevzuatTur=7&MevzuatTertip=5"},
    "haksiz-sartlar": {"ad":"TÜKETİCİ SÖZLEŞMELERİNDEKİ HAKSIZ ŞARTLAR HAKKINDA YÖNETMELİK","no":"19798","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=19798&MevzuatTur=7&MevzuatTertip=5"},
    "yenilenmis-urunler": {"ad":"YENİLENMİŞ ÜRÜNLER HAKKINDA YÖNETMELİK","no":"46233","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=46233&MevzuatTur=7&MevzuatTertip=5"},
    "6585-perakende-kanunu": {"ad":"6585 SAYILI PERAKENDE TİCARETİN DÜZENLENMESİ HAKKINDA KANUN","no":"6585","tur":"1","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6585&MevzuatTur=1&MevzuatTertip=5"},
    "haksiz-fiyat": {"ad":"HAKSIZ FİYAT DEĞERLENDİRME KURULU YÖNETMELİĞİ","no":"34561","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=34561&MevzuatTur=7&MevzuatTertip=5"},
    "tasinmaz-ticareti": {"ad":"TAŞINMAZ TİCARETİ HAKKINDA YÖNETMELİK","no":"24645","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=24645&MevzuatTur=7&MevzuatTertip=5"},
    "motorlu-kara-ticareti": {"ad":"MOTORLU KARA TAŞITLARININ TİCARETİ HAKKINDA YÖNETMELİK","no":"40940","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=40940&MevzuatTur=7&MevzuatTertip=5"},
    "kuyum-ticareti": {"ad":"KUYUM TİCARETİ HAKKINDA YÖNETMELİK","no":"38527","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=38527&MevzuatTur=7&MevzuatTertip=5"},
    "alisveris-merkezleri": {"ad":"ALIŞVERİŞ MERKEZLERİ HAKKINDA YÖNETMELİK","no":"21431","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=21431&MevzuatTur=7&MevzuatTertip=5"},
    "perakende-ilke-kurallar": {"ad":"PERAKENDE TİCARETTE UYGULANACAK İLKE VE KURALLAR HAKKINDA YÖNETMELİK","no":"22722","tur":"7","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=22722&MevzuatTur=7&MevzuatTertip=5"},
    "6563-elektronik-ticaret": {"ad":"6563 SAYILI ELEKTRONİK TİCARETİN DÜZENLENMESİ HAKKINDA KANUN","no":"6563","tur":"1","tertip":"5","kaynak":"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6563&MevzuatTur=1&MevzuatTertip=5"}
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

ARTICLE_RE = re.compile(
    r"(?im)^[ \t]*(?P<title>(?:GEÇİCİ\s+)?MADDE\s+(?P<num>\d+(?:/[A-ZÇĞİÖŞÜ])?))"
    r"\s*[-–—:]?\s*"
)

SECTION_RE = re.compile(
    rf"(?im)^[ \t]*(?:{SECTION_WORDS})\s+BÖLÜM(?:\s*$|\s+.*$)"
)

def clean_line(line):
    return re.sub(r"\s+", " ", line.replace("\xa0", " ")).strip()

def is_structural_heading(line):
    u = line.upper().strip()
    if re.fullmatch(rf"(?:{SECTION_WORDS})\s+BÖLÜM", u):
        return True
    if u.endswith(" KISIM"):
        return True
    return False

def heading_span_before_article(text, article_start):
    """
    MADDE satırından hemen önceki madde başlığını bulur.
    Başlık iki veya daha fazla satıra bölünmüşse tamamını birlikte alır.
    Örn:
      Ön bilgilendirmeye ilişkin
      diğer yükümlülükler
      MADDE 8 -
    Bu durumda iki başlık satırının başlangıcı Madde 7'nin bitişidir.
    """
    prefix = text[:article_start]
    line_matches = list(re.finditer(r"(?m)^.*$", prefix))

    collected = []
    start_pos = article_start
    end_pos = article_start

    for lm in reversed(line_matches):
        candidate = clean_line(lm.group(0))

        if not candidate:
            # Başlık bloğunu toplamaya başladıysak boş satırda dur.
            if collected:
                break
            continue

        if is_structural_heading(candidate):
            break

        upper = candidate.upper()
        if upper.startswith(("RESMÎ GAZETE", "RESMI GAZETE", "SAYFA ")):
            if collected:
                break
            continue

        # Önceki madde gövdesine ulaştığımızı gösteren güçlü işaretler.
        if candidate.endswith((".", ";", "?", "!")):
            break
        if re.match(r"^\(\d+\)\s+", candidate):
            break
        if re.match(r"^[a-zçğıöşü]\)\s+", candidate, flags=re.I):
            break
        if re.match(r"(?i)^(?:GEÇİCİ\s+)?MADDE\s+\d+", candidate):
            break

        # Madde başlığı satırları genellikle kısa olur.
        if len(candidate) > 120:
            break

        collected.append(candidate)
        start_pos = lm.start()
        end_pos = max(end_pos, lm.end())

        # Başlığın 3 satırdan fazla olması beklenmez.
        if len(collected) >= 3:
            break

    if not collected:
        return "", article_start, article_start

    collected.reverse()
    heading = " ".join(collected)
    heading = re.sub(r"\s+", " ", heading).strip()
    return heading, start_pos, end_pos

def format_body(raw):
    # Kaynaktaki yapay satır sonlarını kaldır.
    raw = raw.replace("\xa0", " ")
    raw = re.sub(r"\s+", " ", raw).strip()

    # FIKRALAR:
    # Bir cümle . ! ? ile bittikten sonra gelen (2), (3), (4)... işaretlerini
    # mutlaka yeni satıra alır. İşaretin ardından "(Ek ibare...)" gibi bir
    # açıklama gelse bile çalışır.
    #
    # Değişiklik dipnotlarındaki "(Ek ibare...)(1)" ise öncesinde cümle sonu
    # bulunmadığı için yanlışlıkla yeni fıkra yapılmaz.
    raw = re.sub(r"(?<=[.!?])\s*(?=\(\d+\))", "\n", raw)

    # BENTLER:
    # a), b), c), ç)... bentlerini yeni satıra alır.
    raw = re.sub(
        r"(?<!^)\s+(?=(?:[a-zçğıöşü])\)\s+)",
        "\n",
        raw,
        flags=re.I
    )

    # 1), 2), 3) şeklindeki alt bentleri de yeni satıra al.
    raw = re.sub(
        r"(?<!^)\s+(?=\d+\)\s+)",
        "\n",
        raw
    )

    raw = re.sub(r"\n{2,}", "\n", raw)
    return raw.strip()

def split_articles(text):
    text = normalize_text(text)
    matches = list(ARTICLE_RE.finditer(text))
    headings = [heading_span_before_article(text, m.start()) for m in matches]
    articles = []

    for i, m in enumerate(matches):
        num = m.group("num")
        is_temp = m.group("title").upper().startswith("GEÇİCİ")
        heading, _, _ = headings[i]

        # KRİTİK: Mevcut madde, bir sonraki MADDE satırında değil,
        # bir sonraki maddenin başlığı başladığı yerde biter.
        if i + 1 < len(matches):
            next_heading, next_heading_start, _ = headings[i + 1]
            end = next_heading_start if next_heading else matches[i + 1].start()
        else:
            end = len(text)

        raw_body = text[m.end():end]

        # "ÜÇÜNCÜ BÖLÜM" vb. hiçbir durumda maddeye dahil edilmez.
        sec = SECTION_RE.search(raw_body)
        if sec:
            raw_body = raw_body[:sec.start()]

        body = format_body(raw_body)

        articles.append({
            "id": ("g-" if is_temp else "") + num,
            "etiket": ("Geçici Madde " if is_temp else "Madde ") + num,
            "baslik": heading,
            "madde_no": num,
            "gecici": is_temp,
            "metin": body
        })

    return articles


SUPERSCRIPT_MAP = str.maketrans({
    "0":"⁰", "1":"¹", "2":"²", "3":"³", "4":"⁴",
    "5":"⁵", "6":"⁶", "7":"⁷", "8":"⁸", "9":"⁹",
    "+":"⁺", "-":"⁻", "=":"⁼", "(":"⁽", ")":"⁾",
    "n":"ⁿ", "i":"ⁱ"
})

def to_superscript_text(value):
    value = re.sub(r"\s+", "", value or "")
    return value.translate(SUPERSCRIPT_MAP)

def preserve_superscripts(soup):
    """
    Resmî HTML içindeki <sup> öğelerini düz metne dönüşmeden önce
    Unicode üst karakterlere çevirir.
    Örn. <sup>(1)</sup> -> ⁽¹⁾
    """
    for tag in soup.find_all("sup"):
        value = tag.get_text(" ", strip=True)
        converted = to_superscript_text(value)
        if converted:
            tag.replace_with(converted)
        else:
            tag.decompose()

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
    preserve_superscripts(soup)
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


def fetch_direct_html(item):
    url = item["kaynak"]
    r = requests.get(url, headers=HEADERS, timeout=35)
    r.raise_for_status()

    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
        r.encoding = r.apparent_encoding or "utf-8"

    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    preserve_superscripts(soup)
    articles = split_articles(soup.get_text("\n"))

    if not articles:
        raise RuntimeError("Resmî HTML geldi ancak madde başlıkları ayrıştırılamadı.")

    return {
        "articles": articles,
        "source_type": "resmi_html",
        "source_url": url,
        "fetched_at": now(),
        "ssl_fallback": False
    }

def get_legislation(key):
    item = MEVZUATLAR[key]
    errors = []

    getters = (fetch_direct_html,) if item.get("direct_html") else (fetch_live_html, fetch_official_pdf)

    for getter in getters:
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
