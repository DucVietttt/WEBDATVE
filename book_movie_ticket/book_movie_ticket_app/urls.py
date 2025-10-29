from django.urls import path
from . import views

urlpatterns = [
   path('api/movies/', views.api_movies, name='api_movies'),
    path('api/showtimes/', views.api_showtimes, name='api_showtimes'),
    path('api/seats/', views.api_seats, name='api_seats'),
    path('api/tickets/', views.api_create_ticket, name='api_create_ticket'),

    path('api/ping/', lambda request: __import__('django').http.JsonResponse({'ok': True})),
]