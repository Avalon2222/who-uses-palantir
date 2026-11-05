"""Unduh 10-K Palantir dari SEC EDGAR dan simpan pendapatan per segmen & wilayah.

    python scripts/ambil_pendapatan_sec.py

Hasil: data/pendapatan_palantir.csv (satuan juta USD). Tiap 10-K berisi tiga tahun,
jadi tiga dokumen sudah mencakup 2019-2025. Tambahkan 10-K baru ke daftar LAPORAN
setiap kali Palantir menerbitkannya (biasanya Februari).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR))

from src.sec import cari_pendapatan  # noqa: E402

CIK = "1321655"
# (tahun fiskal, nomor akses, nama dokumen)
LAPORAN = [
    (2025, "000132165526000011", "pltr-20251231.htm"),
    (2023, "000132165524000022", "pltr-20231231.htm"),
    (2021, "000119312522050913", "d273589d10k.htm"),
]
# SEC menolak permintaan tanpa User-Agent berformat "nama kontak@email" (403).
# Ganti alamat contoh ini dengan email kamu sendiri saat menjalankan skrip.
HEADER = {"User-Agent": "who-uses-palantir research-script admin@example.org"}


def main() -> None:
    baris = []
    for fy, akses, dok in LAPORAN:
        url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{akses}/{dok}"
        print("unduh", url)
        r = requests.get(url, headers=HEADER, timeout=60)
        r.raise_for_status()
        hasil = cari_pendapatan(r.text)
        for jenis, isi in hasil.items():
            for h in isi:
                baris.append({**h, "jenis": jenis, "fy": fy, "sumber_10k": f"10-K FY{fy}", "sumber_url": url})
        time.sleep(1)  # batas wajar SEC: maks 10 permintaan per detik

    df = pd.DataFrame(baris)
    # Tahun yang muncul di dua 10-K: ambil SEMUA kategorinya dari laporan terbaru.
    # Jangan dedupe per kategori: 10-K lama memisahkan Prancis, 10-K baru sudah
    # memasukkannya ke "Rest of world", sehingga campuran keduanya menghitung ganda.
    terbaru = df.groupby(["jenis", "tahun"])["fy"].transform("max")
    df = df[df["fy"] == terbaru]
    df["nilai_juta_usd"] = (df["nilai_ribu_usd"] / 1000).round(1)
    df = df.sort_values(["jenis", "tahun", "kategori"])[
        ["tahun", "jenis", "kategori", "nilai_juta_usd", "sumber_10k", "sumber_url"]
    ]
    keluar = AKAR / "data" / "pendapatan_palantir.csv"
    df.to_csv(keluar, index=False)
    print(f"tersimpan {len(df)} baris -> {keluar}")


if __name__ == "__main__":
    main()
