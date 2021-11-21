import graphene
from .models import User
from graphene_django import DjangoObjectType
from loguru import logger


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'telegram_id', 'phone_number')


class Query(graphene.ObjectType):
    all_users = graphene.List(UserType)

    def resolve_all_users(self, info):
        return User.objects.all()


schema = graphene.Schema(query=Query)