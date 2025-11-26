# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from django import forms
# from django.core.exceptions import ValidationError
# from .models import Movie, Ticket, CustomUser, Room, Seat, Showtime
# from django.urls import path
# from django.template.response import TemplateResponse
# from django.db.models import Count
# from django.db.models.functions import TruncDate

# # =========================
# # Validation Forms (Admin)
# # =========================
# class RoomForm(forms.ModelForm):
#     class Meta:
#         model = Room
#         fields = "__all__"

#     def clean_capacity(self):
#         cap = self.cleaned_data.get("capacity")
#         if cap is not None and cap <= 0:
#             raise ValidationError("⚠️ Sức chứa phải lớn hơn 0.")
#         return cap


# class TicketForm(forms.ModelForm):
#     class Meta:
#         model = Ticket
#         fields = "__all__"

#     def clean_price(self):
#         p = self.cleaned_data.get("price")
#         if p is not None and p <= 0:
#             raise ValidationError("⚠️ Giá vé phải lớn hơn 0.")
#         return p


# class SeatForm(forms.ModelForm):
#     class Meta:
#         model = Seat
#         fields = "__all__"

#     def clean_seat_number(self):
#         n = self.cleaned_data.get("seat_number")
#         if n is not None and n <= 0:
#             raise ValidationError("⚠️ Số ghế phải lớn hơn 0.")
#         return n


# # =========================
# # Custom User Admin
# # =========================
# class CustomUserAdmin(UserAdmin):
#     model = CustomUser
#     list_display = ["id", "username", "name", "age", "is_staff", "is_active"]
#     list_filter = ["is_staff", "is_active"]
#     fieldsets = (
#         ("Thông tin tài khoản", {"fields": ("username", "password")}),
#         ("Thông tin cá nhân", {"fields": ("name", "age")}),
#         ("Quyền hạn", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
#         ("Lần đăng nhập cuối", {"fields": ("last_login",)}),
#     )
#     search_fields = ("username", "name")
#     ordering = ("id",)
#     add_fieldsets = (
#         (None, {
#             "classes": ("wide",),
#             "fields": ("username", "name", "age", "password1", "password2", "is_active", "is_staff", "is_superuser"),
#         }),
#     )


# # =========================
# # Movie Admin
# # =========================
# class MovieAdmin(admin.ModelAdmin):
#     list_display = ["id", "title", "genre", "duration", "director", "release_date"]
#     search_fields = ("title", "genre", "director")
#     list_filter = ["genre", "release_date"]
#     ordering = ("id",)


# # =========================
# # Room Admin
# # =========================
# class RoomAdmin(admin.ModelAdmin):
#     form = RoomForm
#     list_display = ["id", "name", "capacity"]
#     search_fields = ("name",)
#     ordering = ("id",)


# # =========================
# # Ticket Admin
# # =========================
# class TicketAdmin(admin.ModelAdmin):
#     form = TicketForm
#     list_display = ["id", "movie", "room", "seat", "price", "type", "date_time"]
#     list_filter = ["movie", "room", "type", "date_time"]
#     search_fields = ("movie__title", "room__name", "seat__seat_number", "type")
#     ordering = ("id",)


# # =========================
# # Seat Admin
# # =========================
# class SeatAdmin(admin.ModelAdmin):
#     form = SeatForm
#     list_display = ["id", "room", "seat_number", "is_available"]
#     list_filter = ["room", "is_available"]
#     search_fields = ("room__name",)
#     ordering = ("id",)


# # =========================
# # Showtime Admin
# # =========================
# @admin.register(Showtime)
# class ShowtimeAdmin(admin.ModelAdmin):
#     list_display = ("movie", "room", "date_time")
#     list_filter = ("movie", "room")
#     ordering = ("date_time",)


# # =========================
# # Register
# # =========================
# admin.site.register(Movie, MovieAdmin)
# admin.site.register(Ticket, TicketAdmin)
# admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(Room, RoomAdmin)
# admin.site.register(Seat, SeatAdmin)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.core.exceptions import ValidationError
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count
from django.db.models.functions import TruncDate

from .models import Movie, Ticket, CustomUser, Room, Seat, Showtime


# =========================
# Validation Forms (Admin)
# =========================
class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = "__all__"

    def clean_capacity(self):
        cap = self.cleaned_data.get("capacity")
        if cap is not None and cap <= 0:
            raise ValidationError("⚠️ Sức chứa phải lớn hơn 0.")
        return cap


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = "__all__"

    def clean_price(self):
        p = self.cleaned_data.get("price")
        if p is not None and p <= 0:
            raise ValidationError("⚠️ Giá vé phải lớn hơn 0.")
        return p


class SeatForm(forms.ModelForm):
    class Meta:
        model = Seat
        fields = "__all__"

    def clean_seat_number(self):
        n = self.cleaned_data.get("seat_number")
        if n is not None and n <= 0:
            raise ValidationError("⚠️ Số ghế phải lớn hơn 0.")
        return n


# =========================
# Custom User Admin
# =========================
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ["id", "username", "name", "age", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active"]
    fieldsets = (
        ("Thông tin tài khoản", {"fields": ("username", "password")}),
        ("Thông tin cá nhân", {"fields": ("name", "age")}),
        ("Quyền hạn", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Lần đăng nhập cuối", {"fields": ("last_login",)}),
    )
    search_fields = ("username", "name")
    ordering = ("id",)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "name", "age", "password1", "password2", "is_active", "is_staff", "is_superuser"),
        }),
    )


# =========================
# Movie Admin
# =========================
class MovieAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "genre", "duration", "director", "release_date"]
    search_fields = ("title", "genre", "director")
    list_filter = ["genre", "release_date"]
    ordering = ("id",)


# =========================
# Room Admin
# =========================
class RoomAdmin(admin.ModelAdmin):
    form = RoomForm
    list_display = ["id", "name", "capacity"]
    search_fields = ("name",)
    ordering = ("id",)


# =========================
# Ticket Admin  (có thêm THỐNG KÊ)
# =========================
class TicketAdmin(admin.ModelAdmin):
    form = TicketForm
    list_display = ["id", "movie", "room", "seat", "price", "type", "date_time"]
    list_filter = ["movie", "room", "type", "date_time"]
    search_fields = ("movie__title", "room__name", "seat__seat_number", "type")
    ordering = ("id",)

    # dùng template riêng cho trang danh sách vé để hiện nút "Thống kê vé"
    change_list_template = "admin/ticket_change_list.html"

    def get_urls(self):
        """
        Thêm URL /admin/book_movie_ticket_app/ticket/stats/ cho trang thống kê vé.
        """
        urls = super().get_urls()
        my_urls = [
            path(
                "stats/",
                self.admin_site.admin_view(self.stats_view),
                name="ticket_stats",
            ),
        ]
        return my_urls + urls

    def stats_view(self, request):
        """
        Trang thống kê vé:
        - Tổng số vé
        - Số vé theo phim
        - Số vé theo ngày chiếu
        """
        total_tickets = Ticket.objects.count()

        stats_by_movie = (
            Ticket.objects
            .values("movie__title")
            .annotate(total_tickets=Count("id"))
            .order_by("-total_tickets")
        )

        stats_by_date = (
            Ticket.objects
            .annotate(date=TruncDate("date_time"))
            .values("date")
            .annotate(total_tickets=Count("id"))
            .order_by("date")
        )

        context = dict(
            self.admin_site.each_context(request),
            opts=self.model._meta,
            title="Thống kê vé",
            total_tickets=total_tickets,
            stats_by_movie=stats_by_movie,
            stats_by_date=stats_by_date,
        )
        return TemplateResponse(request, "admin/ticket_stats.html", context)


# =========================
# Seat Admin
# =========================
class SeatAdmin(admin.ModelAdmin):
    form = SeatForm
    list_display = ["id", "room", "seat_number", "is_available"]
    list_filter = ["room", "is_available"]
    search_fields = ("room__name",)
    ordering = ("id",)


# =========================
# Showtime Admin
# =========================
@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ("movie", "room", "date_time")
    list_filter = ("movie", "room")
    ordering = ("date_time",)


# =========================
# Register
# =========================
admin.site.register(Movie, MovieAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(Seat, SeatAdmin)

