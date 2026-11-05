"""Fungsi analisis murni (tanpa Streamlit) supaya mudah diuji dengan pytest."""

from __future__ import annotations

import pandas as pd

# Kurs perkiraan rata-rata 2024-2026, hanya untuk membandingkan skala kontrak.
# Nilai aslinya tetap ditampilkan di tabel.
KURS_KE_USD = {"USD": 1.0, "GBP": 1.30, "EUR": 1.10, "AUD": 0.66, "CAD": 0.73}

KAWASAN = {
    "USA": "Amerika Utara", "CAN": "Amerika Utara",
    "GBR": "Eropa", "DEU": "Eropa", "FRA": "Eropa", "NLD": "Eropa", "CHE": "Eropa",
    "ESP": "Eropa", "GRC": "Eropa", "POL": "Eropa", "LTU": "Eropa", "DNK": "Eropa",
    "UKR": "Eropa", "BEL": "Eropa", "ITA": "Eropa",
    "ISR": "Timur Tengah", "ARE": "Timur Tengah",
    "JPN": "Asia-Pasifik", "KOR": "Asia-Pasifik", "AUS": "Asia-Pasifik", "NZL": "Asia-Pasifik",
}

# Status yang menandakan hubungan sedang mundur atau ditolak
STATUS_MUNDUR = {"Ditinjau ulang", "Ditolak/diblokir"}


def nilai_usd_juta(nilai: float | None, mata_uang: str) -> float | None:
    """Konversi nilai kontrak (juta) ke juta USD dengan kurs perkiraan."""
    if nilai is None or pd.isna(nilai) or not mata_uang:
        return None
    if mata_uang not in KURS_KE_USD:
        raise ValueError(f"mata uang tidak dikenal: {mata_uang}")
    return round(float(nilai) * KURS_KE_USD[mata_uang], 1)


def lengkapi(df: pd.DataFrame) -> pd.DataFrame:
    """Tambah kolom turunan: nilai dalam USD, kawasan, jumlah kontroversi, organisasi lintas negara."""
    df = df.copy()
    df["nilai_usd_juta"] = [nilai_usd_juta(n, m) for n, m in zip(df["nilai_asli_juta"], df["mata_uang"])]
    df["kawasan"] = df["iso3"].map(KAWASAN).fillna("Lainnya")
    df.loc[df["sektor"] == "Organisasi internasional", "kawasan"] = "Organisasi internasional"
    df["jumlah_kontroversi"] = df["kontroversi"].fillna("").map(lambda s: len([k for k in s.split(";") if k]))
    df["masih_berjalan"] = df["status"].isin(["Aktif", "Rintisan", "Ditinjau ulang"])
    return df


def saring(df: pd.DataFrame, sektor=None, status=None, kepastian=None, tahun=None) -> pd.DataFrame:
    """Filter sederhana. Argumen None berarti tidak difilter."""
    m = pd.Series(True, index=df.index)
    if sektor:
        m &= df["sektor"].isin(sektor)
    if status:
        m &= df["status"].isin(status)
    if kepastian:
        m &= df["kepastian"].isin(kepastian)
    if tahun:
        m &= df["tahun_mulai"].between(tahun[0], tahun[1])
    return df[m]


def ringkas_per_negara(df: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per negara: jumlah lembaga, sektor, nilai kontrak publik, kontroversi."""
    if df.empty:
        return pd.DataFrame(columns=["iso3", "negara", "jumlah", "sektor", "nilai_usd_juta",
                                     "kontroversi", "mundur"])
    g = df.groupby("iso3")
    hasil = pd.DataFrame({
        "negara": g["negara"].first(),
        "jumlah": g.size(),
        "sektor": g["sektor"].agg(lambda s: ", ".join(sorted(set(s)))),
        "nilai_usd_juta": g["nilai_usd_juta"].sum(min_count=1),
        "kontroversi": g["jumlah_kontroversi"].sum(),
        "mundur": g["status"].agg(lambda s: int(s.isin(STATUS_MUNDUR).sum())),
    }).reset_index()
    return hasil.sort_values(["jumlah", "nilai_usd_juta"], ascending=False).reset_index(drop=True)


def aktif_pada(df: pd.DataFrame, tahun: int) -> pd.DataFrame:
    """Baris yang sudah dimulai dan belum berakhir pada `tahun`."""
    akhir = df["tahun_akhir"].astype("float")
    return df[(df["tahun_mulai"] <= tahun) & (akhir.isna() | (akhir >= tahun))]


def peta_per_tahun(df: pd.DataFrame, dari: int, sampai: int) -> pd.DataFrame:
    """Jumlah lembaga aktif per negara untuk setiap tahun (bahan peta animasi)."""
    baris = []
    for th in range(dari, sampai + 1):
        a = aktif_pada(df, th)
        for (iso3, negara), n in a.groupby(["iso3", "negara"]).size().items():
            baris.append({"tahun": th, "iso3": iso3, "negara": negara, "jumlah": int(n)})
    return pd.DataFrame(baris, columns=["tahun", "iso3", "negara", "jumlah"])


def timeline_kumulatif(df: pd.DataFrame, sampai: int | None = None) -> pd.DataFrame:
    """Per tahun: lembaga baru, lembaga aktif, dan jumlah negara aktif.

    `sampai` default = tahun mulai paling akhir di data (tahun_akhir bisa berupa
    rencana di masa depan, misalnya kontrak yang berlaku s.d. 2028).
    """
    if df.empty:
        return pd.DataFrame(columns=["tahun", "baru", "aktif", "negara_aktif"])
    akhir = int(sampai or df["tahun_mulai"].max())
    baris = []
    for th in range(int(df["tahun_mulai"].min()), akhir + 1):
        a = aktif_pada(df, th)
        baris.append({
            "tahun": th,
            "baru": int((df["tahun_mulai"] == th).sum()),
            "aktif": len(a),
            "negara_aktif": a["iso3"].nunique(),
        })
    return pd.DataFrame(baris)


def ringkas_kontroversi(kon: pd.DataFrame, kolom: str) -> pd.DataFrame:
    """Hitung kontroversi per `kolom` (jenis/hasil/negara) beserta rata-rata dampak."""
    return (kon.groupby(kolom)
               .agg(jumlah=("id", "count"), dampak_rata=("dampak", "mean"))
               .reset_index()
               .sort_values(["jumlah", "dampak_rata"], ascending=False)
               .reset_index(drop=True))


def kontroversi_per_tahun(kon: pd.DataFrame) -> pd.DataFrame:
    """Tabel tahun x jenis kontroversi (bahan stacked bar)."""
    return kon.groupby(["tahun", "jenis"]).size().reset_index(name="jumlah")


def kontroversi_untuk(pengguna_row: pd.Series, kon: pd.DataFrame) -> pd.DataFrame:
    ids = [k for k in str(pengguna_row.get("kontroversi", "")).split(";") if k]
    return kon[kon["id"].isin(ids)]


def pangsa_pendapatan(pend: pd.DataFrame, jenis: str) -> pd.DataFrame:
    """Pivot tahun x kategori (juta USD) plus kolom persen.

    Untuk wilayah, Prancis (hanya dilaporkan terpisah 2019-2021) digabung ke
    'Negara lain' supaya kategorinya konsisten di semua tahun.
    """
    d = pend[pend["jenis"] == jenis].copy()
    if jenis == "wilayah":
        d["kategori"] = d["kategori"].replace({"Prancis": "Negara lain"})
    p = d.pivot_table(index="tahun", columns="kategori", values="nilai_juta_usd", aggfunc="sum").fillna(0)
    total = p.sum(axis=1)
    for kol in list(p.columns):
        p[f"{kol} (%)"] = (p[kol] / total * 100).round(1)
    p["Total"] = total.round(1)
    return p.reset_index()


def cagr(awal: float, akhir: float, tahun: int) -> float:
    """Compound annual growth rate dalam persen."""
    if awal <= 0 or tahun <= 0:
        raise ValueError("awal dan tahun harus positif")
    return round(((akhir / awal) ** (1 / tahun) - 1) * 100, 1)


def rekap(df: pd.DataFrame, kon: pd.DataFrame) -> dict:
    """Angka utama untuk kartu KPI."""
    negara = df.loc[df["sektor"] != "Organisasi internasional", "iso3"].nunique()
    return {
        "lembaga": len(df),
        "negara": int(negara),
        "organisasi_internasional": int((df["sektor"] == "Organisasi internasional").sum()),
        "kontroversi": len(kon),
        "nilai_publik_usd_juta": float(df["nilai_usd_juta"].sum(min_count=1) or 0),
        "mundur": int(df["status"].isin(STATUS_MUNDUR).sum()),
        "pemerintah": int((df["sektor"] != "Korporasi").sum()),
    }
