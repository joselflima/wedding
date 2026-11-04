from django.views.generic import TemplateView
from foundation.permissions import RoleRequiredMixin


class HomeView(RoleRequiredMixin, TemplateView):
    required_role = "couple"
    template_name = "couple/home.html"
