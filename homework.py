import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = [
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    ]
    missing_tokens = []
    for token_name, token in tokens:
        if not token:
            missing_tokens.append(token_name)
            logger.critical(f'Отсутствует переменная окружения: {token_name}')
    if len(missing_tokens) != 0:
        raise exceptions.UnavailableTokens(
            'Отсутствуют переменные окружения: {missing_tokens}'
            .format(missing_tokens=missing_tokens)
        )
    logger.debug('Токены проверены')


def send_message(bot, message):
    """Oтправка сообщения в Telegram-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.TelegramError as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
    else:
        logger.debug(f'Cообщение "{message}" успешно отправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        response = requests.get(**params)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                f'Неверный код ответа. Получен код: {response.status_code}.'
                f'{response.reason}'
            )
        logger.debug('Отправлен запрос к API-сервису')
        return response.json()
    except requests.exceptions.RequestException as error:
        raise exceptions.UnavailableEndpoint(
            f'Ошибка запроса к эндпоинту API-сервиса: {error}'
        )
    except json.JSONDecodeError as error:
        raise exceptions.ResponseDatаError(
            f'Ошибка ответа API-сервиса: {error}'
        )


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует типу dict')
    if 'homeworks' not in response:
        raise KeyError('В ответе API нет ключа "homeworks"')
    if 'current_date' not in response:
        raise exceptions.NoCurrentDateKey(
            'В ответе API нет ключа "current_date"'
        )
    if not isinstance(response['current_date'], int):
        raise exceptions.CurrentDateIsNotInt(
            '"current_date" не является целым числом'
        )
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('"homeworks" не является списком')
    logger.debug('Проверен ответ API-сервиса')
    return homeworks


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    for key in (homework_name, homework_status):
        if not key:
            raise KeyError(f'"{key}" отсутствует в словаре')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        raise ValueError(
            f'Неизвестный статус домашней работы: {homework_status}'
        )
    logger.debug('Получен статус домашней работы')
    return ('Изменился статус проверки работы "{homework_name}". {verdict}'
            ).format(homework_name=homework_name,
                     verdict=HOMEWORK_VERDICTS[homework_status]
                     )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
            else:
                logger.debug('Нет новых статусов домашних работ')
            timestamp = response.get('current_date')
        except exceptions.NoCurrentDateKey:
            logger.error('В ответе API нет ключа "current_date"')
        except exceptions.CurrentDateIsNotInt:
            logger.error('"current_date" не является целым числом')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_message:
                logger.error(message)
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(name)s,'
               '%(message)s, %(funcName)s, %(lineno)d',
        filename=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'main.log'),
        filemode='w'
    )
    main()
