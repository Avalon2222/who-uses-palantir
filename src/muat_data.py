"""Memuat dan memeriksa tiga dataset proyek.

- data/pengguna_palantir.csv : satu baris = satu lembaga/kontrak yang memakai Palantir
- data/kontroversi.csv       : satu baris = satu kontroversi, ditautkan lewat kolom `kontroversi`
- data/pendapatan_palantir.csv : pendapatan Palantir per segmen & wilayah dari 10-K SEC
"""

from __future__ import annotations

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
    """'k1; k2;;k1' -> ['k1', 'k2']. Spasi dibuang, sel kosong/NaN jadi list kosong, duplikat dibuang."""
    if teks is None or (not isinstance(teks, str) and pd.isna(teks)):
        return []
    return list(dict.fromkeys(k.strip() for k in str(teks).split(";") if k.strip()))


def muat_pengguna(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or FOLDER_DATA / "pengguna_palantir.csv", dtype={"mata_uang": str})
    df["tahun_mulai"] = df["tahun_mulai"].astype(int)
    df["tahun_akhir"] = pd.to_numeric(df["tahun_akhir"], errors="coerce").astype("Int64")
    df["nilai_asli_juta"] = pd.to_numeric(df["nilai_asli_juta"], errors="coerce")
    for kol in ["mata_uang", "catatan_nilai", "kontroversi"]:
        df[kol] = df[kol].fillna("")
    return df


def muat_kontroversi(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or FOLDER_DATA / "kontroversi.csv")
    df["tahun"] = df["tahun"].astype(int)
    df["dampak"] = df["dampak"].astype(int)
    return df


def muat_pendapatan(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or FOLDER_DATA / "pendapatan_palantir.csv")


def validasi(pengguna: pd.DataFrame, kontroversi: pd.DataFrame) -> list[str]:
    """Kembalikan daftar masalah. List kosong berarti data siap dipakai."""
    masalah: list[str] = []
    if list(pengguna.columns) != KOLOM_PENGGUNA:
        masalah.append("kolom pengguna_palantir.csv tidak sesuai skema")
    if list(kontroversi.columns) != KOLOM_KONTROVERSI:
        masalah.append("kolom kontroversi.csv tidak sesuai skema")
    if pengguna["id"].duplicated().any():
        masalah.append("id pengguna duplikat: " + ", ".join(pengguna.loc[pengguna["id"].duplicated(), "id"]))
    if kontroversi["id"].duplicated().any():
        masalah.append("id kontroversi duplikat")

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
        if len(str(r["iso3"])) != 3 or not str(r["iso3"]).isupper():
            masalah.append(f"{tag}: iso3 tidak valid")
        if not (-90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180):
            masalah.append(f"{tag}: koordinat di luar jangkauan")
        if pd.notna(r["nilai_asli_juta"]) and r["mata_uang"] not in MATA_UANG:
            masalah.append(f"{tag}: nilai ada tetapi mata uang kosong/tidak dikenal")
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
