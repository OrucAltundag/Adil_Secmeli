# -*- coding: utf-8 -*-
# Proje kökünden "python main.py" ile başlatma kısayolu
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import AdilSecmeliApp

if __name__ == "__main__":
    app = AdilSecmeliApp()
    app.mainloop()
