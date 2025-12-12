from sqlalchemy.orm import Session
from app.db.database import SessionLocal

class AssignmentService:
    # db_session tipini doğrudan 'Session' olarak belirtiyoruz
    def __init__(self, db_session: Session): 
        self.db = db_session

    def create_course_pool(self, student_id):
        """
        1. Öğrenci için uygun dersleri getirir.
        2. Önkoşul ve Dinlendirme kurallarını uygular.
        3. Havuzu döndürür.
        """
        pass

    def assign_mandatory_courses(self, student_id, pool):
        """Havuzdan en iyi 2 dersi seçer ve atar"""
        pass