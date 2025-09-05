# terapias/services.py
from datetime import date, timedelta, datetime
from typing import Iterable, List
from django.db import transaction
from .models import Evento, RotinaItem

# mapeia suas keys -> weekday() do Python (segunda=0..domingo=6)
WEEKDAY_MAP = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3,
    "sexta": 4, "sabado": 5, "domingo": 6
}

def _primeira_data_no_ou_apos(inicio: date, weekday: int) -> date:
    delta = (weekday - inicio.weekday()) % 7
    return inicio + timedelta(days=delta)

def _datas_diarias(inicio: date, fim: date) -> Iterable[date]:
    d = inicio
    while d <= fim:
        yield d
        d += timedelta(days=1)

def _datas_semanais(inicio: date, fim: date, weekday: int, passo_dias: int = 7) -> Iterable[date]:
    d = _primeira_data_no_ou_apos(inicio, weekday)
    while d <= fim:
        yield d
        d += timedelta(days=passo_dias)  # 7 (semanal) ou 14 (quinzenal)

def _ultimo_dia_do_mes(year: int, month: int) -> int:
    from calendar import monthrange
    return monthrange(year, month)[1]

def _datas_mensais(inicio: date, fim: date) -> Iterable[date]:
    """regra simples: mesmo 'dia do mês' do início"""
    d = inicio
    while d <= fim:
        yield d
        y, m = d.year, d.month
        m += 1
        if m > 12:
            m = 1; y += 1
        dia = min(d.day, _ultimo_dia_do_mes(y, m))
        d = date(y, m, dia)

def _datas_anuais(inicio: date, fim: date) -> Iterable[date]:
    d = inicio
    while d <= fim:
        yield d
        d = date(d.year + 1, d.month, d.day)

def _calcular_duracao(hora_inicio, hora_fim):
    if not (hora_inicio and hora_fim):
        return None
    base = date.today()
    dt_i = datetime.combine(base, hora_inicio)
    dt_f = datetime.combine(base, hora_fim)
    return dt_f - dt_i

def _default_tipo_evento():
    # tenta usar o primeiro de TIPOS_EVENTO; se não houver, cai em "pontual"
    try:
        from .models import TIPOS_EVENTO
        return TIPOS_EVENTO[0][0] if TIPOS_EVENTO else "pontual"
    except Exception:
        return "pontual"

@transaction.atomic
def expandir_rotina_item(ri: RotinaItem, *, dias_horizonte_if_no_end: int = 30) -> dict:
    """
    Gera Eventos correspondentes ao RotinaItem no intervalo:
    [ri.rotina.data_inicio (ou hoje), ri.rotina.data_termino (ou hoje + N)].

    periodicidade:
      - diaria: todos os dias
      - semanal: weekday de ri.dias_semana
      - quinzenal: mesmo weekday a cada 14 dias
      - mensal: mesmo dia do mês ancorado em data_inicio da rotina
      - anual: mesma data (mês/dia) ancorada em data_inicio
      - pontual: apenas na data_inicio

    Retorna: {"criadas": X, "puladas": Y, "de": start, "ate": end}
    """
    rotina = ri.rotina
    hoje = date.today()
    start = rotina.data_inicio or hoje
    # se não quiser criar retroativo, segure no hoje:
    start = max(start, hoje)
    end = rotina.data_termino or (start + timedelta(days=dias_horizonte_if_no_end))

    # seleciona datas
    datas: List[date] = []
    per = ri.periodicidade

    if per == "diaria":
        datas = list(_datas_diarias(start, end))
    elif per in ("semanal", "quinzenal"):
        weekday = WEEKDAY_MAP.get(ri.dias_semana, start.weekday())
        passo = 7 if per == "semanal" else 14
        datas = list(_datas_semanais(start, end, weekday, passo_dias=passo))
    elif per == "mensal":
        datas = list(_datas_mensais(start, end))
    elif per == "anual":
        datas = list(_datas_anuais(start, end))
    elif per == "pontual":
        datas = [start] if start <= end else []

    dur = ri.duracao or _calcular_duracao(ri.hora_inicio, ri.hora_fim)
    tipo_padrao = _default_tipo_evento()

    criadas = 0
    puladas = 0

    for d in datas:
        Evento.objects.create(
            nome=ri.nome_evento,
            tipo=_default_tipo_evento(),      # ajuste para um tipo válido seu
            data_evento=d,
            hora_inicio=ri.hora_inicio,
            hora_fim=ri.hora_fim,
            duracao=dur,
            profissional=ri.profissional,
            clinica=ri.clinica,
            crianca=ri.rotina.crianca,
            notas=ri.descricao,
            presenca_confirmada=False,
            criado_por=ri.criado_por,
            # se tiver o FK opcional:
            **({"origem_rotina_item": ri} if hasattr(Evento, "origem_rotina_item") else {})
        )
        criadas += 1

    return {"criadas": criadas, "puladas": puladas, "de": start, "ate": end}

def sincronizar_eventos_do_item(ri: RotinaItem, *, apagar_passado: bool = False):
    """
    Remove eventos gerados por este item (futuros por padrão) e reexpande.
    """
    qs = Evento.objects.filter(origem_rotina_item=ri)
    if not apagar_passado:
        qs = qs.filter(data_evento__gte=date.today())
    deletados = qs.delete()
    res = expandir_rotina_item(ri)
    return {"deletados": deletados, **res}
