import re

import aiohttp
from bs4 import BeautifulSoup as BS
from loguru import logger

REQUEST_URL = 'https://rosreestr.gov.ru/wps/portal/online_request'
MACRO_REGIONS_URL = 'http://rosreestr.ru/api/online/macro_regions'
REGIONS_URL = 'http://rosreestr.ru/api/online/regions/'
SATTLMENT_URL = 'https://rosreestr.gov.ru/wps/PA_RRORSrviceExtended/Servlet/ChildsRegionController?settlement_type=\
set0&add_settlement_type=false&parentId='

city_type_map = {
    'город': 'set4',
    'деревня': 'set5',
    'село': 'set22',
    'населенный пункт': 'set14',
    'поселок сельского типа': 'set15',
    'станция': 'set2'
}

street_type_map = {
    'улица': 'str1',
    'переулок': 'str2',
    'проспект': 'str3',
    'площадь': 'str4',
    'микрорайон': 'str5',
    'аллея': 'str6',
    'бульвар': 'str7',
    'аал': 'str8',
    'аул': 'str9',
    'въезд': 'str10',
    'набережная': 'str30',
    'парк': 'str33',
    'переезд': 'str34',
    'проезд': 'str43'
}


class RosrrestrPageError(Exception):
    pass


async def post_async(url, params=None, data=None, json=False):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, json=data) as response:
            if response.status == 503:
                raise RosrrestrPageError
            if json:
                return await response.json()
            else:
                return await response.text()


async def get_async(url, params=None, json=False):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 503:
                raise RosrrestrPageError
            if json:
                return await response.json()
            else:
                return await response.text()


def get_id(key, staff):
    """ Принимает на вход словарь, который вернул росреестр и ищет в нем указанный
    ключ, если находит - возращает его id, если нет - False """
    key = key.strip().lower()
    for item in staff:
        if key in item['name'].lower():
            return item['id']
    raise KeyError(f'Элемент {key} не найден в словаре')


async def get_request_url():
    """ Получает 2 токена с страницы поиска и формирует из них ссылку для запроса """
    response = await get_async(REQUEST_URL)
    soup = BS(response, 'lxml')
    first_part = soup.find('base').get('href')
    token = soup.find('form', method='post').get('action')
    return first_part + token


async def find_object(dadata: dict):
    data = dadata['data']
    logger.debug(data)
    result = await get_adress(
        macro=data['region'],
        region=data['city'] or data['area'],
        city=data['city'] or data['settlment'],
        city_type=city_type_map[data['city_type_full'] or data['settlement_type_full']],
        street=data['street'],
        street_type=street_type_map[data['street_type_full']],
        house=data['house'] or '',
        building=data['block'] or '',
        structure='',
        apartment=data['flat']
    )
    logger.debug(result)
    return [{'nobjectCn': item['Кадастровый номер:'], 'addressNotes': item['Адрес (местоположение):']} for item in result]


async def get_adress(macro, region, city, city_type, street, street_type, house, building, structure, apartment):
    """ Основная функция, принимает на вход адрес и возвращает список из словарей
    с данными об этом адресе """
    url = await get_request_url()
    # получаем необходимые id объектов
    macro_id = get_id(macro, await get_async(MACRO_REGIONS_URL, json=True))
    logger.debug(macro_id)
    region_id = get_id(region, await get_async(REGIONS_URL + str(macro_id), json=True))
    logger.debug(region_id)
    settlement_list = await get_async(SATTLMENT_URL + str(region_id))
    refactored_settlement_list = [{'name': s.split(';')[1], 'id': s.split(';')[0]} for s in
                                  settlement_list.splitlines()]
    logger.debug(refactored_settlement_list)
    settlement_id = get_id(city, refactored_settlement_list)
    logger.debug(settlement_id)

    # делаем запрос
    payload = {
        "search_action": "true",
        "subject": "",
        "region": "",
        "settlement": str(settlement_id),
        "cad_num": "",
        "start_position": "59",
        "obj_num": "",
        "old_number": "",
        "search_type": "ADDRESS",
        "src_object": "0",
        "subject_id": str(macro_id),
        "region_id": str(region_id),
        "settlement_id": str(settlement_id),
        "settlement_type": str(city_type),
        "street": str(street),
        "street_type": str(street_type),
        "house": str(house),
        "building": str(building),
        "structure": str(structure),
        "apartment": str(apartment),
        "right_reg": "",
        "encumbrance_reg": ""
    }
    logger.debug(payload)
    response = await post_async(url, params=payload)
    logger.debug(url)
    # парсим список ссылок на объекты
    soup = BS(response, 'lxml')
    trs = soup.find_all('tr', onmouseout=True)
    urls = [tr.find('a').get('href') for tr in trs]
    logger.debug(urls)
    # print(*[tr.find('td').text.strip() for tr in trs], sep='\n')
    # print(*urls, sep='\n')

    data = []

    for item_url in urls:
        soup = BS(await get_async(url.split('p0')[0] + item_url), 'lxml')
        # print(url.split('p0')[0] + item_url)
        trs = [tr.find_all('td') for tr in soup.find_all('tr')]
        trs = [tr for tr in trs if len(tr) == 2]
        trs = {tr[0].text.strip(): tr[1].text.strip() for tr in trs if tr[0] and tr[0].text.strip()}

        if 'Право' in trs:
            trs.pop('Право')

        try:
            tr = soup.find('font', text=re.compile(r'[\s]*Права и ограничения[\s]*'))
            tr = tr.find_parent('tr').findNext('table').find('table').text.strip().replace('\xa0', '')
            tr = re.sub(r'[\n\r]+', '\n', tr)
            tr = re.sub(r'[ ]+', ' ', tr)
        except AttributeError:
            tr = ''

        trs.update({'Права и ограничения': tr})
        data.append(trs)
    return data
