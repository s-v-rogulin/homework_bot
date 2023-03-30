class ResponseError(Exception):
    """.Недоступен сервис Яндекс.Практикум ! код ошибки !=200 !)."""


class EndpointUnavailableError(Exception):
    """Недоступен сервис Яндекс.Практикум ! код ошибки 404 !."""


class RequestError(Exception):
    """Ошибка при запросе к сервису Яндекс.Практикум."""


class StatusError(Exception):
    """Ошибка статуса для homeworks."""
