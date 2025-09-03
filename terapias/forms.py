from django import forms
from .models import Clinica, Evento, Profissional, Clinica, Rotina, RotinaItem
from datetime import datetime, timedelta
from usuario.models import Crianca
from datetime import date
from .variaveis_categoricas import TIPOS_PERIODICIDADE, TIPOS_DIA_SEMANA

class ClinicaForm(forms.ModelForm):
    class Meta:
        model = Clinica
        # 'criado_por' e 'data_criacao' não vão para o form
        fields = ["nome", "endereco", "telefone"]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Clínica ABC"}),
            "endereco": forms.TextInput(attrs={"placeholder": "Rua, número, bairro – cidade/UF"}),
            "telefone": forms.TextInput(attrs={"placeholder": "(11) 99999-9999"}),
        }
        labels = {
            "nome": "Nome da clínica",
            "endereco": "Endereço",
            "telefone": "Telefone",
        }

class ProfissionalForm(forms.ModelForm):
    class Meta:
        model = Profissional
        # 'criado_por' e 'data_criacao' são automáticos
        fields = ["nome", "tipo", "especialidade", "telefone", "email", "clinica"]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Maria Souza"}),
            "tipo": forms.Select(),  # usa as choices do model (TIPOS_PROFISSIONAL)
            "especialidade": forms.TextInput(attrs={"placeholder": "Ex.: Fonoaudiologia"}),
            "telefone": forms.TextInput(attrs={"placeholder": "(11) 99999-9999"}),
            "email": forms.EmailInput(attrs={"placeholder": "profissional@exemplo.com"}),
            "clinica": forms.Select(),
        }
        labels = {
            "nome": "Nome",
            "tipo": "Tipo",
            "especialidade": "Especialidade",
            "telefone": "Telefone",
            "email": "E-mail",
            "clinica": "Clínica (opcional)",
        }

    # opcional: se quiser filtrar as clínicas (ex.: por usuário) no futuro
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["clinica"].required = False
        self.fields["clinica"].queryset = Clinica.objects.all().order_by("nome")

class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        # duração e campos de sistema ficam fora do form
        fields = [
            "nome", "tipo", "data_evento", "hora_inicio", "hora_fim",
            "crianca", "profissional", "clinica", "notas",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Adicionar título", "class": "titulo-input"}),
            "data_evento": forms.DateInput(attrs={"type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time", "step": 300}),
            "hora_fim": forms.TimeInput(attrs={"type": "time", "step": 300}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "nome": "Título",
            "tipo": "Tipo",
            "data_evento": "Data",
            "hora_inicio": "Início",
            "hora_fim": "Término",
            "crianca": "Criança",
            "profissional": "Profissional (opcional)",
            "clinica": "Clínica (opcional)",
            "notas": "Notas (opcional)",
        }

    # precisamos do request para filtrar as crianças do usuário
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # filtra crianças do responsável logado
        if self.request and not self.request.user.is_superuser:
            self.fields["crianca"].queryset = Crianca.objects.filter(
                responsavel=self.request.user
            ).order_by("nome")

        self.fields["profissional"].required = False
        self.fields["clinica"].required = False

        # se o usuário tiver só uma criança, pré-seleciona
        qs_criancas = self.fields["crianca"].queryset
        if qs_criancas.count() == 1 and not self.is_bound:
            self.fields["crianca"].initial = qs_criancas.first()

    def clean(self):
        cleaned = super().clean()
        data_evento = cleaned.get("data_evento")
        inicio = cleaned.get("hora_inicio")
        fim = cleaned.get("hora_fim")

        # exigir ambos os horários (comportamento "Google")
        if not inicio or not fim:
            raise forms.ValidationError("Preencha horário de início e término.")

        # mesma data: término deve ser depois do início
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError("O horário de término deve ser após o início.")
        return cleaned

    def save(self, commit=True):
        """Calcula a duração automaticamente (não aparece no form)."""
        obj: Evento = super().save(commit=False)
        if obj.hora_inicio and obj.hora_fim and obj.data_evento:
            dt_inicio = datetime.combine(obj.data_evento, obj.hora_inicio)
            dt_fim = datetime.combine(obj.data_evento, obj.hora_fim)
            obj.duracao = dt_fim - dt_inicio  # timedelta
        if commit:
            obj.save()
            self.save_m2m()
        return obj
    
class RotinaForm(forms.ModelForm):
    class Meta:
        model = Rotina
        fields = ["nome", "descricao", "crianca", "data_termino"]
        widgets = {
            "data_termino": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "nome": "Nome da rotina",
            "descricao": "Descrição",
            "crianca": "Criança",
            "data_termino": "Data de término (opcional)",
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # ⚠️ Nada de periodicidade/dia/hora aqui.
        if request and not getattr(request.user, "is_superuser", False):
            self.fields["crianca"].queryset = Crianca.objects.filter(
                responsavel=request.user
            ).order_by("nome")


class RotinaItemForm(forms.ModelForm):
    class Meta:
        model = RotinaItem
        fields = [
            "nome_evento", "descricao", "periodicidade", "dias_semana",
            "hora_inicio", "hora_fim", "profissional", "clinica"
        ]
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time", "step": 300}),
            "hora_fim": forms.TimeInput(attrs={"type": "time", "step": 300}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "nome_evento": "Título",
            "descricao": "Descrição (opcional)",
            "periodicidade": "Periodicidade",
            "dias_semana": "Dia da semana",
            "hora_inicio": "Início",
            "hora_fim": "Término",
            "profissional": "Profissional (opcional)",
            "clinica": "Clínica (opcional)",
        }

    def __init__(self, *args, **kwargs):
        d_semana = kwargs.pop("dia_semana", None)   # "segunda" | "terca" | ...
        hora_ini = kwargs.pop("hora_ini", None)     # "14:00"
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # defaults seguros (só se o campo existir)
        if not self.is_bound:
            fld = self.fields.get("periodicidade")
            if fld:
                fld.initial = "semanal"
            if d_semana and "dias_semana" in self.fields:
                self.fields["dias_semana"].initial = d_semana
            if hora_ini and "hora_inicio" in self.fields:
                self.fields["hora_inicio"].initial = hora_ini

        # filtrar querysets apenas se os campos existirem
        if request and not request.user.is_superuser:
            if "profissional" in self.fields:
                self.fields["profissional"].queryset = Profissional.objects.order_by("nome")
            if "clinica" in self.fields:
                self.fields["clinica"].queryset = Clinica.objects.order_by("nome")

    def clean(self):
        cleaned = super().clean()
        ini = cleaned.get("hora_inicio")
        fim = cleaned.get("hora_fim")
        if not ini or not fim:
            raise forms.ValidationError("Preencha horário de início e término.")
        if fim <= ini:
            raise forms.ValidationError("O término deve ser após o início.")
        return cleaned

    def save(self, commit=True):
        obj: RotinaItem = super().save(commit=False)
        if obj.hora_inicio and obj.hora_fim:
            dt_i = datetime.combine(datetime.today().date(), obj.hora_inicio)
            dt_f = datetime.combine(datetime.today().date(), obj.hora_fim)
            obj.duracao = dt_f - dt_i
        if commit:
            obj.save()
            self.save_m2m()
        return obj
    
class RotinaItemBulkForm(forms.Form):
    nome_evento = forms.CharField(label="Título", max_length=100)
    periodicidade = forms.ChoiceField(choices=TIPOS_PERIODICIDADE, initial="semanal", label="Periodicidade")
    dias_semana_multi = forms.MultipleChoiceField(
        choices=TIPOS_DIA_SEMANA,
        widget=forms.CheckboxSelectMultiple,
        label="Dias da semana",
    )
    hora_inicio = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time", "step": 300}), label="Início")
    hora_fim = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time", "step": 300}), label="Término")
    profissional = forms.ModelChoiceField(queryset=Profissional.objects.order_by("nome"), required=False, label="Profissional")
    clinica = forms.ModelChoiceField(queryset=Clinica.objects.order_by("nome"), required=False, label="Clínica")
    descricao = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Descrição")

    def clean(self):
        cd = super().clean()
        ini, fim = cd.get("hora_inicio"), cd.get("hora_fim")
        if not ini or not fim:
            raise forms.ValidationError("Preencha início e término.")
        if fim <= ini:
            raise forms.ValidationError("O término deve ser após o início.")
        if not cd.get("dias_semana_multi"):
            raise forms.ValidationError("Selecione pelo menos um dia da semana.")
        return cd

    def save_many(self, rotina, user):
        """
        Cria um RotinaItem para cada dia selecionado.
        Evita duplicados (mesmo dia+horário na mesma rotina).
        Retorna (criados, pulados).
        """
        criados, pulados = [], []
        nome = self.cleaned_data["nome_evento"]
        periodicidade = self.cleaned_data["periodicidade"]
        dias = self.cleaned_data["dias_semana_multi"]
        ini = self.cleaned_data["hora_inicio"]
        fim = self.cleaned_data["hora_fim"]
        prof = self.cleaned_data.get("profissional")
        clin = self.cleaned_data.get("clinica")
        desc = self.cleaned_data.get("descricao") or ""

        dur = datetime.combine(date.today(), fim) - datetime.combine(date.today(), ini)

        for d in dias:
            existe = RotinaItem.objects.filter(
                rotina=rotina, dias_semana=d, hora_inicio=ini, hora_fim=fim
            ).exists()
            if existe:
                pulados.append(d)
                continue

            obj = RotinaItem(
                nome_evento=nome,
                descricao=desc,
                periodicidade=periodicidade,
                dias_semana=d,
                hora_inicio=ini,
                hora_fim=fim,
                duracao=dur,
                profissional=prof,
                clinica=clin,
                rotina=rotina,
                criado_por=user,
            )
            obj.save()
            criados.append(obj)

        return criados, pulados    