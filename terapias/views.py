from datetime import time
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, DeleteView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from .models import Clinica, Profissional, Evento, Rotina, RotinaItem
from .forms import ClinicaForm, ProfissionalForm, EventoForm, RotinaForm, RotinaItemBulkForm
from .variaveis_categoricas import TIPOS_DIA_SEMANA

# ------------------------- CRUD DE CLINICAS -----------------------
class ClinicaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Clinica
    form_class = ClinicaForm
    template_name = "terapias/telas_criacao/criar_clinica.html"
    success_message = "Clínica criada com sucesso!"
    # troque depois para a lista/detalhe de clínicas quando existir
    success_url = reverse_lazy("terapias:lista-clinicas")

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)
    
class ClinicaListView(LoginRequiredMixin, ListView):
    model = Clinica
    template_name = "terapias/telas_lista/lista_clinicas.html"
    context_object_name = "clinicas"
    paginate_by = 10
    ordering = ["nome"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(criado_por=self.request.user) # modificar aqui

        # contadores já anotados para evitar N+1 queries no template
        qs = qs.annotate(
            n_profissionais=Count("profissionais", distinct=True),
            n_eventos=Count("eventos", distinct=True),
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(endereco__icontains=q)
                | Q(telefone__icontains=q)
            )
        return qs

class ClinicaDetailView(LoginRequiredMixin, DetailView):
    model = Clinica
    template_name = "terapias/telas_detalhes/detalhes_clinicas.html"
    context_object_name = "clinica"

class ClinicaDeleteView(LoginRequiredMixin, DeleteView):
    model = Clinica
    template_name = "terapias/telas_deletar/clinica_deletar.html"
    success_url = reverse_lazy("terapias:lista-clinicas")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(criado_por=self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, _('Clínica “%(nome)s” excluída com sucesso.') % {"nome": obj.nome})
        return super().delete(request, *args, **kwargs)
    
class ClinicaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Clinica
    form_class = ClinicaForm
    template_name = "terapias/telas_editar/clinica_editar.html"
    success_message = "Clínica atualizada com sucesso!"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(criado_por=self.request.user)

    def get_success_url(self):
        return reverse("terapias:clinica-detail", args=[self.object.pk])

# ------------------------- CRUD DE PROFISSIONAIS -----------------------
    
class ProfissionalCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Profissional
    form_class = ProfissionalForm
    template_name = "terapias/telas_criacao/criar_profissional.html"
    success_message = "Profissional criado com sucesso!"
    success_url = reverse_lazy("terapias:lista-profissionais")  # troque depois para a lista/detalhe

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)
    
class ProfissionalListView(LoginRequiredMixin, ListView):
    model = Profissional
    template_name = "terapias/telas_lista/lista_profissionais.html"
    context_object_name = "profissionais"
    paginate_by = 10  # ajuste como preferir
    ordering = ["nome"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(criado_por=self.request.user)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(especialidade__icontains=q)
                | Q(email__icontains=q)
                | Q(telefone__icontains=q)
            )
        return qs

class ProfissionalDetailView(LoginRequiredMixin, DetailView):
    model = Profissional
    template_name = "terapias/telas_detalhes/detalhes_profissionais.html"
    context_object_name = "profissional"

class ProfissionalDeleteView(LoginRequiredMixin, DeleteView):
    model = Profissional
    template_name = "terapias/telas_deletar/profissional_deletar.html"
    success_url = reverse_lazy("terapias:lista-profissionais")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(criado_por=self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, _('Profissional “%(nome)s” excluído com sucesso.') % {"nome": obj.nome})
        return super().delete(request, *args, **kwargs)
    
class ProfissionalUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Profissional
    form_class = ProfissionalForm
    template_name = "terapias/telas_editar/profissional_editar.html"
    success_message = "Profissional atualizado com sucesso!"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(criado_por=self.request.user)

    def get_success_url(self):
        return reverse("terapias:profissional-detail", args=[self.object.pk])
    
# -------------------------- CRUD DE EVENTOS ------------------------------
class EventoCriarView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "index.html"  # modal + fallback de página
    success_message = "Evento criado com sucesso!" 

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request  # para filtrar crianças no form
        return kwargs

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # fecha o modal e volta para a página de origem quando possível
        return self.request.GET.get("next") or self.request.META.get("HTTP_REFERER") or reverse_lazy("admin:index")

# ----------------------- CRUD ROTINAS ---------------------------
class RotinaCriarView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Rotina
    form_class = RotinaForm
    template_name = "terapias/telas_criacao/rotina_criar.html"
    success_message = "Rotina criada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("terapias:planejar-rotina", args=[self.object.pk])

def _grade_ctx(rotina):
    """Contexto padrão da grade semanal."""
    horas = [time(h, 0) for h in range(8, 20)]  # 08:00..19:00
    dias = list(TIPOS_DIA_SEMANA)               # [('segunda','Segunda-feira'), ...]
    itens = RotinaItem.objects.filter(rotina=rotina).order_by("hora_inicio")
    return {"horas": horas, "dias": dias, "itens": itens}

class RotinaPlanejarView(LoginRequiredMixin, DetailView):
    model = Rotina
    template_name = "terapias/telas_criacao/rotina_planejar.html"
    context_object_name = "rotina"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_grade_ctx(self.object))
        return ctx

def _grade_ctx(rotina):
    horas = [time(h, 0) for h in range(8, 20)]
    dias = list(TIPOS_DIA_SEMANA)
    itens = RotinaItem.objects.filter(rotina=rotina).order_by("hora_inicio")
    return {"horas": horas, "dias": dias, "itens": itens}

class RotinaItemModalView(LoginRequiredMixin, View):
    dialog_tpl = "terapias/partials/rotina_item_dialog.html"
    grade_tpl = "terapias/partials/rotina_grade.html"

    def get(self, request, pk):
        rotina = get_object_or_404(Rotina, pk=pk)
        d = request.GET.get("d")  # "segunda" etc. (opcional)
        t = request.GET.get("t")  # "14:00"     (opcional)
        initial = {}
        if d: initial["dias_semana_multi"] = [d]
        if t: initial["hora_inicio"] = t
        form = RotinaItemBulkForm(initial=initial)
        html = render_to_string(self.dialog_tpl, {"form": form, "rotina": rotina}, request=request)
        return HttpResponse(html)

    def post(self, request, pk):
        rotina = get_object_or_404(Rotina, pk=pk)
        form = RotinaItemBulkForm(request.POST)
        if form.is_valid():
            criados, pulados = form.save_many(rotina, request.user)

            grade_html = render_to_string(
                self.grade_tpl, {"rotina": rotina, **_grade_ctx(rotina), "oob": True}, request=request
            )

            # toast simples (opcional) via OOB
            msg = f"Criados {len(criados)} item(ns)."
            if pulados:
                msg += f" Pulados {len(pulados)} por conflito."
            toast = f'<div id="toast" hx-swap-oob="true" style="position:fixed;bottom:16px;right:16px;background:#111;color:#fff;padding:8px 12px;border-radius:6px;">{msg}</div>'

            return HttpResponse(grade_html + '<div id="modal"></div>' + toast)

        html = render_to_string(self.dialog_tpl, {"form": form, "rotina": rotina}, request=request)
        return HttpResponseBadRequest(html)
    
# Create your views here.
@login_required
def index(request):
    return render(request, "index.html")
