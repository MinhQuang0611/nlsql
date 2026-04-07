import os
import json
import gspread
import logging
from google.oauth2.service_account import Credentials
import asyncio

from config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Config
CREDENTIALS_FILE = os.path.abspath(settings.google_sheets_credentials_file)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

_gc = None

def get_gspread_client():
    global _gc
    if _gc is None:
        try:
            if os.path.exists(CREDENTIALS_FILE):
                credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
                _gc = gspread.authorize(credentials)
                logger.info("Google Sheets authenticated successfully.")
            else:
                logger.error(f"Google Sheets Service account key not found at {CREDENTIALS_FILE}")
        except Exception as e:
            logger.error(f"Error authenticating Google Sheets: {e}")
    return _gc

def sync_append_to_sheet(sheet_url: str, row_data: list):
    """
    Append a row of data to the Google Sheet.
    """
    if not sheet_url:
        logger.warning("No Google Sheet URL provided. Skipping append.")
        return

    gc = get_gspread_client()
    if not gc:
        return

    try:
        if "spreadsheets.google.com" in sheet_url:
            sh = gc.open_by_url(sheet_url)
        else:
            sh = gc.open_by_key(sheet_url)
            
        worksheet = sh.sheet1
        worksheet.append_row(row_data)
        logger.info(f"Successfully appended row to Google Sheet.")
    except Exception as e:
        logger.error(f"Failed to append to Google Sheet: {e}", exc_info=True)

async def append_to_sheet(sheet_url: str, row_data: list):
    """
    Async wrapper to prevent blocking the event loop.
    """
    await asyncio.to_thread(sync_append_to_sheet, sheet_url, row_data)
