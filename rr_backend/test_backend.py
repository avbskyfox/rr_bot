from rr_backend.backend_interface import RossreestrInterface
import random

random.seed()


class TestBackend(RossreestrInterface):
    def address_by_number(self, nuber):
        return {'success': 1, 'data': {'number': '22:11:2134:1234', 'address': 'Екатеринбург, ул. Ленина д. 1'}}

    def number_by_address(self, address):
        rnd = random.randint(1, 2)
        if rnd == 1:
            return {'success': 1, 'data': {'number': '22:11:2134:1234', 'address': 'Екатеринбург, ул. Ленина д. 1'}}
        elif rnd == 2:
            return {'success': 0, 'data': None, 'message': 'Слишком много вариантов, уточните адресс'}

    def get_type1(self, query):
        return {'success': True, 'message': 'сообщение об успехе', 'data': {'number': 1234}}

    def get_type2(self, query):
        return {'success': True, 'message': 'сообщение об успехе',  'data': {'number': 1234}}


class AsyncTestBackend(RossreestrInterface):
    async def address_by_number(self, nuber):
        return {'success': 1, 'data': {'number': '22:11:2134:1234', 'address': 'Екатеринбург, ул. Ленина д. 1'}}

    async def number_by_address(self, address):
        rnd = random.randint(1, 2)
        if rnd == 1:
            return {'success': 1, 'data': {'number': '22:11:2134:1234', 'address': 'Екатеринбург, ул. Ленина д. 1'}}
        elif rnd == 2:
            return {'success': 0, 'data': None, 'message': 'Слишком много вариантов, уточните адресс'}

    def get_type1(self, query):
        return {'success': True, 'message': 'сообщение об успехе', 'data': {'number': 1234}}

    def get_type2(self, query):
        return {'success': True, 'message': 'сообщение об успехе',  'data': {'number': 1234}}


async_backend = AsyncTestBackend()


def get_type1(**kwargs):
    return async_backend.get_type1(kwargs['number'])


def get_type2(**kwargs):
    return async_backend.get_type2(kwargs['number'])