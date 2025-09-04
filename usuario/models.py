from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Crianca(models.Model):
    nome = models.CharField(max_length=100)
    condicao = models.CharField(max_length=100)
    data_nascimento = models.DateField()
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE, default='auth.User', related_name='criancas')
    telefone_contato = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return self.nome