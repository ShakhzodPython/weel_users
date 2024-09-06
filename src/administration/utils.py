import re

from fastapi import HTTPException, status


def validate_username(username: str) -> str:
    if len(username) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Имя пользователя должен состоять минимум из 5 букв")
    return username


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароль должен быть не менее 8 символов")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Пароль должен содержать хотя бы одну заглавную букву")

    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Пароль должен содержать хотя бы одну строчную букву")

    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Пароль должен содержать хотя бы одну цифру")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Пароль должен содержать хотя бы один специальный символ")

    if re.search(r'\b(password|1234|qwerty)\b', password, re.I):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Пароль не должен содержать легко подбираемые последовательности")
    return password
