from httpx import AsyncClient
from fastapi import HTTPException

from logs.logger import logger
from src.payments.utils import generate_access_token, generate_confirm_token, generate_payment_token, \
    generate_uzcard_id_token


async def card_response(partner_key, card_number, expiry_date, login, password):
    """ Отправляет запрос регистрации карты на сервер платежной системы. """
    url = "https://api.upay.uz/STAPI/STWS?wsdl"
    access_token = generate_access_token(login, card_number, expiry_date, password)

    request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:st="http://st.apus.com/"> 
   <soapenv:Header/>
   <soapenv:Body>
      <st:partnerRegisterCard>
        <partnerRegisterCardRequest>  
            <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
            <AccessToken>{access_token}</AccessToken>
            <CardNumber>{card_number}</CardNumber>
            <ExDate>{expiry_date}</ExDate>
            <Version>1</Version>
            <Lang>ru</Lang>
            </partnerRegisterCardRequest>
        </st:partnerRegisterCard>
    </soapenv:Body>
</soapenv:Envelope>"""
    headers = {'Content-Type': 'text/xml'}
    async with AsyncClient() as client:
        response = await client.post(url, data=request_body, headers=headers)

        if response.status_code != 200:
            logger.error(f"Не удалось зарегистрировать карту {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to register card")
    logger.info('Карта успешно зарегистрирована')
    return response


# TODO: Метод находиться в доработке
# async def resend_sms(partner_key, confirm_id, login, password):
#     url = "https://api.upay.uz/STAPI/STWS?wsdl"
#     resend_sms_token = generate_resend_sms_token(login, confirm_id, password)
#
#     request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
#     <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
#         <soapenv:Header/>
#         <soapenv:Body>
#             <st:partnerCardResendSms>
#                 <partnerCardResendSmsRequest>
#                     <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
#                     <AccessToken>{resend_sms_token}</AccessToken>
#                     <ConfirmId>{confirm_id}</ConfirmId>
#                     <Version>1</Version>
#                     <Lang>ru</Lang>
#                 </partnerCardResendSmsRequest>
#             </st:partnerCardResendSms>
#         </soapenv:Body>
#     </soapenv:Envelope>
#     """
#     headers = {'Content-Type': 'text/xml'}
#
#     async with AsyncClient() as client:
#         response = await client.post(url, data=request_body, headers=headers)
#         if response.status_code != 200:
#             raise HTTPException(status_code=response.status_code, detail=response.text)
#     return response


async def confirm_card(partner_key, confirm_id, verify_code, login, password):
    url = "https://api.upay.uz/STAPI/STWS?wsdl"
    confirm_token = generate_confirm_token(login, confirm_id, verify_code, password)

    request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <st:partnerConfirmCard>
            <partnerConfirmCardRequest>
                <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
                <AccessToken>{confirm_token}</AccessToken>
                <ConfirmId>{confirm_id}</ConfirmId>
                <VerifyCode>{verify_code}</VerifyCode>
                <Version>1</Version>
                <Lang>ru</Lang>
            </partnerConfirmCardRequest>
        </st:partnerConfirmCard>
    </soapenv:Body>
</soapenv:Envelope>
    """
    headers = {'Content-Type': 'text/xml'}

    async with AsyncClient() as client:
        response = await client.post(url, data=request_body, headers=headers)
        if response.status_code != 200:
            logger.error(f"Не удалось подтвердить карту {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
    logger.success("Карта успешно подтверждения")
    return response


async def get_all_cards(partner_key, uzcard_id, login, password):
    url = "https://api.upay.uz/STAPI/STWS?wsdl"
    uzcard_token = generate_uzcard_id_token(login, uzcard_id, password)

    request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <st:partnerCardList>
            <partnerCardListRequest>
                <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
                <AccessToken>{uzcard_token}</AccessToken>
                <CardList>{uzcard_id}</CardList>
                <Version>1</Version>
                <Lang>ru</Lang>
            </partnerCardListRequest>
        </st:partnerCardList>
    </soapenv:Body>
</soapenv:Envelope>
    """
    headers = {'Content-Type': 'text/xml'}

    async with AsyncClient() as client:
        response = await client.post(url, data=request_body, headers=headers)

        if response.status_code != 200:
            logger.error(f"Ошибка при получений данных {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to register card")
    logger.success("Данные успешно получены")
    return response


async def create_payment(partner_key, uzcard_id, card_phone, service_id,
                         personal_account, amount_tiyin, login, password):
    url = "https://api.upay.uz/STAPI/STWS?wsdl"
    payment_token = generate_payment_token(login, card_phone, uzcard_id, service_id, personal_account, amount_tiyin,
                                           password)
    request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <st:partnerPayment>
            <partnerPaymentRequest>
                <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
                <AccessToken>{payment_token}</AccessToken>
                <CardPhone>{card_phone}</CardPhone>
                <UzcardId>{uzcard_id}</UzcardId>
                <ServiceId>{service_id}</ServiceId>
                <PaymentType></PaymentType>
                <PersonalAccount>{personal_account}</PersonalAccount>
                <AmountInTiyin>{amount_tiyin}</AmountInTiyin>
                <RegionId></RegionId>
                <SubRegionId></SubRegionId>
                <Version>1</Version>
                <Lang>ru</Lang>
            </partnerPaymentRequest>
        </st:partnerPayment>
    </soapenv:Body>
</soapenv:Envelope>
    """
    headers = {'Content-Type': 'text/xml'}

    async with AsyncClient() as client:
        response = await client.post(url, data=request_body, headers=headers)
        if response.status_code != 200:
            logger.error(f"Ошибка при выполнений транзакции {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to register card")
    logger.success("Средства успешно сняты")
    return response


# TODO: Функция для подтверждения оплаты если смс информирование подключено на другой телефон номер
# async def confirm_payment(partner_key, confirm_id, verify_code, login, password):
#     url = "https://api.upay.uz/STAPI/STWS?wsdl"
#     payment_confirm_token = generate_confirm_payment_token(login, confirm_id, verify_code, password)
#
#     request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
#         <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
#         <soapenv:Header/>
#         <soapenv:Body>
#             <st:partnerConfirmPayment>
#                 <partnerConfirmPaymentRequest>
#                     <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
#                     <AccessToken>{payment_confirm_token}</AccessToken>
#                     <ConfirmId>{confirm_id}</ConfirmId>
#                     <VerifyCode>{verify_code}</VerifyCode>
#                     <Version>1</Version>
#                     <Lang>ru</Lang>
#                 </partnerConfirmPaymentRequest>
#             </st:partnerConfirmPayment>
#         </soapenv:Body>
#     </soapenv:Envelope>
#         """
#     headers = {'Content-Type': 'text/xml'}
#
#     async with AsyncClient() as client:
#         response = await client.post(url, data=request_body, headers=headers)
#         if response.status_code != 200:
#             raise HTTPException(status_code=response.status_code, detail=response.text)
#         return response


# TODO: Метод для проверки статуса оплаты
# async def check_transaction(partner_key, transaction_id, confirm_id, login, password):
#     url = "https://api.upay.uz/STAPI/STWS?wsdl"
#     check_transaction_token = generate_check_transaction_token(login, transaction_id, password)
#
#     request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
#         <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
#         <soapenv:Header/>
#         <soapenv:Body>
#             <st:partnerConfirmPayment>
#                 <partnerConfirmPaymentRequest>
#                     <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
#                     <AccessToken>{check_transaction_token}</AccessToken>
#                     <TransactionId>{transaction_id}</TransactionId>
#                     <ConfirmId>{confirm_id}</ConfirmId>
#                     <Version>1</Version>
#                     <Lang>ru</Lang>
#                 </partnerConfirmPaymentRequest>
#             </st:partnerConfirmPayment>
#         </soapenv:Body>
#     </soapenv:Envelope>
#     """


# TODO: Метод для отмены оплаты
# async def cancel_transaction(partner_key, transaction_id, login, password):
#     url = "https://api.upay.uz/STAPI/STWS?wsdl"
#     cancel_transaction_token = generate_cancel_transaction_token(login, transaction_id, password)
#
#     request_body = f"""<?xml version="1.0" encoding="UTF-8"?>
#     <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:st="http://st.apus.com/">
#     <soapenv:Header/>
#     <soapenv:Body>
#         <st:partnerCancelTransaction>
#         <partnerCancelTransactionRequest>
#                 <StPimsApiPartnerKey>{partner_key}</StPimsApiPartnerKey>
#                 <AccessToken>{cancel_transaction_token}</AccessToken>
#                 <TransactionId>{transaction_id}</TransactionId>
#                 <Version>1</Version>
#                 <Lang>ru</Lang>
#             </partnerCancelTransactionRequest>
#         </st:partnerCancelTransaction>
#     </soapenv:Body>
# </soapenv:Envelope>
#     """
#
#     print(request_body)
#     headers = {'Content-Type': 'text/xml'}
#
#     async with AsyncClient() as client:
#         response = await client.post(url, data=request_body, headers=headers)
#         # if response.status_code != 200:
#         #     raise HTTPException(status_code=response.status_code, detail="Failed to register card")
#     print(response.text)
#     return response
