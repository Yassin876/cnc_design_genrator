import re

def normalize_email(email: str) -> str:
    """Normalize email address by stripping whitespace and converting to lowercase."""
    if not email:
        return ""
    return email.strip().lower()


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength according to production standards.
    Requirements:
    - Minimum 8 characters
    - Must contain at least one letter and one number
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
        
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."

    return True, ""
