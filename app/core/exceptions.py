# -*- coding: utf-8 -*-
# =============================================================================
# app/core/exceptions.py — Ozel Hata Siniflari
# =============================================================================
# Proje genelinde kullanilan istisnai durum (exception) siniflari.
# =============================================================================


class BaseError(Exception):
    """Tum proje hatalarinin taban sinifi."""


class StudentNotFoundError(BaseError):
    """Ogrenci bulunamadiginda firlatilir."""


class CourseQuotaExceededError(BaseError):
    """Ders kontenjani doldugunda firlatilir."""
