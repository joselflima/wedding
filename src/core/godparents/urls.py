from django.urls import path
from .views import HomeView

app_name = "godparents"
urlpatterns = [path("", HomeView.as_view(), name="home")]
