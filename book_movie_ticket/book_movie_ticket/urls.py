from django.contrib import admin
from django.urls import path
from book_movie_ticket_app import views
from django.views.generic.base import RedirectView
from django.conf.urls.static import static
from django.conf import settings

admin.site.site_header = "Hệ thống quản lý rạp phim CinemaPlus"
admin.site.site_title = "Hệ thống quản lý rạp phim CinemaPlus"
admin.site.index_title = "Quản lý rạp phim CinemaPlus"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='trang-chu/')),

    # --- WEB ROUTES ---
    path('trang-chu/', views.homepage, name='homepage'),
    path('lich-chieu/', views.movie_schedule, name='movie_schedule'),
    path('lien-he/', views.contact, name='contact'),
    path('dat-ve/', views.user_login, name='user_login'),
    path('dangxuat/', views.user_logout, name='user_logout'),
    path('dang-ky/', views.user_register, name='user_register'),
    path('phim/', views.movie_list, name='movie_list'),
    path('dat-ve-phim/', views.user_booking, name='user_booking'),
    path('phim/<int:movie_id>/', views.movie_detail, name='movie_detail'),

    # path('lay-ghe/', views.get_seats, name='get_seats'),
    path('lay-ghe/<int:movie_id>/', views.get_seats, name='get_seats'),
    path('tim-kiem/', views.search_movies, name='search_movies'),

    # --- API ROUTES ---
    path('api/movies/', views.api_movies, name='api_movies'),        # GET
    path('api/showtimes/', views.api_showtimes, name='api_showtimes'),  # GET
    path('api/seats/', views.api_seats, name='api_seats'),           # GET
    path('api/tickets/', views.api_create_ticket, name='api_create_ticket'),  # POST
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
