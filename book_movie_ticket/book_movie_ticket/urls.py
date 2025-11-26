from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView
from django.conf.urls.static import static
from django.conf import settings

from book_movie_ticket_app import views

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="CinemaPlus API Documentation",
        default_version='v1',
        description="Tài liệu API hệ thống đặt vé xem phim CinemaPlus",
        contact=openapi.Contact(email="support@cinemaplus.local"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

admin.site.site_header = "Hệ thống quản lý rạp phim CinemaPlus"
admin.site.site_title = "Hệ thống quản lý rạp phim CinemaPlus"
admin.site.index_title = "Quản lý rạp phim CinemaPlus"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='trang-chu/')),
    # path('stats/', views.ticket_stats, name='ticket_stats'),

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

    # Nếu không muốn bị trùng Seats trong Swagger thì bỏ dòng này:
    # path('lay-ghe/', views.api_seats, name='get_seats'),

    path('tim-kiem/', views.search_movies, name='search_movies'),

    # --- API ROUTES ---
    path('api/movies/', views.api_movies, name='api_movies'),
    path('api/showtimes/', views.api_showtimes, name='api_showtimes'),
    path('api/seats/', views.api_seats, name='api_seats'),
    path('api/tickets/', views.api_create_ticket, name='api_create_ticket'),

    # --- Swagger / Redoc ---
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
