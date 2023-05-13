import exceptions
import logging
import os
import requests
import sys
import telegram
import time
from dotenv import load_dotenv
from http import HTTPStatus

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


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s,'
           '%(message)s, %(funcName)s, %(lineno)d',
    filename='main.log',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    logging.info('Проверка токенов..')
    token_list = [
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    ]
    for token_name, token in token_list:
        if not token:
            logger.critical(f'Отсутствует переменная окружения "{token_name}"')
            raise exceptions.UnavailableTokens(f'Отсутствует переменная '
                                               f'окружения "{token_name}"')


def send_message(bot, message):
    """Oтправка сообщения в Telegram-чат."""
    logging.info('Отправка сообщения..')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Cообщение "{message}" успешно отправлено')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        raise exceptions.MessageSendingError(error)


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    logging.info('Отправка запроса к API..')
    params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        response = requests.get(**params)
        logger.debug('Отправлен запрос к API-сервису')
    except Exception as error:
        logger.error(f'Ошибка отправки запроса: {error}')
    if response.status_code != HTTPStatus.OK:
        logger.error(f'Неверный код ответа. '
                     f'Получен код: {response.status_code}')
        raise requests.exceptions.RequestException(
            f'Неверный код ответа. Получен код: {response.status_code}.'
        )
    return response.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    logging.info('Проверка ответа API..')
    if not isinstance(response, dict):
        logger.error('Ответ API не соответствует типу dict')
        raise TypeError('Ответ API не соответствует типу dict')
    try:
        homeworks = response['homeworks']
        if not homeworks:
            logger.debug('Домашних работ на проверке нет')
            raise exceptions.HomeworkNotFound('Домашних работ на проверке нет')
    except KeyError as error:
        logger.error(error)
        raise KeyError('В ответе API нет ключа "homeworks"')
    if not isinstance(homeworks, list):
        logger.error('"homeworks" не является списком')
        raise TypeError('"homeworks" не является списком')
    return homeworks


def parse_status(homework):
    """Получение статуса домашней работы."""
    logging.info('Получение статуса домашней работы..')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logger.error('"homework_name" отсутствует в словаре')
        raise KeyError('"homework_name" отсутствует в словаре')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        logger.error('"homework_status" отсутствует в словаре')
        raise KeyError('"homework_status" отсутствует в словаре')
    logger.debug('Получен статус домашней работы')
    return ('Изменился статус проверки работы "{homework_name}". {verdict}'
            ).format(homework_name=homework_name,
                     verdict=HOMEWORK_VERDICTS[homework_status]
                     )


def main():
    """Основная логика работы бота."""
    logger.info('Запуск бота..')
    if check_tokens():
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            try:
                homework = check_response(response)[0]
                if check_response(response):
                    message = parse_status(homework)
                    if message != last_message:
                        send_message(bot, message)
                        last_message = message
                    else:
                        logger.debug('Статус домашней работы не изменился')
            except Exception as exception:
                message = f'{exception}'
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
            raise error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
