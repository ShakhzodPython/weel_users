from xml.etree import ElementTree
from logs.logger import logger


def parse_confirm_id(xml_response):
    """Находит ConfirmId из ответа card_response"""
    try:
        # Преобразуем строку XML в структуру данных
        root = ElementTree.fromstring(xml_response)
        # Используем правильный XPath с учетом namespace для envelope и body
        ns = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
        # Находим элемент ConfirmId, который находится вне пространства имен ns2
        confirm_id = root.find(".//s:Body/ns2:partnerRegisterCardResponse/return/ConfirmId", namespaces=ns)

        if confirm_id is not None:
            return confirm_id.text
        else:
            logger.error("ConfirmId не найден в ответе")
            raise ValueError("ConfirmId not found in the response")
    except ElementTree.ParseError:
        logger.error("Ошибка при парсинге XML-ответа")
        raise ValueError("Error parsing the XML response")


def parse_uzcard_id(xml_response):
    """ Находит UzcardId из ответа card_confirm_response"""
    try:
        root = ElementTree.fromstring(xml_response)
        namespaces = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
        uzcard_id = root.find(".//s:Body/ns2:partnerConfirmCardResponse/return/UzcardId", namespaces=namespaces)
        if uzcard_id is not None:
            return uzcard_id.text
        else:
            logger.error("UzcardId не найден в ответе")
            raise ValueError("UzcardId not found in the response")
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML-ответа: {e}")
        raise ValueError("Error parsing the XML response: " + str(e))


def parse_card_phone(xml_response):
    """Находит Card_phone из ответа card_confirm_response"""
    try:
        root = ElementTree.fromstring(xml_response)
        namespaces = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
        card_phone = root.find(".//s:Body/ns2:partnerConfirmCardResponse/return/CardPhone", namespaces=namespaces)
        if card_phone is not None:
            return card_phone.text
        else:
            logger.error("Телефон карты не найден в ответе")
            raise ValueError("Card Phone not found in the response")
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML-ответа: {e}")
        raise ValueError("Error parsing the XML response: " + str(e))


def parse_transaction_id(xml_response):
    """Находит TransactionId из ответа payment_response"""
    try:
        root = ElementTree.fromstring(xml_response)
        namespaces = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://st.apus.com/'}
        transaction = root.find(".//s:Body/ns2:partnerPaymentResponse/return/TransactionId", namespaces=namespaces)
        if transaction is not None:
            return transaction.text
        else:
            logger.error("Телефон карты не найден в ответе")
            raise ValueError("Card Phone not found in the response")
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML-ответа: {e}")
        raise ValueError("Error parsing the XML response: " + str(e))


def parse_confirmation(xml_response):
    """Находит confirmed из ответа payment_response"""
    try:
        root = ElementTree.fromstring(xml_response)
        namespaces = {"s": "http://schemas.xmlsoap.org/soap/envelope/", "ns2": "http://st.apus.com/"}
        confirmation = root.find(".//s:Body/ns2:partnerPaymentResponse/return/Confirmed", namespaces=namespaces)
        if confirmation is not None:
            return confirmation.text
        else:
            logger.error("Подтверждение в ответе не найдено")
            raise ValueError("Confirmation not found in the response")
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML-ответа: {e}")
        raise ValueError("Error parsing the XML response: " + str(e))


def parse_balance(xml_response):
    """Находит balance из ответа card_list_response"""
    try:
        root = ElementTree.fromstring(xml_response)
        namespaces = {"s": "http://schemas.xmlsoap.org/soap/envelope/", "ns2": "http://st.apus.com/"}
        balance = root.find(".//s:Body/ns2:partnerCardListResponse/return/CardList/CardList/Balance",
                            namespaces=namespaces)
        if balance is not None:
            return balance.text
        else:
            logger.error("Баланс не найден в ответе")
            raise ValueError("Balance not found in the response")
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML-ответа: {e}")
        raise ValueError("Error parsing the XML response: " + str(e))


def parse_balance_from_confirm(xml_response):
    """Находит balance из ответа card_list_response"""
    try:
        root = ElementTree.fromstring(xml_response)
        namespaces = {"s": "http://schemas.xmlsoap.org/soap/envelope/", "ns2": "http://st.apus.com/"}
        balance = root.find(".//s:Body/ns2:partnerConfirmCardResponse/return/Balance",
                            namespaces=namespaces)
        if balance is not None:
            return balance.text
        else:
            logger.error("Баланс не найден в ответе")
            raise ValueError("Balance not found in the response")
    except ElementTree.ParseError as e:
        logger.error(f"Ошибка при парсинге XML-ответа: {e}")
        raise ValueError("Error parsing the XML response: " + str(e))
