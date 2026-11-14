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


def test_validasi_skema_dan_duplikat(pengguna, kontroversi):
    p = pd.concat([pengguna, pengguna.iloc[[0]]], ignore_index=True)
    k = pd.concat([kontroversi, kontroversi.iloc[[0]]], ignore_index=True)
    masalah = muat_data.validasi(p.assign(kolom_baru=1), k.assign(kolom_baru=1))
    assert "kolom pengguna_palantir.csv tidak sesuai skema" in masalah
    assert "kolom kontroversi.csv tidak sesuai skema" in masalah
    assert f"id pengguna duplikat: {pengguna.loc[0, 'id']}" in masalah
    assert f"id kontroversi duplikat: {kontroversi.loc[0, 'id']}" in masalah


def test_validasi_setiap_kolom_baris(pengguna, kontroversi):
    rusak = pengguna.copy()
    rusak.loc[0, "status"] = "Entah"
    rusak.loc[1, "kepastian"] = "Gosip"
    rusak.loc[2, "iso3"] = "id"
    rusak.loc[3, "mata_uang"] = "XYZ"
    rusak.loc[3, "nilai_asli_juta"] = 5.0
    rusak.loc[4, "tahun_mulai"] = 2025
    rusak.loc[4, "tahun_akhir"] = 2020
    rusak.loc[5, "lon"] = float("nan")
    tag = rusak["id"]
    masalah = muat_data.validasi(rusak, kontroversi)
    assert f"{tag[0]}: status tidak dikenal 'Entah'" in masalah
    assert f"{tag[1]}: kepastian tidak dikenal 'Gosip'" in masalah
    assert f"{tag[2]}: iso3 tidak valid" in masalah
    assert f"{tag[3]}: nilai ada tetapi mata uang kosong/tidak dikenal" in masalah
    assert f"{tag[4]}: tahun_akhir sebelum tahun_mulai" in masalah
    assert f"{tag[5]}: koordinat kosong" in masalah
    assert f"{tag[5]}: koordinat di luar jangkauan" not in masalah


def test_validasi_kontroversi(pengguna, kontroversi):
    rusak = kontroversi.copy()
    rusak.loc[0, "sumber_url"] = "ftp://lama.example"
    rusak.loc[1, "dampak"] = 7
    masalah = muat_data.validasi(pengguna, rusak)
    assert f"{rusak.loc[0, 'id']}: sumber kontroversi harus URL https" in masalah
    assert f"{rusak.loc[1, 'id']}: dampak harus 1, 2, atau 3" in masalah


def test_id_dobel_disebut_sekali_dan_id_angka_aman():
    assert muat_data._id_dobel(pd.Series(["a", "b", "a", "a"])) == ["a"]
    assert muat_data._id_dobel(pd.Series([1, 2, 2])) == ["2"]
    assert muat_data._id_dobel(pd.Series(["x", "y"])) == []


def test_muat_pengguna_tahun_mulai_kosong_sebut_id(tmp_path):
    asli = muat_data.FOLDER_DATA / "pengguna_palantir.csv"
    df = pd.read_csv(asli)
    df.loc[0, "tahun_mulai"] = None
    csv = tmp_path / "pengguna.csv"
    df.to_csv(csv, index=False)
    with pytest.raises(ValueError, match=str(df.loc[0, "id"])):
        muat_data.muat_pengguna(csv)
