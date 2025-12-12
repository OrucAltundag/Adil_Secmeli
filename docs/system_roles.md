# 🎭 System Roles — Paydaş Haritası

Bu belge, **Adil Seçmeli** sistemindeki tüm paydaşları, erişim yetkilerini ve sorumluluklarını tanımlar.

---

## 👩‍🎓 1. Öğrenci (Student)
**Rol Tanımı:**  
Sistemi kullanan ana aktör. Dönem başında 4 seçmeli ders hakkının 2’sini otomatik, 2’sini manuel olarak seçer.

**Yetkiler ve Görünürlük:**  
- Kendi profiline, geçmiş ders kayıtlarına ve skor önerilerine erişim.  
- “Serbest seçim” kısmında ders seçimi.  
- Anket oylaması yapma (1 oy / ders / dönem).  
- Raporlarda anonim şekilde temsil edilir.

**API Görünürlüğü:**  
- `/students/{id}` (GET, PUT)  
- `/recommendations/{id}` (GET)  
- `/surveys` (POST)  

**Veri Modeli:**  
```json
{
  "ogr_id": 1023,
  "fakulte_id": 5,
  "gano": 2.85,
  "durum": "aktif",
  "otomatik_dersler": [3021, 3087],
  "manuel_dersler": [3014, 3066]
}
```

---

## 👨‍🏫 2. Danışman / Öğretim Elemanı (Advisor)
**Rol Tanımı:**  
Öğrencilerin seçtiği veya sistemin atadığı dersleri onaylayan, kontenjanları ve önkoşulları yöneten kişi.

**Yetkiler ve Görünürlük:**  
- Kendi verdiği derslerin kontenjan ve açıklama düzenlemesi.  
- Öğrencilerin önerilen derslerini görüp onaylama.  
- Fakülte raporlarına kısıtlı erişim.  

**API Görünürlüğü:**  
- `/advisor/{id}/courses` (GET, PUT)  
- `/advisor/approvals` (POST)  

**Veri Modeli:**  
```json
{
  "user_id": 501,
  "ad": "Dr. Ayşe Demir",
  "rol": "danisman",
  "dersler": [3021, 3045],
  "kontenjan_duzenleme": true
}
```

---

## 🏛️ 3. Fakülte / Enstitü Yönetimi (Faculty Admin)
**Rol Tanımı:**  
Müfredat planlaması, eşik değerleri (ağırlıklar, kontenjan, başarı oranı) belirleyen üst seviye yönetim.

**Yetkiler ve Görünürlük:**  
- Fakülteye ait tüm ders ve öğrenci kayıtlarını görüntüler.  
- `config.json` içindeki parametreleri günceller (w_B, w_P, w_A).  
- “Müfredat Taslak” raporlarını onaylar.  

**API Görünürlüğü:**  
- `/faculty/config` (GET, PUT)  
- `/faculty/reports` (GET)  
- `/faculty/mufredat/onay` (POST)  

**Veri Modeli:**  
```json
{
  "fakulte_id": 5,
  "ad": "Mühendislik Fakültesi",
  "aktif_yil": 2025,
  "parametreler": {"wB": 0.5, "wP": 0.4, "wA": 0.1}
}
```

---

## 🧑‍💻 4. Sistem Yöneticisi (System Admin)
**Rol Tanımı:**  
Tüm kullanıcı rollerinin yönetimi, log kayıtları ve sistem bakımından sorumlu kişi.

**Yetkiler ve Görünürlük:**  
- Kullanıcı yönetimi (ekle, sil, rol atama).  
- Log kayıtlarını ve erişim izlerini inceleme.  
- API güvenlik anahtarlarını yönetme.  
- Yedekleme ve sürüm yönetimi.  

**API Görünürlüğü:**  
- `/admin/users` (GET, POST, DELETE)  
- `/admin/logs` (GET)  
- `/admin/backup` (POST)  

**Veri Modeli:**  
```json
{
  "admin_id": 1,
  "rol": "sistem_yoneticisi",
  "yetkiler": ["backup", "log_view", "role_assign"],
  "son_giris": "2025-10-25T10:30:00"
}
```

---
