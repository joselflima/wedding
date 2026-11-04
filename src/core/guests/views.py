from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView

from foundation.permissions import CoupleRequiredMixin, RoleRequiredMixin

from .forms import GuestForm
from .models import Guest


class GuestListView(CoupleRequiredMixin, ListView):
    model = Guest
    template_name = "guests/list.html"
    context_object_name = "guests"
    paginate_by = 25
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        self.query = self.request.GET.get("q", "").strip()
        queryset = super().get_queryset()
        if self.query:
            queryset = queryset.filter(Q(name__icontains=self.query) | Q(phone__icontains=self.query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(query=self.query, total=Guest.objects.count())
        return context


class GuestFormMixin(CoupleRequiredMixin):
    model = Guest
    form_class = GuestForm
    template_name = "guests/form.html"
    success_url = reverse_lazy("guests:list")
    http_method_names = ["get", "post", "head", "options"]

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Convidado salvo com sucesso.")
        return response


class GuestCreateView(GuestFormMixin, CreateView):
    pass


class GuestUpdateView(GuestFormMixin, UpdateView):
    pass


class GuestDeleteView(CoupleRequiredMixin, DeleteView):
    model = Guest
    template_name = "guests/confirm_delete.html"
    success_url = reverse_lazy("guests:list")
    http_method_names = ["get", "post", "head", "options"]

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Convidado excluído da lista.")
        return response


class HomeView(RoleRequiredMixin, TemplateView):
    required_role = "guest"
    template_name = "guests/home.html"
