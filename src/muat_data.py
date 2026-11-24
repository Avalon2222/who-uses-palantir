"""Memuat dan memeriksa tiga dataset proyek.

- data/pengguna_palantir.csv : satu baris = satu lembaga/kontrak yang memakai Palantir
- data/kontroversi.csv       : satu baris = satu kontroversi, ditautkan lewat kolom `kontroversi`
- data/pendapatan_palantir.csv : pendapatan Palantir per segmen & wilayah dari 10-K SEC
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

FOLDER_DATA = Path(__file__).resolve().parents[1] / "data"

KOLOM_PENGGUNA = [
    "id", "negara", "iso3", "lembaga", "sektor", "produk", "tahun_mulai", "tahun_akhir",
    "status", "nilai_asli_juta", "mata_uang", "catatan_nilai", "kota", "lat", "lon",
    "ringkasan", "kepastian", "sumber_nama", "sumber_url", "kontroversi",
]
KOLOM_KONTROVERSI = [
    "id", "judul", "negara", "tahun", "jenis", "hasil", "dampak", "ringkasan",
    "sumber_nama", "sumber_url",
]

SEKTOR = [
    "Militer & pertahanan", "Intelijen", "Kepolisian", "Imigrasi & perbatasan",
    "Kesehatan", "Pemerintahan sipil", "Organisasi internasional", "Korporasi",
]
STATUS = ["Aktif", "Rintisan", "Ditinjau ulang", "Ditolak/diblokir", "Berakhir", "Status tidak jelas"]
KEPASTIAN = ["Resmi", "Laporan media"]
MATA_UANG = ["USD", "GBP", "EUR", "AUD", "CAD"]


def pecah_kontroversi(teks) -> list[str]:
    """'k1; k2;;k1' -> ['k1', 'k2']. Spasi dibuang, sel kosong/NaN jadi list kosong, duplikat dibuang.

    Koma juga diterima sebagai pemisah ('k1,k2'), karena id kontroversi sendiri tidak memuat koma;
    tanpa itu 'k1,k2' dibaca sebagai satu id yang tidak ada dan kedua kontroversinya hilang diam-diam.
    """
    if teks is None or (not isinstance(teks, str) and pd.isna(teks)):
        return []
    return list(dict.fromkeys(k.strip() for k in re.split(r"[;,]", str(teks)) if k.strip()))


def muat_pengguna(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or FOLDER_DATA / "pengguna_palantir.csv", dtype={"mata_uang": str})
    mulai = pd.to_numeric(df["tahun_mulai"], errors="coerce")
    # "inf" terbaca to_numeric sebagai tak hingga, lalu astype(int) gagal tanpa menyebut id barisnya.
    mulai = mulai.where(mulai.abs() != math.inf)
    if mulai.isna().any():
        # astype(int) pada sel kosong hanya memberi error pandas yang sulit dibaca.
        raise ValueError("tahun_mulai kosong atau bukan angka untuk id: " + ", ".join(df.loc[mulai.isna(), "id"].astype(str)))
    akhir = pd.to_numeric(df["tahun_akhir"], errors="coerce")
    # Tahun pecahan (2019.5) dulu dipotong diam-diam (tahun_mulai) atau gagal dengan TypeError Int64 (tahun_akhir).
    # tahun_akhir tak hingga juga ditolak (dulu OverflowError saat jadi Int64).
    pecahan = (mulai != mulai.round()) | (akhir.notna() & ((akhir != akhir.round()) | (akhir.abs() == math.inf)))
    if pecahan.any():
        raise ValueError("tahun harus bilangan bulat untuk id: " + ", ".join(df.loc[pecahan, "id"].astype(str)))
    df["tahun_mulai"] = mulai.astype(int)
    df["tahun_akhir"] = akhir.astype("Int64")
    df["nilai_asli_juta"] = pd.to_numeric(df["nilai_asli_juta"], errors="coerce")
    # Koordinat salah ketik ("51,5" pakai koma) membuat kolomnya teks dan validasi gagal dengan
    # TypeError saat membandingkan dengan -90. Jadikan NaN supaya dilaporkan "koordinat kosong".
    for kol in ("lat", "lon"):
        df[kol] = pd.to_numeric(df[kol], errors="coerce")
    for kol in ["mata_uang", "catatan_nilai", "kontroversi"]:
        df[kol] = df[kol].fillna("")
    return df


def muat_kontroversi(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or FOLDER_DATA / "kontroversi.csv")
    for kol in ("tahun", "dampak"):
        angka = pd.to_numeric(df[kol], errors="coerce")
        if angka.isna().any():
            # Sama seperti muat_pengguna: sebut id barisnya, jangan error astype yang sulit dibaca.
            raise ValueError(f"{kol} kosong atau bukan angka untuk id: " + ", ".join(df.loc[angka.isna(), "id"].astype(str)))
        # astype(int) memotong pecahan diam-diam: dampak 2.5 jadi 2 dan lolos validasi.
        pecahan = angka != angka.round()
        if pecahan.any():
            raise ValueError(f"{kol} harus bilangan bulat untuk id: " + ", ".join(df.loc[pecahan, "id"].astype(str)))
        df[kol] = angka.astype(int)
    return df


def muat_pendapatan(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or FOLDER_DATA / "pendapatan_palantir.csv")


def _id_dobel(ids: pd.Series) -> list[str]:
    """Id yang muncul lebih dari sekali, masing-masing disebut satu kali (id angka juga aman)."""
    return [str(i) for i in ids[ids.duplicated()].unique()]


def validasi(pengguna: pd.DataFrame, kontroversi: pd.DataFrame) -> list[str]:
    """Kembalikan daftar masalah. List kosong berarti data siap dipakai."""
    masalah: list[str] = []
    if list(pengguna.columns) != KOLOM_PENGGUNA:
        masalah.append("kolom pengguna_palantir.csv tidak sesuai skema")
    if list(kontroversi.columns) != KOLOM_KONTROVERSI:
        masalah.append("kolom kontroversi.csv tidak sesuai skema")
    for nama, tabel in (("pengguna", pengguna), ("kontroversi", kontroversi)):
        dobel = _id_dobel(tabel["id"])
        if dobel:
            masalah.append(f"id {nama} duplikat: " + ", ".join(dobel))

    id_kon = set(kontroversi["id"])
    for _, r in pengguna.iterrows():
        tag = r["id"]
        if r["sektor"] not in SEKTOR:
            masalah.append(f"{tag}: sektor tidak dikenal '{r['sektor']}'")
        if r["status"] not in STATUS:
            masalah.append(f"{tag}: status tidak dikenal '{r['status']}'")
        if r["kepastian"] not in KEPASTIAN:
            masalah.append(f"{tag}: kepastian tidak dikenal '{r['kepastian']}'")
        if not str(r["sumber_url"]).startswith("https://"):
            masalah.append(f"{tag}: sumber harus URL https")
        # Tepat tiga huruf A-Z: "U5A" atau "GB1" lolos isupper() tetapi bukan kode ISO-3.
        if not re.fullmatch(r"[A-Z]{3}", str(r["iso3"])):
            masalah.append(f"{tag}: iso3 tidak valid")
        if pd.isna(r["lat"]) or pd.isna(r["lon"]):
            masalah.append(f"{tag}: koordinat kosong")
        elif not (-90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180):
            masalah.append(f"{tag}: koordinat di luar jangkauan")
        # Normalisasi sama dengan analisis.nilai_usd_juta: " usd" tetap dianggap USD.
        mata_uang = r["mata_uang"].strip().upper() if isinstance(r["mata_uang"], str) else ""
        if pd.notna(r["nilai_asli_juta"]) and mata_uang not in MATA_UANG:
            masalah.append(f"{tag}: nilai ada tetapi mata uang kosong/tidak dikenal")
        # Nilai kontrak negatif hampir pasti salah ketik, dan diam-diam mengurangi total di kartu KPI.
        if pd.notna(r["nilai_asli_juta"]) and r["nilai_asli_juta"] < 0:
            masalah.append(f"{tag}: nilai kontrak negatif")
        # "inf" dibaca to_numeric sebagai tak hingga dan membuat total di kartu KPI jadi inf.
        elif pd.notna(r["nilai_asli_juta"]) and not math.isfinite(r["nilai_asli_juta"]):
            masalah.append(f"{tag}: nilai kontrak tak hingga")
        if pd.notna(r["tahun_akhir"]) and r["tahun_akhir"] < r["tahun_mulai"]:
            masalah.append(f"{tag}: tahun_akhir sebelum tahun_mulai")
        for k in pecah_kontroversi(r["kontroversi"]):
            if k not in id_kon:
                masalah.append(f"{tag}: kontroversi '{k}' tidak ada di kontroversi.csv")
    for _, r in kontroversi.iterrows():
        if not str(r["sumber_url"]).startswith("https://"):
            masalah.append(f"{r['id']}: sumber kontroversi harus URL https")
        if r["dampak"] not in (1, 2, 3):
            masalah.append(f"{r['id']}: dampak harus 1, 2, atau 3")
    return masalah
