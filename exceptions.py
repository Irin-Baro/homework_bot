class UnavailableTokens(Exception):
    """Не доступны переменные окружения."""

    pass


class UnavailableEndpoint(Exception):
    """Ошибка запроса к эндпоинту API-сервиса."""

    pass


class InvalidResponseCode(Exception):
    """Неверный код ответа."""

    pass


class ResponseDatаError(Exception):
    """Ошибка ответа API-сервиса."""

    pass


class NoCurrentDateKey(Exception):
    """В ответе API нет ключа 'current_date'."""

    pass
