from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from core.guests.views import HomeView as GuestHomeView
from foundation.accounts.views import WeddingLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", WeddingLoginView.as_view(), name="home"),
    path("login/", WeddingLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("couple/", include("core.couple.urls")),
    path("couple/guests/", include("core.guests.urls")),
    path("guests/", GuestHomeView.as_view(), name="guest_home"),
    path("godparents/", include("core.godparents.urls")),
]
