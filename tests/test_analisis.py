"""Uji fungsi analisis dengan data kecil buatan sendiri (tidak bergantung pada CSV)."""

import pandas as pd
import pytest

from src import analisis


def contoh() -> pd.DataFrame:
    df = pd.DataFrame({
        "id": ["a", "b", "c", "d", "e"],
        "negara": ["Amerika Serikat", "Amerika Serikat", "Inggris", "Jerman", "Organisasi internasional (NATO)"],
        "iso3": ["USA", "USA", "GBR", "DEU", "BEL"],
        "lembaga": ["Army", "ICE", "NHS", "Polisi Hessen", "NATO"],
        "sektor": ["Militer & pertahanan", "Imigrasi & perbatasan", "Kesehatan", "Kepolisian", "Organisasi internasional"],
        "tahun_mulai": [2010, 2014, 2020, 2017, 2025],
        "tahun_akhir": pd.array([pd.NA, pd.NA, 2023, pd.NA, pd.NA], dtype="Int64"),
        "status": ["Aktif", "Aktif", "Berakhir", "Ditinjau ulang", "Aktif"],
        "kepastian": ["Resmi", "Resmi", "Laporan media", "Laporan media", "Resmi"],
        "nilai_asli_juta": [100.0, None, 10.0, 20.0, None],
        "mata_uang": ["USD", "", "GBP", "EUR", ""],
        "kontroversi": ["k1", "k2;k3", "", "k4", ""],
    })
    return analisis.lengkapi(df)


def test_konversi_kurs():
    assert analisis.nilai_usd_juta(10, "GBP") == pytest.approx(13.0)
    assert analisis.nilai_usd_juta(100, "USD") == 100.0
    assert analisis.nilai_usd_juta(None, "USD") is None
    assert analisis.nilai_usd_juta(5, "") is None
    with pytest.raises(ValueError):
        analisis.nilai_usd_juta(5, "IDR")


def test_lengkapi_menambah_kolom():
    df = contoh()
    assert df.loc[df["id"] == "c", "nilai_usd_juta"].iloc[0] == pytest.approx(13.0)
    assert df.loc[df["id"] == "b", "jumlah_kontroversi"].iloc[0] == 2
    assert df.loc[df["id"] == "e", "kawasan"].iloc[0] == "Organisasi internasional"
    assert df.loc[df["id"] == "a", "kawasan"].iloc[0] == "Amerika Utara"


def test_saring_kombinasi():
    df = contoh()
    assert len(analisis.saring(df)) == 5
    assert len(analisis.saring(df, sektor=["Kesehatan"])) == 1
    assert len(analisis.saring(df, kepastian=["Resmi"], tahun=(2012, 2030))) == 2
    assert analisis.saring(df, status=["Ditolak/diblokir"]).empty


def test_ringkas_per_negara():
    r = analisis.ringkas_per_negara(contoh())
    usa = r[r["iso3"] == "USA"].iloc[0]
    assert usa["jumlah"] == 2
    assert usa["kontroversi"] == 3
    assert usa["nilai_usd_juta"] == pytest.approx(100.0)
    assert r.iloc[0]["iso3"] == "USA"  # diurutkan dari yang terbanyak
    assert r[r["iso3"] == "DEU"].iloc[0]["mundur"] == 1


def test_ringkas_per_negara_kosong():
    kosong = analisis.ringkas_per_negara(contoh().iloc[0:0])
    assert kosong.empty and "jumlah" in kosong.columns


def test_aktif_pada_menghormati_tahun_akhir():
    df = contoh()
    assert set(analisis.aktif_pada(df, 2021)["id"]) == {"a", "b", "c", "d"}
    assert "c" not in set(analisis.aktif_pada(df, 2024)["id"])
    assert set(analisis.aktif_pada(df, 2012)["id"]) == {"a"}


def test_timeline_kumulatif():
    tl = analisis.timeline_kumulatif(contoh()).set_index("tahun")
    assert tl.index.min() == 2010 and tl.index.max() == 2025
    assert tl.loc[2014, "baru"] == 1
    assert tl.loc[2021, "aktif"] == 4
    assert tl.loc[2024, "aktif"] == 3  # NHS berakhir 2023
    assert tl.loc[2021, "negara_aktif"] == 3


def test_peta_per_tahun():
    m = analisis.peta_per_tahun(contoh(), 2016, 2018)
    assert set(m["tahun"]) == {2016, 2017, 2018}
    th2017 = m[m["tahun"] == 2017].set_index("iso3")["jumlah"]
    assert th2017.to_dict() == {"DEU": 1, "USA": 2}


def test_ringkas_kontroversi():
    kon = pd.DataFrame({"id": ["k1", "k2", "k3"], "jenis": ["A", "A", "B"], "dampak": [1, 3, 2], "tahun": [2020, 2021, 2021]})
    r = analisis.ringkas_kontroversi(kon, "jenis")
    assert r.iloc[0]["jenis"] == "A" and r.iloc[0]["jumlah"] == 2
    assert r.iloc[0]["dampak_rata"] == pytest.approx(2.0)
    per_tahun = analisis.kontroversi_per_tahun(kon)
    assert per_tahun["jumlah"].sum() == 3


def test_kontroversi_untuk():
    kon = pd.DataFrame({"id": ["k2", "k3", "k9"], "judul": ["x", "y", "z"]})
    baris = contoh().iloc[1]
    assert list(analisis.kontroversi_untuk(baris, kon)["id"]) == ["k2", "k3"]


def test_kontroversi_tahan_spasi_kosong_dan_duplikat():
    from src.muat_data import pecah_kontroversi
    assert pecah_kontroversi("k2; k3;;k2 ") == ["k2", "k3"]
    assert pecah_kontroversi("") == []
    assert pecah_kontroversi(float("nan")) == []
    kon = pd.DataFrame({"id": ["k2", "k3", "nan"], "judul": ["x", "y", "z"]})
    assert list(analisis.kontroversi_untuk(pd.Series({"kontroversi": "k2; k3"}), kon)["id"]) == ["k2", "k3"]
    assert analisis.kontroversi_untuk(pd.Series({"kontroversi": float("nan")}), kon).empty


def test_pangsa_pendapatan_menggabung_prancis():
    pend = pd.DataFrame({
        "tahun": [2020, 2020, 2020, 2020],
        "jenis": ["wilayah"] * 4,
        "kategori": ["Amerika Serikat", "Inggris", "Prancis", "Negara lain"],
        "nilai_juta_usd": [50.0, 20.0, 10.0, 20.0],
    })
    p = analisis.pangsa_pendapatan(pend, "wilayah").iloc[0]
    assert "Prancis" not in p.index
    assert p["Negara lain"] == pytest.approx(30.0)
    assert p["Amerika Serikat (%)"] == pytest.approx(50.0)
    assert p["Total"] == pytest.approx(100.0)


def test_cagr():
    assert analisis.cagr(100, 200, 1) == pytest.approx(100.0)
    assert analisis.cagr(100, 121, 2) == pytest.approx(10.0)
    with pytest.raises(ValueError):
        analisis.cagr(0, 10, 2)


def test_rekap():
    kon = pd.DataFrame({"id": ["k1", "k2"]})
    r = analisis.rekap(contoh(), kon)
    assert r["lembaga"] == 5
    assert r["negara"] == 3  # NATO tidak dihitung sebagai negara
    assert r["organisasi_internasional"] == 1
    assert r["mundur"] == 1
    assert r["nilai_publik_usd_juta"] == pytest.approx(100 + 13 + 22)


def test_rekap_tanpa_nilai_publik_jadi_nol_bukan_nan():
    df = contoh()
    tanpa_nilai = df[df["nilai_usd_juta"].isna()]
    r = analisis.rekap(tanpa_nilai, pd.DataFrame({"id": []}))
    assert r["nilai_publik_usd_juta"] == 0.0
    assert r["lembaga"] == 2 and r["organisasi_internasional"] == 1


def test_rekap_jumlahkan_nilai_dan_hitung_mundur():
    r = analisis.rekap(contoh(), pd.DataFrame({"id": ["k1", "k2"]}))
    assert r["nilai_publik_usd_juta"] == pytest.approx(100 + 13.0 + df_eur(20))
    assert r["mundur"] == 1 and r["kontroversi"] == 2
    assert r["negara"] == 3          # NATO tidak dihitung sebagai negara


def df_eur(nilai):
    return analisis.nilai_usd_juta(nilai, "EUR")


def test_peta_per_tahun_hitung_lembaga_aktif_per_negara():
    p = analisis.peta_per_tahun(contoh(), 2019, 2021)
    usa_2020 = p[(p["tahun"] == 2020) & (p["iso3"] == "USA")]["jumlah"].iloc[0]
    assert usa_2020 == 2
    # NHS (GBR) mulai 2020, jadi belum ada di 2019.
    assert p[(p["tahun"] == 2019) & (p["iso3"] == "GBR")].empty
    assert analisis.peta_per_tahun(contoh(), 1990, 1991).empty


def test_timeline_kumulatif_baru_dan_aktif():
    t = analisis.timeline_kumulatif(contoh()).set_index("tahun")
    assert t.index.min() == 2010 and t.index.max() == 2025
    assert t["baru"].sum() == len(contoh())
    assert t.loc[2024, "aktif"] == 3            # NHS berakhir 2023
    assert analisis.timeline_kumulatif(contoh().iloc[0:0]).empty
