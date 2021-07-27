class HttpError(Exception):
    pass


class PaymentCreationError(Exception):
    pass


class PaymentCancelError(Exception):
    pass


class GetStateError(Exception):
    pass