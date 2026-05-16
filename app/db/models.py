# -*- coding: utf-8 -*-
# =============================================================================
# app/db/models.py — SQLAlchemy ORM Modelleri
# =============================================================================
# Veritabani tablolarinin Python sinif karsiliklari (ORM).
# Tablolar: okul, fakulte, bolum, ogrenci, ders, havuz, ogretim_gorevlisi,
#   ders_ogretim, mufredat, mufredat_ders, kayit, performans, populerlik,
#   anket_form, anket_cevap, anket_sonuclari, skor, ogrenci_engel
#
# Not: havuz.ders_id TEXT olarak saklanir; JOIN'lerde CAST gerekir.
# =============================================================================
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Date, DateTime, Boolean, Float, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.database import Base


# ---------------------------
# 1) OKUL
# ---------------------------
class Okul(Base):
    __tablename__ = "okul"

    school_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    kampus = Column(String)

    fakulteler = relationship("Fakulte", back_populates="okul")


# ---------------------------
# 2) BÖLÜM
# ---------------------------
class Bolum(Base):
    __tablename__ = "bolum"

    bolum_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)

    fakulte = relationship("Fakulte", back_populates="bolumler")
    mufredatlar = relationship("Mufredat", back_populates="bolum")


# ---------------------------
# 3) FAKÜLTE
# ---------------------------
class Fakulte(Base):
    __tablename__ = "fakulte"

    fakulte_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    okul_id = Column(Integer, ForeignKey("okul.school_id"), nullable=False)
    tip = Column(String)
    kampus = Column(String)

    okul = relationship("Okul", back_populates="fakulteler")
    bolumler = relationship("Bolum", back_populates="fakulte")
    dersler = relationship("Ders", back_populates="fakulte")
    ogretim_gorevlileri = relationship("OgretimGorevlisi", back_populates="fakulte")
    havuz_kayitlari = relationship("Havuz", back_populates="fakulte")


# ---------------------------
# 4) ÖĞRENCİ
# ---------------------------
class Ogrenci(Base):
    __tablename__ = "ogrenci"

    ogr_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    soyad = Column(String, nullable=False)
    email = Column(String)
    ogrenci_no = Column(String, unique=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))

    fakulte = relationship("Fakulte")
    kayitlar = relationship("Kayit", back_populates="ogrenci")
    anket_cevaplari = relationship("AnketCevap", back_populates="ogrenci")
    engeller = relationship("OgrenciEngel", back_populates="ogrenci")


# ---------------------------
# 5) DERS (tip/tur/DersTipi uyumluluğu için)
# ---------------------------
class Ders(Base):
    __tablename__ = "ders"

    ders_id = Column(Integer, primary_key=True, index=True)
    kod = Column(String)
    ad = Column(String, nullable=False)
    kredi = Column(Integer)
    akts = Column(Integer)
    onkosul = Column(Integer, ForeignKey("ders.ders_id"), nullable=True)
    bilgi = Column(Text)
    bolum_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=True)
    DersTipi = Column(String)
    tip = Column(String)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    # Kontenjan kuralı: Varsayılan kontenjan (ders_ogretim veya populerlik ile override)
    kontenjan = Column(Integer)

    fakulte = relationship("Fakulte", back_populates="dersler")
    havuz_kayitlari = relationship("Havuz", back_populates="ders")
    ders_ogretim = relationship("DersOgretim", back_populates="ders")
    kayitlar = relationship("Kayit", back_populates="ders")
    performanslar = relationship("Performans", back_populates="ders")
    populerlikler = relationship("Populerlik", back_populates="ders")
    skorlar = relationship("Skor", back_populates="ders")
    anket_cevaplari = relationship("AnketCevap", back_populates="ders")

    @property
    def normalized_type(self) -> str:
        for attr in ("DersTipi", "tip"):
            value = getattr(self, attr, None)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""


# ---------------------------
# 5.1) DERS_KRITERLERI
# ---------------------------
class DersKriterleri(Base):
    __tablename__ = "ders_kriterleri"
    __table_args__ = (
        UniqueConstraint("ders_id", "yil", "donem", name="uq_ders_kriterleri_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False, default="Güz")
    toplam_ogrenci = Column(Integer, default=0)
    gecen_ogrenci = Column(Integer, default=0)
    basari_ortalamasi = Column(Float, default=0.0)
    kontenjan = Column(Integer, default=0)
    kayitli_ogrenci = Column(Integer, default=0)
    anket_katilimci = Column(Integer, default=0)
    anket_dersi_secen = Column(Integer, default=0)
    anket_veri_kaynagi = Column(String, default="manual")
    anket_manual_locked = Column(Integer, nullable=False, default=0)
    anket_import_id = Column(Integer)
    anket_imported_at = Column(String)
    criteria_import_id = Column(Integer)
    criteria_veri_kaynagi = Column(String, default="manual")
    criteria_manual_override = Column(Integer, nullable=False, default=0)
    criteria_updated_at = Column(String)
    source_import_batch_id = Column(Integer)
    is_active = Column(Integer, nullable=False, default=1)
    superseded_by_import_batch_id = Column(Integer)

    ders = relationship("Ders")


# ---------------------------
# 6) HAVUZ
# ---------------------------
class Havuz(Base):
    __tablename__ = "havuz"
    __table_args__ = (
        UniqueConstraint(
            "ders_id",
            "fakulte_id",
            "yil",
            "donem",
            name="uq_havuz_ders_fac_yil_donem",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)
    yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False, default="Guz")
    statu = Column(Integer, default=0)
    sayac = Column(Integer, default=0)
    skor = Column(Float, default=0.0)
    recommended_status = Column(Integer)
    final_status = Column(Integer)
    lifecycle_label = Column(String)
    approval_required = Column(Boolean, nullable=False, default=False)
    approval_status = Column(String)
    transition_id = Column(Integer)
    explanation = Column(Text)
    policy_id = Column(Integer)

    secilebilirlik_durumu = Column(Boolean, default=True)
    kontenjan_durumu = Column(String)
    on_kosul_durumu = Column(String)
    ogrenci_dinlendirme_durumu = Column(String)
    acilis_tarihi = Column(Date)
    kapanis_tarihi = Column(Date)
    durum_degeri = Column(Float)

    ders = relationship("Ders", back_populates="havuz_kayitlari")
    fakulte = relationship("Fakulte", back_populates="havuz_kayitlari")


# ---------------------------
# 7) ÖĞRETİM GÖREVLİSİ
# ---------------------------
class OgretimGorevlisi(Base):
    __tablename__ = "ogretim_gorevlisi"

    ogrt_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    soyad = Column(String, nullable=False)
    unvan = Column(String)
    email = Column(String)
    tel = Column(String)
    durum = Column(String)
    bilgi = Column(Text)
    memnuniyet_puani = Column(Float)
    kidem_yil = Column(Integer)
    atanma_tarihi = Column(Date)
    school_id = Column(Integer, ForeignKey("okul.school_id"))
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    basarim_ort = Column(Float)

    okul = relationship("Okul")
    fakulte = relationship("Fakulte", back_populates="ogretim_gorevlileri")
    ders_gorevleri = relationship("DersOgretim", back_populates="ogretim_gorevlisi")
    kayitlar = relationship("Kayit", back_populates="ogretim_gorevlisi")


# ---------------------------
# 8) DERS_ÖĞRETİM (Kontenjan, gün/saat çakışma için)
# ---------------------------
class DersOgretim(Base):
    __tablename__ = "ders_ogretim"

    ders_ogrt_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    ogrt_id = Column(Integer, ForeignKey("ogretim_gorevlisi.ogrt_id"), nullable=False)
    rol = Column(String)
    donem = Column(String)
    akademik_yil = Column(Integer)
    ders_saati = Column(Integer)
    katki_oran = Column(Float)
    not_ortalaması = Column(Float)
    kontenjan = Column(Integer)
    gun = Column(String)
    baslangic_saati = Column(String)
    bitis_saati = Column(String)

    ders = relationship("Ders", back_populates="ders_ogretim")
    ogretim_gorevlisi = relationship("OgretimGorevlisi", back_populates="ders_gorevleri")

    __table_args__ = (
        UniqueConstraint("ders_id", "ogrt_id", "akademik_yil", "donem", name="uq_ders_ogrt_yil_donem"),
    )


# ---------------------------
# 9) MÜFREDAT
# ---------------------------
class Mufredat(Base):
    __tablename__ = "mufredat"

    mufredat_id = Column(Integer, primary_key=True, index=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    bolum_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    donem = Column(String)
    durum = Column(String)
    versiyon = Column(Integer, default=1)

    fakulte = relationship("Fakulte")
    bolum = relationship("Bolum", back_populates="mufredatlar")
    dersler = relationship("MufredatDers", back_populates="mufredat")


# ---------------------------
# 10) MÜFREDAT_DERS
# ---------------------------
class MufredatDers(Base):
    __tablename__ = "mufredat_ders"

    mders_id = Column(Integer, primary_key=True, index=True)
    mufredat_id = Column(Integer, ForeignKey("mufredat.mufredat_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)

    mufredat = relationship("Mufredat", back_populates="dersler")
    ders = relationship("Ders")

    __table_args__ = (UniqueConstraint("mufredat_id", "ders_id", name="uq_mufredat_ders"),)


# ---------------------------
# 11) KAYIT (failed_before: daha önce kaldı mı)
# ---------------------------
class Kayit(Base):
    __tablename__ = "kayit"

    kayit_id = Column(Integer, primary_key=True, index=True)
    ogr_id = Column(Integer, ForeignKey("ogrenci.ogr_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)
    kayit_turu = Column(String)
    kayit_tarih = Column(DateTime)
    durum = Column(String)
    ogrt_id = Column(Integer, ForeignKey("ogretim_gorevlisi.ogrt_id"))
    failed_before = Column(Boolean, default=False)

    ogrenci = relationship("Ogrenci", back_populates="kayitlar")
    ders = relationship("Ders", back_populates="kayitlar")
    ogretim_gorevlisi = relationship("OgretimGorevlisi", back_populates="kayitlar")


# ---------------------------
# 12) PERFORMANS
# ---------------------------
class Performans(Base):
    __tablename__ = "performans"

    pfrs_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, default="Güz")
    ortalama_not = Column(Float)
    basari_orani = Column(Float)
    ham_puan = Column(Float)

    ders = relationship("Ders", back_populates="performanslar")

    __table_args__ = (
        UniqueConstraint("ders_id", "akademik_yil", "donem", name="uq_performans_yil"),
    )


# ---------------------------
# 13) POPÜLERLİK (Kontenjan kuralı)
# ---------------------------
class Populerlik(Base):
    __tablename__ = "populerlik"

    pop_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, default="Güz")
    talep_sayisi = Column(Integer)
    kontenjan = Column(Integer)
    fakulte_mevcudu = Column(Integer)
    doluluk_orani = Column(Float)
    ilgi_orani = Column(Float)
    ham_puan = Column(Float)

    ders = relationship("Ders", back_populates="populerlikler")

    __table_args__ = (
        UniqueConstraint("ders_id", "akademik_yil", "donem", name="uq_populerlik_yil"),
    )


# ---------------------------
# 14) ANKET_FORM
# ---------------------------
class AnketForm(Base):
    __tablename__ = "anket_form"

    form_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    baslangic_tarih = Column(Date)
    bitis_tarih = Column(Date)
    aktif_mi = Column(Boolean, default=True)
    aciklama = Column(Text)

    fakulte = relationship("Fakulte")
    cevaplar = relationship("AnketCevap", back_populates="form")
    sonuclar = relationship("AnketSonuclari", back_populates="form")


# ---------------------------
# 15) ANKET_CEVAP
# ---------------------------
class AnketCevap(Base):
    __tablename__ = "anket_cevap"

    cevap_id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("anket_form.form_id"), nullable=False)
    ogr_id = Column(Integer, ForeignKey("ogrenci.ogr_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    rank = Column(Integer)
    siddet = Column(Integer)
    puan = Column(Float)
    cevap_tarihi = Column(DateTime)
    ip_hash = Column(String(128))

    form = relationship("AnketForm", back_populates="cevaplar")
    ogrenci = relationship("Ogrenci", back_populates="anket_cevaplari")
    ders = relationship("Ders", back_populates="anket_cevaplari")

    __table_args__ = (UniqueConstraint("form_id", "ogr_id", "ders_id", name="uq_anket_tekoy"),)


# ---------------------------
# 16) ANKET_SONUCLARI
# ---------------------------
class AnketSonuclari(Base):
    __tablename__ = "anket_sonuclari"

    anketsonuc_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    form_id = Column(Integer, ForeignKey("anket_form.form_id"), nullable=False)
    toplam_puan = Column(Float)
    oy_sayisi = Column(Integer)
    ortalama_siddet = Column(Float)
    a_norm = Column(Float)
    hesaplanma_tarihi = Column(DateTime)

    ders = relationship("Ders")
    form = relationship("AnketForm", back_populates="sonuclar")

    __table_args__ = (UniqueConstraint("form_id", "ders_id", name="uq_anket_sonuc_form_ders"),)


# ---------------------------
# 17) SKOR
# ---------------------------
class Skor(Base):
    __tablename__ = "skor"

    skor_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)
    b_norm = Column(Float)
    p_norm = Column(Float)
    a_norm = Column(Float)
    g_norm = Column(Float)
    skor_top = Column(Float)
    hesap_tarih = Column(DateTime)

    ders = relationship("Ders", back_populates="skorlar")

    __table_args__ = (UniqueConstraint("ders_id", "akademik_yil", "donem", name="uq_skor_dersterm"),)


# ---------------------------
# 18) ÖĞRENCİ_ENGEL (Engel Denetimi: is_active)
# ---------------------------
class OgrenciEngel(Base):
    __tablename__ = "ogrenci_engel"

    engel_id = Column(Integer, primary_key=True, index=True)
    ogr_id = Column(Integer, ForeignKey("ogrenci.ogr_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    engel_baslangic = Column(Date)
    engel_bitis = Column(Date)
    neden = Column(Text)
    is_active = Column(Boolean, default=True)

    ogrenci = relationship("Ogrenci", back_populates="engeller")
    ders = relationship("Ders")


# ---------------------------
# 19) CRITERIA_DEPARTMENT_STATUS
# ---------------------------
class CriteriaDepartmentStatus(Base):
    __tablename__ = "criteria_department_status"

    id = Column(Integer, primary_key=True, index=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)
    bolum_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=False)
    yil = Column(Integer, nullable=False)
    criteria_status = Column(String, nullable=False, default="not_started")
    required_course_count = Column(Integer, nullable=False, default=0)
    completed_course_count = Column(Integer, nullable=False, default=0)
    missing_course_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("fakulte_id", "bolum_id", "yil", name="uq_criteria_department_status_scope"),
    )


# ---------------------------
# 20) CRITERIA_FACULTY_STATUS
# ---------------------------
class CriteriaFacultyStatus(Base):
    __tablename__ = "criteria_faculty_status"

    id = Column(Integer, primary_key=True, index=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)
    yil = Column(Integer, nullable=False)
    criteria_status = Column(String, nullable=False, default="not_started")
    total_department_count = Column(Integer, nullable=False, default=0)
    completed_department_count = Column(Integer, nullable=False, default=0)
    algorithm_run_status = Column(String, nullable=False, default="not_run")
    algorithm_run_at = Column(DateTime)
    generated_year = Column(Integer)
    year_active = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("fakulte_id", "yil", name="uq_criteria_faculty_status_scope"),
    )


# ---------------------------
# 21) CURRICULUM_GENERATION_AUDIT
# ---------------------------
class CurriculumGenerationAudit(Base):
    __tablename__ = "curriculum_generation_audit"

    id = Column(Integer, primary_key=True, index=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)
    bolum_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=False)
    source_year = Column(Integer, nullable=False)
    generated_year = Column(Integer, nullable=False)
    dis_bolum_ders_sayisi = Column(Integer, nullable=False, default=0)
    run_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint(
            "fakulte_id",
            "bolum_id",
            "source_year",
            "generated_year",
            name="uq_curriculum_generation_audit_scope",
        ),
    )


# ---------------------------
# 22) AHP WEIGHT PROFILE
# ---------------------------
class DecisionCriteriaDefinition(Base):
    __tablename__ = "decision_criteria_definitions"

    id = Column(Integer, primary_key=True, index=True)
    criterion_key = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    criterion_type = Column(String, nullable=False, default="score")
    is_benefit = Column(Boolean, nullable=False, default=True)
    default_enabled = Column(Boolean, nullable=False, default=True)
    min_value = Column(Float)
    max_value = Column(Float)
    normalization_method = Column(String)
    source_type = Column(String)
    sort_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class AHPWeightProfile(Base):
    __tablename__ = "ahp_weight_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    profile_name = Column(String)
    profile_code = Column(String)
    scope_type = Column(String, nullable=False, default="global")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    semester = Column(String)
    version = Column(Integer, nullable=False, default=1)
    criteria_keys_json = Column(Text, nullable=False)
    pairwise_matrix_json = Column(Text, nullable=False)
    weights_json = Column(Text, nullable=False)
    consistency_index = Column(Float)
    consistency_ratio = Column(Float)
    is_consistent = Column(Boolean, nullable=False, default=True)
    consistency_warning = Column(Text)
    source = Column(String, nullable=False, default="default")
    status = Column(String, nullable=False, default="active")
    created_by = Column(String)
    notes = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    approved_by = Column(String)
    approved_at = Column(DateTime)
    rejected_by = Column(String)
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    parent_profile_id = Column(Integer, ForeignKey("ahp_weight_profiles.id"))
    superseded_by_profile_id = Column(Integer, ForeignKey("ahp_weight_profiles.id"))


class AHPProfilePolicy(Base):
    __tablename__ = "ahp_profile_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False, default="global")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    semester = Column(String)
    max_consistency_ratio = Column(Float, nullable=False, default=0.10)
    require_approval_for_activation = Column(Boolean, nullable=False, default=True)
    allow_inconsistent_profile_for_draft_runs = Column(Boolean, nullable=False, default=False)
    allow_default_profile_if_missing = Column(Boolean, nullable=False, default=True)
    mark_decisions_stale_on_profile_change = Column(Boolean, nullable=False, default=True)
    require_notes_for_manual_profile = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class AHPProfileApprovalLog(Base):
    __tablename__ = "ahp_profile_approval_logs"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("ahp_weight_profiles.id"), nullable=False)
    action = Column(String, nullable=False)
    old_status = Column(String)
    new_status = Column(String)
    actor = Column(String)
    message = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 23) DECISION POLICY
# ---------------------------
class DecisionPolicy(Base):
    __tablename__ = "decision_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False, default="global")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    mode = Column(String, nullable=False, default="static_threshold")
    curriculum_keep_threshold = Column(Float, nullable=False, default=70.0)
    pool_threshold = Column(Float, nullable=False, default=50.0)
    rest_threshold = Column(Float, nullable=False, default=40.0)
    cancel_candidate_threshold = Column(Float)
    min_success_rate = Column(Float)
    min_survey_count = Column(Integer)
    min_enrollment_rate = Column(Float)
    new_course_grace_period_years = Column(Integer, nullable=False, default=2)
    low_data_confidence_threshold = Column(Float, nullable=False, default=0.50)
    sensitivity_margin = Column(Float, nullable=False, default=3.0)
    top_percent_curriculum = Column(Float)
    middle_percent_pool = Column(Float)
    bottom_percent_rest = Column(Float)
    require_manual_approval_for_cancel = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


# ---------------------------
# 24) DECISION RUN
# ---------------------------
class DecisionRun(Base):
    __tablename__ = "decision_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    semester = Column(String)
    algorithm_version = Column(String, nullable=False)
    ahp_profile_id = Column(Integer, ForeignKey("ahp_weight_profiles.id"))
    ahp_profile_version = Column(Integer)
    ahp_weights_snapshot_json = Column(Text)
    ahp_consistency_ratio = Column(Float)
    ahp_profile_status_at_run = Column(String)
    ahp_profile_source = Column(String)
    decision_policy_id = Column(Integer, ForeignKey("decision_policies.id"))
    input_data_hash = Column(String)
    status = Column(String, nullable=False, default="started")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String)
    summary_json = Column(Text)
    error_message = Column(Text)
    stale_flag = Column(Boolean, nullable=False, default=False)
    recalculate_required = Column(Boolean, nullable=False, default=False)


# ---------------------------
# 25) COURSE DECISION
# ---------------------------
class CourseDecision(Base):
    __tablename__ = "course_decisions"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    semester = Column(String)
    old_status = Column(Integer)
    recommended_status = Column(Integer)
    final_status = Column(Integer)
    topsis_score = Column(Float)
    trend_score = Column(Float)
    trend_label = Column(String)
    data_confidence_score = Column(Float)
    decision_stability = Column(String)
    approval_required = Column(Boolean, nullable=False, default=False)
    approval_status = Column(String)
    approval_by = Column(String)
    approval_at = Column(DateTime)
    approval_reason = Column(Text)
    override_applied = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text)
    main_reason = Column(Text)
    rule_triggered = Column(String)
    created_at = Column(DateTime)


class CourseScoreBreakdown(Base):
    __tablename__ = "course_score_breakdowns"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    ahp_profile_id = Column(Integer, ForeignKey("ahp_weight_profiles.id"))
    raw_values_json = Column(Text)
    normalized_values_json = Column(Text)
    weighted_values_json = Column(Text)
    weights_json = Column(Text)
    positive_distance = Column(Float)
    negative_distance = Column(Float)
    closeness_coefficient = Column(Float)
    final_score = Column(Float)
    contribution_json = Column(Text)
    weighted_contribution_json = Column(Text)
    created_at = Column(DateTime)


class CourseTrendAnalysis(Base):
    __tablename__ = "course_trend_analysis"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    values_by_year_json = Column(Text)
    trend_score = Column(Float)
    trend_label = Column(String)
    volatility_score = Column(Float)
    data_points_count = Column(Integer, nullable=False, default=0)
    explanation = Column(Text)
    created_at = Column(DateTime)


class CourseDataConfidence(Base):
    __tablename__ = "course_data_confidence"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    level = Column(String, nullable=False, default="low")
    has_success_data = Column(Boolean, nullable=False, default=False)
    has_popularity_data = Column(Boolean, nullable=False, default=False)
    has_survey_data = Column(Boolean, nullable=False, default=False)
    has_trend_data = Column(Boolean, nullable=False, default=False)
    has_recent_data = Column(Boolean, nullable=False, default=False)
    survey_count = Column(Integer)
    data_points_count = Column(Integer, nullable=False, default=0)
    missing_fields_json = Column(Text)
    explanation = Column(Text)
    created_at = Column(DateTime)


class CourseDecisionExplanation(Base):
    __tablename__ = "course_decision_explanations"

    id = Column(Integer, primary_key=True, index=True)
    course_decision_id = Column(Integer, ForeignKey("course_decisions.id"), nullable=False)
    main_reason = Column(Text)
    secondary_reasons_json = Column(Text)
    positive_factors_json = Column(Text)
    negative_factors_json = Column(Text)
    rule_triggered = Column(String)
    confidence_level = Column(String)
    human_readable_text = Column(Text)
    created_at = Column(DateTime)


class DecisionSensitivityResult(Base):
    __tablename__ = "decision_sensitivity_results"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    base_score = Column(Float)
    min_score = Column(Float)
    max_score = Column(Float)
    score_range = Column(Float)
    decision_changed = Column(Boolean, nullable=False, default=False)
    stability_level = Column(String, nullable=False, default="medium")
    tested_variations_json = Column(Text)
    explanation = Column(Text)
    created_at = Column(DateTime)


class DecisionFairnessReport(Base):
    __tablename__ = "decision_fairness_reports"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer, nullable=False)
    report_json = Column(Text)
    summary_text = Column(Text)
    created_at = Column(DateTime)


class CourseGovernanceFlag(Base):
    __tablename__ = "course_governance_flags"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False, unique=True)
    strategic_flag = Column(Boolean, nullable=False, default=False)
    accreditation_flag = Column(Boolean, nullable=False, default=False)
    protected_flag = Column(Boolean, nullable=False, default=False)
    required_course_flag = Column(Boolean, nullable=False, default=False)
    service_course_flag = Column(Boolean, nullable=False, default=False)
    new_course_flag = Column(Boolean, nullable=False, default=False)
    revised_course_flag = Column(Boolean, nullable=False, default=False)
    revision_year = Column(Integer)
    first_offered_year = Column(Integer)
    instructor_changed = Column(Boolean, nullable=False, default=False)
    content_updated = Column(Boolean, nullable=False, default=False)
    protected_until_year = Column(Integer)
    protection_reason = Column(Text)
    updated_by = Column(String)
    notes = Column(Text)
    updated_at = Column(DateTime)


class PoolStatePolicy(Base):
    __tablename__ = "pool_state_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False, default="global")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    semester = Column(String)
    low_score_threshold = Column(Float, nullable=False, default=50.0)
    medium_score_threshold = Column(Float, nullable=False, default=70.0)
    high_score_threshold = Column(Float, nullable=False, default=80.0)
    pool_entry_threshold = Column(Float, nullable=False, default=60.0)
    rest_threshold = Column(Float, nullable=False, default=45.0)
    cancel_candidate_threshold = Column(Float, nullable=False, default=35.0)
    reactivation_threshold = Column(Float, nullable=False, default=75.0)
    rest_after_years_in_pool = Column(Integer, nullable=False, default=2)
    cancel_after_years_in_rest = Column(Integer, nullable=False, default=2)
    max_years_in_pool = Column(Integer)
    new_course_grace_period_years = Column(Integer, nullable=False, default=2)
    revised_course_grace_period_years = Column(Integer, nullable=False, default=1)
    require_approval_for_cancel = Column(Boolean, nullable=False, default=True)
    require_approval_for_reactivation = Column(Boolean, nullable=False, default=True)
    protect_accreditation_courses = Column(Boolean, nullable=False, default=True)
    protect_strategic_courses = Column(Boolean, nullable=False, default=True)
    protect_required_courses = Column(Boolean, nullable=False, default=True)
    low_confidence_blocks_cancel = Column(Boolean, nullable=False, default=True)
    low_confidence_blocks_rest = Column(Boolean, nullable=False, default=True)
    minimum_data_confidence_for_cancel = Column(Float, nullable=False, default=0.75)
    minimum_data_confidence_for_rest = Column(Float, nullable=False, default=0.60)
    allow_reactivation_from_rest = Column(Boolean, nullable=False, default=True)
    allow_reactivation_from_cancelled = Column(Boolean, nullable=False, default=False)
    reactivation_requires_manual_approval = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class CourseStateTransition(Base):
    __tablename__ = "course_state_transitions"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String)
    old_status = Column(Integer)
    recommended_status = Column(Integer)
    final_status = Column(Integer)
    lifecycle_label = Column(String)
    trigger = Column(String, nullable=False, default="algorithm")
    rule_applied = Column(String)
    topsis_score = Column(Float)
    trend_score = Column(Float)
    trend_label = Column(String)
    data_confidence_score = Column(Float)
    policy_id = Column(Integer, ForeignKey("pool_state_policies.id"))
    governance_flags_snapshot_json = Column(Text)
    counter_before = Column(Integer)
    counter_after = Column(Integer)
    approval_required = Column(Boolean, nullable=False, default=False)
    approval_status = Column(String)
    override_applied = Column(Boolean, nullable=False, default=False)
    override_id = Column(Integer)
    explanation = Column(Text)
    warnings_json = Column(Text)
    metadata_json = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime)


class CourseStateApproval(Base):
    __tablename__ = "course_state_approvals"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String)
    transition_id = Column(Integer, ForeignKey("course_state_transitions.id"))
    requested_status = Column(Integer, nullable=False)
    current_status = Column(Integer)
    approval_type = Column(String, nullable=False)
    approval_status = Column(String, nullable=False, default="pending")
    requested_by = Column(String)
    requested_at = Column(DateTime)
    approval_reason = Column(Text)
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime)
    review_note = Column(Text)
    expires_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class CourseStateOverride(Base):
    __tablename__ = "course_state_overrides"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String)
    transition_id = Column(Integer, ForeignKey("course_state_transitions.id"))
    recommended_status = Column(Integer)
    overridden_final_status = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    requested_by = Column(String)
    approved_by = Column(String)
    approved_at = Column(DateTime)
    created_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, nullable=False, default=True)


# ---------------------------
# 33) IMPORT GOVERNANCE
# ---------------------------
class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    import_type = Column(String, nullable=False)
    source_table = Column(String)
    source_import_id = Column(Integer)
    original_filename = Column(String)
    stored_filename = Column(String)
    file_hash_sha256 = Column(String)
    file_size = Column(Integer)
    sheet_names_json = Column(Text)
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)
    column_signature_hash = Column(String)
    scope_type = Column(String)
    school_id = Column(Integer, ForeignKey("okul.school_id"))
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    semester = Column(String)
    uploaded_by = Column(String)
    uploaded_at = Column(DateTime)
    status = Column(String, nullable=False, default="uploaded")
    previous_import_batch_id = Column(Integer, ForeignKey("import_batches.id"))
    superseded_by_import_batch_id = Column(Integer, ForeignKey("import_batches.id"))
    duplicate_of_import_batch_id = Column(Integer, ForeignKey("import_batches.id"))
    validation_summary_json = Column(Text)
    quality_score = Column(Float)
    quality_level = Column(String)
    error_message = Column(Text)
    notes = Column(Text)
    approved_by = Column(String)
    approved_at = Column(DateTime)
    rejected_by = Column(String)
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    rolled_back_by = Column(String)
    rolled_back_at = Column(DateTime)
    rollback_reason = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class ImportQualityCheck(Base):
    __tablename__ = "import_quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    quality_score = Column(Float, nullable=False, default=0.0)
    quality_level = Column(String, nullable=False, default="low")
    required_columns_ok = Column(Boolean, nullable=False, default=True)
    successful_row_ratio = Column(Float, nullable=False, default=0.0)
    matched_course_ratio = Column(Float, nullable=False, default=0.0)
    valid_numeric_ratio = Column(Float, nullable=False, default=0.0)
    duplicate_row_count = Column(Integer, nullable=False, default=0)
    unmatched_row_count = Column(Integer, nullable=False, default=0)
    invalid_numeric_count = Column(Integer, nullable=False, default=0)
    missing_required_count = Column(Integer, nullable=False, default=0)
    out_of_range_count = Column(Integer, nullable=False, default=0)
    warning_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    summary_json = Column(Text)
    created_at = Column(DateTime)


class ImportRowIssue(Base):
    __tablename__ = "import_row_issues"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    source_row_id = Column(Integer)
    row_number = Column(Integer, nullable=False, default=0)
    severity = Column(String, nullable=False, default="warning")
    issue_type = Column(String, nullable=False, default="unknown_error")
    field_name = Column(String)
    raw_value = Column(Text)
    normalized_value = Column(Text)
    message = Column(Text, nullable=False)
    suggestion = Column(Text)
    created_at = Column(DateTime)


class ImportDiff(Base):
    __tablename__ = "import_diffs"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    compared_to_import_batch_id = Column(Integer, ForeignKey("import_batches.id"))
    added_count = Column(Integer, nullable=False, default=0)
    removed_count = Column(Integer, nullable=False, default=0)
    changed_count = Column(Integer, nullable=False, default=0)
    unchanged_count = Column(Integer, nullable=False, default=0)
    summary_json = Column(Text)
    created_at = Column(DateTime)


class ImportDiffItem(Base):
    __tablename__ = "import_diff_items"

    id = Column(Integer, primary_key=True, index=True)
    import_diff_id = Column(Integer, ForeignKey("import_diffs.id"), nullable=False)
    change_type = Column(String, nullable=False)
    entity_key = Column(String)
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    field_name = Column(String)
    before_value = Column(Text)
    after_value = Column(Text)
    before_row_json = Column(Text)
    after_row_json = Column(Text)
    message = Column(Text)


class ImportRollbackLog(Base):
    __tablename__ = "import_rollback_logs"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    action = Column(String, nullable=False)
    affected_table = Column(String, nullable=False)
    affected_record_id = Column(Integer)
    before_json = Column(Text)
    after_json = Column(Text)
    message = Column(Text)
    created_at = Column(DateTime)


class DecisionRunImportSource(Base):
    __tablename__ = "decision_run_import_sources"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    import_type = Column(String, nullable=False)
    created_at = Column(DateTime)


class ImportImpactReport(Base):
    __tablename__ = "import_impact_reports"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    previous_decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    new_decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    changed_decision_count = Column(Integer, nullable=False, default=0)
    curriculum_to_pool_count = Column(Integer, nullable=False, default=0)
    pool_to_curriculum_count = Column(Integer, nullable=False, default=0)
    rest_candidate_count = Column(Integer, nullable=False, default=0)
    cancel_candidate_count = Column(Integer, nullable=False, default=0)
    significant_score_change_count = Column(Integer, nullable=False, default=0)
    data_confidence_improved_count = Column(Integer)
    data_confidence_decreased_count = Column(Integer)
    summary_json = Column(Text)
    summary_text = Column(Text)
    created_at = Column(DateTime)


class DecisionStalenessFlag(Base):
    __tablename__ = "decision_staleness_flags"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"), nullable=False)
    reason = Column(String, nullable=False)
    old_reference_id = Column(Integer)
    new_reference_id = Column(Integer)
    message = Column(Text)
    requires_recalculation = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)


class AHPSensitivityResult(Base):
    __tablename__ = "ahp_sensitivity_results"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"), nullable=False)
    ahp_profile_id = Column(Integer, ForeignKey("ahp_weight_profiles.id"))
    variation_percent = Column(Float, nullable=False, default=0.05)
    tested_variations_json = Column(Text)
    affected_courses_count = Column(Integer, nullable=False, default=0)
    sensitive_courses_json = Column(Text)
    stability_summary_json = Column(Text)
    created_at = Column(DateTime)


class AHPCourseSensitivityItem(Base):
    __tablename__ = "ahp_course_sensitivity_items"

    id = Column(Integer, primary_key=True, index=True)
    sensitivity_result_id = Column(Integer, ForeignKey("ahp_sensitivity_results.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    base_score = Column(Float)
    min_score = Column(Float)
    max_score = Column(Float)
    score_range = Column(Float)
    base_decision = Column(String)
    changed_decision = Column(String)
    stability_level = Column(String, nullable=False, default="medium")
    explanation = Column(Text)
    created_at = Column(DateTime)


class CriteriaValueSource(Base):
    __tablename__ = "criteria_value_sources"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    field_name = Column(String, nullable=False)
    value_text = Column(Text)
    value_numeric = Column(Float)
    source_type = Column(String, nullable=False)
    source_import_batch_id = Column(Integer, ForeignKey("import_batches.id"))
    source_row_id = Column(Integer)
    is_locked = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    overridden_by_source_id = Column(Integer, ForeignKey("criteria_value_sources.id"))
    override_reason = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime)


class CriteriaCompletionMatrix(Base):
    __tablename__ = "criteria_completion_matrix"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String)
    criterion_key = Column(String, nullable=False)
    is_required = Column(Boolean, nullable=False, default=True)
    is_present = Column(Boolean, nullable=False, default=False)
    is_valid = Column(Boolean, nullable=False, default=False)
    value_text = Column(Text)
    value_numeric = Column(Float)
    missing_reason = Column(Text)
    invalid_reason = Column(Text)
    source_type = Column(String)
    source_id = Column(Integer)
    checked_at = Column(DateTime)


class CriteriaValidationIssue(Base):
    __tablename__ = "criteria_validation_issues"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    year = Column(Integer, nullable=False)
    semester = Column(String)
    criterion_key = Column(String)
    severity = Column(String, nullable=False, default="warning")
    issue_type = Column(String, nullable=False, default="unknown_error")
    raw_value = Column(Text)
    message = Column(Text, nullable=False)
    suggestion = Column(Text)
    created_at = Column(DateTime)


class CriteriaCompletionPolicy(Base):
    __tablename__ = "criteria_completion_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False, default="global")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    semester = Column(String)
    required_completion_ratio = Column(Float, nullable=False, default=1.0)
    required_fields_json = Column(Text, nullable=False)
    optional_fields_json = Column(Text)
    allow_new_course_missing_history = Column(Boolean, nullable=False, default=True)
    new_course_grace_period_years = Column(Integer, nullable=False, default=2)
    min_survey_response_count = Column(Integer)
    block_on_invalid_numeric = Column(Boolean, nullable=False, default=True)
    block_on_critical_issues = Column(Boolean, nullable=False, default=True)
    allow_override = Column(Boolean, nullable=False, default=True)
    override_requires_reason = Column(Boolean, nullable=False, default=True)
    override_requires_approval = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class CriteriaMissingDataRisk(Base):
    __tablename__ = "criteria_missing_data_risks"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    year = Column(Integer, nullable=False)
    semester = Column(String)
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String, nullable=False, default="low")
    missing_required_fields_json = Column(Text)
    missing_optional_fields_json = Column(Text)
    affected_weight_sum = Column(Float)
    explanation = Column(Text)
    created_at = Column(DateTime)


class CriteriaCompletionTask(Base):
    __tablename__ = "criteria_completion_tasks"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    year = Column(Integer, nullable=False)
    semester = Column(String)
    assigned_to = Column(String)
    assigned_role = Column(String)
    due_date = Column(Date)
    status = Column(String, nullable=False, default="open")
    missing_fields_json = Column(Text)
    validation_issues_json = Column(Text)
    priority = Column(String, nullable=False, default="medium")
    created_by = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    completed_at = Column(DateTime)
    approved_by = Column(String)
    approved_at = Column(DateTime)
    notes = Column(Text)


class CriteriaCompletionOverride(Base):
    __tablename__ = "criteria_completion_overrides"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    year = Column(Integer, nullable=False)
    semester = Column(String)
    missing_fields_json = Column(Text)
    validation_issues_json = Column(Text)
    reason = Column(Text, nullable=False)
    requested_by = Column(String)
    requested_at = Column(DateTime)
    approval_status = Column(String, nullable=False, default="pending")
    approved_by = Column(String)
    approved_at = Column(DateTime)
    rejected_by = Column(String)
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)
    expires_at = Column(DateTime)
    allowed_for_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    used_at = Column(DateTime)
    created_at = Column(DateTime)


class CriteriaCompletionHistory(Base):
    __tablename__ = "criteria_completion_history"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer, nullable=False)
    semester = Column(String)
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    old_completion_ratio = Column(Float)
    new_completion_ratio = Column(Float, nullable=False, default=0.0)
    old_completion_level = Column(String)
    new_completion_level = Column(String)
    changed_by = Column(String)
    change_reason = Column(Text)
    created_at = Column(DateTime)
    summary_json = Column(Text)


# ---------------------------
# 34) ML GOVERNANCE
# ---------------------------
class MLAlgorithmRegistry(Base):
    __tablename__ = "ml_algorithm_registry"

    id = Column(Integer, primary_key=True, index=True)
    algorithm_key = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    algorithm_type = Column(String, nullable=False)
    usage_role = Column(String, nullable=False, default="advisory_ml")
    default_enabled = Column(Boolean, nullable=False, default=True)
    min_training_samples = Column(Integer, nullable=False, default=50)
    min_samples_per_class = Column(Integer)
    requires_validation = Column(Boolean, nullable=False, default=True)
    supports_confidence = Column(Boolean, nullable=False, default=False)
    supports_explainability = Column(Boolean, nullable=False, default=False)
    notes = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class MLFeatureSnapshot(Base):
    __tablename__ = "ml_feature_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    feature_schema_version = Column(String, nullable=False)
    scope_json = Column(Text)
    year = Column(Integer)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    sample_count = Column(Integer, nullable=False, default=0)
    feature_names_json = Column(Text, nullable=False)
    missing_features_summary_json = Column(Text)
    imputation_strategy_json = Column(Text)
    normalization_summary_json = Column(Text)
    created_at = Column(DateTime)


class MLModelRun(Base):
    __tablename__ = "ml_model_runs"

    id = Column(Integer, primary_key=True, index=True)
    algorithm_key = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    usage_role = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    feature_schema_version = Column(String, nullable=False)
    training_scope_json = Column(Text)
    training_sample_count = Column(Integer, nullable=False, default=0)
    target_column = Column(String)
    class_distribution_json = Column(Text)
    parameters_json = Column(Text)
    train_metrics_json = Column(Text)
    validation_metrics_json = Column(Text)
    cross_validation_json = Column(Text)
    overfitting_report_json = Column(Text)
    readiness_level = Column(String)
    readiness_warnings_json = Column(Text)
    status = Column(String, nullable=False, default="created")
    skip_reason = Column(Text)
    artifact_path = Column(Text)
    created_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String)
    notes = Column(Text)


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True)
    model_run_id = Column(Integer, ForeignKey("ml_model_runs.id"))
    algorithm_key = Column(String, nullable=False)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    prediction_type = Column(String, nullable=False)
    predicted_value_text = Column(Text)
    predicted_value_numeric = Column(Float)
    confidence_score = Column(Float)
    confidence_level = Column(String)
    uncertainty_reasons_json = Column(Text)
    fallback_used = Column(Boolean, nullable=False, default=False)
    fallback_method = Column(String)
    fallback_reason = Column(Text)
    advisory_only = Column(Boolean, nullable=False, default=True)
    should_influence_decision = Column(Boolean, nullable=False, default=False)
    explanation = Column(Text)
    created_at = Column(DateTime)


class MLPredictionExplanation(Base):
    __tablename__ = "ml_prediction_explanations"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("ml_predictions.id"), nullable=False)
    top_features_json = Column(Text)
    feature_importance_json = Column(Text)
    decision_path_json = Column(Text)
    limitations_json = Column(Text)
    human_readable_text = Column(Text, nullable=False)
    created_at = Column(DateTime)


class MLReadinessReport(Base):
    __tablename__ = "ml_readiness_reports"

    id = Column(Integer, primary_key=True, index=True)
    scope_json = Column(Text)
    year = Column(Integer)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    sample_count = Column(Integer, nullable=False, default=0)
    algorithm_readiness_json = Column(Text)
    feature_quality_json = Column(Text)
    recommendations_json = Column(Text)
    summary_text = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 35) ALGORITHM GOVERNANCE
# ---------------------------
class AlgorithmGovernanceRegistry(Base):
    __tablename__ = "algorithm_governance_registry"

    id = Column(Integer, primary_key=True, index=True)
    algorithm_key = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    algorithm_family = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    usage_role = Column(String, nullable=False)
    can_affect_final_decision = Column(Boolean, nullable=False, default=False)
    default_enabled = Column(Boolean, nullable=False, default=True)
    minimum_sample_count = Column(Integer, nullable=False, default=10)
    minimum_samples_per_class = Column(Integer)
    requires_feature_scaling = Column(Boolean, nullable=False, default=False)
    requires_target = Column(Boolean, nullable=False, default=False)
    supports_probability = Column(Boolean, nullable=False, default=False)
    supports_feature_importance = Column(Boolean, nullable=False, default=False)
    supports_explainability = Column(Boolean, nullable=False, default=False)
    supports_cross_validation = Column(Boolean, nullable=False, default=False)
    recommended_validation_strategy = Column(String)
    recommended_metrics_json = Column(Text)
    risk_notes = Column(Text)
    user_facing_warning = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class AlgorithmTaskMapping(Base):
    __tablename__ = "algorithm_task_mapping"

    id = Column(Integer, primary_key=True, index=True)
    task_key = Column(String, nullable=False)
    algorithm_key = Column(String, nullable=False)
    allowed_usage_role = Column(String, nullable=False)
    is_recommended = Column(Boolean, nullable=False, default=False)
    notes = Column(Text)
    created_at = Column(DateTime)


class AlgorithmBenchmarkRun(Base):
    __tablename__ = "algorithm_benchmark_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_name = Column(String)
    task_type = Column(String, nullable=False)
    dataset_name = Column(String)
    dataset_scope_json = Column(Text)
    sample_count = Column(Integer, nullable=False, default=0)
    feature_count = Column(Integer, nullable=False, default=0)
    target_column = Column(String)
    algorithms_json = Column(Text)
    validation_strategy = Column(String)
    primary_metric_name = Column(String)
    status = Column(String, nullable=False, default="created")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String)
    summary_json = Column(Text)
    warnings_json = Column(Text)
    error_message = Column(Text)


class BenchmarkMetricResult(Base):
    __tablename__ = "benchmark_metric_results"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("algorithm_benchmark_runs.id"))
    algorithm_key = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    metrics_json = Column(Text)
    primary_metric_name = Column(String)
    primary_metric_value = Column(Float)
    warnings_json = Column(Text)
    created_at = Column(DateTime)


class BenchmarkValidationResult(Base):
    __tablename__ = "benchmark_validation_results"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("algorithm_benchmark_runs.id"))
    algorithm_key = Column(String, nullable=False)
    validation_strategy = Column(String, nullable=False)
    fold_count = Column(Integer)
    split_summary_json = Column(Text)
    fold_metrics_json = Column(Text)
    mean_metrics_json = Column(Text)
    std_metrics_json = Column(Text)
    warnings_json = Column(Text)
    created_at = Column(DateTime)


class BenchmarkStatisticalComparison(Base):
    __tablename__ = "benchmark_statistical_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("algorithm_benchmark_runs.id"))
    task_type = Column(String, nullable=False)
    primary_metric_name = Column(String)
    compared_algorithms_json = Column(Text)
    confidence_intervals_json = Column(Text)
    pairwise_tests_json = Column(Text)
    global_test_json = Column(Text)
    effect_sizes_json = Column(Text)
    significance_groups_json = Column(Text)
    summary_text = Column(Text)
    created_at = Column(DateTime)


class BenchmarkDataLeakageReport(Base):
    __tablename__ = "benchmark_data_leakage_reports"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("algorithm_benchmark_runs.id"))
    algorithm_key = Column(String)
    leakage_detected = Column(Boolean, nullable=False, default=False)
    leakage_level = Column(String, nullable=False, default="none")
    warnings_json = Column(Text)
    blocked = Column(Boolean, nullable=False, default=False)
    summary_text = Column(Text)
    created_at = Column(DateTime)


class BenchmarkModelDiagnostic(Base):
    __tablename__ = "benchmark_model_diagnostics"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("algorithm_benchmark_runs.id"))
    algorithm_key = Column(String, nullable=False)
    overfitting_warning = Column(Boolean, nullable=False, default=False)
    overfitting_score = Column(Float)
    train_validation_gap_json = Column(Text)
    class_imbalance_warning = Column(Boolean, nullable=False, default=False)
    class_distribution_json = Column(Text)
    high_variance_warning = Column(Boolean, nullable=False, default=False)
    diagnostics_json = Column(Text)
    summary_text = Column(Text)
    created_at = Column(DateTime)


class ClusteringEvaluationResult(Base):
    __tablename__ = "clustering_evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_run_id = Column(Integer, ForeignKey("algorithm_benchmark_runs.id"))
    algorithm_key = Column(String, nullable=False)
    cluster_count = Column(Integer, nullable=False, default=0)
    noise_ratio = Column(Float)
    silhouette_score = Column(Float)
    davies_bouldin_score = Column(Float)
    calinski_harabasz_score = Column(Float)
    cluster_size_distribution_json = Column(Text)
    stability_score = Column(Float)
    dbscan_params_json = Column(Text)
    warnings_json = Column(Text)
    summary_text = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 36) SEMESTER PLANNING GOVERNANCE
# ---------------------------
class SemesterPlanningPolicy(Base):
    __tablename__ = "semester_planning_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    scope_type = Column(String, nullable=False, default="global")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    curriculum_year = Column(Integer)
    total_elective_target = Column(Integer, nullable=False, default=8)
    fall_min = Column(Integer, nullable=False, default=4)
    fall_max = Column(Integer, nullable=False, default=4)
    spring_min = Column(Integer, nullable=False, default=4)
    spring_max = Column(Integer, nullable=False, default=4)
    max_semester_imbalance = Column(Integer, nullable=False, default=0)
    allow_unbalanced_distribution = Column(Boolean, nullable=False, default=False)
    same_course_repeat_policy = Column(String, nullable=False, default="disallow")
    same_course_repeat_requires_approval = Column(Boolean, nullable=False, default=True)
    high_demand_repeat_threshold = Column(Float)
    consider_course_availability = Column(Boolean, nullable=False, default=True)
    consider_instructor_availability = Column(Boolean, nullable=False, default=False)
    consider_resource_constraints = Column(Boolean, nullable=False, default=False)
    consider_prerequisites = Column(Boolean, nullable=False, default=True)
    consider_required_course_load = Column(Boolean, nullable=False, default=False)
    consider_expected_demand = Column(Boolean, nullable=False, default=True)
    consider_capacity_balance = Column(Boolean, nullable=False, default=True)
    consider_time_conflicts = Column(Boolean, nullable=False, default=False)
    minimum_plan_score = Column(Float)
    hard_constraint_policy = Column(String, nullable=False, default="strict")
    soft_constraint_weight_json = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class CourseSemesterAvailability(Base):
    __tablename__ = "course_semester_availability"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    allowed_fall = Column(Boolean, nullable=False, default=True)
    allowed_spring = Column(Boolean, nullable=False, default=True)
    preferred_semester = Column(String, nullable=False, default="either")
    availability_type = Column(String, nullable=False, default="always")
    unavailable_reason = Column(Text)
    effective_from_year = Column(Integer)
    effective_to_year = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class CourseInstructorAssignment(Base):
    __tablename__ = "course_instructor_assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("instructors.id"), nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    can_teach = Column(Boolean, nullable=False, default=True)
    preferred = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class InstructorSemesterAvailability(Base):
    __tablename__ = "instructor_semester_availability"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, ForeignKey("instructors.id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String, nullable=False)
    available = Column(Boolean, nullable=False, default=True)
    max_elective_courses = Column(Integer, nullable=False, default=2)
    current_assigned_elective_count = Column(Integer)
    unavailable_reason = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class TeachingResource(Base):
    __tablename__ = "teaching_resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_name = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    capacity = Column(Integer)
    available_fall = Column(Boolean, nullable=False, default=True)
    available_spring = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class CourseResourceRequirement(Base):
    __tablename__ = "course_resource_requirements"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    resource_type = Column(String, nullable=False)
    required_capacity = Column(Integer)
    required_hours = Column(Float)
    hard_requirement = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class SemesterResourceCapacity(Base):
    __tablename__ = "semester_resource_capacity"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("teaching_resources.id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String, nullable=False)
    available_capacity = Column(Integer)
    available_hours = Column(Float)
    reserved_hours = Column(Float)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    prerequisite_course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    prerequisite_type = Column(String, nullable=False, default="hard")
    relation_note = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class SemesterRequiredCourseLoad(Base):
    __tablename__ = "semester_required_course_loads"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String, nullable=False)
    required_course_count = Column(Integer, nullable=False, default=0)
    total_credits = Column(Float)
    total_ects = Column(Float)
    workload_score = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class CourseTimeConstraint(Base):
    __tablename__ = "course_time_constraints"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer)
    semester = Column(String)
    unavailable_slots_json = Column(Text)
    preferred_slots_json = Column(Text)
    conflict_group = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    notes = Column(Text)


class SemesterPlanRun(Base):
    __tablename__ = "semester_plan_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_name = Column(String)
    year = Column(Integer, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    policy_id = Column(Integer, ForeignKey("semester_planning_policies.id"))
    total_candidate_count = Column(Integer, nullable=False, default=0)
    selected_count = Column(Integer, nullable=False, default=0)
    fall_count = Column(Integer, nullable=False, default=0)
    spring_count = Column(Integer, nullable=False, default=0)
    plan_score = Column(Float)
    status = Column(String, nullable=False, default="created")
    metrics_json = Column(Text)
    policy_snapshot_json = Column(Text)
    warnings_json = Column(Text)
    created_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String)
    error_message = Column(Text)


class SemesterPlanCourseAssignment(Base):
    __tablename__ = "semester_plan_course_assignments"

    id = Column(Integer, primary_key=True, index=True)
    plan_run_id = Column(Integer, ForeignKey("semester_plan_runs.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    assigned_semester = Column(String, nullable=False)
    assignment_type = Column(String, nullable=False, default="selected")
    course_score = Column(Float)
    expected_demand = Column(Float)
    expected_capacity = Column(Float)
    constraint_status = Column(String, nullable=False, default="ok")
    explanation = Column(Text)
    created_at = Column(DateTime)


class SemesterPlanConstraintViolation(Base):
    __tablename__ = "semester_plan_constraint_violations"

    id = Column(Integer, primary_key=True, index=True)
    plan_run_id = Column(Integer, ForeignKey("semester_plan_runs.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    constraint_type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="warning")
    message = Column(Text, nullable=False)
    suggestion = Column(Text)
    created_at = Column(DateTime)


class SemesterPlanScenario(Base):
    __tablename__ = "semester_plan_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    plan_run_id = Column(Integer, ForeignKey("semester_plan_runs.id"), nullable=False)
    scenario_name = Column(String, nullable=False)
    scenario_type = Column(String, nullable=False)
    fall_courses_json = Column(Text)
    spring_courses_json = Column(Text)
    metrics_json = Column(Text)
    constraint_violations_json = Column(Text)
    explanations_json = Column(Text)
    plan_score = Column(Float)
    created_at = Column(DateTime)


# ---------------------------
# 37) ARCHITECTURE / SCHEMA AUDIT
# ---------------------------
class SchemaCompatLog(Base):
    __tablename__ = "schema_compat_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, nullable=False)
    table_name = Column(String, nullable=False)
    column_name = Column(String)
    index_name = Column(String)
    sql_text = Column(Text)
    success = Column(Boolean, nullable=False, default=True)
    message = Column(Text)
    created_at = Column(DateTime)



# 38) DATA COVERAGE REPORTS
# ---------------------------
class DataCoverageReport(Base):
    __tablename__ = "data_coverage_reports"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)  # global, faculty, department
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    semester = Column(String)
    total_courses = Column(Integer, nullable=False, default=0)
    courses_with_criteria = Column(Integer, nullable=False, default=0)
    courses_with_performance = Column(Integer, nullable=False, default=0)
    courses_with_popularity = Column(Integer, nullable=False, default=0)
    courses_with_survey = Column(Integer, nullable=False, default=0)
    courses_with_score = Column(Integer, nullable=False, default=0)
    courses_with_trend_data = Column(Integer, nullable=False, default=0)
    criteria_coverage_ratio = Column(Float, nullable=False, default=0.0)  # 0-1
    performance_coverage_ratio = Column(Float, nullable=False, default=0.0)
    popularity_coverage_ratio = Column(Float, nullable=False, default=0.0)
    survey_coverage_ratio = Column(Float, nullable=False, default=0.0)
    score_coverage_ratio = Column(Float, nullable=False, default=0.0)
    trend_coverage_ratio = Column(Float, nullable=False, default=0.0)
    overall_coverage_score = Column(Float, nullable=False, default=0.0)  # 0-1
    missing_data_summary_json = Column(Text)
    recommendations_json = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 39) DATA READINESS ASSESSMENTS
# ---------------------------
class DataReadinessAssessment(Base):
    __tablename__ = "data_readiness_assessments"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)  # global, faculty, department
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    readiness_score = Column(Float, nullable=False, default=0.0)  # 0-100
    readiness_level = Column(String, nullable=False, default="not_ready")  # not_ready, low, medium, good, decision_ready
    criteria_coverage_score = Column(Float, nullable=False, default=0.0)
    performance_coverage_score = Column(Float, nullable=False, default=0.0)
    popularity_coverage_score = Column(Float, nullable=False, default=0.0)
    survey_coverage_score = Column(Float, nullable=False, default=0.0)
    trend_readiness_score = Column(Float, nullable=False, default=0.0)
    validation_quality_score = Column(Float, nullable=False, default=0.0)
    data_confidence_average = Column(Float, nullable=False, default=0.0)
    blocking_issues_count = Column(Integer, nullable=False, default=0)
    warning_issues_count = Column(Integer, nullable=False, default=0)
    recommendation_summary = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 40) MISSING DATA ITEMS
# ---------------------------
class MissingDataItem(Base):
    __tablename__ = "missing_data_items"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(String)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    missing_field = Column(String, nullable=False)  # success_rate, avg_grade, capacity, enrollment, survey_count, trend_history, popularity, score
    severity = Column(String, nullable=False, default="warning")  # info, warning, critical
    required_for_decision = Column(Boolean, nullable=False, default=True)
    message = Column(Text)
    suggested_action = Column(Text)
    detected_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)


# ---------------------------
# 41) DATA VALIDATION ISSUES
# ---------------------------
class DataValidationIssue(Base):
    __tablename__ = "data_validation_issues"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, nullable=False)  # manual_entry, criteria_import, survey_import, curriculum_import, computed, api
    source_id = Column(Integer)
    source_row_id = Column(Integer)
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    field_name = Column(String)
    issue_type = Column(String, nullable=False)  # missing_required, out_of_range, inconsistent_value, duplicate, unmatched_course, stale_data, suspicious_value
    severity = Column(String, nullable=False, default="warning")  # info, warning, error, critical
    message = Column(Text)
    suggested_action = Column(Text)
    raw_value = Column(Text)
    normalized_value = Column(Text)
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_by = Column(String)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime)


# ---------------------------
# 42) LOW CONFIDENCE DECISION FLAGS
# ---------------------------
class LowConfidenceDecisionFlag(Base):
    __tablename__ = "low_confidence_decision_flags"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"), nullable=False)
    course_decision_id = Column(Integer, ForeignKey("course_decisions.id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    year = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0-1
    confidence_level = Column(String, nullable=False, default="low")  # low, medium
    reason = Column(Text)
    recommended_action = Column(Text)
    created_at = Column(DateTime)
    resolved_at = Column(DateTime)


# ---------------------------
# 43) DATA COLLECTION PRIORITIES
# ---------------------------
class DataCollectionPriority(Base):
    __tablename__ = "data_collection_priorities"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)  # global, faculty, department
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    year = Column(Integer)
    priority_rank = Column(Integer, nullable=False, default=100)
    target_entity_type = Column(String, nullable=False)  # course, department, faculty, criterion_type
    course_id = Column(Integer, ForeignKey("ders.ders_id"))
    missing_field = Column(String)
    priority_reason = Column(Text)
    expected_impact = Column(String, nullable=False, default="medium")  # low, medium, high
    suggested_action = Column(Text)
    status = Column(String, nullable=False, default="open")  # open, in_progress, completed, ignored
    created_at = Column(DateTime)
    completed_at = Column(DateTime)


# ---------------------------
# 44) POST DECISION OUTCOMES
# ---------------------------
class PostDecisionOutcome(Base):
    __tablename__ = "post_decision_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    decision_run_id = Column(Integer, ForeignKey("decision_runs.id"))
    course_decision_id = Column(Integer, ForeignKey("course_decisions.id"))
    course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    decision_year = Column(Integer, nullable=False)
    outcome_year = Column(Integer, nullable=False)
    final_status_applied = Column(Integer)
    actual_enrollment = Column(Integer)
    actual_capacity = Column(Integer)
    actual_fill_rate = Column(Float)
    actual_success_rate = Column(Float)
    actual_average_grade = Column(Float)
    actual_survey_demand = Column(Integer)
    outcome_label = Column(String)  # improved, worsened, stable, unknown
    decision_was_effective = Column(Boolean)
    notes = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 45) FAIRNESS METRIC ITEMS (detailed)
# ---------------------------
class FairnessMetricItem(Base):
    __tablename__ = "fairness_metric_items"

    id = Column(Integer, primary_key=True, index=True)
    fairness_report_id = Column(Integer, ForeignKey("decision_fairness_reports.id"), nullable=False)
    metric_key = Column(String, nullable=False)  # department_representation, semester_balance, new_course_opportunity, low_confidence_rate, diversity, survey_participation_bias
    metric_value = Column(Float)
    metric_level = Column(String, nullable=False, default="warning")  # good, warning, critical
    explanation = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 46) ML DATASET SNAPSHOTS
# ---------------------------
class MLDatasetSnapshot(Base):
    __tablename__ = "ml_dataset_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_name = Column(String)
    scope_json = Column(Text)
    year = Column(Integer)
    feature_schema_version = Column(String, nullable=False)
    sample_count = Column(Integer, nullable=False, default=0)
    feature_count = Column(Integer, nullable=False, default=0)
    target_column = Column(String)
    coverage_score = Column(Float, nullable=False, default=0.0)
    average_confidence_score = Column(Float, nullable=False, default=0.0)
    missing_data_summary_json = Column(Text)
    created_at = Column(DateTime)


# ---------------------------
# 47) API CLIENTS (Security)
# ---------------------------
class ApiClient(Base):
    __tablename__ = "api_clients"

    id = Column(String, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    api_key_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="api_client")
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=True)
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime)
    last_used_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


# ---------------------------
# 48) SQL CONSOLE AUDIT LOGS (Security)
# ---------------------------
class SqlConsoleAuditLog(Base):
    __tablename__ = "sql_console_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True)
    client_id = Column(String, nullable=True)
    role = Column(String, nullable=True)
    sql_text = Column(Text, nullable=False)
    statement_type = Column(String, nullable=False)
    read_only = Column(Boolean, nullable=False, default=True)
    dangerous = Column(Boolean, nullable=False, default=False)
    allowed = Column(Boolean, nullable=False, default=False)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    row_count = Column(Integer, nullable=True)
    executed_at = Column(DateTime)
    environment = Column(String)
    request_id = Column(String, nullable=True)


# ---------------------------
# 49) SECURE IMPORT JOBS (Security)
# ---------------------------
class SecureImportJob(Base):
    __tablename__ = "secure_import_jobs"

    id = Column(String, primary_key=True, index=True)
    import_type = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=True)
    uploaded_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=True)
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=True)
    year = Column(Integer, nullable=True)
    semester = Column(String, nullable=True)
    status = Column(String, nullable=False, default="uploaded")
    validation_summary_json = Column(Text, nullable=True)
    preview_summary_json = Column(Text, nullable=True)
    row_count = Column(Integer, nullable=True)
    warning_count = Column(Integer, nullable=True)
    error_count = Column(Integer, nullable=True)
    critical_count = Column(Integer, nullable=True)
    approval_required = Column(Boolean, nullable=False, default=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_by = Column(String, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    applied_by = Column(String, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    rollback_available = Column(Boolean, nullable=False, default=False)
    rollback_snapshot_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)


class SecureImportJobRow(Base):
    __tablename__ = "secure_import_job_rows"

    id = Column(Integer, primary_key=True, index=True)
    import_job_id = Column(String, ForeignKey("secure_import_jobs.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data_json = Column(Text, nullable=False)
    normalized_data_json = Column(Text, nullable=True)
    matched_course_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=True)
    row_status = Column(String, nullable=False, default="valid")
    issues_json = Column(Text, nullable=True)
    created_at = Column(DateTime)


# ---------------------------
# 50) SECURITY AUDIT LOGS (Security)
# ---------------------------
class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String, nullable=True)
    role = Column(String, nullable=True)
    faculty_id = Column(Integer, nullable=True)
    department_id = Column(Integer, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    severity = Column(String, nullable=False, default="info")
    message = Column(Text, nullable=False)
    before_json = Column(Text, nullable=True)
    after_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    request_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime)
    previous_hash = Column(String, nullable=True)
    event_hash = Column(String, nullable=True)


# ---------------------------
# 51) DATA SNAPSHOTS (Security / Rollback)
# ---------------------------
class DataSnapshot(Base):
    __tablename__ = "data_snapshots"

    id = Column(String, primary_key=True, index=True)
    snapshot_type = Column(String, nullable=False)
    scope_type = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=True)
    department_id = Column(Integer, ForeignKey("bolum.bolum_id"), nullable=True)
    year = Column(Integer, nullable=True)
    related_import_job_id = Column(String, nullable=True)
    related_decision_run_id = Column(Integer, nullable=True)
    snapshot_path = Column(String, nullable=True)
    snapshot_hash = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime)
    notes = Column(Text, nullable=True)
