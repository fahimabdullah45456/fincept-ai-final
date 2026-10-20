"""Shared CSV cell neutralisation for spreadsheet formula injection (CWE-1236)."""

def csv_safe(value):
    text = '' if value is None else str(value)
    stripped = text.lstrip(' \t\r\n\ufeff\u200b')
    if stripped.startswith(('=', '+', '-', '@')) or (bool(text) and ord(text[0]) < 32):
        return "'" + text
    return text
