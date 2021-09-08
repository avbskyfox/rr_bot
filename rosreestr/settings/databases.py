from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEVELOP_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

PRODUCTION_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'rosreestr_db',
        'USER': 'web',
        'PASSWORD': 'gqqw14d6DY%34y',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
