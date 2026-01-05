import re
from datetime import datetime

def ddmmyyyy_to_iso(s: str) -> str:
    # DD/MM/YYYY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s.strip())
    if not m:
        raise ValueError("Invalid dateOfBirth format, expected DD/MM/YYYY")
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    dt = datetime(int(yyyy), int(mm), int(dd))
    return dt.strftime("%Y-%m-%d")

def iso_to_ddmmyyyy(iso: str) -> str:
    dt = datetime.strptime(iso, "%Y-%m-%d")
    return dt.strftime("%d-%m-%Y")

def normalize_ddmmyyyy(s: str) -> str:
    s = s.strip()
    if re.match(r"^\d{2}-\d{2}-\d{4}$", s):
        return s
    if re.match(r"^\d{2}/\d{2}/\d{4}$", s):
        dd, mm, yyyy = s.split("/")
        return f"{dd}-{mm}-{yyyy}"
    raise ValueError("Invalid date format, expected DD-MM-YYYY or DD/MM/YYYY")
