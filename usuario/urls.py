from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'usuario'

urlpatterns = [
    path('perfil/<int:user_id>/', views.perfil, name='perfil'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.register_view, name="registro"),

    # CRIANÇAS
    path("criancas/", views.CriancaListView.as_view(), name="lista-criancas"),
    path("criancas/nova/", views.CriancaCreateView.as_view(), name="crianca-criar"),
    path("criancas/<int:pk>/", views.CriancaDetailView.as_view(), name="detalhes-crianca"),
    path("criancas/<int:pk>/editar/", views.CriancaUpdateView.as_view(), name="editar-crianca"),
    path("criancas/<int:pk>/deletar/", views.CriancaDeleteView.as_view(), name="deletar-crianca"),
]