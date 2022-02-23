import json
from rr_backend.rosreestr_scraper.scraper import get_adress
import asyncio


if __name__ == '__main__':
    out1 = asyncio.run(get_adress('Свердловская', 'Екатеринбург', 'Екатеринбург', 'set4', 'Машинная', 'str1', '31в', '', '', '107'))
    # out1 = get_adress('Свердловская', 'Екатеринбург', 'Екатеринбург', 'set4', 'Машинная', 'str1', '31в', '', '', '107')
    # out2 = get_adress('свердловская', 'екатеринбург', 'екатеринбург', 'set4', 'ленина', 'str3', '9', '', '', '')
    # out3 = get_adress('свердловская', 'екатеринбург', 'екатеринбург', 'set4', 'ленина', 'str3', '10', '', '', '')
    print(out1)

    with open('out1.json', 'w', encoding='utf-8') as f:
        json.dump(out1, f, indent=4, ensure_ascii=False)
    # with open('out2.json', 'w', encoding='utf-8') as f:
    #     json.dump(out2, f, indent=4, ensure_ascii=False)
    # with open('out3.json', 'w', encoding='utf-8') as f:
    #     json.dump(out3, f, indent=4, ensure_ascii=False)
