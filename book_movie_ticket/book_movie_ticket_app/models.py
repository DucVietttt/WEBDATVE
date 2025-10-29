from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver


# =========================
# Custom User
# =========================
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError(_("Phải có tên đăng nhập"))
        username = self.model.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_("username"), max_length=30, unique=True)
    name = models.CharField(_("Tên"), max_length=30)
    age = models.PositiveIntegerField(_("Tuổi"), validators=[MinValueValidator(1)])

    is_superuser = models.BooleanField(_("superuser status"), default=False)
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_active = models.BooleanField(_("active"), default=True)
    last_login = models.DateTimeField(_("Lần đăng nhập cuối"), blank=True, null=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name", "age"]
    objects = CustomUserManager()

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = _("Người dùng")
        verbose_name_plural = _("Người dùng")
        ordering = ["username"]


# =========================
# Movie
# =========================
class Movie(models.Model):
    title = models.CharField(_("Tên phim"), max_length=100)
    genre = models.CharField(_("Thể loại"), max_length=100)
    duration = models.PositiveIntegerField(_("Thời lượng (phút)"), validators=[MinValueValidator(1)])
    director = models.CharField(_("Đạo diễn"), max_length=100)
    release_date = models.DateField(_("Ngày công chiếu"))
    description = models.TextField(_("Mô tả"))
    poster = models.ImageField(_("Ảnh bìa"), upload_to="movie_poster/")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Phim")
        verbose_name_plural = _("Phim")
        constraints = [
            models.CheckConstraint(check=Q(duration__gt=0), name="movie_duration_gt_0"),
        ]


# =========================
# Room
# =========================
class Room(models.Model):
    name = models.CharField(_("Tên phòng"), max_length=100, help_text=_("VD: A, B, C..."))
    capacity = models.PositiveIntegerField(_("Sức chứa"), validators=[MinValueValidator(1)])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Phòng chiếu")
        verbose_name_plural = _("Phòng chiếu")
        constraints = [
            models.CheckConstraint(check=Q(capacity__gt=0), name="room_capacity_gt_0"),
        ]


# =========================
# Seat
# =========================
class Seat(models.Model):
    seat_number = models.PositiveIntegerField(_("Số ghế"), validators=[MinValueValidator(1)])
    is_available = models.BooleanField(_("Trạng thái"), default=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    def __str__(self):
        return f"Ghế {self.seat_number} ({self.room.name})"

    @receiver(post_save, sender=Room)
    def create_seats(sender, instance, created, **kwargs):
        """Tự tạo ghế khi thêm phòng mới"""
        if created:
            if not Seat.objects.filter(room=instance).exists():
                Seat.objects.bulk_create([
                    Seat(room=instance, seat_number=i) for i in range(1, instance.capacity + 1)
                ])

    class Meta:
        verbose_name = _("Ghế")
        verbose_name_plural = _("Ghế")
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(check=Q(seat_number__gt=0), name="seat_number_gt_0"),
        ]


# =========================
# Showtime
# =========================
class Showtime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="showtimes")
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    date_time = models.DateTimeField(_("Ngày giờ chiếu"))

    def __str__(self):
        return f"{self.movie.title} - {self.date_time:%d/%m %H:%M} - {self.room.name}"

    class Meta:
        ordering = ["date_time"]


# =========================
# Ticket 
# =========================
class Ticket(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("Người đặt"))
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name=_("Phòng chiếu"))
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    price = models.PositiveIntegerField(_("Giá vé"), validators=[MinValueValidator(1)], null=True, blank=True)
    type = models.CharField(_("Loại vé"), max_length=50, choices=[("Adult", "Người lớn"), ("Child", "Trẻ em")])
    date_time = models.DateTimeField(_("Ngày giờ chiếu"))

    def __str__(self):
        return f"Vé {self.id} - {self.movie.title} - Ghế {self.seat.seat_number}"

    class Meta:
        verbose_name = _("Vé")
        verbose_name_plural = _("Vé")
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(check=Q(price__gt=0), name="ticket_price_gt_0"),
        ]
