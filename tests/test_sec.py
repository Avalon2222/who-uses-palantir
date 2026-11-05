"""Uji parser tabel 10-K dengan potongan HTML tiruan yang meniru gaya EDGAR."""

from src import sec

HTML_TIRUAN = """<?xml version="1.0" encoding="utf-8"?>
<html><body>
<table>
  <tr><td></td><td colspan="2">Years Ended December 31,</td><td colspan="2">Years Ended December 31,</td><td colspan="2">Years Ended December 31,</td></tr>
  <tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td><td colspan="2">2023</td></tr>
  <tr><td>Revenue:</td></tr>
  <tr><td>Government</td><td>$</td><td>2,402,287</td><td>$</td><td>1,569,605</td><td>$</td><td>1,222,215</td></tr>
  <tr><td>Commercial</td><td></td><td>2,073,159</td><td></td><td>1,295,902</td><td></td><td>1,002,797</td></tr>
  <tr><td>Total revenue</td><td>$</td><td>4,475,446</td><td>$</td><td>2,865,507</td><td>$</td><td>2,225,012</td></tr>
</table>
<table>
  <tr><td></td><td colspan="4">Years Ended December 31,</td></tr>
  <tr><td></td><td colspan="2">2025</td><td colspan="2">2024</td></tr>
  <tr><td>United States</td><td>3,320,043</td><td>74</td><td>1,900,247</td><td>66</td></tr>
  <tr><td>United Kingdom</td><td>427,398</td><td>10</td><td>304,575</td><td>11</td></tr>
  <tr><td>Rest of world (1)</td><td>728,005</td><td>16</td><td>660,685</td><td>23</td></tr>
  <tr><td>Total revenue</td><td>4,475,446</td><td>100</td><td>2,865,507</td><td>100</td></tr>
</table>
<table>
  <tr><td></td><td>2025</td><td>2024</td><td>2023</td></tr>
  <tr><td>Government</td><td>1,576,070</td><td>948,440</td><td>724,970</td></tr>
  <tr><td>Commercial</td><td>1,366,627</td><td>771,508</td><td>520,585</td></tr>
  <tr><td>Total contribution</td><td>2,942,697</td><td>1,719,948</td><td>1,245,555</td></tr>
</table>
</body></html>"""


def test_bersihkan_baris_buang_simbol_dan_duplikat():
    baris = ["Government", "Government", "$", "2,402,287", "2,402,287", "nan", "$", "1,569,605", ")"]
    assert sec.bersihkan_baris(baris) == ["Government", "2,402,287", "1,569,605"]


def test_ke_angka():
    assert sec.ke_angka("1,569,605") == 1569605.0
    assert sec.ke_angka("(826,217)") == -826217.0
    assert sec.ke_angka("Amount") is None
    assert sec.ke_angka("2025") == 2025.0


def test_cari_pendapatan_segmen():
    hasil = sec.cari_pendapatan(HTML_TIRUAN)
    seg = {(h["tahun"], h["kategori"]): h["nilai_ribu_usd"] for h in hasil["segmen"]}
    assert seg[(2025, "Pemerintah")] == 2402287
    assert seg[(2023, "Komersial")] == 1002797
    assert len(seg) == 6


def test_tabel_contribution_tidak_dianggap_pendapatan():
    hasil = sec.cari_pendapatan(HTML_TIRUAN)
    nilai = {h["nilai_ribu_usd"] for h in hasil["segmen"]}
    assert 1576070 not in nilai  # angka laba kontribusi, bukan pendapatan


def test_cari_pendapatan_wilayah_lewati_kolom_persen():
    hasil = sec.cari_pendapatan(HTML_TIRUAN)
    wil = {(h["tahun"], h["kategori"]): h["nilai_ribu_usd"] for h in hasil["wilayah"]}
    assert wil[(2025, "Amerika Serikat")] == 3320043
    assert wil[(2024, "Negara lain")] == 660685  # label "(1)" dibersihkan
    assert all(v > 100 for v in wil.values())


def test_html_tanpa_tabel():
    assert sec.cari_pendapatan("<html><body><p>kosong</p></body></html>") == {"segmen": [], "wilayah": []}
