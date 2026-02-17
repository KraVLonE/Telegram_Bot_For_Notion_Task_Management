import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    NOTION_KEY = os.getenv("NOTION_KEY")
    DATABASE_ID = os.getenv("DATABASE_ID")
    GEMINI_KEY = os.getenv("GEMINI_KEY")
    AUTHORIZED_USER_ID = int(os.getenv("TELEGRAM_USERID", 0))

    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_TOKEN: missing.append("TELEGRAM_TOKEN")
        if not cls.NOTION_KEY: missing.append("NOTION_KEY")
        if not cls.DATABASE_ID: missing.append("DATABASE_ID")
        if not cls.GEMINI_KEY: missing.append("GEMINI_KEY")
        if not cls.AUTHORIZED_USER_ID: missing.append("TELEGRAM_USERID")
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
