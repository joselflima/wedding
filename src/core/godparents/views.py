from django.views.generic import TemplateView
from foundation.permissions import RoleRequiredMixin


class HomeView(RoleRequiredMixin, TemplateView):
    required_role = "godparent"
    template_name = "godparents/home.html"
