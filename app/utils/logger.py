import logging
import sys

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout), # Konsola yaz
        logging.FileHandler("app.log")     # Dosyaya yaz
    ]
)

logger = logging.getLogger("AdilSecmeli")