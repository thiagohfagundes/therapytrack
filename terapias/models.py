from django.db import models
from datetime import date
from usuario.models import Crianca
from .variaveis_categoricas import TIPOS_PROFISSIONAL, TIPOS_EVENTO, TIPOS_PERIODICIDADE, TIPOS_DIA_SEMANA

class Clinica(models.Model):
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    criado_por = models.ForeignKey('auth.User', on_delete=models.CASCADE, default='auth.User')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class Profissional(models.Model):
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS_PROFISSIONAL)
    especialidade = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    criado_por = models.ForeignKey('auth.User', on_delete=models.CASCADE, default='auth.User')
    data_criacao = models.DateTimeField(auto_now_add=True)
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='profissionais', blank=True, null=True)

    def __str__(self):
        return self.nome

class Rotina(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)
    crianca = models.ForeignKey(Crianca, on_delete=models.CASCADE, related_name='rotinas')
    data_inicio = models.DateField(default=date.today, blank=True)
    data_termino = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey('auth.User', on_delete=models.CASCADE, default='auth.User')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome if self.nome else f"Rotina {self.id} de {self.crianca.nome}"

class RotinaItem(models.Model):
    nome_evento = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)
    periodicidade = models.CharField(max_length=50, choices=TIPOS_PERIODICIDADE)
    dias_semana = models.CharField(max_length=50, choices=TIPOS_DIA_SEMANA, null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)
    duracao = models.DurationField(null=True, blank=True)
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE, related_name='rotinas_itens', blank=True, null=True)
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='rotinas_itens', blank=True, null=True)
    rotina = models.ForeignKey(Rotina, on_delete=models.CASCADE, related_name='rotinas_itens')
    criado_por = models.ForeignKey('auth.User', on_delete=models.CASCADE, default='auth.User')
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Item de {self.rotina.nome} - {self.descricao}"
    
class Evento(models.Model):
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPOS_EVENTO)
    data_evento = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)
    duracao = models.DurationField(null=True, blank=True)
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE, related_name='eventos', blank=True, null=True)
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='eventos', blank=True, null=True)
    crianca = models.ForeignKey(Crianca, on_delete=models.CASCADE, related_name='eventos')
    notas = models.TextField(blank=True, null=True)
    presenca_confirmada = models.BooleanField(default=False)
    criado_por = models.ForeignKey('auth.User', on_delete=models.CASCADE, default='auth.User')
    data_criacao = models.DateTimeField(auto_now_add=True)
    origem_rotina_item = models.ForeignKey(
        "RotinaItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="eventos_gerados"
    )

    def __str__(self):
        return f"Evento de {self.crianca} com {self.profissional or '—'} em {self.data_evento}"