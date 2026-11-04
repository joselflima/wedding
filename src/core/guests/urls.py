from django.urls import path
from . import views
app_name = "guests"
urlpatterns = [
    path("", views.GuestListView.as_view(), name="list"),
    path("adicionar/", views.GuestCreateView.as_view(), name="create"),
    path("<int:pk>/editar/", views.GuestUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.GuestDeleteView.as_view(), name="delete"),
]
