from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q

from .models import Crianca
from .forms import CriancaForm

# Create your views here.
def perfil(request, user_id):
    return HttpResponse(f"Perfil do usuário {user_id}")

#----------- Autenticação -------------------

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("terapias:index")  
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("usuario:login")


def register_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]

        if User.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, "Conta criada com sucesso! 🎉")
            return redirect("terapias:index")

    return render(request, "auth/register.html")


# ----------------- CRUD de Criança ----------------------
class CriancaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Crianca
    form_class = CriancaForm
    template_name = "usuario/telas_criacao/criar_crianca.html"
    success_message = "Criança criada com sucesso!"
    # use admin como alvo “seguro” por enquanto; troque quando tiver sua página de detalhe/lista
    success_url = reverse_lazy("usuario:lista-criancas")

    def form_valid(self, form):
        # preenche o responsável automaticamente
        form.instance.responsavel = self.request.user
        return super().form_valid(form)
    
class CriancaListView(LoginRequiredMixin, ListView):
    model = Crianca
    template_name = "usuario/telas_lista/crianca_lista.html"
    context_object_name = "criancas"
    paginate_by = 10
    ordering = ["nome"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(responsavel=self.request.user)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(condicao__icontains=q)
                | Q(telefone_contato__icontains=q)
            )
        return qs

class CriancaDetailView(LoginRequiredMixin, DetailView):
    model = Crianca
    template_name = "usuario/telas_detalhes/crianca_detalhe.html"
    context_object_name = "crianca"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(responsavel=self.request.user)
    
class CriancaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Crianca
    form_class = CriancaForm
    template_name = "usuario/telas_edicao/crianca_editar.html"
    success_message = "Criança atualizada com sucesso!"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        # apenas o responsável pode editar
        return qs.filter(responsavel=self.request.user)

    def get_success_url(self):
        return reverse("usuario:lista-criancas")

class CriancaDeleteView(LoginRequiredMixin, DeleteView):
    model = Crianca
    template_name = "usuario/telas_deletar/crianca_deletar.html"
    success_url = reverse_lazy("usuario:lista-criancas")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        # apenas o responsável pode excluir
        return qs.filter(responsavel=self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f'Criança “{obj.nome}” excluída com sucesso.')
        return super().delete(request, *args, **kwargs)