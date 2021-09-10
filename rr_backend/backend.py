from loguru import logger

from rr_backend.apiegrn import ApiEgrnClient
from rr_backend.dadata import DadataClient
from rr_backend.rosreestr import RosreestrClient, NotFound
from rr_backend.basen import BasenClient
from rr_backend.rosreestr_scraper.scraper import find_object
from rr_telebot.tasks_notifier import send_progress_message, delete_last_progress_message


class Backend:
    @staticmethod
    async def async_find_adress(address: str, chat_id):
        variants = await DadataClient.find_address(address)
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

        return variants

    @staticmethod
    async def async_objects_by_address(dadata, chat_id):
        logger.debug(dadata)

        async def obj_filter(arg):
            logger.debug(item)
            asd = await DadataClient.find_address(arg['addressNotes'])
            if len(asd) == 0:
                return False
            logger.debug(asd[0]['value'])
            logger.debug(dadata['value'])
            return (asd[0]['value']) == dadata['value']

        try:
            send_progress_message.delay(chat_id, 'опрашиваем сервис Росреестра...')
            objects = await RosreestrClient.find_objects(dadata)
            logger.debug(objects)
            filtred_objects = []
            for item in objects:
                if await obj_filter(item):
                        filtred_objects.append(item)
            logger.debug(filtred_objects)
            result = []
            for item in filtred_objects:
                send_progress_message.delay(chat_id, 'ищем подробную информацию об объекте...')
                info = await ApiEgrnClient.get_info(item['nobjectCn'])
                result.append(info)
        except NotFound:
            send_progress_message.delay(chat_id, 'парсим страничку поиска Росреестра...')
            result = await find_object(dadata)
            for item in result:
                send_progress_message.delay(chat_id, 'ищем подробную информацию об объекте...')
                info = await ApiEgrnClient.get_info(item['nobjectCn'])
                result.append(info)
        logger.debug(result)
        if len(result) != 0:
            delete_last_progress_message.delay(chat_id)
            return result
        else:
            return result

    @staticmethod
    async def async_object_by_number(number: str, chat_id):
        logger.debug(number)
        send_progress_message.delay(chat_id, 'опрашиваем сервис Росреестра...')
        result = await ApiEgrnClient.get_info(number)
        delete_last_progress_message(chat_id)
        return result

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
