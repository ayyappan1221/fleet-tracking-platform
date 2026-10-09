"""Password strength rules, shared by API validation and tests.

Five rules; a password is acceptable only when all five pass:
  1. At least 8 characters
  2. At least one uppercase letter (A-Z)
  3. At least one lowercase letter (a-z)
  4. At least one digit (0-9)
  5. At least one special character (anything that is not a letter or digit)
"""

MIN_PASSWORD_LENGTH = 8


def check_password_strength(password: str) -> list[str]:
    """Return the list of unmet rule labels. Empty list means the password is OK."""
    password = password or ''
    unmet: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        unmet.append(f'At least {MIN_PASSWORD_LENGTH} characters')
    if not any(c.isupper() for c in password):
        unmet.append('At least one uppercase letter (A-Z)')
    if not any(c.islower() for c in password):
        unmet.append('At least one lowercase letter (a-z)')
    if not any(c.isdigit() for c in password):
        unmet.append('At least one digit (0-9)')
    if not any(not c.isalnum() for c in password):
        unmet.append('At least one special character (e.g. !@#$)')
    return unmet


def password_strength_message(password: str) -> str:
    """Single human-readable message listing every unmet rule."""
    unmet = check_password_strength(password)
    if not unmet:
        return 'Password meets all strength requirements'
    return 'Password too weak: ' + '; '.join(unmet)
