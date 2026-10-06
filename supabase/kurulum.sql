-- =====================================================================
--  Set Çantası — Alet Avı  ·  ortak skor tablosu
--  Supabase > SQL Editor > New query > buraya yapıştır > Run
--
--  Oluşturur:
--    1) public.skor_tablosu        (skor saklama tablosu)
--    2) public.skor_gonder(...)    (puanı güvenli yazan RPC)
--    3) RLS + kolon bazlı izinler  (öğrenci numaraları dışarı sızmasın)
--
--  Bu dosya TEKRAR ÇALIŞTIRILABİLİR (idempotent); mevcut verileri silmez.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1) Tablo
-- ---------------------------------------------------------------------
create table if not exists public.skor_tablosu (
  id           bigint generated always as identity primary key,
  oyun         text        not null,              -- oyun kodu (birden çok oyun aynı tabloyu paylaşır)
  no           text        not null,              -- öğrenci no (SADECE sunucuda kalır, okunamaz)
  ad           text        not null,
  soyad        text        not null,
  no_maskeli   text        not null,              -- 12•••345  (görünen hali)
  puan         integer     not null default 0,
  dogru        integer     not null default 0,
  tarih        timestamptz not null default now(), -- bu puanın KAZANILDIĞI an
  guncellendi  timestamptz not null default now(), -- son gönderim (eşitlik kırıcı: eski olan önde)
  oyun_sayisi  integer     not null default 0,
  constraint skor_tablosu_oyun_no_key unique (oyun, no)
);

comment on table public.skor_tablosu is 'Oyunlarda öğrenci başına en iyi skor. Öğrenci no sunucuda gizlidir.';


-- ---------------------------------------------------------------------
-- 2) Puan gönderme RPC'si  (oyun HTML'i bunu çağırır)
--    Öğrenci başına SADECE EN İYİ skor tutulur.
-- ---------------------------------------------------------------------
create or replace function public.skor_gonder(
  p_oyun   text,
  p_no     text,
  p_ad     text,
  p_soyad  text,
  p_puan   integer,
  p_dogru  integer
) returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_mask text;
  v_dogru integer;
begin
  -- --- Girdi doğrulama (tarayıcıdan gelen veri olduğu için şart) ---
  if p_oyun is null or length(p_oyun) < 1 or length(p_oyun) > 60 then
    raise exception 'Geçersiz oyun kodu.';
  end if;

  if p_no is null or p_no !~ '^[0-9]{9}$' then
    raise exception 'Öğrenci numarası 9 rakam olmalı.';
  end if;

  if p_ad is null or length(btrim(p_ad)) < 1 or length(p_ad) > 30 then
    raise exception 'Geçersiz ad.';
  end if;

  if p_soyad is null or length(btrim(p_soyad)) < 1 or length(p_soyad) > 30 then
    raise exception 'Geçersiz soyad.';
  end if;

  if p_puan is null or p_puan < 0 or p_puan > 5000 then
    raise exception 'Puan aralık dışı.';
  end if;

  v_dogru := coalesce(p_dogru, 0);
  if v_dogru < 0 or v_dogru > 100 then v_dogru := 0; end if;

  v_mask := left(p_no, 3) || '•••' || right(p_no, 2);

  -- --- En iyi skoru koruyan upsert ---
  insert into public.skor_tablosu as t
        (oyun, no, ad, soyad, no_maskeli, puan, dogru, tarih, guncellendi, oyun_sayisi)
  values (p_oyun, p_no, btrim(p_ad), btrim(p_soyad), v_mask, p_puan, v_dogru, now(), now(), 1)
  on conflict (oyun, no) do update
     set ad          = case when excluded.puan > t.puan then excluded.ad        else t.ad        end,
         soyad       = case when excluded.puan > t.puan then excluded.soyad     else t.soyad     end,
         dogru       = case when excluded.puan > t.puan then excluded.dogru     else t.dogru     end,
         puan        = greatest(t.puan, excluded.puan),
         tarih       = case when excluded.puan > t.puan then excluded.tarih    else t.tarih    end,
         guncellendi = now(),
         oyun_sayisi = t.oyun_sayisi + 1;
end;
$$;

comment on function public.skor_gonder(text, text, text, text, integer, integer)
  is 'Oyun bitince çağrılır; öğrenci başına en iyi skoru saklar.';


-- ---------------------------------------------------------------------
-- 3) Yetkiler — öğrenci numaraları okunamaz olsun
--    Tarayıcı sadece MASKE + puan görebilir, tabloya doğrudan yazamaz.
-- ---------------------------------------------------------------------
alter table public.skor_tablosu enable row level security;

revoke all on table public.skor_tablosu from anon, authenticated;

-- Sadece bu kolonlar okunabilir (özellikle `no` ve `id` verilmedi):
grant select (oyun, ad, soyad, no_maskeli, puan, dogru, tarih, guncellendi, oyun_sayisi)
  on public.skor_tablosu to anon, authenticated;

drop policy if exists skor_tablosu_okuma on public.skor_tablosu;
create policy skor_tablosu_okuma on public.skor_tablosu
  for select to anon, authenticated
  using (true);

-- Yazma yolu sadece RPC (o da giriş doğrulamalı):
revoke all on function public.skor_gonder(text, text, text, text, integer, integer) from public;
grant execute on function public.skor_gonder(text, text, text, text, integer, integer)
  to anon, authenticated;