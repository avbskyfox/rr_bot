import configparser
import environ

env = environ.Env()
creds = configparser.ConfigParser()
creds.read('tokens.ini')
tokens = creds['TOKENS']

BACKEND = 'rr_backend.basen'

DEFAULT_CURENCY = 'RUR'

TELEGRAM_API_TOKEN = env('TELEGRAM_API_TOKEN')
DADATA_TOKEN = env('DADATA_TOKEN')
APIEGRN_TOKEN = env('APIEGRN_TOKEN')
BASE_N_TOKEN = env('BASE_N_TOKEN')
FGIS_EGRN_TOKEN = env('FGIS_EGRN_TOKEN')
TINKOFF_TERMINAL = env('TINKOFF_TERMINAL')
TINKOFF_PASSWORD = env('TINKOFF_PASSWORD')
