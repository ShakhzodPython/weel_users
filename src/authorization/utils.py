from fastapi import HTTPException, status

from logs.logger import logger


async def check_phone(phone_number: str):
    if not phone_number.isnumeric():
        logger.error("Номер телефона должен состоять только из цифр")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Номер телефона должен состоять только из цифр")
    elif len(phone_number) != 9:
        logger.error("Номер телефона должен состоять только из цифр")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Номер телефона должен состоять только из 9 цифр")
    return phone_number



