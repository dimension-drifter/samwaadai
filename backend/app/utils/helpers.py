"""
Helper utilities for the application
"""

from datetime import datetime
from typing import Dict, List
import json

def format_duration(seconds: int) -> str:
    """Format duration in seconds to readable format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text"""
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    return re.sub(r'[^\w\s-]', '', filename).strip()