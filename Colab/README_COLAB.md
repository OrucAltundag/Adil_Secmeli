Colab Kullanım Talimatı — Adil_Secmeli

1) Notebook'u Colab'da açma
- En kolay yol: GitHub'dan "Open in Colab" veya Drive'a kopyalayıp Colab ile açmaktır.
- Eğer notebook'u doğrudan bu depodan kullanacaksanız, GitHub üzerinden "Open in Colab" seçin veya Drive'a kopyalayın.

2) Drive'ı bağlama ve paketleri yükleme
- Not defterinin en başındaki hücre Colab ortamını algılar, gerekli paketleri kurar ve Drive'ı bağlar.
- Hücreyi çalıştırdığınızda `DATA_ROOT` değişkeni otomatik olarak `'/content/drive/MyDrive/Adil_Secmeli_Python'` olarak ayarlanır. Gerekirse bu yolu güncelleyin.

3) Veri dosyalarını yerleştirme
- Excel/CSV dosyalarınızı Drive içine `Adil_Secmeli_Python/data/` klasörüne koyun (örn. `data/2022_ogrenci_not_veri_seti.xlsx`).
- Alternatif: Colab'a küçük dosyalar yüklemek için `files.upload()` kullanabilirsiniz, fakat büyük/kalıcı veriler için Drive önerilir.

4) Tam çalıştırma
- `Runtime -> Run all` ile hücreleri baştan sona çalıştırın.
- Eğer paket kurulumları uzun sürerse (ilk seferde), hücre tamamlanana kadar bekleyin.

5) Notlar
- Bu notebook ağırlıklı olarak CPU ile çalışır; GPU gerekmez.
- `FAST_MODE = True` ayarı, eğitim ve benchmark adımlarını hızlandırmak için varsayılan. Tam ölçekli deneyler için `FAST_MODE = False` yapın.

İyi çalışmalar — sorun olursa bana bildirin, Colab üzerinde adım adım ilerleyelim.