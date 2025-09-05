from django.contrib import admin
from django.urls import path, include
from . import views

app_name = "terapias"

urlpatterns = [
    path('', views.AgendaIndexView.as_view(), name='index'),

    # CLINICAS
    path("clinicas/", views.ClinicaListView.as_view(), name="lista-clinicas"),
    path("clinicas/nova/", views.ClinicaCreateView.as_view(), name="criar-clinica"),
    path("clinicas/<int:pk>/", views.ClinicaDetailView.as_view(), name="detalhes-clinica"),
    path("clinicas/<int:pk>/deletar/", views.ClinicaDeleteView.as_view(), name="deletar-clinica"),
    path("clinicas/<int:pk>/editar/", views.ClinicaUpdateView.as_view(), name="editar-clinica"),

    # PROFISSIONAIS
    path("profissionais/novo/", views.ProfissionalCreateView.as_view(), name="criar-profissional"),
    path("profissionais/", views.ProfissionalListView.as_view(), name="lista-profissionais"),
    path("profissionais/<int:pk>/", views.ProfissionalDetailView.as_view(), name="detalhes-profissional"),
    path("profissionais/<int:pk>/deletar/", views.ProfissionalDeleteView.as_view(), name="deletar-profissional"),
    path("profissionais/<int:pk>/editar/", views.ProfissionalUpdateView.as_view(), name="editar-profissional"),

    # EVENTOS
    path("eventos/novo/", views.EventoCriarView.as_view(), name="criar-evento"),

    # ROTINAS
    path("rotinas/nova/", views.RotinaCriarView.as_view(), name="criar-rotina"),
    path("rotinas/<int:pk>/planejar/", views.RotinaPlanejarView.as_view(), name="planejar-rotina"),
    path("rotinas/<int:pk>/novo-item/", views.RotinaItemModalView.as_view(), name="novo-item-rotina"),
    path("rotinas/itens/<int:item_id>/editar/", views.RotinaItemEditarModalView.as_view(), name="editar-item-rotina"),
    path("rotinas/itens/<int:item_id>/excluir/", views.RotinaItemExcluirView.as_view(), name="excluir-item-rotina"),
]