"""
app.py - Who Uses Palantir
==========================
Jalankan dengan:   streamlit run app.py

Alur besar file ini (baca dari atas ke bawah):
  1. Import library + konfigurasi halaman
  2. Muat tiga dataset (src/muat_data.py) dan tambah kolom turunan (src/analisis.py)
  3. Sidebar: filter sektor, status, kepastian sumber, rentang tahun, learning mode
  4. Angka ringkasan -> tab World map / Who's who / Timeline / Controversies /
     Follow the revenue / Data & sources / How it works

Setiap bagian diberi komentar "APA" dan "MENGAPA". Penjelasan istilah ada di docs/BELAJAR.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analisis, muat_data

# ----------------------------------------------------------------------------
# 0. KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Who Uses Palantir", page_icon="🔮", layout="wide")

TEMPLATE = "plotly_dark"
WARNA_UTAMA = "#fb923c"
# Delapan warna kategori dengan urutan tetap (lolos uji buta warna di latar gelap).
# Warna mengikuti sektor, bukan peringkat, jadi filter tidak mengubah warna sektor lain.
WARNA_SEKTOR = dict(zip(muat_data.SEKTOR, [
    "#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767",
]))
WARNA_STATUS = {
    "Aktif": "#199e70", "Rintisan": "#3987e5", "Ditinjau ulang": "#c98500",
    "Ditolak/diblokir": "#e66767", "Berakhir": "#6b7280", "Status tidak jelas": "#9ca3af",
}
# Skala satu warna (oranye) dari gelap ke terang. Langkahnya rapat di ujung bawah karena sebagian besar
# negara hanya punya 1-3 lembaga, sementara Amerika Serikat belasan.
SKALA_ORANYE = [[0, "#4a2a12"], [0.1, "#8a3f10"], [0.3, "#d4691c"], [1, "#fed7aa"]]
SIMBOL_KEPASTIAN = {"Resmi": "circle", "Laporan media": "diamond"}
DISCLAIMER = (
    "ℹ️ Seluruh data dirangkum dari **sumber publik**: pengumuman resmi, dokumen pengadaan, laporan tahunan SEC, "
    "dan liputan media yang ditautkan di setiap baris. Daftar ini tidak lengkap, karena banyak kontrak intelijen dan "
    "militer bersifat rahasia. Kolom *kepastian* membedakan yang diumumkan resmi dari yang hanya dilaporkan media. "
    "Proyek edukatif dan portofolio pribadi, tidak berafiliasi dengan Palantir atau instansi mana pun."
)


def rapikan(fig: go.Figure, tinggi: int = 420) -> go.Figure:
    """Gaya seragam untuk semua grafik Plotly: latar transparan, grid tipis, legenda di atas."""
    fig.update_layout(
        template=TEMPLATE, height=tinggi,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=95, b=10),
        title=dict(y=0.99, yanchor="top", x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif"),
        hoverlabel=dict(bgcolor="#161c28", font_size=13),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#2a3242", zeroline=False)
    return fig


def gaya_peta(fig: go.Figure, tinggi: int = 560) -> go.Figure:
    fig.update_geos(
        projection_type="natural earth", showframe=False, showcoastlines=False,
        showcountries=True, countrycolor="#2a3242", showland=True, landcolor="#1a2130",
        showocean=True, oceancolor="#0b0f17", bgcolor="rgba(0,0,0,0)", lataxis_range=[-58, 85],
    )
    fig.update_layout(height=tinggi, margin=dict(l=0, r=0, t=40, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", template=TEMPLATE,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None))
    return fig


def format_usd(juta: float | None) -> str:
    if juta is None or pd.isna(juta):
        return "tidak diumumkan"
    if juta >= 1000:
        return f"${juta / 1000:,.1f} miliar"
    return f"${juta:,.1f} juta"


KONFIG_PLOTLY = {"displayModeBar": False}
KONFIG_TABEL = {
    "Sumber": st.column_config.LinkColumn("Sumber", display_text="buka ↗"),
    "Nilai (juta USD)": st.column_config.NumberColumn(format="%.1f"),
}


# ----------------------------------------------------------------------------
# 1. MUAT DATA
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Membaca dataset...")
def muat_semua():
    """
    APA: tiga CSV di folder data/. MENGAPA di-cache: file kecil, tetapi Streamlit menjalankan
    ulang seluruh skrip setiap kali pengguna menggeser filter.
    """
    pengguna = analisis.lengkapi(muat_data.muat_pengguna())
    kontroversi = muat_data.muat_kontroversi()
    pendapatan = muat_data.muat_pendapatan()
    return pengguna, kontroversi, pendapatan


df_semua, kon_semua, pend = muat_semua()

# ----------------------------------------------------------------------------
# 2. SIDEBAR
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🔮 Who Uses Palantir")
    st.caption("Peta lembaga yang memakai Palantir di seluruh dunia, lengkap dengan kontroversi dan sumbernya.")

    st.subheader("Filter")
    sektor_pilih = st.multiselect("Sektor", muat_data.SEKTOR, default=muat_data.SEKTOR)
    status_pilih = st.multiselect("Status", muat_data.STATUS, default=muat_data.STATUS,
                                  help="Ditinjau ulang = kontrak masih berjalan tetapi sedang dievaluasi atau dijadwalkan diganti.")
    kepastian_pilih = st.multiselect("Kepastian sumber", muat_data.KEPASTIAN, default=muat_data.KEPASTIAN,
                                     help="Resmi = diumumkan pemerintah/Palantir atau ada dokumen pengadaan. "
                                          "Laporan media = berasal dari investigasi jurnalis.")
    th_min, th_maks = int(df_semua["tahun_mulai"].min()), int(df_semua["tahun_mulai"].max())
    rentang = st.slider("Tahun mulai", th_min, th_maks, (th_min, th_maks))
    warnai = st.radio("Warnai titik di peta menurut", ["Sektor", "Status"], horizontal=True)

    mode_belajar = st.toggle("🎓 Learning mode", value=False, help="Tampilkan rumus dan potongan kode di setiap bagian.")
    st.caption(f"Dataset: {len(df_semua)} lembaga, {len(kon_semua)} kontroversi, pendapatan 10-K "
               f"{int(pend['tahun'].min())}–{int(pend['tahun'].max())}. Kurasi terakhir: November 2026.")

df = analisis.saring(df_semua, sektor_pilih, status_pilih, kepastian_pilih, rentang).reset_index(drop=True)
# Kontroversi yang relevan: yang ditautkan ke lembaga terpilih, plus kontroversi tingkat kawasan
# (misalnya gelombang Eropa) yang negaranya masih ada di pilihan.
id_terkait = {k for s in df["kontroversi"] for k in s.split(";") if k}
kon = kon_semua[kon_semua["id"].isin(id_terkait) | kon_semua["negara"].isin(["Eropa", "PBB", "Uni Eropa"])]

if df.empty:
    st.warning("Tidak ada lembaga yang cocok dengan filter. Longgarkan filter di sidebar.")
    st.stop()

# ----------------------------------------------------------------------------
# 3. HEADER + ANGKA RINGKASAN
# ----------------------------------------------------------------------------
st.title("🔮 Who Uses Palantir")
st.markdown(
    "**The seeing stone has customers.** Palantir menjual perangkat lunak yang menyatukan data menjadi satu "
    "'peta operasi': untuk militer, intelijen, polisi, imigrasi, sampai rumah sakit. Aplikasi ini memetakan "
    "siapa saja pembelinya, berapa nilainya bila diumumkan, dan kontroversi apa yang mengikutinya."
)

r = analisis.rekap(df, kon)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Lembaga & kontrak", r["lembaga"])
k2.metric("Negara", r["negara"], help=f"Ditambah {r['organisasi_internasional']} organisasi internasional (NATO, Europol, WFP).")
k3.metric("Nilai kontrak publik", format_usd(r["nilai_publik_usd_juta"]),
          help="Jumlah nilai/plafon kontrak yang diumumkan, dikonversi dengan kurs perkiraan. "
               "Plafon US Army $10 miliar mendominasi angka ini.")
k4.metric("Kontroversi tercatat", r["kontroversi"])
k5.metric("Sedang mundur", r["mundur"], help="Lembaga dengan status Ditinjau ulang atau Ditolak/diblokir.")

tab_peta, tab_siapa, tab_waktu, tab_kon, tab_uang, tab_data, tab_cara = st.tabs([
    "🌍 World map", "🏛️ Who's who", "⏳ Timeline", "⚠️ Controversies",
    "💰 Follow the revenue", "📋 Data & sources", "🧭 How it works",
])

# ----------------------------------------------------------------------------
# 4a. WORLD MAP
# ----------------------------------------------------------------------------
with tab_peta:
    df_negara = df[df["sektor"] != "Organisasi internasional"]
    per_negara = analisis.ringkas_per_negara(df_negara)

    # APA: dua lapis. Choropleth = jumlah lembaga per negara; titik = setiap lembaga di kotanya.
    # MENGAPA titik digeser sedikit: banyak lembaga berkantor di kota yang sama (Washington, London),
    # tanpa geseran mereka akan bertumpuk menjadi satu titik.
    titik = df.copy()
    urutan = titik.groupby("kota").cumcount()
    sudut = urutan * 2.4
    titik["lat_t"] = titik["lat"] + np.where(urutan > 0, 0.9 * np.sin(sudut) * np.sqrt(urutan), 0)
    titik["lon_t"] = titik["lon"] + np.where(urutan > 0, 1.2 * np.cos(sudut) * np.sqrt(urutan), 0)
    titik["nilai_teks"] = titik["nilai_usd_juta"].map(format_usd)

    fig = go.Figure(go.Choropleth(
        locations=per_negara["iso3"], z=per_negara["jumlah"], text=per_negara["negara"],
        colorscale=SKALA_ORANYE, marker_line_color="#0b0f17",
        marker_line_width=0.6, colorbar=dict(title="Lembaga", thickness=10, len=0.5, x=0.0, y=0.25),
        hovertemplate="<b>%{text}</b><br>%{z} lembaga/kontrak<extra></extra>",
    ))
    kolom_warna = "sektor" if warnai == "Sektor" else "status"
    peta_warna = WARNA_SEKTOR if warnai == "Sektor" else WARNA_STATUS
    for kategori, warna in peta_warna.items():
        bagian = titik[titik[kolom_warna] == kategori]
        if bagian.empty:
            continue
        fig.add_trace(go.Scattergeo(
            lat=bagian["lat_t"], lon=bagian["lon_t"], name=kategori, mode="markers",
            marker=dict(size=10, color=warna, line=dict(color="#0b0f17", width=2),
                        symbol=[SIMBOL_KEPASTIAN[k] for k in bagian["kepastian"]]),
            customdata=bagian[["lembaga", "negara", "status", "tahun_mulai", "nilai_teks", "produk"]],
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]} · sejak %{customdata[3]}<br>"
                           "Status: %{customdata[2]}<br>Produk: %{customdata[5]}<br>Nilai: %{customdata[4]}<extra></extra>"),
        ))
    st.plotly_chart(gaya_peta(fig, 580), use_container_width=True, config=KONFIG_PLOTLY)
    st.caption("Lingkaran = diumumkan resmi, belah ketupat = laporan media. Organisasi internasional "
               "digambar di markasnya (NATO di Mons, Europol di Den Haag, WFP di Roma) tetapi tidak ikut mewarnai negaranya.")
    st.info(DISCLAIMER)

    kiri, kanan = st.columns([3, 2])
    with kiri:
        st.subheader("Negara dengan lembaga terbanyak")
        tampil = per_negara.rename(columns={
            "negara": "Negara", "jumlah": "Lembaga", "sektor": "Sektor",
            "nilai_usd_juta": "Nilai (juta USD)", "kontroversi": "Kontroversi", "mundur": "Mundur"})
        st.dataframe(tampil.drop(columns="iso3"), hide_index=True, use_container_width=True,
                     column_config=KONFIG_TABEL, height=360)
    with kanan:
        st.subheader("🇮🇩 Bagaimana dengan Indonesia?")
        st.markdown(
            "Sampai November 2026 **tidak ditemukan kontrak publik** antara Palantir dan pemerintah Indonesia, "
            "dan juga tidak ada di negara ASEAN lain. Pelanggan Asia Palantir yang terdokumentasi adalah "
            "korporasi Jepang dan Korea Selatan, serta militer dan intelijen Australia dan Selandia Baru.\n\n"
            "Polanya menarik: Palantir paling kuat di negara sekutu dekat Amerika Serikat. Di Eropa, "
            "isu kedaulatan data justru membuat beberapa negara mundur sepanjang 2026."
        )
        jumlah_kawasan = df.groupby("kawasan").size().reset_index(name="lembaga").sort_values("lembaga")
        fig_k = px.bar(jumlah_kawasan, x="lembaga", y="kawasan", orientation="h",
                       title="Lembaga per kawasan", text="lembaga", color_discrete_sequence=[WARNA_UTAMA])
        fig_k.update_traces(marker_cornerradius=4, textposition="outside",
                            hovertemplate="%{y}: %{x} lembaga<extra></extra>")
        fig_k.update_layout(yaxis_title=None, xaxis_title=None)
        st.plotly_chart(rapikan(fig_k, 300), use_container_width=True, config=KONFIG_PLOTLY)

    if mode_belajar:
        with st.expander("🎓 Membuat peta dua lapis dengan Plotly"):
            st.markdown(
                "Peta ini adalah satu `go.Figure` berisi **satu trace `Choropleth`** (warna negara dari kode "
                "ISO-3) dan **beberapa trace `Scattergeo`** (satu per kategori warna, supaya legendanya rapi).\n\n"
                "Titik yang berbagi kota disusun mengikuti spiral kecil, sehingga tidak saling menutupi:"
            )
            st.code(
                "urutan = titik.groupby('kota').cumcount()          # 0, 1, 2, ... per kota\n"
                "sudut = urutan * 2.4                               # ±137 derajat (golden angle)\n"
                "titik['lat_t'] = lat + 0.9 * np.sin(sudut) * np.sqrt(urutan)\n"
                "titik['lon_t'] = lon + 1.2 * np.cos(sudut) * np.sqrt(urutan)",
                language="python",
            )
            st.markdown("Sudut 2,4 radian adalah *golden angle*: titik ke-n tidak pernah segaris dengan titik "
                        "sebelumnya, pola yang sama dengan susunan biji bunga matahari.")

# ----------------------------------------------------------------------------
# 4b. WHO'S WHO
# ----------------------------------------------------------------------------
with tab_siapa:
    kiri, kanan = st.columns([1, 1])
    with kiri:
        # APA: sunburst sektor -> negara -> lembaga. MENGAPA: satu gambar memperlihatkan sektor mana yang
        # mendominasi dan negara mana yang tersebar di banyak sektor.
        sb = df.assign(jumlah=1)
        fig_sb = px.sunburst(sb, path=["sektor", "negara", "lembaga"], values="jumlah", color="sektor",
                             color_discrete_map=WARNA_SEKTOR, maxdepth=2,
                             title="Sektor → negara (klik untuk masuk ke lembaga)")
        fig_sb.update_traces(marker_line_color="#0b0f17", marker_line_width=2, insidetextorientation="radial",
                             hovertemplate="<b>%{label}</b><br>%{value} lembaga<extra></extra>")
        st.plotly_chart(rapikan(fig_sb, 560), use_container_width=True, config=KONFIG_PLOTLY)
    with kanan:
        hitung = df.groupby(["sektor", "status"]).size().reset_index(name="jumlah")
        urut_sektor = df["sektor"].value_counts().index.tolist()[::-1]
        fig_st = px.bar(hitung, y="sektor", x="jumlah", color="status", orientation="h",
                        color_discrete_map=WARNA_STATUS, category_orders={"sektor": urut_sektor, "status": muat_data.STATUS},
                        title="Status hubungan per sektor")
        fig_st.update_traces(marker_line_color="#0b0f17", marker_line_width=2,
                             hovertemplate="%{y} · %{fullData.name}: %{x}<extra></extra>")
        fig_st.update_layout(yaxis_title=None, xaxis_title="Jumlah lembaga")
        st.plotly_chart(rapikan(fig_st, 560), use_container_width=True, config=KONFIG_PLOTLY)

    st.subheader("🔎 Telusuri satu lembaga")
    c1, c2 = st.columns([1, 2])
    cari = c1.text_input("Cari nama lembaga, negara, atau produk", placeholder="contoh: NHS, ICE, Gotham, polisi")
    pilihan = df
    if cari:
        kunci = cari.lower()
        pilihan = df[df[["lembaga", "negara", "produk", "ringkasan", "sektor"]].apply(
            lambda b: b.str.lower().str.contains(kunci, regex=False)).any(axis=1)]
    if pilihan.empty:
        c2.warning("Tidak ada lembaga yang cocok.")
    else:
        nama = c2.selectbox("Lembaga", pilihan["lembaga"] + " · " + pilihan["negara"], index=0)
        baris = pilihan.iloc[(pilihan["lembaga"] + " · " + pilihan["negara"]).tolist().index(nama)]
        with st.container(border=True):
            a, b, c = st.columns(3)
            a.metric("Sejak", int(baris["tahun_mulai"]))
            b.metric("Status", baris["status"])
            c.metric("Nilai", format_usd(baris["nilai_usd_juta"]))
            st.markdown(f"<span style='background:{WARNA_SEKTOR[baris['sektor']]};padding:2px 10px;border-radius:10px;"
                        f"color:#fff;font-size:0.85rem'>{baris['sektor']}</span>", unsafe_allow_html=True)
            st.markdown(f"**{baris['lembaga']}** ({baris['negara']}, {baris['kota']}). Produk: *{baris['produk']}*.")
            st.write(baris["ringkasan"])
            if baris["catatan_nilai"]:
                nilai_asli = ""
                if pd.notna(baris["nilai_asli_juta"]):
                    nilai_asli = f"{baris['mata_uang']} {baris['nilai_asli_juta']:,.1f} juta. "
                st.caption(f"💵 {nilai_asli}{baris['catatan_nilai']}")
            st.caption(f"Kepastian: **{baris['kepastian']}** · Sumber: [{baris['sumber_nama']}]({baris['sumber_url']})")
            terkait = analisis.kontroversi_untuk(baris, kon_semua)
            for _, k in terkait.iterrows():
                st.warning(f"**⚠️ {k['judul']}** ({k['tahun']}, {k['jenis']}). {k['ringkasan']} "
                           f"[{k['sumber_nama']}]({k['sumber_url']})")

# ----------------------------------------------------------------------------
# 4c. TIMELINE
# ----------------------------------------------------------------------------
with tab_waktu:
    tl = analisis.timeline_kumulatif(df)
    kiri, kanan = st.columns([3, 2])
    with kiri:
        # APA: setiap lembaga sebagai satu titik di tahun mulainya, dikelompokkan per sektor.
        # MENGAPA scatter, bukan bar: kita ingin melihat siapa, bukan hanya berapa.
        tsc = df.copy()
        fig_t = px.strip(tsc, x="tahun_mulai", y="sektor", color="status", color_discrete_map=WARNA_STATUS,
                         hover_data={"lembaga": True, "negara": True, "tahun_mulai": True, "sektor": False},
                         category_orders={"sektor": muat_data.SEKTOR, "status": muat_data.STATUS},
                         title="Kapan setiap lembaga mulai memakai Palantir")
        fig_t.update_traces(marker=dict(size=11, line=dict(color="#0b0f17", width=2)), jitter=0.5)
        fig_t.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(rapikan(fig_t, 460), use_container_width=True, config=KONFIG_PLOTLY)
    with kanan:
        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(x=tl["tahun"], y=tl["aktif"], name="Lembaga aktif", mode="lines+markers",
                                   line=dict(color=WARNA_UTAMA, width=2), marker=dict(size=8),
                                   hovertemplate="%{x}: %{y} lembaga aktif<extra></extra>"))
        fig_a.add_trace(go.Bar(x=tl["tahun"], y=tl["baru"], name="Mulai tahun itu", marker_color="#3987e5",
                               marker_cornerradius=4, hovertemplate="%{x}: %{y} lembaga baru<extra></extra>"))
        fig_a.update_layout(title="Lembaga aktif per tahun", hovermode="x unified", barmode="overlay")
        st.plotly_chart(rapikan(fig_a, 460), use_container_width=True, config=KONFIG_PLOTLY)

    # Peta animasi: negara yang punya lembaga aktif di setiap tahun
    st.subheader("▶️ Penyebaran dari tahun ke tahun")
    animasi = analisis.peta_per_tahun(df[df["sektor"] != "Organisasi internasional"],
                                      int(df["tahun_mulai"].min()), int(df["tahun_mulai"].max()))
    if not animasi.empty:
        fig_m = px.choropleth(animasi, locations="iso3", color="jumlah", animation_frame="tahun",
                              hover_name="negara", range_color=(0, max(1, animasi["jumlah"].max())),
                              color_continuous_scale=SKALA_ORANYE,
                              labels={"jumlah": "Lembaga aktif"})
        fig_m.update_traces(marker_line_color="#0b0f17", marker_line_width=0.6)
        st.plotly_chart(gaya_peta(fig_m, 520), use_container_width=True, config=KONFIG_PLOTLY)
        st.caption("Tekan ▶ untuk memutar. Lembaga yang kontraknya berakhir (misalnya NYPD 2017, Europol 2021) hilang dari peta pada tahun berikutnya.")

    st.markdown(
        "**Tiga gelombang.** (1) 2005–2012: intelijen dan polisi Amerika Serikat, lalu sekutu Five Eyes. "
        "(2) 2016–2020: kepolisian Eropa dan pandemi, saat pemerintah butuh dashboard cepat. "
        "(3) 2022–2026: perang di Ukraina dan AI militer (Maven, NATO, Inggris, Polandia), "
        "bersamaan dengan gelombang balik di Eropa: Swiss, Bundeswehr, Prancis, Belanda, dan Spanyol mulai menjaga jarak."
    )
    if mode_belajar:
        with st.expander("🎓 Menghitung 'aktif pada tahun X'"):
            st.markdown("Sebuah kontrak dihitung aktif pada tahun *t* jika sudah dimulai dan belum berakhir:")
            st.latex(r"\text{aktif}(t) = \{\, i \mid \text{mulai}_i \le t \;\wedge\; (\text{akhir}_i = \varnothing \;\vee\; \text{akhir}_i \ge t) \,\}")
            st.code("akhir = df['tahun_akhir'].astype('float')\n"
                    "aktif = df[(df['tahun_mulai'] <= t) & (akhir.isna() | (akhir >= t))]", language="python")
            st.markdown("Kolom `tahun_akhir` memakai tipe `Int64` (huruf I besar) milik pandas, yang bisa menyimpan "
                        "nilai kosong. Tipe `int64` biasa tidak bisa, sehingga kontrak yang masih berjalan akan "
                        "dipaksa menjadi angka desimal `NaN`.")

# ----------------------------------------------------------------------------
# 4d. CONTROVERSIES
# ----------------------------------------------------------------------------
with tab_kon:
    st.markdown("Setiap kontroversi diberi skor **dampak**: 1 = kritik dan liputan media, 2 = investigasi besar "
                "atau kampanye publik, 3 = berujung putusan pengadilan, kontrak dihentikan, atau diblokir.")
    kiri, kanan = st.columns(2)
    with kiri:
        per_jenis = analisis.ringkas_kontroversi(kon, "jenis").sort_values("jumlah")
        fig_j = px.bar(per_jenis, x="jumlah", y="jenis", orientation="h", text="jumlah",
                       color="dampak_rata", color_continuous_scale=[[0, "#3b2412"], [1, WARNA_UTAMA]],
                       range_color=(1, 3), title="Jenis kontroversi (warna = rata-rata dampak)")
        fig_j.update_traces(marker_cornerradius=4, textposition="outside",
                            hovertemplate="%{y}: %{x} kontroversi<br>rata-rata dampak %{marker.color:.1f}<extra></extra>")
        fig_j.update_layout(yaxis_title=None, xaxis_title=None, coloraxis_colorbar=dict(title="Dampak", thickness=10))
        st.plotly_chart(rapikan(fig_j, 440), use_container_width=True, config=KONFIG_PLOTLY)
    with kanan:
        per_tahun = analisis.kontroversi_per_tahun(kon)
        fig_y = px.bar(per_tahun, x="tahun", y="jumlah", color="jenis", title="Kontroversi per tahun",
                       color_discrete_sequence=list(WARNA_SEKTOR.values()))
        fig_y.update_traces(marker_line_color="#0b0f17", marker_line_width=2,
                            hovertemplate="%{x} · %{fullData.name}: %{y}<extra></extra>")
        fig_y = rapikan(fig_y, 440)
        fig_y.update_layout(xaxis_title=None, yaxis_title=None, xaxis=dict(dtick=2),
                            legend=dict(orientation="h", yanchor="top", y=-0.12, x=0), margin=dict(t=50, b=10))
        st.plotly_chart(fig_y, use_container_width=True, config=KONFIG_PLOTLY)

    hasil = analisis.ringkas_kontroversi(kon, "hasil")
    st.markdown("**Bagaimana akhirnya?** " + " · ".join(f"{h['hasil']}: **{h['jumlah']}**" for _, h in hasil.iterrows()))
    st.markdown(
        "**Polanya berbeda per kawasan.** Di Amerika Serikat, kritik berkisar pada imigrasi, deportasi, dan "
        "privasi data pajak. Di Inggris, sorotannya pada pengadaan tanpa tender dan data pasien NHS. Di Eropa "
        "daratan, isu terbesarnya adalah **kedaulatan data** dan konstitusi: siapa yang bisa mengakses data "
        "polisi dan militer jika vendornya perusahaan Amerika."
    )

    st.subheader("Daftar kontroversi")
    urut = st.radio("Urutkan", ["Dampak tertinggi", "Terbaru"], horizontal=True)
    daftar = kon.sort_values(["dampak", "tahun"] if urut == "Dampak tertinggi" else ["tahun", "dampak"], ascending=False)
    for _, k in daftar.iterrows():
        with st.expander(f"{'🔥' * int(k['dampak'])}  {k['judul']} · {k['negara']}, {k['tahun']}"):
            st.write(k["ringkasan"])
            st.caption(f"Jenis: {k['jenis']} · Hasil: {k['hasil']} · Sumber: [{k['sumber_nama']}]({k['sumber_url']})")
            lembaga_terkait = df_semua[df_semua["kontroversi"].str.contains(k["id"], regex=False)]["lembaga"].tolist()
            if lembaga_terkait:
                st.caption("Lembaga terkait: " + ", ".join(lembaga_terkait))

# ----------------------------------------------------------------------------
# 4e. FOLLOW THE REVENUE
# ----------------------------------------------------------------------------
with tab_uang:
    st.markdown("Kontrak di peta hanya sebagian kecil yang kebetulan diumumkan. Gambaran utuhnya ada di "
                "**laporan tahunan (10-K)** Palantir ke SEC: pendapatan per segmen dan per wilayah, diaudit.")
    seg = analisis.pangsa_pendapatan(pend, "segmen")
    wil = analisis.pangsa_pendapatan(pend, "wilayah")
    th_awal, th_akhir = int(seg["tahun"].min()), int(seg["tahun"].max())

    m1, m2, m3, m4 = st.columns(4)
    pemerintah_akhir = float(seg.loc[seg["tahun"] == th_akhir, "Pemerintah"].iloc[0])
    m1.metric(f"Pendapatan pemerintah {th_akhir}", format_usd(pemerintah_akhir))
    m2.metric("Porsi pemerintah", f"{seg.loc[seg['tahun'] == th_akhir, 'Pemerintah (%)'].iloc[0]:.0f}%")
    m3.metric(f"Pertumbuhan tahunan {th_awal}–{th_akhir}",
              f"{analisis.cagr(float(seg['Total'].iloc[0]), float(seg['Total'].iloc[-1]), th_akhir - th_awal):.0f}%",
              help="CAGR total pendapatan.")
    m4.metric(f"Porsi Amerika Serikat {th_akhir}", f"{wil.loc[wil['tahun'] == th_akhir, 'Amerika Serikat (%)'].iloc[0]:.0f}%",
              delta=f"{wil['Amerika Serikat (%)'].iloc[-1] - wil['Amerika Serikat (%)'].iloc[0]:+.0f} poin sejak {th_awal}")

    kiri, kanan = st.columns(2)
    with kiri:
        seg_long = seg.melt(id_vars="tahun", value_vars=["Pemerintah", "Komersial"], var_name="segmen", value_name="juta")
        fig_s = px.bar(seg_long, x="tahun", y="juta", color="segmen", title="Pendapatan per segmen (juta USD)",
                       color_discrete_map={"Pemerintah": WARNA_UTAMA, "Komersial": "#3987e5"})
        fig_s.update_traces(marker_line_color="#0b0f17", marker_line_width=2,
                            hovertemplate="%{x} · %{fullData.name}: $%{y:,.0f} juta<extra></extra>")
        fig_s.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(rapikan(fig_s, 420), use_container_width=True, config=KONFIG_PLOTLY)
    with kanan:
        wil_long = wil.melt(id_vars="tahun", value_vars=["Amerika Serikat (%)", "Inggris (%)", "Negara lain (%)"],
                            var_name="wilayah", value_name="persen")
        wil_long["wilayah"] = wil_long["wilayah"].str.replace(" (%)", "", regex=False)
        fig_w = px.area(wil_long, x="tahun", y="persen", color="wilayah", title="Porsi pendapatan per wilayah (%)",
                        color_discrete_map={"Amerika Serikat": "#3987e5", "Inggris": WARNA_UTAMA, "Negara lain": "#199e70"})
        fig_w.update_traces(line=dict(width=2), hovertemplate="%{x} · %{fullData.name}: %{y:.1f}%<extra></extra>")
        fig_w.update_layout(xaxis_title=None, yaxis_title=None, yaxis=dict(range=[0, 100]), hovermode="x unified")
        st.plotly_chart(rapikan(fig_w, 420), use_container_width=True, config=KONFIG_PLOTLY)

    st.markdown(
        f"**Bacaannya:** Inggris konsisten menyumbang 10–16% pendapatan, terbesar kedua setelah Amerika Serikat, "
        f"cocok dengan banyaknya kontrak Inggris di peta (NHS, MoD, polisi). Sebaliknya, porsi negara lain menyusut dari "
        f"{wil['Negara lain (%)'].iloc[0]:.0f}% ({th_awal}) menjadi {wil['Negara lain (%)'].iloc[-1]:.0f}% ({th_akhir}): "
        "pertumbuhan Palantir makin bertumpu pada pasar Amerika, tepat saat sebagian Eropa mulai mundur."
    )
    if mode_belajar:
        with st.expander("🎓 Membaca tabel 10-K dari SEC EDGAR"):
            st.markdown(
                "`scripts/ambil_pendapatan_sec.py` mengunduh tiga 10-K (FY2021, FY2023, FY2025). Setiap 10-K memuat "
                "tiga tahun, jadi tiga dokumen sudah mencakup 2019–2025. Tabel HTML-nya berantakan: satu angka bisa "
                "terpecah menjadi `$`, `1,569,605`, `)` di sel terpisah, dan setiap sel terduplikasi karena *colspan*. "
                "`src/sec.py` merapikannya:"
            )
            st.code("bersihkan_baris(['Government', 'Government', '$', '2,402,287', '2,402,287', '$', '1,569,605'])\n"
                    "# -> ['Government', '2,402,287', '1,569,605']", language="python")
            st.markdown("Jebakan yang ditemukan: 10-K lama melaporkan **Prancis** terpisah, 10-K baru memasukkannya ke "
                        "*Rest of world*. Jika data digabung per kategori, tahun 2021 terhitung ganda. Solusinya: untuk "
                        "setiap tahun, ambil semua kategori dari 10-K **terbaru** yang memuat tahun itu.")
            st.markdown("CAGR (*compound annual growth rate*):")
            st.latex(r"\text{CAGR} = \left(\frac{\text{nilai akhir}}{\text{nilai awal}}\right)^{1/n} - 1")

# ----------------------------------------------------------------------------
# 4f. DATA & SOURCES
# ----------------------------------------------------------------------------
with tab_data:
    st.subheader("Lembaga pengguna")
    tabel = df[["lembaga", "negara", "sektor", "produk", "tahun_mulai", "tahun_akhir", "status",
                "nilai_usd_juta", "kepastian", "ringkasan", "sumber_url"]].rename(columns={
        "lembaga": "Lembaga", "negara": "Negara", "sektor": "Sektor", "produk": "Produk",
        "tahun_mulai": "Mulai", "tahun_akhir": "Akhir", "status": "Status", "nilai_usd_juta": "Nilai (juta USD)",
        "kepastian": "Kepastian", "ringkasan": "Ringkasan", "sumber_url": "Sumber"})
    st.dataframe(tabel, hide_index=True, use_container_width=True, column_config=KONFIG_TABEL, height=420)
    st.download_button("⬇️ Download pengguna_palantir.csv", df_semua.drop(columns=["masih_berjalan"]).to_csv(index=False),
                       "pengguna_palantir.csv", "text/csv")

    st.subheader("Kontroversi")
    st.dataframe(kon_semua.rename(columns={"sumber_url": "Sumber"}), hide_index=True, use_container_width=True,
                 column_config=KONFIG_TABEL, height=320)
    st.download_button("⬇️ Download kontroversi.csv", kon_semua.to_csv(index=False), "kontroversi.csv", "text/csv")

    st.subheader("Pendapatan Palantir (10-K)")
    st.dataframe(pend.rename(columns={"sumber_url": "Sumber"}), hide_index=True, use_container_width=True,
                 column_config=KONFIG_TABEL, height=260)

    st.subheader("Metodologi & keterbatasan")
    st.markdown(
        "- **Kurasi manual.** Setiap baris dirangkum dari satu sumber utama yang ditautkan. Prioritas sumber: "
        "pengumuman resmi atau dokumen pengadaan, lalu media dengan reputasi baik, lalu investigasi jurnalis.\n"
        "- **Kepastian.** *Resmi* = diumumkan pemerintah/Palantir atau tercatat di dokumen pengadaan. "
        "*Laporan media* = berasal dari liputan; bisa dibantah oleh pihak terkait.\n"
        "- **Nilai kontrak** sering berupa *plafon* (batas atas), bukan uang yang benar-benar dibelanjakan. "
        "Konversi ke USD memakai kurs perkiraan tetap: "
        + ", ".join(f"1 {k} = {v} USD" for k, v in analisis.KURS_KE_USD.items() if k != "USD") + ".\n"
        "- **Tidak lengkap.** Banyak kontrak intelijen dan militer bersifat rahasia. Korporasi hanya dicantumkan "
        "sebagai contoh (Airbus, bp, SOMPO, KT/LIG Nex1, Dubai Holding), bukan daftar lengkap ratusan klien komersial.\n"
        "- **Bukan penilaian.** Skor dampak kontroversi menggambarkan konsekuensinya (kritik, investigasi, putusan), "
        "bukan menilai siapa yang benar."
    )

# ----------------------------------------------------------------------------
# 4g. HOW IT WORKS
# ----------------------------------------------------------------------------
with tab_cara:
    st.subheader("Dari berita dan dokumen ke peta")
    st.graphviz_chart("""
    digraph {
      rankdir=LR; bgcolor="transparent";
      node [shape=box, style="rounded,filled", fillcolor="#161c28", color="#fb923c", fontcolor="#e8e8e8", fontname="Helvetica"];
      edge [color="#8b93a7"];
      a [label="Sumber publik\\n(pengumuman, pengadaan,\\nmedia, parlemen)"];
      b [label="Kurasi manual\\ndata/pengguna_palantir.csv\\ndata/kontroversi.csv"];
      c [label="SEC EDGAR 10-K\\nscripts/ambil_pendapatan_sec.py"];
      d [label="src/muat_data.py\\nvalidasi skema"];
      e [label="src/analisis.py\\nkurs, kawasan, timeline,\\nringkasan"];
      f [label="app.py\\nStreamlit + Plotly"];
      a -> b -> d; c -> d; d -> e -> f;
    }
    """)
    st.markdown(
        "**Produk Palantir yang muncul di data:**\n\n"
        "| Produk | Untuk siapa | Fungsinya |\n|---|---|---|\n"
        "| **Gotham** | Intelijen, militer, polisi | Menghubungkan orang, tempat, kendaraan, dan kejadian dari banyak basis data menjadi satu graf yang bisa ditelusuri |\n"
        "| **Foundry** | Pemerintahan sipil, kesehatan, korporasi | Platform integrasi data dengan *ontology*: tabel mentah dipetakan menjadi objek bisnis (pasien, kapal, pesawat) |\n"
        "| **AIP** | Semua | Lapisan model bahasa besar di atas Gotham/Foundry, dengan batasan akses dan jejak audit |\n"
        "| **Maven Smart System** | Militer AS & NATO | Fusi sensor, citra satelit, dan intelijen untuk mengenali dan memprioritaskan target |\n"
        "| **MetaConstellation** | Militer | Mengatur satelit komersial untuk memotret area tertentu dan menganalisis hasilnya |\n"
    )
    st.markdown(
        "**Mengapa ini penting.** Palantir tidak mengumpulkan data sendiri. Ia menjual kemampuan untuk "
        "*menyatukan* data yang sebelumnya terpisah. Justru di situlah perdebatannya: data yang aman saat "
        "terpisah bisa menjadi alat pengawasan saat disatukan. Mahkamah Konstitusi Jerman memakai logika "
        "yang sama pada 2023, dan isu kedaulatan data di Eropa berangkat dari pertanyaan siapa yang memegang kuncinya."
    )
    st.caption("Kode sumber dan panduan belajar: docs/BELAJAR.md dan docs/LATIHAN.md di repositori.")
