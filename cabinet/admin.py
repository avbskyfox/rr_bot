from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Curency)
admin.site.register(Purse)
admin.site.register(ExcerptType)
admin.site.register(Service)
admin.site.register(Order)
admin.site.register(Excerpt)


class BillAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        if obj: # when editing an object
            return ('number', 'user', 'amount', 'curency', 'price', 'payment', 'created_at', 'is_payed')
        return self.readonly_fields

admin.site.register(Bill, BillAdmin)

