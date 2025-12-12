import pandas as pd

def import_students_from_excel(file_path):
    """Excel dosyasından öğrencileri okur ve listeye çevirir"""
    try:
        df = pd.read_excel(file_path)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Excel okuma hatası: {e}")
        return []