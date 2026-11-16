from django.contrib import admin
from django.db import connection, DatabaseError
from django.http import JsonResponse
from django.urls import path
from django.views.generic import RedirectView


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [path("", RedirectView.as_view(url="/admin/")), path("health/", health), path("admin/", admin.site.urls)]

from django.contrib.auth.views import LoginView, LogoutView
from wedding import views
urlpatterns = [path('', views.home), path('login/', LoginView.as_view(template_name='wedding/page.html'), name='login'), path('logout/', LogoutView.as_view(), name='logout'), path('people/', views.people, name='people'), path('people/<int:pk>/', views.people, name='person'), path('activate/<int:pk>/<str:token>/', views.activate, name='activate')] + urlpatterns[1:]
