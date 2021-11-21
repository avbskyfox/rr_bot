import json

from django.http import HttpResponse
from django.views import View
from loguru import logger

from tinkoff_kassa.misc import generate_token
from .models import Bill


# Create your views here.


class TinkoffWebhookView(View):
    def post(self, request, *args, **kwargs):
        logger.debug(request.headers)
        logger.debug(request.body)
        body = json.loads(request.body.decode())
        logger.debug(body)
        data = body
        logger.debug(data)
        token = data.pop('Token', None)
        my_token = generate_token(data)
        logger.debug(token)
        logger.debug(my_token)
        if token == my_token:
            try:
                bill = Bill.objects.get(number=data['OrderId'])
                bill.update_payment()
                return HttpResponse('OK')
            except Bill.DoesNotExist:
                return HttpResponse('NOT FOUND', status=404)
        else:
            logger.warning(f'BAD TOKEN: {request}')
            return HttpResponse('BAD TOKEN', status=403)
