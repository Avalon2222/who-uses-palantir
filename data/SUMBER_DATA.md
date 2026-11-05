# Sumber data

Tiga file di folder ini. Dua dikurasi manual, satu dibangun otomatis dari SEC EDGAR.

## 1. `pengguna_palantir.csv`: lembaga dan kontrak

Satu baris = satu lembaga (atau satu kontrak besar di lembaga yang sama, misalnya US Army dan Maven Smart System
dipisah karena pembeli dan programnya berbeda). Kurasi terakhir: **5 November 2026**.

| Kolom | Isi |
|---|---|
| `id` | Kode unik, misalnya `uk-nhs-fdp` |
| `negara`, `iso3` | Negara dan kode ISO 3166-1 alpha-3. Organisasi internasional memakai negara markasnya (NATO → BEL) tetapi tidak ikut mewarnai peta |
| `lembaga` | Nama lembaga/program |
| `sektor` | Salah satu dari 8: Militer & pertahanan, Intelijen, Kepolisian, Imigrasi & perbatasan, Kesehatan, Pemerintahan sipil, Organisasi internasional, Korporasi |
| `produk` | Produk Palantir yang disebut sumber (Gotham, Foundry, AIP, Maven Smart System, MetaConstellation) |
| `tahun_mulai`, `tahun_akhir` | Tahun pertama penggunaan yang terdokumentasi; `tahun_akhir` kosong bila masih berjalan |
| `status` | Aktif, Rintisan, Ditinjau ulang, Ditolak/diblokir, Berakhir, Status tidak jelas |
| `nilai_asli_juta`, `mata_uang` | Nilai kontrak dalam juta, mata uang asli. Kosong bila tidak diumumkan |
| `catatan_nilai` | Konteks nilai: plafon atau belanja, periode, cara pengadaan |
| `kota`, `lat`, `lon` | Lokasi kantor pusat lembaga (perkiraan tingkat kota) |
| `ringkasan` | Ringkasan satu-dua kalimat, ditulis sendiri |
| `kepastian` | **Resmi** (pengumuman pemerintah/Palantir, dokumen pengadaan) atau **Laporan media** |
| `sumber_nama`, `sumber_url` | Sumber utama baris ini |
| `kontroversi` | Id di `kontroversi.csv`, dipisah `;` |

### Aturan kurasi

1. Setiap baris wajib punya satu sumber https yang bisa dibuka publik.
2. Urutan prioritas sumber: pengumuman resmi atau dokumen pengadaan → media dengan reputasi baik (CNBC,
   Defense News, USNI News, DefenseScoop, The Guardian, heise, netzpolitik.org) → investigasi jurnalis dan LSM.
3. Klaim yang hanya ada di blog, agregator, atau situs advokasi tanpa sumber primer **tidak dimasukkan**. Contoh
   yang dibuang: klaim kontrak pemerintah India, Qatar, dan Arab Saudi, serta nilai kontrak Kanada US$44 juta dari
   agregator.
4. Bila sumber saling bertentangan (misalnya nilai kontrak Europol €5 juta vs €7,5 juta, atau biaya FCA per minggu
   vs per bulan), dipakai angka yang lebih konservatif atau nilainya dikosongkan, dan perbedaannya ditulis di
   `catatan_nilai`.
5. Nilai kontrak sering berupa **plafon** (batas atas). Angka ini bukan uang yang sudah dibelanjakan.
6. Korporasi hanya dicantumkan sebagai contoh yang relevan dengan pemerintah atau infrastruktur strategis (Airbus,
   bp, SOMPO, KT/LIG Nex1, Dubai Holding). Palantir punya ratusan klien komersial lain.

### Kurs perkiraan

Dipakai hanya untuk membandingkan skala, ditetapkan di `src/analisis.py` (`KURS_KE_USD`):
1 GBP = 1,30 USD · 1 EUR = 1,10 USD · 1 AUD = 0,66 USD · 1 CAD = 0,73 USD.

## 2. `kontroversi.csv`

| Kolom | Isi |
|---|---|
| `id`, `judul`, `negara`, `tahun` | Identitas kontroversi; `negara` bisa berupa kawasan (Eropa, PBB, Uni Eropa) |
| `jenis` | Privasi & pengawasan, Pengadaan & tender, Kedaulatan data, Transparansi, Perang & targeting, Konstitusi & hukum, Imigrasi & deportasi |
| `hasil` | Investigasi media, Protes & kampanye, Kontrak dihentikan, Putusan pengadilan, Divestasi investor, Masih berjalan |
| `dampak` | 1 = kritik dan liputan · 2 = investigasi besar atau kampanye publik · 3 = putusan pengadilan, kontrak dihentikan, atau diblokir |
| `ringkasan`, `sumber_nama`, `sumber_url` | Ringkasan ditulis sendiri + sumber utama |

Skor dampak menggambarkan **konsekuensi**, bukan menilai siapa yang benar. Tanggapan Palantir (misalnya bantahan
terhadap laporan militer Swiss, atau gugatan terhadap Wali Kota London) disebut di ringkasan bila ada.

## 3. `pendapatan_palantir.csv`: laporan tahunan SEC

Dibangun oleh `scripts/ambil_pendapatan_sec.py` dari tiga 10-K Palantir Technologies Inc. (CIK 0001321655) di
[SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001321655&type=10-K):

| Laporan | Tahun yang dimuat |
|---|---|
| 10-K FY2025 (diajukan 17 Februari 2026) | 2023, 2024, 2025 |
| 10-K FY2023 (diajukan 20 Februari 2024) | 2021, 2022, 2023 |
| 10-K FY2021 (diajukan 24 Februari 2022) | 2019, 2020, 2021 |

- `jenis = segmen`: Government dan Commercial (diterjemahkan Pemerintah dan Komersial).
- `jenis = wilayah`: United States, United Kingdom, Rest of world. 10-K FY2021 juga memisahkan France; untuk tahun
  yang dimuat lebih dari satu 10-K, semua kategori diambil dari laporan terbaru supaya Prancis tidak terhitung ganda.
- Satuan: juta USD (10-K melaporkan ribu USD).
- Total per tahun sudah dicocokkan dengan baris *Total revenue* di 10-K (diuji di `tests/test_data.py`).

Data SEC adalah domain publik. Perhatikan bahwa "Government" di 10-K mencakup pemerintah AS dan negara lain;
10-K tidak merinci pendapatan per lembaga.

## Keterbatasan umum

- **Tidak lengkap.** Kontrak intelijen dan militer sering rahasia; dataset ini hanya memuat yang pernah muncul ke
  publik. Ketiadaan sebuah negara di peta tidak berarti negara itu pasti tidak memakai Palantir.
- **Status bisa berubah cepat.** Beberapa kontrak sedang dinegosiasikan atau ditinjau saat kurasi (NHS England,
  DGSI Prancis, CIFAS Spanyol, Met Police). Cek tautan sumber untuk perkembangan terbaru.
- **Koordinat** adalah perkiraan tingkat kota, bukan alamat fasilitas.
