from .models import *
from .forms import *

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, HttpResponseNotAllowed
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from datetime import datetime, timedelta



def _parse_dt_loose(s: str):
    """
    Parse nhiều format ngày-giờ, hỗ trợ tiếng Việt SA/CH -> AM/PM.
    Trả về datetime (naive) hoặc None.
    """
    if not s:
        return None
    s = s.strip()
    # map SA/CH -> AM/PM để dùng %p
    s = s.replace(" SA", " AM").replace(" CH", " PM").replace("SA", "AM").replace("CH", "PM")

    # thử ISO/auto trước
    dt = parse_datetime(s)
    if dt:
        return dt

    for fmt in (
        "%Y-%m-%d %H:%M:%S",  # 2025-10-31 11:40:00
        "%Y-%m-%dT%H:%M",     # 2025-10-31T11:40
        "%d/%m/%Y %H:%M",     # 31/10/2025 11:40 (24h)
        "%d/%m/%Y %I:%M %p",  # 31/10/2025 11:40 AM/PM (đã map từ SA/CH)
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


# ==================== MAIN WEB VIEWS ====================

def homepage(request):
    if request.user.is_anonymous:
        return render(request, 'home.html')
    return book_ticket(request)


def book_ticket(request):
    username = getattr(request.user, "username", "")
    name = getattr(request.user, "name", "")
    age = getattr(request.user, "age", "")

    user_tickets = Ticket.objects.filter(user=request.user)
    for ticket in user_tickets:
        ticket.date_time = datetime.strptime(
            str(ticket.date_time).split('+')[0],
            '%Y-%m-%d %H:%M:%S'
        ).strftime('%d/%m/%Y %H:%M:%S')

    return render(request, 'book_ticket.html', {
        'username': username,
        'name': name,
        'age': age,
        'user_tickets': user_tickets
    })


def user_login(request):
    show_login_form = True
    if request.method != 'POST':
        messages.error(request, "Vui lòng đăng nhập hoặc đăng ký để đặt vé")
        return render(request, 'home.html', {'show_login_form': show_login_form})

    username = request.POST.get('username')
    password = request.POST.get('password')
    remember_me = request.POST.get('rememberMe')

    if remember_me == 'on':
        request.session.set_expiry(1209600)  # 14 ngày

    if not username or not password:
        messages.error(request, "Vui lòng nhập tên tài khoản và mật khẩu!")
        return render(request, 'home.html', {'show_login_form': show_login_form})

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        if user.is_staff:
            return redirect('/admin/')
        return book_ticket(request)
    else:
        messages.error(request, "Tên tài khoản hoặc mật khẩu không đúng!")
        return render(request, 'home.html', {'show_login_form': show_login_form})


def user_logout(request):
    logout(request)
    return homepage(request)


def user_register(request):
    show_register_form = True
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        name = request.POST.get('name')
        age = request.POST.get('age')

        if not username or not password or not name or not age:
            messages.error(request, "Vui lòng điền đầy đủ thông tin!")
            return render(request, 'home.html', {'show_register_form': show_register_form})

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập đã tồn tại!")
            return render(request, 'home.html', {'show_register_form': show_register_form})

        if password != password_confirm:
            messages.error(request, "Mật khẩu không trùng khớp!")
            return render(request, 'home.html', {'show_register_form': show_register_form})

        age = int(age)
        if age < 0 or age > 100:
            messages.error(request, "Tuổi không hợp lệ!")
            return render(request, 'home.html', {'show_register_form': show_register_form})

        user = CustomUser.objects.create_user(username=username, password=password, name=name, age=age)
        user.save()
        messages.success(request, "Đăng ký tài khoản thành công!")
        return render(request, 'home.html', {'register_sucess': True})
    else:
        return render(request, 'home.html', {'show_register_form': show_register_form})


def movie_schedule(request):
    now = timezone.now()
    upcoming = (Showtime.objects
                .select_related('movie', 'room')
                .filter(date_time__gte=now)
                .order_by('date_time'))
    past = (Showtime.objects
            .select_related('movie', 'room')
            .filter(date_time__lt=now)
            .order_by('-date_time')[:50])
    return render(request, 'movie_schedule.html', {
        'upcoming': upcoming,
        'past': past,
        'form': BookTicketForm(),
    })


def contact(request):
    return render(request, 'contact.html')


def movie_list(request):
    return render(request, 'movie_list.html', {
        'movies': Movie.objects.all(),
        'rooms': Room.objects.all(),
        'seats': Seat.objects.all(),
        'form': BookTicketForm(),
    })


# ==================== AJAX BOOKING ====================

@login_required
@transaction.atomic
def user_booking(request):
    """Đặt vé qua AJAX, trả JSON; có khóa hàng để tránh đặt trùng."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        room_id = request.POST.get('room_id')
        movie_id = request.POST.get('movie_id')
        # chấp nhận cả 'selected_seats[]' (checkbox) và 'selected_seats' (array)
        selected_seats = (request.POST.getlist('selected_seats[]')
                          or request.POST.getlist('selected_seats'))
        date_time_str = request.POST.get('date_time')
        qty_str = request.POST.get('quantity')

        if not (room_id and movie_id and date_time_str and selected_seats):
            return JsonResponse({'status': 'error', 'message': 'Thiếu dữ liệu đặt vé'}, status=400)

        # Parse thời gian chuẩn (hỗ trợ SA/CH)
        dt = _parse_dt_loose(date_time_str)
        if not dt:
            return JsonResponse({'status': 'error', 'message': 'date_time không hợp lệ'}, status=400)
        if settings.USE_TZ and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        # số lượng và số ghế chọn phải khớp
        try:
            quantity = int(qty_str) if qty_str is not None else len(selected_seats)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'quantity phải là số nguyên'}, status=400)
        if quantity < 1:
            return JsonResponse({'status': 'error', 'message': 'Số lượng phải >= 1'}, status=400)

        selected_seat_ids = list({int(s) for s in selected_seats})
        if len(selected_seat_ids) != quantity:
            return JsonResponse({'status': 'error',
                                 'message': 'Số ghế chọn phải đúng bằng số lượng vé'}, status=400)

        # Kiểm tra tồn tại & khóa hàng
        room = Room.objects.select_for_update().get(id=room_id)
        movie = Movie.objects.get(id=movie_id)

        start = dt - timedelta(minutes=1)
        end = dt + timedelta(minutes=1)
        showtime = (Showtime.objects
                    .filter(movie_id=movie_id, room_id=room_id, date_time__range=(start, end))
                    .first())
        if not showtime:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy suất chiếu phù hợp'}, status=404)

        seats_qs = (Seat.objects
                    .select_for_update()
                    .filter(id__in=selected_seat_ids, room_id=room_id))
        if seats_qs.count() != len(selected_seat_ids):
            return JsonResponse({'status': 'error', 'message': 'Một số ghế không tồn tại trong phòng này'}, status=400)

        # đã có vé cùng suất?
        collisions = set(Ticket.objects.filter(
            movie_id=movie_id,
            room_id=room_id,
            date_time__range=(start, end),
            seat_id__in=selected_seat_ids
        ).values_list('seat_id', flat=True))
        if collisions:
            return JsonResponse({'status': 'error',
                                 'message': f'Ghế đã được đặt: {sorted(list(collisions))}'}, status=409)

        # ghế không sẵn sàng?
        not_available = set(seats_qs.filter(is_available=False).values_list('id', flat=True))
        if not_available:
            return JsonResponse({'status': 'error',
                                 'message': f'Ghế không sẵn sàng: {sorted(list(not_available))}'}, status=409)

        # tạo vé
        to_create = [
            Ticket(
                movie=movie,
                user=request.user,
                room=room,
                seat=seat,
                price=100000,   # TODO: tính theo loại vé nếu cần
                type='Adult',   # TODO: lấy từ request.POST.get('type')
                date_time=showtime.date_time
            )
            for seat in seats_qs
        ]
        created = Ticket.objects.bulk_create(to_create)

        # cập nhật trạng thái ghế
        Seat.objects.filter(id__in=selected_seat_ids).update(is_available=False)

        return JsonResponse({
            'status': 'success',
            'created': len(created),
            'ticket_ids': [t.id for t in created],
            'showtime': showtime.date_time.strftime('%Y-%m-%d %H:%M:%S'),
        }, status=201)

    except Room.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Phòng không tồn tại'}, status=404)
    except Movie.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Phim không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    showtimes = Showtime.objects.filter(movie=movie).order_by('date_time')
    return render(request, 'movie_detail.html', {
        'movie': movie,
        'showtimes': showtimes,
        'form': BookTicketForm(),
    })


# ==================== APIs ====================

def api_movies(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    data = list(Movie.objects.values('id', 'title', 'genre', 'duration', 'director', 'release_date'))
    return JsonResponse({'results': data})


def api_showtimes(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    qs = Showtime.objects.select_related('movie', 'room').all()
    movie_id = request.GET.get('movie_id')
    room_id = request.GET.get('room_id')
    date = request.GET.get('date')
    if movie_id:
        qs = qs.filter(movie_id=movie_id)
    if room_id:
        qs = qs.filter(room_id=room_id)
    if date:
        qs = qs.filter(date_time__date=date)
    results = [{
        'id': st.id,
        'movie_id': st.movie_id,
        'movie_title': st.movie.title,
        'room_id': st.room_id,
        'room_name': st.room.name,
        'date_time': st.date_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for st in qs.order_by('date_time')]
    return JsonResponse({'results': results})


def api_seats(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    movie_id = request.GET.get('movie_id')
    room_id = request.GET.get('room_id')
    dt_str = request.GET.get('date_time')

    if not room_id:
        return JsonResponse({'detail': 'room_id is required'}, status=400)

    # toàn bộ ghế của phòng (để front-end tự đánh dấu)
    seats_qs = Seat.objects.filter(room_id=room_id).values('id', 'seat_number')
    available = list(seats_qs)

    # nếu có đủ tham số → loại ghế đã đặt ở suất đó
    if movie_id and dt_str:
        dt = _parse_dt_loose(dt_str)
        if not dt:
            return JsonResponse({'detail': 'Invalid date_time format'}, status=400)
        if settings.USE_TZ and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        start = dt - timedelta(minutes=1)
        end = dt + timedelta(minutes=1)

        booked_ids = set(
            Ticket.objects
            .filter(movie_id=movie_id, room_id=room_id, date_time__range=(start, end))
            .values_list('seat_id', flat=True)
        )
        available = [s for s in available if s['id'] not in booked_ids]

    # trả về cả id và số ghế
    return JsonResponse({'available': sorted(available, key=lambda x: x['seat_number'])})


@csrf_exempt
@transaction.atomic
def api_create_ticket(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    import json
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    required = ['user_id', 'movie_id', 'room_id', 'date_time', 'seats']
    if not all(k in payload for k in required):
        return JsonResponse({'detail': f'Missing fields. Required: {required}'}, status=400)

    user_id = payload['user_id']
    movie_id = payload['movie_id']
    room_id = payload['room_id']
    dt_str = payload['date_time']
    seats_req = payload['seats'] or []

    if not CustomUser.objects.filter(id=user_id).exists():
        return JsonResponse({'detail': 'User not found'}, status=404)
    if not Movie.objects.filter(id=movie_id).exists():
        return JsonResponse({'detail': 'Movie not found'}, status=404)
    if not Room.objects.filter(id=room_id).exists():
        return JsonResponse({'detail': 'Room not found'}, status=404)
    if not isinstance(seats_req, list) or len(seats_req) == 0:
        return JsonResponse({'detail': 'seats must be a non-empty list of seat_number'}, status=400)

    dt = _parse_dt_loose(dt_str)
    if not dt:
        return JsonResponse({'detail': 'Invalid date_time format'}, status=400)
    if settings.USE_TZ and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    start = dt - timedelta(minutes=1)
    end = dt + timedelta(minutes=1)

    showtime = Showtime.objects.filter(movie_id=movie_id, room_id=room_id, date_time__range=(start, end)).first()
    if not showtime:
        return JsonResponse({'detail': 'Showtime not found'}, status=404)

    seats_qs = Seat.objects.select_for_update().filter(room_id=room_id, seat_number__in=seats_req, is_available=True)
    if seats_qs.count() != len(set(seats_req)):
        return JsonResponse({'detail': 'Some seats not found or not available in this room'}, status=400)

    collisions = Ticket.objects.filter(
        movie_id=movie_id,
        room_id=room_id,
        date_time__range=(start, end),
        seat_id__in=seats_qs.values_list('id', flat=True)
    ).exists()
    if collisions:
        return JsonResponse({'detail': 'Some seats are already booked'}, status=409)

    created_ids = []
    for seat in seats_qs:
        t = Ticket.objects.create(
            user_id=user_id,
            movie_id=movie_id,
            room_id=room_id,
            seat_id=seat.id,
            date_time=showtime.date_time,
            price=100000,
            type='Adult'
        )
        created_ids.append(t.id)

    Seat.objects.filter(id__in=seats_qs.values_list('id', flat=True)).update(is_available=False)
    return JsonResponse({'status': 'success', 'created_ticket_ids': created_ids}, status=201)


def get_seats(request, movie_id):
    """
    Trang HTML hiển thị chọn ghế cho 1 phim (nếu cần render server).
    Có thể nhận thêm room_id và date_time qua query.
    """
    movie = get_object_or_404(Movie, id=movie_id)
    room_id = request.GET.get('room_id')
    dt_str = request.GET.get('date_time')

    showtimes = (Showtime.objects
                 .select_related('room')
                 .filter(movie=movie)
                 .order_by('date_time'))

    seats = []
    room = None

    if room_id and dt_str:
        room = get_object_or_404(Room, id=room_id)
        booked_ids = Ticket.objects.filter(
            movie_id=movie_id, room_id=room_id, date_time=dt_str
        ).values_list('seat_id', flat=True)
        seats = (Seat.objects
                 .filter(room=room, is_available=True)
                 .exclude(id__in=booked_ids)
                 .order_by('seat_number'))

    return render(request, 'book_ticket/seats.html', {
        'movie': movie,
        'room': room,
        'date_time': dt_str,
        'showtimes': showtimes,
        'seats': seats,
        'form': BookTicketForm(),
    })


# ==================== SEARCH ====================

def search_movies(request):
    q = (request.GET.get('q') or "").strip()
    movies = Movie.objects.none()

    if q:
        movies = Movie.objects.filter(
            Q(title__icontains=q) |
            Q(genre__icontains=q) |
            Q(director__icontains=q) |
            Q(description__icontains=q)
        ).order_by('title')

    return render(request, 'movie_search.html', {
        'q': q,
        'movies': movies
    })
