from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, DeleteView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from datetime import date, datetime, timedelta, time
from calendar import monthrange
from collections import defaultdict

from usuario.models import Crianca
from .models import Clinica, Profissional, Evento, Rotina, RotinaItem
from .forms import ClinicaForm, ProfissionalForm, EventoForm, RotinaForm, RotinaItemBulkForm, RotinaItemForm
from .variaveis_categoricas import TIPOS_DIA_SEMANA
from .services import expandir_rotina_item, sincronizar_eventos_do_item

from .variaveis_categoricas import TIPOS_DIA_SEMANA, TIPOS_PROFISSIONAL

# ------------------------- HELPERS -----------------------
def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())  # 0 = Monday

def _last_day_of_month(y: int, m: int) -> date:
    return date(y, m, monthrange(y, m)[1])

def _duration(ev: Evento) -> timedelta:
    """Retorna a duração do evento (usa campo ou calcula por hora_inicio/fim)."""
    if ev.duracao:
        return ev.duracao
    if ev.hora_inicio and ev.hora_fim:
        base = date.today()
        dt_i = datetime.combine(base, ev.hora_inicio)
        dt_f = datetime.combine(base, ev.hora_fim)
        return dt_f - dt_i
    return timedelta()

def _fmt_td(td: timedelta) -> str:
    """Formata timedelta como 2h30, 45min, etc."""
    total_min = int(td.total_seconds() // 60)
    h, m = divmod(total_min, 60)
    if h and m:
        return f"{h}h{m:02d}"
    if h:
        return f"{h}h"
    return f"{m}min"

# Mapa helper (segunda..domingo)
DIA_KEY_TO_LABEL = dict(TIPOS_DIA_SEMANA)               # 'segunda' -> 'Segunda-feira'
WEEKDAY_TO_KEY = {0: 'segunda', 1: 'terca', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sabado', 6: 'domingo'}
PROF_TIPO_LABEL = dict(TIPOS_PROFISSIONAL)              # 'fonoaudiologo' -> 'Fonoaudiólogo(a)'

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

            # 👇 GERA OS EVENTOS para cada RotinaItem criado
            total_eventos = 0
            for it in criados:
                res = expandir_rotina_item(it)
                total_eventos += res["criadas"]

            grade_html = render_to_string(
                self.grade_tpl, {"rotina": rotina, **_grade_ctx(rotina), "oob": True}, request=request
            )

            msg = f"Criados {len(criados)} item(ns), {total_eventos} evento(s)."
            if pulados:
                msg += f" Itens pulados: {len(pulados)} (conflito dia/horário)."
            toast = f'<div id="toast" hx-swap-oob="true" style="position:fixed;bottom:16px;right:16px;background:#111;color:#fff;padding:8px 12px;border-radius:6px;">{msg}</div>'

            return HttpResponse(grade_html + '<div id="modal"></div>' + toast)

        html = render_to_string(self.dialog_tpl, {"form": form, "rotina": rotina}, request=request)
        return HttpResponseBadRequest(html)
    
def _pode_editar_item(user, item: RotinaItem) -> bool:
    # ajuste a regra se tiver outro modelo de permissão
    if getattr(user, "is_superuser", False):
        return True
    return getattr(item.rotina.crianca, "responsavel_id", None) == user.id


class RotinaItemEditarModalView(LoginRequiredMixin, View):
    """
    GET  -> dialog de edição (form pré-preenchido)
    POST -> salva alterações, ressincroniza eventos e atualiza grade via OOB
    """
    dialog_tpl = "terapias/partials/rotina_item_dialog_editar.html"
    grade_tpl = "terapias/partials/rotina_grade.html"

    def get(self, request, item_id):
        item = get_object_or_404(RotinaItem.objects.select_related("rotina", "rotina__crianca"), pk=item_id)
        if not _pode_editar_item(request.user, item):
            return HttpResponseForbidden("Permissão negada")
        form = RotinaItemForm(instance=item, request=request)
        html = render_to_string(self.dialog_tpl, {"form": form, "item": item, "rotina": item.rotina}, request=request)
        return HttpResponse(html)

    def post(self, request, item_id):
        item = get_object_or_404(RotinaItem.objects.select_related("rotina", "rotina__crianca"), pk=item_id)
        if not _pode_editar_item(request.user, item):
            return HttpResponseForbidden("Permissão negada")
        form = RotinaItemForm(request.POST, instance=item, request=request)
        if form.is_valid():
            item = form.save()
            # ressincroniza eventos futuros deste item
            sincronizar_eventos_do_item(item, apagar_passado=False)

            grade_html = render_to_string(self.grade_tpl, {"rotina": item.rotina, **_grade_ctx(item.rotina), "oob": True}, request=request)
            toast = '<div id="toast" hx-swap-oob="true" style="position:fixed;bottom:16px;right:16px;background:#111;color:#fff;padding:8px 12px;border-radius:6px;">Item atualizado.</div>'
            return HttpResponse(grade_html + '<div id="modal"></div>' + toast)

        html = render_to_string(self.dialog_tpl, {"form": form, "item": item, "rotina": item.rotina}, request=request)
        return HttpResponseBadRequest(html)


class RotinaItemExcluirView(LoginRequiredMixin, View):
    """
    POST -> exclui item, apaga eventos futuros gerados por ele e atualiza grade.
    """
    grade_tpl = "terapias/partials/rotina_grade.html"

    def post(self, request, item_id):
        item = get_object_or_404(RotinaItem.objects.select_related("rotina", "rotina__crianca"), pk=item_id)
        if not _pode_editar_item(request.user, item):
            return HttpResponseForbidden("Permissão negada")

        rotina = item.rotina
        # apaga eventos futuros do item (antes de excluir o item)
        try:
            sincronizar_eventos_do_item(item, apagar_passado=False)  # isso já apaga futuros e reexpande
        except Exception:
            pass  # se quiser apenas apagar, troque por: Evento.objects.filter(origem_rotina_item=item, data_evento__gte=date.today()).delete()

        item.delete()

        grade_html = render_to_string(self.grade_tpl, {"rotina": rotina, **_grade_ctx(rotina), "oob": True}, request=request)
        toast = '<div id="toast" hx-swap-oob="true" style="position:fixed;bottom:16px;right:16px;background:#111;color:#fff;padding:8px 12px;border-radius:6px;">Item excluído.</div>'
        return HttpResponse(grade_html + '<div id="modal"></div>' + toast)
    
# ---------------------- AGENDA ------------------------
# Create your views here.
class AgendaIndexView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Crianças do responsável (default = primeira)
        criancas = Crianca.objects.filter(responsavel=user).order_by("nome")
        crianca_id = self.request.GET.get("crianca")
        if crianca_id:
            crianca = get_object_or_404(criancas, pk=crianca_id)
        else:
            crianca = criancas.first() if criancas.exists() else None

        ctx["criancas"] = criancas
        ctx["crianca"] = crianca

        # Se não houver criança, finaliza contexto mínimo
        if not crianca:
            ctx.update({
                "sem_crianca": True,
            })
            return ctx

        # Data de referência (para navegar nas semanas) — querystring ?d=YYYY-MM-DD
        try:
            ref_str = self.request.GET.get("d")
            ref_date = datetime.strptime(ref_str, "%Y-%m-%d").date() if ref_str else date.today()
        except ValueError:
            ref_date = date.today()

        semana_ini = _monday_of(ref_date)
        semana_fim = semana_ini + timedelta(days=6)

        # Eventos da semana
        semana_qs = (Evento.objects
                     .select_related("profissional", "clinica")
                     .filter(crianca=crianca, data_evento__range=(semana_ini, semana_fim))
                     .order_by("data_evento", "hora_inicio", "hora_fim", "nome"))

        # Monta grade [dia][hora_int] -> lista de eventos
        horas = [time(h, 0) for h in range(8, 21)]  # 08:00..20:00
        grade = {key: {h: [] for h in horas} for key, _ in TIPOS_DIA_SEMANA}
        for ev in semana_qs:
            dia_key = WEEKDAY_TO_KEY[ev.data_evento.weekday()]
            hcell = time(ev.hora_inicio.hour, 0) if ev.hora_inicio else horas[0]
            grade[dia_key][hcell].append(ev)

        # Métricas do mês corrente (com base no ref_date)
        m_ini = date(ref_date.year, ref_date.month, 1)
        m_fim = _last_day_of_month(ref_date.year, ref_date.month)
        mes_qs = (Evento.objects
                  .select_related("profissional", "clinica")
                  .filter(crianca=crianca, data_evento__range=(m_ini, m_fim)))

        # Indicadores
        hoje = date.today()
        total_agendados = mes_qs.count()
        total_comparecimentos = mes_qs.filter(presenca_confirmada=True).count()
        total_faltas = mes_qs.filter(presenca_confirmada=False, data_evento__lt=hoje).count()
        total_pendentes = mes_qs.filter(presenca_confirmada=False, data_evento__gte=hoje).count()

        # Carga horária por clínica e por especialidade (somando durações)
        por_clinica = defaultdict(timedelta)
        por_especialidade = defaultdict(timedelta)

        for ev in mes_qs:
            dur = _duration(ev)
            clin_key = ev.clinica.nome if ev.clinica else "—"
            por_clinica[clin_key] += dur

            tipo_code = getattr(ev.profissional, "tipo", None) if ev.profissional else None
            tipo_label = PROF_TIPO_LABEL.get(tipo_code, "—")
            por_especialidade[tipo_label] += dur

        grid_rows = []
        for h in horas:
            row = {"hora": h, "cells": []}
            for key, label in TIPOS_DIA_SEMANA:
                row["cells"].append({
                    "dia_key": key,
                    "events": grade[key][h],  # já é uma lista
                })
            grid_rows.append(row)

        # Ordena por maior carga
        por_clinica_list = sorted(
            [{"clinica": k, "duracao": _fmt_td(v), "seconds": int(v.total_seconds())} for k, v in por_clinica.items()],
            key=lambda x: -x["seconds"]
        )
        por_especialidade_list = sorted(
            [{"especialidade": k, "duracao": _fmt_td(v), "seconds": int(v.total_seconds())} for k, v in por_especialidade.items()],
            key=lambda x: -x["seconds"]
        )

        # Próximas consultas (próximos 7 a 10 itens)
        proximos = (Evento.objects
                    .select_related("profissional", "clinica")
                    .filter(crianca=crianca, data_evento__gte=hoje)
                    .order_by("data_evento", "hora_inicio")[:10])

        ctx.update({
            "ref_date": ref_date,
            "semana_ini": semana_ini,
            "semana_fim": semana_fim,
            "horas": horas,
            "dias": list(TIPOS_DIA_SEMANA),  # [('segunda','Segunda-feira'), ...]
            "grade": grade,
            "grid_rows": grid_rows,

            "m_ini": m_ini,
            "m_fim": m_fim,
            "total_agendados": total_agendados,
            "total_comparecimentos": total_comparecimentos,
            "total_faltas": total_faltas,
            "total_pendentes": total_pendentes,

            "por_clinica": por_clinica_list,
            "por_especialidade": por_especialidade_list,
            "proximos": proximos,
        })
        return ctx
