"""Membaca tabel pendapatan Palantir dari laporan tahunan (10-K) di SEC EDGAR.

Setiap 10-K memuat dua tabel yang dibutuhkan proyek ini:
- pendapatan per segmen (Government dan Commercial), tiga tahun terakhir
- pendapatan per wilayah (United States, United Kingdom, Rest of world), tiga tahun terakhir

Tabel HTML dari EDGAR sangat "berisik": satu angka bisa terpecah ke beberapa sel
("$", "1,569,605", ")"), dan setiap sel bisa terduplikasi karena colspan. Fungsi di
sini merapikannya menjadi baris sederhana seperti ['Government', '2402287', '1569605'].
"""

from __future__ import annotations

import re
from io import StringIO

import pandas as pd

# Nama baris di 10-K -> label yang dipakai di aplikasi
SEGMEN = {
    "Government": "Pemerintah",
    "Government revenue": "Pemerintah",
    "Commercial": "Komersial",
    "Commercial revenue": "Komersial",
}
WILAYAH = {
    "United States": "Amerika Serikat",
    "United Kingdom": "Inggris",
    "France": "Prancis",
    "Rest of world": "Negara lain",
}
_SAMPAH = {"nan", "$", "%", ")", "—", ""}


def bersihkan_baris(baris: list) -> list[str]:
    """Buang sel kosong/simbol dan duplikat berurutan akibat colspan."""
    hasil: list[str] = []
    for sel in baris:
        teks = str(sel).replace("\xa0", " ").strip()
        if teks in _SAMPAH:
            continue
        if not hasil or hasil[-1] != teks:
            hasil.append(teks)
    return hasil


def ke_angka(teks: str) -> float | None:
    """'1,569,605' -> 1569605.0 ; '(826,217)' -> -826217.0 ; 'Amount' -> None."""
    t = teks.replace(",", "").strip()
    negatif = t.startswith("(")
    t = t.strip("()")
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    nilai = float(t)
    return -nilai if negatif else nilai


def _label_bersih(teks: str) -> str:
    return re.sub(r"\s*\(\d+\)\s*$", "", teks).strip()


def baca_tabel(html: str) -> list[list[list[str]]]:
    """Semua tabel di dokumen, masing-masing sebagai daftar baris yang sudah dibersihkan."""
    html = re.sub(r"<\?xml[^>]*>", "", html)
    try:
        tabel = pd.read_html(StringIO(html), flavor="lxml")
    except ValueError:
        return []
    return [[b for b in (bersihkan_baris(r) for r in t.values.tolist()) if b] for t in tabel]


def _tahun_header(baris_tabel: list[list[str]]) -> list[int]:
    for b in baris_tabel[:4]:
        tahun = [int(x) for x in b if re.fullmatch(r"20\d\d", x)]
        if len(tahun) >= 2:
            return tahun
    return []


def _ambil(baris_tabel, peta: dict[str, str], tahun: list[int]) -> list[dict]:
    """Ambil angka per tahun untuk setiap label di `peta`.

    Kolom persen (angka kecil <= 100 yang muncul setelah nilai) dilewati: tabel wilayah
    menulis 'nilai, persen, nilai, persen'. Nilai pendapatan selalu jauh di atas 100
    karena satuannya ribu dolar.
    """
    hasil = []
    for b in baris_tabel:
        label = _label_bersih(b[0])
        if label not in peta:
            continue
        angka = [ke_angka(x) for x in b[1:]]
        angka = [a for a in angka if a is not None and abs(a) > 100]
        for th, nilai in zip(tahun, angka):
            hasil.append({"tahun": th, "kategori": peta[label], "nilai_ribu_usd": nilai})
    return hasil


def cari_pendapatan(html: str) -> dict[str, list[dict]]:
    """Cari tabel segmen dan wilayah di satu 10-K.

    Satu 10-K bisa memuat beberapa tabel serupa (dua tahun di MD&A, tiga tahun di
    catatan laporan keuangan). Yang dipilih adalah tabel dengan tahun terbanyak.
    """
    terbaik = {"segmen": [], "wilayah": []}
    for t in baca_tabel(html):
        if len(t) > 14:
            continue
        label = {_label_bersih(b[0]) for b in t}
        tahun = _tahun_header(t)
        if len(tahun) < 2 or not label & {"Total revenue", "Total contribution"}:
            continue
        kandidat = {}
        # Tabel "contribution" juga punya baris Government/Commercial, tetapi isinya laba
        # kontribusi, bukan pendapatan. Terima hanya tabel yang jelas tabel pendapatan.
        tabel_pendapatan = "Total revenue" in label or "Government revenue" in label
        if tabel_pendapatan and label & {"Government", "Government revenue"} and label & {"Commercial", "Commercial revenue"}:
            kandidat["segmen"] = _ambil(t, SEGMEN, tahun)
        if {"United States", "United Kingdom"} <= label and "Total revenue" in label:
            kandidat["wilayah"] = _ambil(t, WILAYAH, tahun)
        for jenis, isi in kandidat.items():
            if len({h["tahun"] for h in isi}) > len({h["tahun"] for h in terbaik[jenis]}):
                terbaik[jenis] = isi
    return terbaik
