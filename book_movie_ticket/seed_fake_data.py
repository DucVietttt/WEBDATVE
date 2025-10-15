# seed_fake_data.py (đặt cạnh manage.py)
import os, django, random, io
from datetime import datetime, timedelta
from tqdm import tqdm
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_movie_ticket.settings')
django.setup()

from django.core.files.base import ContentFile
from PIL import Image

from book_movie_ticket_app.models import (
    Movie, Room, Seat, Showtime, Ticket, CustomUser
)

fake = Faker('vi_VN')

# ====== CẤU HÌNH SỐ LƯỢNG ======
NUM_USERS = 200
NUM_MOVIES = 50
NUM_ROOMS = 5
SEATS_PER_ROOM = 40            # dùng cho Room.capacity
SHOWTIMES_PER_MOVIE = 4
TICKETS_PER_USER = 5
# ==============================

def tiny_png_bytes(color=(120, 120, 120)):
    """Tạo ảnh PNG nhỏ trong RAM để gán cho ImageField."""
    im = Image.new('RGB', (300, 450), color=color)
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return buf.getvalue()

print("Bắt đầu sinh dữ liệu giả...")

# 1) Users
users = []
for _ in tqdm(range(NUM_USERS), desc="Tạo Users"):
    username = f"{fake.user_name()}{random.randint(1000,9999)}"
    CustomUser.objects.create_user(
        username=username,
        password="123456",
        name=fake.name(),
        age=random.randint(16, 60)
    )

# 2) Movies (có poster)
movies = []
for _ in tqdm(range(NUM_MOVIES), desc="Tạo Movies"):
    m = Movie(
        title=fake.sentence(nb_words=3),
        genre=random.choice(["Action", "Drama", "Comedy", "Sci-Fi", "Horror"]),
        duration=random.randint(90, 180),
        director=fake.name(),
        release_date=fake.date_this_decade(),
        description=fake.text(max_nb_chars=120),
    )
    # tạo poster giả
    poster_bytes = tiny_png_bytes(color=(random.randint(50,200),random.randint(50,200),random.randint(50,200)))
    m.poster.save(f"{m.title.replace(' ','_')}.png", ContentFile(poster_bytes), save=False)
    m.save()
    movies.append(m)

# 3) Rooms (NHỚ truyền capacity; ghế sẽ tự tạo qua signal)
rooms = []
for i in tqdm(range(NUM_ROOMS), desc="Tạo Rooms"):
    r = Room.objects.create(name=f"Rạp {chr(65+i)}", capacity=SEATS_PER_ROOM)
    rooms.append(r)
# -> KHÔNG tự tạo Seat; signal đã tạo đủ 1..capacity

# 4) Showtimes
showtimes = []
now = datetime.now().replace(minute=0, second=0, microsecond=0)
for mv in tqdm(movies, desc="Tạo Showtimes"):
    for _ in range(SHOWTIMES_PER_MOVIE):
        room = random.choice(rooms)
        dt = now + timedelta(days=random.randint(0, 10), hours=random.choice([10, 13, 16, 19, 21]))
        st = Showtime.objects.create(movie=mv, room=room, date_time=dt)
        showtimes.append(st)

# 5) Tickets (chỉ tạo cho ghế còn trống trong đúng suất chiếu)
#   Lưu ý: Ticket.type chỉ 'Adult' hoặc 'Child'
for u in tqdm(users, desc="Tạo Tickets"):
    for _ in range(TICKETS_PER_USER):
        st = random.choice(showtimes)
        # ghế thuộc đúng phòng, còn available và chưa bị đặt trong suất này
        taken_seat_ids = set(
            Ticket.objects.filter(movie=st.movie, room=st.room, date_time=st.date_time)
                          .values_list('seat_id', flat=True)
        )
        cand = (Seat.objects
                .filter(room=st.room, is_available=True)
                .exclude(id__in=taken_seat_ids)
                .order_by('?')
                .first())
        if not cand:
            continue
        Ticket.objects.create(
            movie=st.movie,
            user=u,
            room=st.room,
            seat=cand,
            price=random.choice([80000, 100000, 120000]),
            type=random.choice(['Adult', 'Child']),
            date_time=st.date_time
        )
        # signal Ticket sẽ tự cập nhật Seat.is_available=False

print("Đã sinh xong dữ liệu!")
