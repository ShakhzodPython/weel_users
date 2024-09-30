import xmltodict

from uuid import UUID
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, HTTPException, Form, Response, status

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from logs.logger import logger
from database.settings import get_db
from database.security import get_current_user, hash_data, get_api_key, is_superuser
from database.config import STPimsApiPartnerKey, PASSWORD, LOGIN, SERVICE_ID
from src.payments.requests import card_response, confirm_card, get_all_cards, create_payment
from src.payments.response_parser import parse_confirm_id, parse_uzcard_id, parse_card_phone, \
    parse_balance_from_confirm, parse_transaction_id, parse_confirmation
from src.payments.utils import convert_expiry_date
from src.payments.redis import save_confirm_id, get_confirm_id, get_card, save_card, save_uzcard_id, get_uzcard_id, \
    save_card_phone, save_balance, get_card_phone, save_transaction_id
from src.users.models import Card, User

router_payment = APIRouter(
    tags=["Payments"]
)


@router_payment.get("/api/v1/cards/{user_id}/", status_code=status.HTTP_200_OK)
async def get_cards(user_id: UUID,
                    current_user: User = Depends(get_current_user)):
    logger.info(f"Попытка получения кредитной карты пользователя с UUID: {user_id}")

    try:
        # Получение uzcard_id из Redis
        uzcard_id = await get_uzcard_id(user_id)
        if not uzcard_id:
            logger.error("Uzcard ID не найден или просрочен")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uzcard ID not found or expired")

        response = await get_all_cards(STPimsApiPartnerKey, uzcard_id, LOGIN, PASSWORD)

        # Парсинг ошибки
        root = ElementTree.fromstring(response.text)
        namespaces = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
        correct = root.find(".//s:Body/ns2:partnerCardListResponse/return/Result/code", namespaces=namespaces)
        error = root.find(".//s:Body/ns2:partnerCardListResponse/return/Result/Description", namespaces=namespaces)
        if correct is not None and correct.text != "OK":
            logger.error(error.text)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.text)

        xml_data = response.content
        data_to_dict = xmltodict.parse(xml_data)

        card_lst = data_to_dict.get("S:Envelope", {}).get("S:Body", {}).get("ns2:partnerCardListResponse", {}).get(
            "return", {})
        logger.success(f"Кредитная карта пользователя с UUID: {user_id} получена успешно")
        return {"cards": card_lst}
    except HTTPException as e:
        logger.error(str(e))
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router_payment.post("/api/v1/cards/add/", status_code=status.HTTP_200_OK)
async def card_registration(
        card_number: str = Form(...),
        expiry_date: str = Form(..., description="Enter expiry date in format MM/YY"),
        current_user: UUID = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    # Проверка наличия карты в базе данных
    logger.info(f"Попытка регистрации кредитной карты пользователь с UUID: {current_user.id}")

    # Проверка наличия карты в базе данных
    card_number_hashed = hash_data(card_number)
    existing_card_stmt = await db.execute(select(Card).where(Card.card_number_hashed == card_number_hashed))
    existing_card = existing_card_stmt.scalars().one_or_none()
    if existing_card:
        logger.error(f"Кредитная карта пользователя с UUID: {current_user.id} уже существует")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Card already exist")

    # Переформатирование формата срока действия карты
    try:
        formatted_expiry_date = convert_expiry_date(expiry_date)
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Отправка данных в платежный сервис
    response = await card_response(STPimsApiPartnerKey, card_number, formatted_expiry_date, LOGIN, PASSWORD)

    # Парсинг ошибки
    root = ElementTree.fromstring(response.text)
    namespaces = {"s": "http://schemas.xmlsoap.org/soap/envelope/", "ns2": "http://st.apus.com/"}
    correct = root.find(".//s:Body/ns2:partnerRegisterCardResponse/return/Result/code", namespaces=namespaces)
    error = root.find(".//s:Body/ns2:partnerRegisterCardResponse/return/Result/Description", namespaces=namespaces)

    if correct is not None and correct.text != "OK":
        logger.error(error.text)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.text)

    # Извлечение confirm_id из ответа
    confirm_id = parse_confirm_id(response.text)
    await save_confirm_id(current_user.id, confirm_id)
    await save_card(current_user.id, card_number, formatted_expiry_date)
    logger.success(f"СМС-код успешно отправлен пользователю с UUID: {current_user.id}")
    return {"detail": "Sms code send successfully"}


# TODO: Метод для пере отправки смс кода находиться в доработке
# @router_payment.post("/card/resend-sms/")
# async def card_resend_sms(current_user: User = Depends(get_current_admin_or_user)):
#     # Получение confirm_id из Redis
#     confirm_id = await get_confirm_id(current_user.id)
#
#     if confirm_id is None:
#         raise HTTPException(status_code=404, detail="Confirmation ID not found")
#
#     response = await resend_sms(STPimsApiPartnerKey, confirm_id, LOGIN, PASSWORD)
#
#     root = ElementTree.fromstring(response.text)
#     namespaces = {"s": "http://schemas.xmlsoap.org/soap/envelope/", "ns2": "http://st.apus.com/"}
#     correct = root.find(".//s:Body/ns2:partnerRegisterCardResponse/return/Result/code", namespaces=namespaces)
#     error = root.find(".//s:Body/ns2:partnerRegisterCardResponse/return/Result/Description", namespaces=namespaces)
#
#     if correct is not None and correct.text != "OK":
#         raise HTTPException(status_code=400, detail=error.text)
#
#     return {
#         "detail": "Sms code send successfully",
#     }

@router_payment.post("/api/v1/cards/confirm/", status_code=status.HTTP_201_CREATED)
async def card_confirmation(verify_code: int,
                            current_user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка подтверждения кредитной карты пользователем с UUID: {current_user.id}")
    # Получение confirm_id из Redis
    confirm_id = await get_confirm_id(current_user.id)

    if not confirm_id:
        logger.error("Confirmation ID не найдено")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Confirmation ID not found")

    response = await confirm_card(STPimsApiPartnerKey, confirm_id, verify_code, LOGIN, PASSWORD)

    # Парсинг ошибки
    root = ElementTree.fromstring(response.text)
    namespaces = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
    correct = root.find(".//s:Body/ns2:partnerConfirmCardResponse/return/Result/code", namespaces=namespaces)
    error = root.find(".//s:Body/ns2:partnerConfirmCardResponse/return/Result/Description", namespaces=namespaces)
    if correct is not None and correct.text != "OK":
        logger.error(f"Ошибка при подтверждений кредитной карты: {error.text}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.text)

    # Получение хешированных данных карты из Redis
    card_number, expiry_date = await get_card(current_user.id)
    if not card_number or not expiry_date:
        logger.error("Кредитная карта или срок действия карты не валиден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid card_number or expiry_date")

    # Извлечение uzcard_id из ответа
    uzcard_id = parse_uzcard_id(response.text)
    card_phone = parse_card_phone(response.text)
    balance = parse_balance_from_confirm(response.text)
    await save_uzcard_id(current_user.id, uzcard_id)
    await save_card_phone(current_user.id, card_phone)
    await save_balance(current_user.id, balance)

    card_number_hashed = hash_data(card_number)
    expiry_date_hashed = hash_data(expiry_date)

    try:
        new_card = Card(
            user_id=current_user.id,
            card_number_hashed=card_number_hashed,
            expiry_date_hashed=expiry_date_hashed,
            is_blacklisted=False
        )
        db.add(new_card)
        await db.commit()
        await db.refresh(new_card)
        logger.success(f"Кредитная карта пользователя: {current_user.id} добавлена успешно")
        return {"detail": "Card added successfully"}
    except Exception as e:
        logger.error(f"Failed to save new card: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register the card")


# TODO: Эндпоит для проверки статуса оплаты


# TODO: Метод для отмены оплаты находиться в доработке
# @router_payment.post("/card/payment/cancel")
# async def cancel_payment(current_user: User = Depends(get_current_admin_or_user)):
#     transaction_id = await get_transaction_id(current_user.id)
#     if transaction_id is None:
#         logger.error("")
#         raise HTTPException(status_code=404, detail="ID транзакции не найден")
#
#     response = await cancel_transaction(STPimsApiPartnerKey, transaction_id, LOGIN, PASSWORD)
#     if response.status_code != 200:
#         logger.error("Не удалось зарегистрировать карту")
#         raise HTTPException(status_code=response.status_code, detail="Failed to register card")
#     logger.info("Платеж отменен")
#     return {
#         "detail": "Payment canceled",
#     }

@router_payment.post("/api/v1/cards/pay/{user_id}/", status_code=status.HTTP_200_OK)
async def card_payment(user_id: UUID,
                       amount_tiyin: int):
    logger.info(f"Попытка снятия средств с карты пользователя с UUID: {user_id}")

    uzcard_id = await get_uzcard_id(user_id)
    if not uzcard_id:
        logger.error("Uzcard ID не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uzcard ID not found")

    card_phone = await get_card_phone(user_id)
    if not card_phone:
        logger.error("Номер телефона карты не найден")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card phone number not found")

    response = await create_payment(STPimsApiPartnerKey, uzcard_id, card_phone, SERVICE_ID, user_id,
                                    amount_tiyin, LOGIN, PASSWORD)

    # Парсинг ошибки
    root = ElementTree.fromstring(response.text)
    namespaces = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
    correct = root.find(".//s:Body/ns2:partnerPaymentResponse/return/Result/code", namespaces=namespaces)
    error = root.find(".//s:Body/ns2:partnerPaymentResponse/return/Result/Description", namespaces=namespaces)
    if correct is not None and correct.text != "OK":
        logger.error(f"Ошибка при оплате по кредитной карте {error.text}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.text)

    # Извлечение uzcard_id из ответа
    transaction = parse_transaction_id(response.text)
    await save_transaction_id(user_id, transaction)

    confirmed = parse_confirmation(response.text)
    if confirmed == "false":
        logger.error("Ваша карта не привязана к вашему номеру телефона")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Your card not connected to your phone_number")

    logger.success(f"Со пользователь с UUID: {user_id} успешно сняты средства")
    return {"detail": "Payment was successfully"}


@router_payment.delete("/api/v1/cards/delete/{card_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int,
                      user_id: UUID,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    logger.info(f"Попытка удаления кредитной карты с ID: {card_id}")

    if "SUPERUSER" not in [role.name for role in current_user.roles] and user_id != current_user.id:
        logger.error("Доступ запрещен: У вас недостаточно прав")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You don't have enough privileges")

    stmt = await db.execute(select(Card).options(selectinload(Card.user)).where(Card.id == card_id))
    card = stmt.scalars().one_or_none()

    if card is None:
        logger.error(f"Карта с ID:{card_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    await db.delete(card)
    await db.commit()
    logger.success(f"Карта с ID: {card} успешно удалена")
    return Response(status.HTTP_204_NO_CONTENT)


@router_payment.post("/api/v1/black-list/add/cards/{card_id}/", status_code=status.HTTP_200_OK)
async def add_blacklist_card(card_id: int,
                             db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(is_superuser)):
    logger.info(f"Попытка добавить кредитную карту с ID: {card_id} в черный список")

    stmt = await db.execute(select(Card).where(Card.id == card_id))
    card = stmt.scalars().one_or_none()
    if card is None:
        logger.error(f"Кредитная карта с ID: {card_id} не найдена")
        raise HTTPException(status_code=404, detail="Card not found")

    if card.is_blacklisted == True:
        logger.error(f"Ваше кредитная карта с ID: {card_id} уже находиться в черном списке")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your card already located in blacklist")

    # Добавляем кредитную карту в черный список
    card.is_blacklisted = True
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.success(f"Кредитная карта с ID: {card_id} добавлена в черный список успешно")
    return {"detail": f"Card with ID: {card_id} has been blacklisted successfully"}


@router_payment.post("/api/v1/black-list/remove/cards/{card_id}/", status_code=status.HTTP_200_OK)
async def remove_blacklist_card(card_id: int,
                                db: AsyncSession = Depends(get_db),
                                current_user: User = Depends(is_superuser)):
    logger.info(f"Попытка добавить кредитную карту с ID: {card_id} в черный список")

    stmt = await db.execute(select(Card).where(Card.id == card_id))
    card = stmt.scalars().one_or_none()
    if card is None:
        logger.error(f"Кредитная карта с ID: {card_id} не найдена")
        raise HTTPException(status_code=404, detail="Card not found")

    if card.is_blacklisted == False:
        logger.error(f"Ваше кредитная карта с ID: {card_id} уже удалена из черного списка")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your card already removed from blacklist")
    card.is_blacklisted = False
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.success(f"Кредитная карта с ID: {card_id} удалена из черный список успешно")
    return {"detail": f"Card with ID: {card_id} has been removed from blacklist successfully"}
