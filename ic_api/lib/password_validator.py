"""
Password strength validator for backend
"""

import re

COMMON_PASSWORDS = {
    "password", "123456", "password123", "admin", "letmein", "welcome",
    "monkey", "dragon", "master", "sunshine", "qwerty", "123123",
    "111111", "abc123", "123456789", "password1", "pass", "test",
    "guest", "hello", "world", "strawbay", "invoice", "scanner"
}


def validate_password_strength(password):
    """
    Validate password strength.
    Returns a dict with:
    - is_valid: bool
    - strength: int (0-5)
    - errors: list of error messages
    - feedback: list of improvement tips
    """
    result = {
        "is_valid": False,
        "strength": 0,
        "errors": [],
        "feedback": []
    }

    if not password:
        result["errors"].append("Password is required")
        return result

    if len(password) < 8:
        result["errors"].append("Password must be at least 8 characters")
    elif len(password) < 12:
        result["feedback"].append("Longer passwords are more secure")
    else:
        result["strength"] += 1

    # Check for lowercase letters
    if not re.search(r'[a-z]', password):
        result["errors"].append("Password must contain lowercase letters")
    else:
        result["strength"] += 1

    # Check for uppercase letters
    if not re.search(r'[A-Z]', password):
        result["errors"].append("Password must contain uppercase letters")
    else:
        result["strength"] += 1

    # Check for numbers
    if not re.search(r'\d', password):
        result["errors"].append("Password must contain numbers")
    else:
        result["strength"] += 1

    # Check for special characters
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        result["feedback"].append("Adding special characters makes password stronger")
    else:
        result["strength"] += 1

    # Check for common passwords
    if password.lower() in COMMON_PASSWORDS:
        result["errors"].append("This password is too common")
    else:
        result["strength"] += 1

    # Check for repeating characters
    if re.search(r'(.)\1{2,}', password):
        result["feedback"].append("Avoid repeating characters")

    # Check for keyboard patterns
    if re.search(r'qwerty|asdfgh|zxcvbn|123456|654321', password.lower()):
        result["feedback"].append("Avoid keyboard patterns")

    # Validate
    result["is_valid"] = len(result["errors"]) == 0

    # Clamp strength to 0-5
    result["strength"] = min(5, result["strength"])

    return result
