from rr_telebot.backend_interface import RossreestrInterface
import random

random.seed()


class TestBackend(RossreestrInterface):
    def address_by_number(self, nuber):
        print(nuber)
        return {'success': 1, 'data': {'number': '22:11:2134:1234', 'address': 'Екатеринбург, ул. Ленина д. 1'}}

    def number_by_address(self, address):
        print(address)
        rnd = random.randint(1, 2)
        if rnd == 1:
            return {'success': 1, 'data': {'number': '22:11:2134:1234', 'address': 'Екатеринбург, ул. Ленина д. 1'}}
        elif rnd == 2:
            return {'success': 0, 'data': None, 'message': 'Слишком много вариантов, уточните адресс'}

    def get_doc_type1(self, query):
        print(query)
        return {'success': 1, 'message': 'сообщение об успехе'}

    def get_doc_type2(self, query):
        print(query)
        return {'success': 1, 'message': 'сообщение об успехе'}
