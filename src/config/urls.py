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
from wedding import password_reset, views
urlpatterns = [path('', views.home), path('login/', LoginView.as_view(template_name='wedding/page.html'), name='login'), path('logout/', LogoutView.as_view(next_page='login'), name='logout'), path('people/', views.people, name='people'), path('people/<int:pk>/', views.people, name='person'), path('activate/<int:pk>/<str:token>/', views.activate, name='activate')] + urlpatterns[1:]
urlpatterns += [path('manifest.webmanifest', views.manifest, name='manifest')]
urlpatterns += [
    path('password-reset/', password_reset.request_reset, name='password_reset_request'),
    path('password-reset/requested/', password_reset.requested, name='password_reset_requested'),
    path('password-reset/<int:pk>/confirm/', password_reset.confirm, name='password_reset_confirm'),
    path('password-reset/<int:pk>/link/<slug:token>/', password_reset.open_link, name='password_reset_link'),
    path('people/password-resets/', password_reset.panel, name='password_reset_panel'),
    path('people/password-resets/<int:pk>/issue/', password_reset.issue_link, name='password_reset_issue'),
]
