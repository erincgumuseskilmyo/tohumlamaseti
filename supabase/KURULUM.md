# Skor Tablosunu Supabase'e Bağlama

Oyunun HTML'i (`index.html`) Supabase'e bağlanacak şekilde hazır.
Senin yapman gereken **3 adım** var. Toplam ~10 dakika.

---

## 1. Supabase projesi oluştur

1. <https://supabase.com> → **Start your project** (ücretsiz).
2. Organizasyon/veritabanı/şifre belirle → **Create new project**.
3. Proje birkaç dakika kurulur. Beklerken 2. adıma geçebilirsin.

---

## 2. Tabloyu oluştur

1. Supabase panelinde sol menü → **SQL Editor** → **New query**.
2. `supabase/kurulum.sql` dosyasının **tamamını** yapıştır.
3. **Run** (▶) tuşuna bas.

Şu iki nesne oluşmalı:

- `public.skor_tablosu` — skorların tutulduğu tablo
- `public.skor_gonder(...)` — oyunun puanı gönderdiği fonksiyon

> Bu SQL tekrar çalıştırılabilir; verileri silmez.

---

## 3. Anahtarları oyuna yaz

1. Sol menü → ⚙ **Project Settings** → **API** (yeni sürümde **API Keys**).
2. Şu iki değeri kopyala:

   | Ne | Nerede | Örnek |
   |---|---|---|
   | **Project URL** | Project Details bölümü | `https://abcdefghijklm.supabase.co` |
   | **Publishable key** | API Keys bölümü | `sb_publishable_...` (yeni) veya `eyJhbGci...` (eski anon key) |

   > **service_role / secret key ASLA kullanma.** Oyun tarayıcıda çalışıyor, anahtar
   > herkese görünür olacak. Sadece `publishable` (ya da eski `anon`) anahtarı.

3. `index.html` dosyasını aç, 1228. satırdaki bloğu düzenle:

```js
const SUPABASE = {
  url:    "https://abcdefghijklm.supabase.co",   // ← Project URL
  apiKey: "sb_publishable_xxxxxxxxxxxx",          // ← Publishable key
  oyun:   "tohumlama-seti-alet-avi",              // bu oyunun kodu
};
```

4. Kaydet, dosyayı tarayıcıda aç. **Artık bağlı.**

---

## Doğru çalıştığını nasıl anlarsın?

Skor tablosunun sağ üstündeki küçük yazı:

| Yazı | Anlamı |
|---|---|
| `tüm oyuncular · ortak tablo` | ✅ Supabase'e bağlı, herkes ortak tabloyu görüyor |
| `yalnızca bu cihaz` | ❌ Anahtar boş/hatalı, ya da internet/sunucu erişimi yok |

Tablo boşken *"Henüz kimse oynamadı — ilk sen ol."* yazar; oyun yine normal çalışır.

**Hızlı test:** Tarayıcıda F12 → **Console**. Şu komutu yapıştır:

```js
await fetch("https://PROJE-REF.supabase.co/rest/v1/skor_tablosu?select=puan", {
  headers: { apikey: "PUBLISHABLE_KEY" }
}).then(r => console.log(r.status, r.statusText))
```

`200 OK` → bağlantı sağlam. `401` → anahtar yanlış.

---

## Sorun giderme

| Belirti | Sebep / Çözüm |
|---|---|
| Console'da `401` / `Invalid API key` | `apiKey` yanlış kopyalanmış. Tekrar al, boşluksuz yapıştır. |
| `relation "skor_tablosu" does not exist` | SQL Editor'de SQL çalıştırılmamış. 2. adıma dön. |
| `permission denied for function skor_gonder` | Proje **Database → Policies** bölümünde tablo RLS'siz kalmış olabilir. `kurulum.sql`'i tekrar çalıştır. |
| `yetersiz privilege` hatası | SQL'i **postgres**/kurucu rolüyle çalıştırman gerekiyor (SQL Editor'de çalıştırman yeterli). |
| Tablo hep boş / `yalnızca bu cihaz` | Anahtar girilmemiş ya da `url` sonunda `/` bırakılmış. Sondaki `/`'yi sil. |
| Skor gidiyor ama tablo boş | Supabase → **Table Editor → skor_tablosu**, `no` kolonunda 9 rakamlı numara gör. Her şey yazılmışsa sorun `select` kolsuz erişimdir: `grant select` satırlarını yeniden çalıştır. |

---

## Veri gizliliği ve güvenlik

**Öğrenci numarası korunuyor.** Tabloya yazılan `no` kolonu RLS + kolon yetkisi
sayesinde dışarıdan **okunamaz**; oyun sadece `12•••345` maskesini görür ve
sunucuda da maskeli hali saklanır.

**Skorlar kanıtlanabilir değil.** Publishable anahtar tarayıcıda olduğu için
ileride birisi tarayıcı konsolundan doğrudan `skor_gonder` çağırıp istediği
puanı yazabilir. Sınıf içi kullanımda çoğu zaman sorun olmaz; sıkıntı yaşarsan:

- Sunucu tarafında bir **Edge Function** yaz, anahtarı oradan tut.
- Gönderimi **okul saatleri** gibi bir zaman aralığıyla sınırla (Edge Function içinde).

Yerelde PHP hostun varsa `api/skor.php` aynı işi SQLite ile yapar; anahtar
gerekmez, ama ortak tablo için o cihazın PHP + SQLite desteği olmalıdır.

---

## Birden fazla oyun aynı tabloyu kullanır

`oyun` kodu her oyunda farklı olmalı — skorlar bu kodla ayrılır:

```js
oyun: "tohumlama-seti-alet-avi"     // bu oyun
oyun: "diger-oyun-adi"              // başka oyun
```

Aynı öğrenci her iki oyunda da ayrı ayrı en iyi skorunu tutar.

---

## Not defteri için tüm listeyi alma

Supabase → **Table Editor → skor_tablosu** → filtreyi kaldır, `no` ve `no_maskeli`
sütunlarını gör. Dışa aktarmak için **Download CSV** düğmesini kullan.

Tam liste + sütun başlıkları hazır olsun diye eski PHP ucu CSV indirme özelliği
taşıyor (`api/skor.php?tum=1&anahtar=...`), ancak **Supabase projeni kendisi
CSV verir** — PHP'ye gerek yok.

---

## Sıfırlama

- **Tek öğrenciyi silmek:** Table Editor → satırı seç → trash ikonu.
- **Tüm listeyi sıfırlamak:** SQL Editor → `delete from public.skor_tablosu;`