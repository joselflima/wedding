from django.contrib.auth import views as auth_views
from django.urls import include, path
from core.guests.views import HomeView as GuestHomeView
from foundation.accounts.views import WeddingLoginView

urlpatterns = [
    path("", WeddingLoginView.as_view(), name="home"),
    path("entrar/", WeddingLoginView.as_view(), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("noivos/", include("core.couple.urls")),
    path("noivos/convidados/", include("core.guests.urls")),
    path("convidados/", GuestHomeView.as_view(), name="guest_home"),
    path("padrinhos/", include("core.godparents.urls")),
]
