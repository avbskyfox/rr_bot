from django.contrib import admin
from .models import *

# Register your models here.


class TicketModelAdmin(admin.ModelAdmin):
    list_filter = ('closed', )


admin.site.register(Ticket, TicketModelAdmin)
admin.site.register(Review)
