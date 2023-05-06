import logging
import os
import time
import sys

import requests
from dotenv import load_dotenv
import telegram

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Проверка токенов."""
    TOKEN_DICT = {
        'Токен Яндекс.практикума': PRACTICUM_TOKEN,
        'ID чата': TELEGRAM_CHAT_ID,
        'Токен телеграм бота': TELEGRAM_TOKEN,
    }
    for token_name, token in TOKEN_DICT.items():
        if token is None:
            logging.critical(f'Отсутствует обязательная переменная окружения '
                             f'{token_name}')
            sys.exit(f'Отсутствует обязательная переменная окружения '
                     f'{token_name}')


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение успешно отправлено {message}')
    except telegram.error.TelegramError:
        logging.error('Ошибка при отправке сообщения')
        raise telegram.error.TelegramError('Не удалось отправить сообщение')


def get_api_answer(timestamp):
    """Получение ответа API."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=timestamp
        )
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise ConnectionError(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != 200:
        logging.error('HTTPResponse is not 200')
        raise requests.exceptions.HTTPError('HTTPResponse is not 200')
    try:
        return homework_statuses.json()
    except TypeError:
        logging.error('Данные не в json формате')
        raise TypeError('Данные не в json формате')


def check_response(response):
    """Проверка типа данных."""
    if not isinstance(response, dict):
        logging.error('Тип данных не является словарём')
        response_type = type(response)
        raise TypeError(f'response is {response_type}, expected a dict')
    if 'homeworks' not in response:
        logging.error('Ключ homeworks отсутствует в словаре')
        raise KeyError('Ключа homeworks нет в словаре')
    if not isinstance(response['homeworks'], list):
        logging.error('Тип данных не является списком')
        response_type = type(response['homeworks'])
        raise TypeError(f'response is {response_type}, expected a list')
    return response


def parse_status(homework):
    """Проверка статуса работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        logging.error('Нет ключа homework_name в словаре')
        raise KeyError('Нет ключа в словаре')
    if status not in HOMEWORK_VERDICTS:
        logging.error('Статус работы неизвестен')
        raise ValueError('Status is None')
    verdict = HOMEWORK_VERDICTS[status]
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            response = check_response(get_api_answer(timestamp))
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                if message != last_status:
                    send_message(bot, message)
                    last_status = message
                    logging.debug('Статус изменился')
        except requests.exceptions.RequestException:
            logging.error('Ошибка при запросе к основному API')
            try:
                send_message(bot, 'Ошибка при запросе к основному API')
            except telegram.error.TelegramError:
                logging.error('Ошибка при отправке сообщения')
                raise telegram.error.TelegramError(
                    'Не удалось отправить сообщение')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
