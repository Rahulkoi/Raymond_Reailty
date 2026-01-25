import re

def valid_phone(phone):
    return bool(re.fullmatch(r"\+?\d{10,13}", phone or ""))

def valid_email(email):
    return "@" in (email or "")

def validate_lead(data: dict):
    errors = []

    if not valid_phone(data["mobile_number"]):
        errors.append("phone")

    if not valid_email(data["email"]):
        errors.append("email")

    if not data["full_name"]:
        errors.append("name")

    if not data["city"]:
        errors.append("city")

    return errors
