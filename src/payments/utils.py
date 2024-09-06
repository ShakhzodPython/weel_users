import hashlib

from logs.logger import logger



def generate_access_token(login, card_number, expiry_date, password):
    """ Генерирует MD5 хеш для access_token"""
    token = f"{login}{card_number}{expiry_date}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def generate_resend_sms_token(login, confirm_id, password):
    """Генерирует токен для переотправки смс кода"""
    token = f"{login}{confirm_id}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def generate_confirm_token(login, confirm_id, verify_code, password):
    """ Генерирует MD5 хеш для confirm_token"""
    token = f"{login}{confirm_id}{verify_code}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def convert_expiry_date(expiry_date: str) -> str:
    """ Меняет формат срок действия YYMM на MMYY"""
    if len(expiry_date) != 4:
        logger.error("Неверный формат даты истечения срока. Ожидается MMYY.")
        raise ValueError("Invalid expiry date format. Expected MMYY.")

    # Разделяем строку на месяц и год
    month = expiry_date[:2]
    year = expiry_date[2:]
    return year + month


def generate_uzcard_id_token(login, uzcard_id, password):
    """ Генерирует MD5 хеш для uzcard_id"""
    token = f"{login}{uzcard_id}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def generate_payment_token(login, card_phone, uzcard_id, service_id, personal_account, amount_tiyin, password):
    """ Генерирует MD5 хеш для оплаты"""
    token = f"{login}{card_phone}{uzcard_id}{service_id}{personal_account}{amount_tiyin}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def generate_confirm_payment_token(login, confirm_id, verify_code, password):
    """Генерирует токен для подтверждения оплаты если телефон номер смс информирования была изменена"""
    token = f"{login}{confirm_id}{verify_code}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def generate_check_transaction_token(login, transaction_id, password):
    """Генерирует токен для проверки статуса оплаты"""
    token = f"{login}{transaction_id}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


def generate_cancel_transaction_token(login, transaction_id, password):
    """Генерирует токен для отмены оплаты"""
    token = f"{login}{transaction_id}{password}"
    md5_hash = hashlib.md5(token.encode()).hexdigest()
    return md5_hash


