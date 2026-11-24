"""Print a password hash for ADMIN_PASSWORD_HASH: python -m app.hashpw"""
import getpass
import sys

from app.auth import hash_password

if __name__ == "__main__":
    pw = getpass.getpass("New password: ")
    if pw != getpass.getpass("Repeat password: "):
        sys.exit("Passwords don't match.")
    if len(pw) < 8:
        sys.exit("Use at least 8 characters.")
    print(hash_password(pw))
