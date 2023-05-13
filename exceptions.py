class UnavailableTokens(Exception):
    """Не доступны переменные окружения."""

    pass


class MessageSendingError(Exception):
    """Ошибка отправки сообщения."""

    pass


class HomeworkNotFound(Exception):
    """В ответе API нет домашних работ."""

    pass
