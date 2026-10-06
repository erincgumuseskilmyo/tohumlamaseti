<?php
/**
 * Set Çantası — Alet Avı · skor tablosu ucu (PHP 7.4+ / SQLite)
 *
 * GET  skor.php                     -> {"skorlar":[{ad,soyad,no,puan,dogru,tarih}, ...]}  (ilk 10)
 * POST skor.php  {ad,soyad,no,puan,dogru}  -> {"ok":true}   (öğrenci başına EN İYİ skor tutulur)
 * GET  skor.php?tum=1&anahtar=...   -> CSV (tüm liste, tam öğrenci no) — not defteri için
 *
 * Kurulum: bu dosyayı oyunun yanındaki api/ klasörüne koy. Veritabanı ilk
 * istekte api/data/skorlar.sqlite olarak kendiliğinden oluşur; o klasörün
 * web'den okunmasını engellemek için api/data/.htaccess birlikte gelir.
 */
declare(strict_types=1);

// --- Ayarlar ---------------------------------------------------------------
const DB_PATH     = __DIR__ . '/data/skorlar.sqlite';
const TOP_N       = 10;      // tabloda gösterilecek satır sayısı
const MAX_PUAN    = 5000;    // makul üst sınır (bozuk/şişirilmiş gönderimleri eler)
const MAX_DOGRU   = 14;      // ünitedeki doğru alet sayısı
const MIN_ARALIK  = 2;       // aynı öğrenci no için iki gönderim arası en az saniye
const DISA_AKTAR_ANAHTARI = '';   // CSV dışa aktarma için parola; boşken bu uç kapalıdır

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function bitir(int $kod, array $govde): void {
    http_response_code($kod);
    echo json_encode($govde, JSON_UNESCAPED_UNICODE);
    exit;
}
function hata(int $kod, string $mesaj): void { bitir($kod, ['hata' => $mesaj]); }

// --- Veritabanı ------------------------------------------------------------
$klasor = dirname(DB_PATH);
if (!is_dir($klasor) && !@mkdir($klasor, 0775, true) && !is_dir($klasor)) {
    hata(500, 'Veri klasörü oluşturulamadı.');
}
try {
    $pdo = new PDO('sqlite:' . DB_PATH, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    $pdo->exec('PRAGMA journal_mode = WAL');
    $pdo->exec('PRAGMA busy_timeout = 4000');
    $pdo->exec('CREATE TABLE IF NOT EXISTS skorlar (
        no           TEXT PRIMARY KEY,
        ad           TEXT NOT NULL,
        soyad        TEXT NOT NULL,
        puan         INTEGER NOT NULL,
        dogru        INTEGER NOT NULL DEFAULT 0,
        tarih        TEXT NOT NULL,
        son_gonderim TEXT NOT NULL,
        oyun_sayisi  INTEGER NOT NULL DEFAULT 1
    )');
} catch (Throwable $e) {
    hata(500, 'Veritabanı açılamadı.');
}

$yontem = $_SERVER['REQUEST_METHOD'] ?? 'GET';

// --- Eğitmen için CSV dışa aktarma ----------------------------------------
if ($yontem === 'GET' && isset($_GET['tum'])) {
    $anahtar = (string)($_GET['anahtar'] ?? '');
    if (DISA_AKTAR_ANAHTARI === '' || !hash_equals(DISA_AKTAR_ANAHTARI, $anahtar)) {
        hata(403, 'Dışa aktarma kapalı ya da anahtar hatalı.');
    }
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="skorlar.csv"');
    $cikti = fopen('php://output', 'w');
    fwrite($cikti, "\xEF\xBB\xBF");                       // Excel için BOM
    fputcsv($cikti, ['Ad', 'Soyad', 'Ogrenci No', 'Puan', 'Dogru', 'Tarih', 'Oyun Sayisi'], ';');
    $st = $pdo->query('SELECT ad, soyad, no, puan, dogru, tarih, oyun_sayisi FROM skorlar ORDER BY puan DESC');
    foreach ($st as $s) {
        fputcsv($cikti, [$s['ad'], $s['soyad'], $s['no'], $s['puan'], $s['dogru'], $s['tarih'], $s['oyun_sayisi']], ';');
    }
    exit;
}

// --- Tablo ----------------------------------------------------------------
if ($yontem === 'GET') {
    $st = $pdo->prepare('SELECT ad, soyad, no, puan, dogru, tarih FROM skorlar
                         ORDER BY puan DESC, tarih ASC LIMIT :n');
    $st->bindValue(':n', TOP_N, PDO::PARAM_INT);
    $st->execute();
    bitir(200, ['skorlar' => $st->fetchAll()]);
}

if ($yontem !== 'POST') hata(405, 'Yöntem desteklenmiyor.');

// --- Skor gönderimi -------------------------------------------------------
$gelen = json_decode((string)file_get_contents('php://input'), true);
if (!is_array($gelen)) hata(400, 'Geçersiz istek gövdesi.');

/** Ad/soyad: kontrol karakterlerini at, 30 karaktere kırp. */
function metin($v): string {
    $s = preg_replace('/[\x00-\x1F\x7F]/u', '', trim((string)$v));
    return mb_substr($s, 0, 30, 'UTF-8');
}

$ad    = metin($gelen['ad'] ?? '');
$soyad = metin($gelen['soyad'] ?? '');
$no    = trim((string)($gelen['no'] ?? ''));
$puan  = filter_var($gelen['puan'] ?? null, FILTER_VALIDATE_INT);
$dogru = filter_var($gelen['dogru'] ?? 0, FILTER_VALIDATE_INT);

if ($ad === '' || $soyad === '')            hata(400, 'Ad ve soyad gerekli.');
if (!preg_match('/^[0-9]{9}$/', $no))       hata(400, 'Öğrenci numarası 9 rakam olmalı.');
if ($puan === false || $puan < 0 || $puan > MAX_PUAN)     hata(400, 'Puan aralık dışı.');
if ($dogru === false || $dogru < 0 || $dogru > MAX_DOGRU) $dogru = 0;

$simdi = gmdate('c');

try {
    $pdo->beginTransaction();
    $st = $pdo->prepare('SELECT puan, son_gonderim, oyun_sayisi FROM skorlar WHERE no = :no');
    $st->execute([':no' => $no]);
    $mevcut = $st->fetch();

    if ($mevcut) {
        // Çok sık gönderimi (yenile-bas döngüsü, otomatik istek) sessizce yut
        if (strtotime($simdi) - strtotime((string)$mevcut['son_gonderim']) < MIN_ARALIK) {
            $pdo->rollBack();
            bitir(200, ['ok' => true, 'not' => 'cok_sik']);
        }
        if ($puan > (int)$mevcut['puan']) {
            $pdo->prepare('UPDATE skorlar SET ad=:ad, soyad=:soyad, puan=:puan, dogru=:dogru,
                           tarih=:tarih, son_gonderim=:simdi, oyun_sayisi=oyun_sayisi+1
                           WHERE no=:no')
                ->execute([':ad'=>$ad, ':soyad'=>$soyad, ':puan'=>$puan, ':dogru'=>$dogru,
                           ':tarih'=>$simdi, ':simdi'=>$simdi, ':no'=>$no]);
        } else {
            $pdo->prepare('UPDATE skorlar SET son_gonderim=:simdi, oyun_sayisi=oyun_sayisi+1 WHERE no=:no')
                ->execute([':simdi'=>$simdi, ':no'=>$no]);
        }
    } else {
        $pdo->prepare('INSERT INTO skorlar (no, ad, soyad, puan, dogru, tarih, son_gonderim, oyun_sayisi)
                       VALUES (:no, :ad, :soyad, :puan, :dogru, :tarih, :simdi, 1)')
            ->execute([':no'=>$no, ':ad'=>$ad, ':soyad'=>$soyad, ':puan'=>$puan,
                       ':dogru'=>$dogru, ':tarih'=>$simdi, ':simdi'=>$simdi]);
    }
    $pdo->commit();
} catch (Throwable $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    hata(500, 'Skor kaydedilemedi.');
}

bitir(200, ['ok' => true]);
