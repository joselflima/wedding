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
