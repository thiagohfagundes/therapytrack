from django.contrib import admin
from .models import Evento, Profissional, Clinica, Rotina, RotinaItem

# Register your models here.
admin.site.register(Evento)
admin.site.register(Profissional)
admin.site.register(Clinica)
admin.site.register(Rotina)
admin.site.register(RotinaItem)
