import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.DATABASE_URL = self._require("DATABASE_URL")
        self.SUPABASE_URL = self._require("SUPABASE_URL")
        self.SUPABASE_KEY = self._require("SUPABASE_KEY")
        self.SUPABASE_STORAGE_BUCKET = self._require("SUPABASE_STORAGE_BUCKET")
        self.APP_PASSWORD = self._require("APP_PASSWORD")
        self.SESSION_SECRET_KEY = self._require("SESSION_SECRET_KEY")
        self.INVOICE_RECIPIENT_EMAIL = self._require("INVOICE_RECIPIENT_EMAIL")

        # Business rule constants — change here to affect all calculations
        self.TOTE_RATE = 5
        self.FOLLOWUP_DAYS_THRESHOLD = 60
        self.UPCOMING_PICKUP_DAYS = 14
        self.SESSION_EXPIRY_DAYS = 30
        self.PDF_SIGNED_URL_EXPIRY_SECONDS = 3600

    def _require(self, key: str) -> str:
        value = os.environ.get(key)
        if value is None:
            raise KeyError(key)
        return value


settings = Settings()
