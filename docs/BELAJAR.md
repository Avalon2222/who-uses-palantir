# 📚 Belajar dari proyek ini

Panduan ini menjelaskan apa yang terjadi di balik aplikasi, dari satu artikel berita sampai titik di peta. Tidak
perlu latar belakang khusus; cukup Python dasar, pandas sedikit, dan rasa penasaran. Setiap bagian menunjuk ke file
dan fungsi yang bisa langsung dibaca.

---

## 1. Gambaran besar

```
Berita, siaran pers, dokumen ──► kurasi manual ──► data/pengguna_palantir.csv
                                                    data/kontroversi.csv
                                                           │
SEC EDGAR (10-K) ──► scripts/ambil_pendapatan_sec.py ──► data/pendapatan_palantir.csv
                     (memakai src/sec.py)                  │
                                                           ▼
                                                 src/muat_data.py   (baca + validasi)
                                                           │
                                                           ▼
                                                 src/analisis.py    (kurs, kawasan, timeline, ringkasan)
                                                           │
                                                           ▼
                                                 app.py             (sidebar, 7 tab, Plotly)
```

Berbeda dengan proyek yang mengambil data dari satu API, sebagian besar data di sini **dikumpulkan dengan tangan**.
Itu bukan kelemahan selama prosesnya jujur dan bisa diperiksa ulang. Bagian 2 dan 3 membahas caranya.

| Pertanyaan | Di mana dijawab |
|---|---|
| Siapa saja yang memakai Palantir, di mana? | `analisis.ringkas_per_negara` + peta di tab World map |
| Sejak kapan, dan bagaimana menyebarnya? | `analisis.aktif_pada`, `analisis.timeline_kumulatif`, `analisis.peta_per_tahun` |
| Kontroversi apa yang muncul dan bagaimana akhirnya? | `analisis.ringkas_kontroversi`, `analisis.kontroversi_per_tahun` |
| Seberapa besar bisnis pemerintah Palantir sebenarnya? | `src/sec.py` + `analisis.pangsa_pendapatan` |

---

## 2. Merancang dataset kurasi

Dataset kurasi yang baik punya tiga sifat:

1. **Satu baris, satu fakta yang bisa dicek.** Setiap baris lembaga punya `sumber_url`. Pembaca yang ragu bisa
   langsung membuka sumbernya.
2. **Kepastian dibedakan.** Kolom `kepastian` memisahkan yang **resmi** (diumumkan pemerintah atau Palantir) dari
   yang **dilaporkan media**. Kontrak polisi Belanda, misalnya, hanya diketahui lewat investigasi Volkskrant, jadi
   kepastiannya "Laporan media" walaupun menteri kemudian mengonfirmasi.
3. **Kosong lebih baik daripada menebak.** Nilai kontrak NATO tidak pernah diumumkan, maka `nilai_asli_juta`
   dibiarkan kosong. Mengisinya dengan perkiraan akan membuat grafik terlihat lebih lengkap, tetapi salah.

Dua tabel dihubungkan lewat id, seperti *foreign key* di database:

```
pengguna_palantir.csv                       kontroversi.csv
id            ... kontroversi               id                ... dampak
us-ice        ... no-tech-for-ice    ───►   no-tech-for-ice   ... 2
deu-hessen    ... bverfg-2023        ───►   bverfg-2023       ... 3
deu-nrw       ... bverfg-2023        ───┘
```

Satu kontroversi bisa terkait beberapa lembaga (putusan Mahkamah Konstitusi Jerman berlaku untuk Hessen, NRW,
dan Baden-Württemberg), dan satu lembaga bisa punya beberapa kontroversi (dipisah `;`).

---

## 3. Validasi: data kurasi juga perlu dites

Mengetik 48 baris dengan tangan pasti menghasilkan salah ketik. `muat_data.validasi()` memeriksa setiap baris dan
mengembalikan daftar masalah:

```python
if r["sektor"] not in SEKTOR:
    masalah.append(f"{tag}: sektor tidak dikenal '{r['sektor']}'")
if not str(r["sumber_url"]).startswith("https://"):
    masalah.append(f"{tag}: sumber harus URL https")
for k in filter(None, str(r["kontroversi"]).split(";")):
    if k not in id_kon:
        masalah.append(f"{tag}: kontroversi '{k}' tidak ada di kontroversi.csv")
```

Lalu `tests/test_data.py` menegaskan bahwa daftar itu kosong:

```python
def test_dataset_lolos_validasi(pengguna, kontroversi):
    assert muat_data.validasi(pengguna, kontroversi) == []
```

Hasilnya, setiap kali kamu menambah baris dan menjalankan `pytest`, kesalahan seperti "Kepolisan" (salah ketik)
atau id kontroversi yang belum dibuat langsung ketahuan. GitHub Actions menjalankan tes yang sama setiap push.

Ada juga tes untuk validatornya sendiri (`test_validasi_menangkap_kesalahan`): data sengaja dirusak, lalu dicek
bahwa validator menemukan kerusakannya. Validator yang tidak pernah gagal belum tentu bekerja.

---

## 4. Tipe data yang boleh kosong

Kontrak yang masih berjalan tidak punya `tahun_akhir`. Di pandas, kolom angka biasa (`int64`) tidak bisa menyimpan
nilai kosong, sehingga pandas diam-diam mengubahnya menjadi desimal (`2017.0`, `NaN`). Solusinya tipe `Int64`
(huruf I besar) yang bisa menyimpan `<NA>`:

```python
df["tahun_akhir"] = pd.to_numeric(df["tahun_akhir"], errors="coerce").astype("Int64")
```

---

## 5. "Aktif pada tahun X"

Timeline dan peta animasi bergantung pada satu fungsi kecil:

```python
def aktif_pada(df, tahun):
    akhir = df["tahun_akhir"].astype("float")
    return df[(df["tahun_mulai"] <= tahun) & (akhir.isna() | (akhir >= tahun))]
```

Artinya: sudah dimulai **dan** (belum berakhir **atau** berakhir pada/sesudah tahun itu). NYPD (2012–2017) dihitung
aktif pada 2017, tetapi tidak lagi pada 2018. `peta_per_tahun` cukup memanggil fungsi ini untuk setiap tahun dan
menghitung per negara; hasilnya diberikan ke `px.choropleth(..., animation_frame="tahun")`.

---

## 6. Membaca tabel dari laporan 10-K

Perusahaan publik di AS wajib menyerahkan laporan tahunan (10-K) ke SEC, dan semuanya gratis di EDGAR. Tabel
pendapatan per segmen dan per wilayah ada di dalamnya, tetapi HTML-nya berantakan. Satu baris bisa terbaca seperti ini:

```
['Government', 'Government', 'Government', '$', '$', '2,402,287', '2,402,287', 'nan', '$', '1,569,605', ...]
```

Langkah merapikannya ada di `src/sec.py`:

| Masalah | Solusi |
|---|---|
| Sel terduplikasi karena *colspan* | `bersihkan_baris` membuang nilai yang sama berurutan |
| Simbol `$`, `%`, `)` di sel sendiri | dibuang lewat himpunan `_SAMPAH` |
| `1,569,605` dan `(826,217)` | `ke_angka`: buang koma, tanda kurung berarti negatif |
| Kolom persen di tabel wilayah (`74`, `10`, `16`) | hanya ambil angka > 100 (satuan ribu USD, jadi pendapatan selalu jauh di atas 100) |
| Tabel *contribution* juga punya baris "Government" | hanya terima tabel yang punya baris *Total revenue* atau *Government revenue* |
| Ada tabel 2 tahun dan 3 tahun | pilih yang tahunnya paling banyak |

**Jebakan terbesar** baru ketahuan saat totalnya dicek: pendapatan 2021 terhitung $1,63 miliar, padahal 10-K
menulis $1,54 miliar. Penyebabnya, 10-K FY2021 memisahkan *France*, sedangkan 10-K FY2023 sudah memasukkannya ke
*Rest of world*. Kode lama mengambil "Rest of world 2021" dari laporan baru dan "France 2021" dari laporan lama,
sehingga Prancis terhitung dua kali. Perbaikannya: untuk setiap tahun, ambil **semua** kategori dari 10-K terbaru
yang memuat tahun itu. Tes `test_pendapatan_cocok_dengan_total_10k` sekarang menjaga agar kesalahan ini tidak kembali.

Pelajaran umumnya: **selalu cocokkan hasil olahan dengan angka total dari sumber aslinya.**

---

## 7. Peta dua lapis

Peta utama adalah satu `go.Figure` dengan:

- **Satu `go.Choropleth`**: warna negara dari kode ISO-3 dan jumlah lembaga.
- **Beberapa `go.Scattergeo`**: satu trace per kategori warna (sektor atau status), supaya legenda bisa diklik
  untuk menyembunyikan kategori.

Dua detail desain:

1. **Skala warna satu hue** (oranye gelap → terang) untuk jumlah. Langkahnya rapat di bagian bawah karena sebagian
   besar negara hanya punya 1–3 lembaga, sementara Amerika Serikat 12. Dengan skala linear, semua negara selain AS
   akan terlihat hampir sama gelapnya.
2. **Titik yang berbagi kota disusun spiral** dengan *golden angle* (±137°), sehingga lembaga-lembaga yang berkantor di Washington tidak
   menumpuk menjadi satu titik.

Warna sektor memakai delapan warna dengan **urutan tetap** yang sudah diuji untuk buta warna di latar gelap. Warna
mengikuti sektor, bukan peringkat, jadi saat filter diubah, warna sektor yang tersisa tidak berganti.

---

## 8. Membaca angka dengan hati-hati

- **Plafon bukan belanja.** "US Army $10 miliar" adalah batas atas selama 10 tahun. Karena itu kartu KPI menyebut
  "nilai kontrak publik", dan tooltip menjelaskan bahwa satu kontrak mendominasi angkanya.
- **Kurs tetap.** Nilai dalam GBP, EUR, AUD, dan CAD dikonversi dengan satu kurs perkiraan, cukup untuk
  membandingkan skala tetapi tidak untuk akuntansi.
- **Ketiadaan data bukan bukti.** Indonesia tidak ada di peta karena tidak ditemukan kontrak publik, bukan karena
  sudah dipastikan tidak ada.

---

## 9. Ide eksplorasi

- Tambahkan kolom `tanggal_cek` per baris untuk mencatat kapan sumbernya terakhir diverifikasi.
- Bandingkan daftar kurasi AS dengan data otomatis dari USAspending.gov (lihat Latihan 7).
- Hitung "rasio kontroversi" per sektor: kontroversi dibagi jumlah lembaga. Sektor mana yang paling sering bermasalah?
