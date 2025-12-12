class BaseError(Exception):
    """Temel hata sınıfı"""
    pass

class StudentNotFoundError(BaseError):
    """Öğrenci bulunamadığında fırlatılır."""
    pass

class CourseQuotaExceededError(BaseError):
    """Ders kontenjanı dolduğunda fırlatılır."""
    pass