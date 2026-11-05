# 🏋️ Latihan

Diurutkan dari yang mudah ke yang lebih menantang. Setiap latihan dilengkapi petunjuk dan kunci jawaban yang dapat
dibuka. Usahakan mencoba minimal 10 menit sebelum membuka kunci. Setelah setiap latihan, jalankan
`python -m pytest tests/` dan `streamlit run app.py`.

---

### Latihan 1 — Tambah satu lembaga ⭐

Temukan satu lembaga pengguna Palantir yang belum ada di dataset (misalnya dari siaran pers Palantir atau berita),
lalu tambahkan sebagai baris baru di `data/pengguna_palantir.csv`. Pastikan tes tetap lulus.

<details><summary>Petunjuk</summary>
Salin satu baris yang mirip, ganti nilainya. Perhatikan: `id` harus unik, `sektor` dan `status` harus persis salah
satu nilai di `src/muat_data.py`, dan `sumber_url` wajib diawali `https://`. Teks yang mengandung koma harus diapit
tanda kutip.
</details>

<details><summary>Kunci</summary>

Contoh baris (lembaga fiktif, ganti dengan yang asli):

```csv
xx-contoh,Negara Contoh,XXX,Kementerian Contoh,Pemerintahan sipil,Foundry,2024,,Aktif,,,,"Ibu Kota",0.0,0.0,"Ringkasan satu kalimat.",Resmi,Nama Media,https://contoh.com/berita,
```

Jika `pytest` gagal di `test_dataset_lolos_validasi`, pesan errornya menyebut id dan kolom yang bermasalah.
Jika negaranya baru, tambahkan juga kode ISO-3-nya ke `KAWASAN` di `src/analisis.py` (tes `test_semua_kawasan_dikenal`).
</details>

---

### Latihan 2 — Ganti warna utama ⭐

Warna utama aplikasi saat ini oranye `#fb923c`. Ubah menjadi biru es `#7dd3fc` di tombol, slider, dan skala peta.

<details><summary>Petunjuk</summary>
Ada dua tempat: `primaryColor` di `.streamlit/config.toml` (komponen Streamlit) dan `WARNA_UTAMA` + `SKALA_ORANYE`
di `app.py` (grafik Plotly).
</details>

<details><summary>Kunci</summary>

```toml
# .streamlit/config.toml
primaryColor = "#7dd3fc"
```

```python
# app.py
WARNA_UTAMA = "#7dd3fc"
SKALA_ORANYE = [[0, "#0c2a3a"], [0.1, "#0e4a66"], [0.3, "#2b8fbf"], [1, "#e0f2fe"]]
```
Sebaiknya ganti juga nama `SKALA_ORANYE` menjadi `SKALA_UTAMA`.
</details>

---

### Latihan 3 — Filter kawasan ⭐⭐

Tambahkan `st.multiselect("Kawasan", ...)` di sidebar sehingga pengguna bisa melihat Eropa saja, atau Asia-Pasifik saja.

<details><summary>Petunjuk</summary>
Kolom `kawasan` sudah ditambahkan oleh `analisis.lengkapi`. Kamu bisa menambah parameter `kawasan=None` ke
`analisis.saring`, lalu menulis tesnya di `tests/test_analisis.py`.
</details>

<details><summary>Kunci</summary>

```python
# src/analisis.py
def saring(df, sektor=None, status=None, kepastian=None, tahun=None, kawasan=None):
    ...
    if kawasan:
        m &= df["kawasan"].isin(kawasan)
    return df[m]
```

```python
# app.py (sidebar)
semua_kawasan = sorted(df_semua["kawasan"].unique())
kawasan_pilih = st.multiselect("Kawasan", semua_kawasan, default=semua_kawasan)
...
df = analisis.saring(df_semua, sektor_pilih, status_pilih, kepastian_pilih, rentang, kawasan_pilih)
```
</details>

---

### Latihan 4 — Rasio kontroversi per sektor ⭐⭐

Buat fungsi `rasio_kontroversi(df)` yang menghitung, untuk setiap sektor, jumlah kontroversi dibagi jumlah lembaga.
Tampilkan sebagai bar chart di tab Controversies. Sektor mana yang paling "bermasalah" per lembaga?

<details><summary>Petunjuk</summary>
Kolom `jumlah_kontroversi` sudah ada per baris. Gunakan `groupby("sektor").agg(...)`.
</details>

<details><summary>Kunci</summary>

```python
def rasio_kontroversi(df):
    g = df.groupby("sektor").agg(lembaga=("id", "count"), kontroversi=("jumlah_kontroversi", "sum"))
    g["rasio"] = (g["kontroversi"] / g["lembaga"]).round(2)
    return g.reset_index().sort_values("rasio", ascending=False)
```
Perhatikan bahwa sektor dengan sedikit lembaga bisa punya rasio ekstrem. Tampilkan juga jumlah lembaganya agar
pembaca tidak salah tafsir.
</details>

---

### Latihan 5 — Peta khusus kontroversi ⭐⭐

Buat peta baru yang mewarnai negara menurut **rata-rata dampak** kontroversinya (1–3), bukan jumlah lembaga.

<details><summary>Petunjuk</summary>
Kontroversi tidak punya kode ISO-3, tetapi bisa dihubungkan lewat lembaga: pecah kolom `kontroversi` dengan
`str.split(";")` lalu `explode()`, kemudian `merge` dengan `kontroversi.csv`.
</details>

<details><summary>Kunci</summary>

```python
pasangan = (df[["iso3", "negara", "kontroversi"]]
            .assign(kontroversi=lambda d: d["kontroversi"].str.split(";"))
            .explode("kontroversi"))
pasangan = pasangan[pasangan["kontroversi"] != ""]
gabung = pasangan.merge(kon, left_on="kontroversi", right_on="id")
per_negara = gabung.groupby(["iso3", "negara_x"])["dampak"].mean().reset_index()
fig = px.choropleth(per_negara, locations="iso3", color="dampak", range_color=(1, 3))
```
Satu kontroversi yang terkait dua lembaga di negara yang sama akan terhitung dua kali. Pakai
`drop_duplicates(["iso3", "kontroversi"])` sebelum `groupby` untuk menghindarinya.
</details>

---

### Latihan 6 — Pendapatan kuartalan ⭐⭐⭐

Laporan 10-Q (kuartalan) punya tabel yang sama dengan 10-K. Kembangkan `scripts/ambil_pendapatan_sec.py` agar juga
mengambil pendapatan per kuartal dari 10-Q tahun 2026, lalu tampilkan di tab Follow the revenue.

<details><summary>Petunjuk</summary>
Daftar laporan ada di `https://data.sec.gov/submissions/CIK0001321655.json` (kolom `form`, `accessionNumber`,
`primaryDocument`). Header tabel 10-Q berbunyi *Three Months Ended* dan *Nine Months Ended*; `_tahun_header` hanya
mengenali tahun, jadi kamu perlu membedakan kolom tiga bulan dan sembilan bulan.
</details>

<details><summary>Kunci</summary>

Garis besarnya:
1. Ambil JSON submissions, saring `form == "10-Q"`.
2. Untuk setiap 10-Q, cari tabel yang barisnya memuat *Three Months Ended*; ambil dua kolom pertama (kuartal ini dan
   kuartal yang sama tahun lalu).
3. Simpan dengan kolom `periode` seperti `2026-Q3`.
4. Tulis tes dengan potongan HTML tiruan seperti di `tests/test_sec.py`.
</details>

---

### Latihan 7 — Cocokkan dengan USAspending ⭐⭐⭐

USAspending.gov punya API gratis untuk semua kontrak federal AS. Ambil total obligasi kontrak ke Palantir per lembaga
(agency) dan bandingkan dengan baris AS di dataset kurasi. Lembaga mana yang ada di USAspending tetapi belum ada di
dataset?

<details><summary>Petunjuk</summary>
Endpoint `POST https://api.usaspending.gov/api/v2/search/spending_by_category/awarding_agency/` dengan filter
`recipient_search_text: ["Palantir"]` dan `award_type_codes` kontrak (`A`, `B`, `C`, `D`). Tidak perlu API key.
</details>

<details><summary>Kunci</summary>

```python
import requests
body = {
    "filters": {
        "recipient_search_text": ["Palantir"],
        "award_type_codes": ["A", "B", "C", "D"],
        "time_period": [{"start_date": "2020-10-01", "end_date": "2026-09-30"}],
    },
    "limit": 50,
}
r = requests.post("https://api.usaspending.gov/api/v2/search/spending_by_category/awarding_agency/", json=body, timeout=60)
for baris in r.json()["results"]:
    print(baris["name"], round(baris["amount"] / 1e6, 1), "juta USD")
```
Perhatikan perbedaan **obligasi** (uang yang sudah dikontrakkan) dengan **plafon** di dataset kurasi. Keduanya
bisa sangat berbeda.
</details>

---

### Latihan 8 — Riwayat status ⭐⭐⭐

Saat ini setiap lembaga hanya punya status terakhir. Rancang tabel baru `data/riwayat.csv` (id_lembaga, tanggal,
peristiwa, status_sesudah, sumber_url) dan tampilkan riwayat NHS England dan DGSI Prancis sebagai timeline.

<details><summary>Petunjuk</summary>
Untuk DGSI: mulai 2016, diperpanjang Desember 2025, penggantian diumumkan Juni 2026. Gunakan
`px.timeline` atau `go.Scatter` dengan mode `lines+markers+text`.
</details>

<details><summary>Kunci</summary>

Skema yang disarankan:

```csv
id_lembaga,tanggal,peristiwa,status_sesudah,sumber_url
fra-dgsi,2016-01-01,Kontrak awal setelah serangan teror 2015,Aktif,https://...
fra-dgsi,2025-12-01,Diperpanjang tiga tahun,Aktif,https://...
fra-dgsi,2026-06-01,Penggantian dengan ChapsVision diumumkan,Ditinjau ulang,https://...
```
Tambahkan validasi bahwa `id_lembaga` ada di `pengguna_palantir.csv` dan tanggal terurut per lembaga, lalu tulis
tesnya. Status terakhir di riwayat seharusnya sama dengan kolom `status` di dataset utama; itu juga bisa dites.
</details>
