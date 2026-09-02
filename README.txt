MEVZUAT SORGULAMA - RENDER'A HAZIR PAKET
=========================================

İlk canlı mevzuat:
MESAFELİ SÖZLEŞMELER YÖNETMELİĞİ

Resmî kaynak:
https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20237&MevzuatTur=7&MevzuatTertip=5

DOSYALAR
--------
app.py                  Flask uygulaması / canlı veri çekme
templates/index.html    Kullanıcı arayüzü
requirements.txt        Python bağımlılıkları
render.yaml             Render Blueprint ayarları
cache/                  Son başarılı sorgular için geçici önbellek

RENDER YAYIN ADIMLARI
---------------------
1. Bu ZIP'i bilgisayarınızda bir klasöre çıkarın.
2. Dosyaları bir GitHub deposuna yükleyin.
3. Render.com hesabınıza girin.
4. New > Blueprint seçin.
5. GitHub deposunu bağlayın.
6. Render, render.yaml dosyasını otomatik okuyacaktır.
7. Deploy tamamlanınca size https://...onrender.com şeklinde bir adres verir.

Alternatif olarak New > Web Service kullanılabilir:
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app

ÇALIŞMA ŞEKLİ
-------------
1. Önce mevzuat.gov.tr canlı HTML/iframe adresi denenir.
2. Olmazsa mevzuat.gov.tr resmî PDF üretim adresi denenir.
3. Başarılı veri geçici önbelleğe kaydedilir.
4. Canlı kaynak geçici olarak erişilemezse, aynı çalışan servis örneğinde varsa
   son başarılı kopya gösterilir.

ÖNEMLİ
------
Render'ın ücretsiz servislerinde yerel dosya sistemi kalıcı depolama olarak
kullanılmamalıdır. Bu nedenle cache klasörü yalnızca geçici yedektir.
Kalıcı önbellek istenirse daha sonra PostgreSQL/Redis eklenebilir.

Yeni mevzuat eklemek için app.py içindeki MEVZUATLAR sözlüğüne yalnızca
ad, MevzuatNo, MevzuatTur, MevzuatTertip ve resmî kaynak URL'si eklenir.
