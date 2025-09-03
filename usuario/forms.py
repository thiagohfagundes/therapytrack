from django import forms
from .models import Crianca

class CriancaForm(forms.ModelForm):
    class Meta:
        model = Crianca
        # 'responsavel' será setado na view; não aparece no form
        fields = ["nome", "condicao", "data_nascimento", "telefone_contato"]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "nome": "Nome",
            "condicao": "Condição (diagnóstico)",
            "data_nascimento": "Data de nascimento",
            "telefone_contato": "Telefone de contato",
        }