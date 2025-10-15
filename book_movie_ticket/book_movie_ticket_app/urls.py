from django.urls import path
from . import views

urlpatterns = [
    path("lich-chieu/", views.movie_schedule, name="showtimes"),
]