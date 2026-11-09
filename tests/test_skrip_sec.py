"""Tes penggabungan hasil beberapa 10-K di scripts/ambil_pendapatan_sec.py (tanpa unduh)."""

import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "ambil_pendapatan_sec.py"
spec = importlib.util.spec_from_file_location("ambil_pendapatan_sec", PATH)
skrip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skrip)


def _b(fy, tahun, kategori, nilai, jenis="wilayah"):
    return {"tahun": tahun, "kategori": kategori, "nilai_ribu_usd": nilai, "jenis": jenis, "fy": fy,
            "sumber_10k": f"10-K FY{fy}", "sumber_url": f"https://contoh/{fy}"}


def test_tahun_ganda_ambil_semua_dari_10k_terbaru():
    baris = [
        # 10-K FY2023 masih memisahkan Prancis.
        _b(2023, 2023, "Prancis", 50_000), _b(2023, 2023, "Negara lain", 400_000),
        # 10-K FY2025 sudah menggabungkan Prancis ke "Negara lain".
        _b(2025, 2023, "Negara lain", 450_000), _b(2025, 2025, "Negara lain", 728_005),
    ]
    df = skrip.rapikan(baris)
    th2023 = df[df["tahun"] == 2023]
    assert th2023["kategori"].tolist() == ["Negara lain"]       # Prancis lama tidak ikut terhitung ganda
    assert th2023["sumber_10k"].tolist() == ["10-K FY2025"]
    assert df["nilai_juta_usd"].tolist() == [450.0, 728.0]


def test_kolom_dan_urutan():
    df = skrip.rapikan([_b(2025, 2025, "Pemerintah", 2_402_287, "segmen"),
                        _b(2025, 2024, "Komersial", 1_295_902, "segmen")])
    assert list(df.columns) == ["tahun", "jenis", "kategori", "nilai_juta_usd", "sumber_10k", "sumber_url"]
    assert df["tahun"].tolist() == [2024, 2025]
    assert df["nilai_juta_usd"].tolist() == [1295.9, 2402.3]
