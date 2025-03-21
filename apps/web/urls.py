from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "web"
urlpatterns = [
    path("", views.home, name="home"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots.txt"),
    path("status/", views.HealthCheck.as_view()),
    path("status/<str:subset>/", views.HealthCheck.as_view()),
    path("sudo/<slug:slug>/", views.acquire_superuser_powers, name="sudo"),
    path("sudo/<slug:slug>/release/", views.release_superuser_powers, name="release_sudo"),
    path("search", views.global_search, name="global_search"),
]

team_urlpatterns = (
    [
        path("", views.team_home, name="home"),
    ],
    "web_team",
)
