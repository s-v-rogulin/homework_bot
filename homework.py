import logging
import os
import time

from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram.ext

from dotenv import load_dotenv

from exceptions import (
    EndpointUnavailableError, RequestError, ResponseError, StatusError,
)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    filemode='w',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('main.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('TOKEN_YA')
TELEGRAM_TOKEN = os.getenv('TOKEN_TG')
TELEGRAM_CHAT_ID = os.getenv('TG_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность токенов."""
    if not PRACTICUM_TOKEN:
        logging.critical('Отсутствует токен платформы Яндекс.Практикум')
        raise SystemExit('Потерян токен Яндекс.Практикум')
    if not TELEGRAM_TOKEN:
        logging.critical('Отсутствует токен платформы Телеграм')
        raise SystemExit('Потерян токен Телеграм')
    if not TELEGRAM_CHAT_ID:
        logging.critical('Отсутствует ID пользователя')
        raise SystemExit('Потерян айди пользователя телеграм')
    return True


def send_message(bot, message):
    """Отвечает за отправку сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение успешно отправлено: {message}')
    except Exception as error:
        logging.error(f'Ошибка при обращении к API Telegram: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )

        if homework_statuses.status_code == HTTPStatus.NOT_FOUND:
            raise EndpointUnavailableError(
                'Эндпоинт Практикум.Домашка недоступен. Код ответа: 404.'
            )

        if homework_statuses.status_code != HTTPStatus.OK:
            raise ResponseError(
                f'При запросе к сервису Практикум.Домашка возникла ошибка.'
                f'Код ответа: {homework_statuses.status_code}.'
            )

        return homework_statuses.json()
    except requests.exceptions.RequestException as error:
        raise RequestError(
            f'Сбой при запросе к сервису Практикум.Домашка: {error}.'
        )


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ сервиса не является словарем. Ответ сервиса {response}.'
        )
    homeworks = response.get('homeworks')
    if not response.get('homeworks'):
        raise KeyError('В полученном ответе отсутствует ключ `homeworks`.')

    if not response.get('current_date'):
        raise KeyError('В полученном ответе отсутствует ключ `current_date`.')

    if not isinstance(homeworks, list):
        raise TypeError(
            f'Значение по ключу `homeworks` не является списком.'
            f'Ответ сервиса: {homeworks}'
        )

    if not homeworks:
        raise IndexError('Значение по ключу `homeworks` - пустой список.')

    return homeworks


def parse_status(homework):
    """Извлекает статус  конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not (homework_status and homework_name):
        raise KeyError(
            'В ответе отсутствуют ключи `homework_name` и/или `status`'
        )

    if homework_status not in HOMEWORK_VERDICTS:
        raise StatusError('Получен некорректный статус работы.')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return (f'Изменился статус проверки работы "{homework_name}". {verdict}')


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())

        while True:
            try:
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                new_rep_homeworks = len(homeworks)
                while new_rep_homeworks > 0:
                    message = parse_status(homeworks[new_rep_homeworks - 1])
                    send_message(bot, message)
                    new_rep_homeworks -= 1
                timestamp = int(time.time())
                time.sleep(RETRY_PERIOD)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
