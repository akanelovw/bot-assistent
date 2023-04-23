import logging
import os
import time

import requests
from dotenv import load_dotenv
import telegram

load_dotenv()

secret_token = os.getenv('TOKEN')
practicum_token = os.getenv('PRACTICUM_TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

PRACTICUM_TOKEN = practicum_token
TELEGRAM_TOKEN = '6235105987:AAErJbT1Uxd2riA0os8_7OWbLgUOifdvOGU'
TELEGRAM_CHAT_ID = '5989373675'

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов."""
    if PRACTICUM_TOKEN is None:
        logging.critical('Токен Яндекс.Практикума не был предоставлен')
        raise ValueError('PRACTICUM_TOKEN is None')
    if TELEGRAM_CHAT_ID is None:
        logging.critical('ID чата не был предоставлен')
        raise ValueError('TELEGRAM_CHAT_ID is None')
    if TELEGRAM_TOKEN is None:
        logging.critical('Токен телеграм бота не был предоставлен')
        raise ValueError('TELEGRAM_TOKEN is None')


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение успешно отправлено {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Получение ответа API."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=timestamp
        )
        if homework_statuses.status_code == 200:
            return homework_statuses.json()
        else:
            raise ValueError('httpResponse is not 200')
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверка типа данных."""
    if isinstance(response, dict):
        if 'homeworks' not in response:
            logging.error('Ключ homeworks отсутствует в словаре')
            raise KeyError('Ключа homeworks нет в словаре')
        if isinstance(response['homeworks'], list):
            return response
        else:
            logging.error('Тип данных не является списком')
            raise TypeError('homeworks is not a list')
    else:
        logging.error('Тип данных не является словарём')
        raise TypeError('response is not a dict')


def parse_status(homework):
    """Проверка статуса работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is not None:
        if status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS[status]
            return (f'Изменился статус проверки работы "{homework_name}".'
                    f'{verdict}')
        else:
            logging.error('Статус работы неизвестен')
            raise ValueError('Status is None')
    else:
        logging.error('Нет ключа homework_name в словаре')
        raise KeyError('Нет ключа в словаре')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework['homeworks'][0])
            if message != last_status:
                send_message(bot, message)
                last_status = message
                logging.debug('Статус изменился')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
