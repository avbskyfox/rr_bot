import requests
import aiohttp
import os
from loguru import logger
import asyncio
from yarl import URL
import json
from rr_backend.dadata import DadataClient
from rr_backend.rosreestr import RosreestrClient
from rr_backend.apiegrn import ApiEgrnClient


class Backend:

    @staticmethod
    async def async_find_adress(address: str):
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
    async def async_objects_by_address(dadata):
        objects = await RosreestrClient.find_objects(dadata)
        logger.debug(objects)

        async def obj_filter(arg):
            logger.debug(item)
            asd = await DadataClient.find_address(arg['addressNotes'])
            logger.debug(asd)
            return (asd[0]['value']) == dadata['value']

        filtred_objects = []
        for item in objects:
            if await obj_filter(item):
                filtred_objects.append(item)

        logger.debug(filtred_objects)

        result = []

        for item in filtred_objects:
            info = await ApiEgrnClient.get_info(item['nobjectCn'])
            result.append(info)

        logger.debug(result)
        return result

    @staticmethod
    async def async_object_by_number(number: str):
        pass

    @staticmethod
    def get_doc_type1(query):
        pass

    @staticmethod
    def get_doc_type2(self, query):
        pass


