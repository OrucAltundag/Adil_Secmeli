# -*- coding: utf-8 -*-
# =============================================================================
# app/utils/etl.py — ETL Yardimci Fonksiyonlari
# =============================================================================
# Excel dosyalarindan veri okuma islemleri.
# =============================================================================
import pandas as pd


def import_students_from_excel(file_path):
    """Excel dosyasindan ogrenci kayitlarini okuyup sozluk listesi olarak doner."""
    try:
        df = pd.read_excel(file_path)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Excel okuma hatasi: {e}")
        return []
