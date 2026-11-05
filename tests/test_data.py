"""Pemeriksaan kualitas dataset: skema, sumber, dan konsistensi antar-file."""

import pandas as pd
import pytest

from src import analisis, muat_data


@pytest.fixture(scope="module")
def pengguna():
    return muat_data.muat_pengguna()


@pytest.fixture(scope="module")
def kontroversi():
    return muat_data.muat_kontroversi()


@pytest.fixture(scope="module")
def pendapatan():
    return muat_data.muat_pendapatan()


def test_dataset_lolos_validasi(pengguna, kontroversi):
    assert muat_data.validasi(pengguna, kontroversi) == []


def test_ukuran_dataset_masuk_akal(pengguna, kontroversi):
    assert len(pengguna) >= 40
    assert len(kontroversi) >= 20
    assert pengguna["iso3"].nunique() >= 15


def test_setiap_baris_punya_sumber(pengguna, kontroversi):
    assert pengguna["sumber_url"].str.startswith("https://").all()
    assert pengguna["sumber_nama"].str.len().gt(0).all()
    assert kontroversi["sumber_url"].str.startswith("https://").all()


def test_semua_sektor_dan_status_dipakai(pengguna):
    assert set(pengguna["sektor"]) == set(muat_data.SEKTOR)
    assert set(pengguna["status"]) <= set(muat_data.STATUS)


def test_semua_kawasan_dikenal(pengguna):
    lengkap = analisis.lengkapi(pengguna)
    assert "Lainnya" not in set(lengkap["kawasan"])


def test_setiap_kontroversi_punya_lembaga_atau_kawasan(pengguna, kontroversi):
    dipakai = {k for s in pengguna["kontroversi"] for k in s.split(";") if k}
    yatim = set(kontroversi["id"]) - dipakai
    tingkat_kawasan = set(kontroversi.loc[kontroversi["negara"].isin(["Eropa", "PBB", "Uni Eropa"]), "id"])
    assert yatim <= tingkat_kawasan


def test_validasi_menangkap_kesalahan(pengguna, kontroversi):
    rusak = pengguna.copy()
    rusak.loc[0, "sektor"] = "Alien"
    rusak.loc[1, "sumber_url"] = "http://tidak-aman.example"
    rusak.loc[2, "kontroversi"] = "tidak-ada"
    rusak.loc[3, "lat"] = 123.0
    masalah = muat_data.validasi(rusak, kontroversi)
    teks = " ".join(masalah)
    assert "sektor tidak dikenal" in teks
    assert "URL https" in teks
    assert "tidak ada di kontroversi.csv" in teks
    assert "koordinat" in teks


def test_pendapatan_cocok_dengan_total_10k(pendapatan):
    # Total pendapatan dari 10-K (ribu USD): 2019 742.555, 2023 2.225.012, 2025 4.475.446
    seg = analisis.pangsa_pendapatan(pendapatan, "segmen").set_index("tahun")
    wil = analisis.pangsa_pendapatan(pendapatan, "wilayah").set_index("tahun")
    for th, total in {2019: 742.6, 2023: 2225.0, 2025: 4475.4}.items():
        assert seg.loc[th, "Total"] == pytest.approx(total, abs=0.3)
        assert wil.loc[th, "Total"] == pytest.approx(total, abs=0.3)


def test_pendapatan_tujuh_tahun_tanpa_lubang(pendapatan):
    for jenis in ["segmen", "wilayah"]:
        tahun = sorted(pendapatan.loc[pendapatan["jenis"] == jenis, "tahun"].unique())
        assert tahun == list(range(2019, 2026))
    assert pd.api.types.is_numeric_dtype(pendapatan["nilai_juta_usd"])
