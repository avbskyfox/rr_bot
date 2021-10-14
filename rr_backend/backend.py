from asyncio import sleep

from asgiref.sync import async_to_sync
from loguru import logger

from rr_backend.apiegrn import ApiEgrnClient
from rr_backend.basen import BasenClient
from rr_backend.dadata import DadataClient
from rr_backend.rosreestr import RosreestrClient, NotFound
from rr_telebot.tasks_notifier import send_progress_message, delete_last_progress_message


class Backend:
    @classmethod
    @async_to_sync
    async def find_adress(cls, address: str, chat_id):
        return await cls.async_find_adress(address, chat_id)

    @staticmethod
    async def async_find_adress(address: str, chat_id):
        send_progress_message.delay(chat_id, 'проверяем адрес...')
        variants = await DadataClient.async_find_address(address)
        # logger.debug(len(variants))
        #
        # def group_bt_street(variants):
        #     logger.debug(variants)
        #     result = {}
        #     for i, item in enumerate(variants):
        #         logger.debug(item)
        #         if item['data']['block'] is None:
        #             if item['data']['street_fias_id'] not in result.keys():
        #                 result[item['data']['street_fias_id']] = [item]
        #             else:
        #                 result[item['data']['street_fias_id']].append(item)
        #             del variants[i]
        #         else:
        #             logger.debug(item)
        #
        #     logger.debug(len(variants))
        #     for key, items in result.items():
        #         lower = items[0]
        #         for item in items:
        #             if item['data']['house'] < lower['data']['house']:
        #                 lower = item
        #         variants.append(lower)
        #
        # group_bt_street(variants)
        delete_last_progress_message.delay(chat_id)
        return variants

    @classmethod
    @async_to_sync
    async def objects_by_address(cls, dadata, chat_id):
        return await cls.async_objects_by_address(dadata, chat_id)

    @classmethod
    async def async_objects_by_address(cls, dadata, chat_id):

        async def obj_filter(arg):
            asd = await DadataClient.async_find_address(arg['addressNotes'])
            if len(asd) == 0:
                return False
            return (asd[0]['value']) == dadata['value']

        try:
            send_progress_message.delay(chat_id, 'опрашиваем Росреестра...')
            objects = await RosreestrClient.find_objects(dadata)
            filtred_objects = []
            for item in objects:
                if await obj_filter(item):
                    filtred_objects.append(item)
            result = []
            for item in filtred_objects:
                try:
                    info = await cls.async_object_by_number(item['nobjectCn'], chat_id)
                    result.append(info)
                except NotFound:
                    pass
            if len(result) == 0:
                raise TimeoutError('не найдена инфомрация ни по одному объекту')
        except NotFound:
            send_progress_message.delay(chat_id, 'ищем информацию...')
            objects = await ApiEgrnClient.search(dadata['value'])
            # objects = await find_object(dadata)
            result = []
            for item in objects:
                info = await cls.async_object_by_number(item['nobjectCn'], chat_id)
                result.append(info)
        if len(result) != 0:
            delete_last_progress_message.delay(chat_id)
            return result
        else:
            return result

    @staticmethod
    async def async_object_by_number(number: str, chat_id):
        send_progress_message.delay(chat_id, 'ищем подробную информацию об объекте')
        found = False
        for i in range(0, 3):
            try:
                result = await ApiEgrnClient.get_info(number)
                found = True
            except NotFound:
                await sleep(3)
            else:
                break
        if not found:
            raise NotFound
        delete_last_progress_message(chat_id)
        return result

    @classmethod
    @async_to_sync
    async def object_by_number(cls, number: str, chat_id):
        return await cls.async_object_by_number(number, chat_id)

    @staticmethod
    def get_doc_type1(cadnum):
        return BasenClient.order_docs(cadnum, 'object_info')

    @staticmethod
    def get_doc_type2(cadnum):
        return BasenClient.order_docs(cadnum, 'ownership')

    @staticmethod
    def get_doc_status(doc_number):
        return BasenClient.check_status(doc_number)

    @staticmethod
    async def async_get_doc_status(doc_number):
        return await BasenClient.async_check_status(doc_number)

    @staticmethod
    def download_doc(doc_number):
        return {'pdf': BasenClient.get_excerpt(doc_number, 'pdf'),
                'zip': BasenClient.get_excerpt(doc_number, 'zip')}
