import json

from django.http import HttpResponse, JsonResponse
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


class ApiView(View):
    def get(self, request, *args, **kwargs):
        logger.debug(request.headers)
        # logger.debug(request.params)
        logger.debug(request.body)
        data = {
            'data': {
                'type': 'account',
                'id': 1,
                'attributes': {
                    'username': 'hui',
                    'telegram-id': 'asda',
                    'email': 'asdasd@asd.er',
                }
            }
        }
        response = JsonResponse(data)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
        logger.debug(response.content)
        return response

    # def post(self, request, *args, **kwargs):
    #     logger.debug(request.headers)
    #     logger.debug(request.params)
    #     logger.debug(request.body)
    #     response = JsonResponse({'data': {'username': 'hui', 'id': 1, 'telegram_id': 'asda', 'email': 'asdasd@asd.er'}})
    #     response["Access-Control-Allow-Origin"] = "*"
    #     response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    #     response["Access-Control-Max-Age"] = "1000"
    #     response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
    #     return response
