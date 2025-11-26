# ==================== FIXED VERSION với @api_view ====================

from .models import *
from .forms import *

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from datetime import datetime, timedelta

# Swagger + DRF imports
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status as http_status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def _parse_dt_loose(s: str):
    """Parse nhiều format ngày-giờ"""
    if not s:
        return None
    s = s.strip()
    s = s.replace(" SA", " AM").replace(" CH", " PM").replace("SA", "AM").replace("CH", "PM")
    
    dt = parse_datetime(s)
    if dt:
        return dt
    
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %I:%M %p",
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


# ==================== MAIN VIEWS (giữ nguyên) ====================

def homepage(request):
    if request.user.is_anonymous:
        return render(request, 'home.html')
    return book_ticket(request)


def book_ticket(request):
    username = getattr(request.user, "username", "")
    name = getattr(request.user, "name", "")
    age = getattr(request.user, "age", "")

    user_tickets = Ticket.objects.filter(user=request.user)
    
    # FIX: Không gán lại vào ticket.date_time
    for ticket in user_tickets:
        ticket.formatted_date = ticket.date_time.strftime('%d/%m/%Y %H:%M:%S')

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
        request.session.set_expiry(1209600)

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
    """Đặt vé qua AJAX với locking đúng"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        room_id = request.POST.get('room_id')
        movie_id = request.POST.get('movie_id')
        selected_seats = (request.POST.getlist('selected_seats[]') 
                         or request.POST.getlist('selected_seats'))
        date_time_str = request.POST.get('date_time')
        qty_str = request.POST.get('quantity')

        if not (room_id and movie_id and date_time_str and selected_seats):
            return JsonResponse({'status': 'error', 'message': 'Thiếu dữ liệu'}, status=400)

        dt = _parse_dt_loose(date_time_str)
        if not dt:
            return JsonResponse({'status': 'error', 'message': 'date_time không hợp lệ'}, status=400)
        if settings.USE_TZ and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        try:
            quantity = int(qty_str) if qty_str else len(selected_seats)
        except:
            return JsonResponse({'status': 'error', 'message': 'quantity không hợp lệ'}, status=400)

        selected_seat_ids = list({int(s) for s in selected_seats})
        if len(selected_seat_ids) != quantity:
            return JsonResponse({'status': 'error', 
                               'message': 'Số ghế phải bằng số lượng'}, status=400)

        room = Room.objects.select_for_update().get(id=room_id)
        movie = Movie.objects.get(id=movie_id)

        start = dt - timedelta(minutes=1)
        end = dt + timedelta(minutes=1)
        
        showtime = (Showtime.objects
                   .filter(movie_id=movie_id, room_id=room_id, 
                          date_time__range=(start, end))
                   .first())
        if not showtime:
            return JsonResponse({'status': 'error', 
                               'message': 'Không tìm thấy suất chiếu'}, status=404)

        seats_qs = (Seat.objects
                   .select_for_update()
                   .filter(id__in=selected_seat_ids, room_id=room_id))
        
        if seats_qs.count() != len(selected_seat_ids):
            return JsonResponse({'status': 'error', 
                               'message': 'Ghế không tồn tại'}, status=400)

        collisions = Ticket.objects.filter(
            movie_id=movie_id,
            room_id=room_id,
            date_time__range=(start, end),
            seat_id__in=selected_seat_ids
        ).values_list('seat_id', flat=True)
        
        if collisions:
            collision_list = list(collisions)
            return JsonResponse({'status': 'error',
                               'message': f'Ghế đã được đặt: {collision_list}'}, 
                              status=409)

        to_create = [
            Ticket(
                movie=movie,
                user=request.user,
                room=room,
                seat=seat,
                price=100000,
                type='Adult',
                date_time=showtime.date_time
            )
            for seat in seats_qs
        ]
        created = Ticket.objects.bulk_create(to_create)

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


# ==================== APIs với @api_view ====================

@swagger_auto_schema(
    method='get',
    tags=['Movies'],
    operation_summary='Danh sách phim',
    operation_description='Trả về danh sách tất cả phim với các trường cơ bản.',
    responses={
        200: openapi.Response(
            description='Danh sách phim',
            examples={
                'application/json': {
                    'results': [
                        {
                            'id': 1,
                            'title': 'Avengers',
                            'genre': 'Action',
                            'duration': 120,
                            'director': 'Russo Brothers',
                            'release_date': '2025-05-01'
                        }
                    ]
                }
            }
        ),
    }
)
@api_view(['GET'])
def api_movies(request):
    data = list(Movie.objects.values(
        'id', 'title', 'genre', 'duration', 'director', 'release_date'
    ))
    return Response({'results': data})


@swagger_auto_schema(
    method='get',
    tags=['Showtimes'],
    operation_summary='Danh sách suất chiếu',
    operation_description='Lọc theo movie_id, room_id, date (YYYY-MM-DD). Kết quả sắp xếp tăng dần.',
    manual_parameters=[
        openapi.Parameter('movie_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='ID phim'),
        openapi.Parameter('room_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='ID phòng'),
        openapi.Parameter('date', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Ngày (YYYY-MM-DD)'),
    ],
    responses={
        200: openapi.Response(
            description='Danh sách suất chiếu',
            examples={
                'application/json': {
                    'results': [
                        {
                            'id': 10,
                            'movie_id': 1,
                            'movie_title': 'Avengers',
                            'room_id': 2,
                            'room_name': 'Room 2',
                            'date_time': '2025-10-31 11:40:00'
                        }
                    ]
                }
            }
        ),
    }
)
@api_view(['GET'])
def api_showtimes(request):
    qs = Showtime.objects.select_related('movie', 'room').all()
    
    if movie_id := request.GET.get('movie_id'):
        qs = qs.filter(movie_id=movie_id)
    if room_id := request.GET.get('room_id'):
        qs = qs.filter(room_id=room_id)
    if date := request.GET.get('date'):
        qs = qs.filter(date_time__date=date)
    
    results = [{
        'id': st.id,
        'movie_id': st.movie_id,
        'movie_title': st.movie.title,
        'room_id': st.room_id,
        'room_name': st.room.name,
        'date_time': st.date_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for st in qs.order_by('date_time')]
    
    return Response({'results': results})


@swagger_auto_schema(
    method='get',
    tags=['Seats'],
    operation_summary='Danh sách ghế còn trống',
    operation_description='Trả về toàn bộ ghế của phòng. Nếu có movie_id + date_time thì loại ghế đã đặt.',
    manual_parameters=[
        openapi.Parameter('room_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description='ID phòng'),
        openapi.Parameter('movie_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='ID phim'),
        openapi.Parameter('date_time', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Thời điểm suất chiếu'),
    ],
    responses={
        200: openapi.Response(
            description='Danh sách ghế',
            examples={
                'application/json': {
                    'available': [
                        {'id': 101, 'seat_number': 1},
                        {'id': 102, 'seat_number': 2},
                    ]
                }
            }
        ),
        400: 'Thiếu room_id',
    }
)
@api_view(['GET'])
def api_seats(request):
    movie_id = request.GET.get('movie_id')
    room_id = request.GET.get('room_id')
    dt_str = request.GET.get('date_time')

    if not room_id:
        return Response({'detail': 'room_id is required'}, status=http_status.HTTP_400_BAD_REQUEST)

    seats_qs = Seat.objects.filter(room_id=room_id).values('id', 'seat_number')
    available = list(seats_qs)

    if movie_id and dt_str:
        dt = _parse_dt_loose(dt_str)
        if not dt:
            return Response({'detail': 'Invalid date_time format'}, status=http_status.HTTP_400_BAD_REQUEST)
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

    return Response({'available': sorted(available, key=lambda x: x['seat_number'])})


@swagger_auto_schema(
    method='post',
    tags=['Tickets'],
    operation_summary='Tạo vé mới',
    operation_description='Tạo vé cho một suất chiếu. Hệ thống khóa bản ghi ghế để tránh đặt trùng.',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['user_id', 'movie_id', 'room_id', 'date_time', 'seats'],
        properties={
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID người dùng'),
            'movie_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID phim'),
            'room_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID phòng'),
            'date_time': openapi.Schema(type=openapi.TYPE_STRING, description='Thời điểm suất chiếu'),
            'seats': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description='Danh sách seat_number cần đặt'
            ),
        },
        example={
            'user_id': 1,
            'movie_id': 2,
            'room_id': 3,
            'date_time': '2025-10-31 11:40:00',
            'seats': [1, 2]
        }
    ),
    responses={
        201: openapi.Response(
            description='Tạo vé thành công',
            examples={'application/json': {'status': 'success', 'created_ticket_ids': [11, 12]}}
        ),
        400: 'Dữ liệu không hợp lệ',
        404: 'Không tìm thấy user/phim/phòng/suất',
        409: 'Ghế đã bị đặt',
    }
)
@api_view(['POST'])
@transaction.atomic
def api_create_ticket(request):
    payload = request.data

    required = ['user_id', 'movie_id', 'room_id', 'date_time', 'seats']
    if not all(k in payload for k in required):
        return Response({'detail': f'Missing: {required}'}, status=http_status.HTTP_400_BAD_REQUEST)

    user_id = payload['user_id']
    movie_id = payload['movie_id']
    room_id = payload['room_id']
    dt_str = payload['date_time']
    seats_req = payload['seats'] or []

    # Validate existence
    try:
        user = CustomUser.objects.get(id=user_id)
        movie = Movie.objects.get(id=movie_id)
        room = Room.objects.select_for_update().get(id=room_id)
    except CustomUser.DoesNotExist:
        return Response({'detail': 'User not found'}, status=http_status.HTTP_404_NOT_FOUND)
    except Movie.DoesNotExist:
        return Response({'detail': 'Movie not found'}, status=http_status.HTTP_404_NOT_FOUND)
    except Room.DoesNotExist:
        return Response({'detail': 'Room not found'}, status=http_status.HTTP_404_NOT_FOUND)

    if not isinstance(seats_req, list) or len(seats_req) == 0:
        return Response({'detail': 'seats must be non-empty list'}, status=http_status.HTTP_400_BAD_REQUEST)

    dt = _parse_dt_loose(dt_str)
    if not dt:
        return Response({'detail': 'Invalid date_time'}, status=http_status.HTTP_400_BAD_REQUEST)
    if settings.USE_TZ and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    start = dt - timedelta(minutes=1)
    end = dt + timedelta(minutes=1)

    showtime = Showtime.objects.filter(
        movie_id=movie_id, room_id=room_id, date_time__range=(start, end)
    ).first()
    if not showtime:
        return Response({'detail': 'Showtime not found'}, status=http_status.HTTP_404_NOT_FOUND)

    # Khóa ghế
    seats_qs = Seat.objects.select_for_update().filter(
        room_id=room_id, 
        seat_number__in=seats_req
    )
    
    if seats_qs.count() != len(set(seats_req)):
        return Response({'detail': 'Some seats not found'}, status=http_status.HTTP_400_BAD_REQUEST)

    # Kiểm tra collision
    seat_ids = list(seats_qs.values_list('id', flat=True))
    collisions = Ticket.objects.filter(
        movie_id=movie_id,
        room_id=room_id,
        date_time__range=(start, end),
        seat_id__in=seat_ids
    ).exists()
    
    if collisions:
        return Response({'detail': 'Seats already booked'}, status=http_status.HTTP_409_CONFLICT)

    # Tạo vé
    created_ids = []
    for seat in seats_qs:
        t = Ticket.objects.create(
            user=user,
            movie=movie,
            room=room,
            seat=seat,
            date_time=showtime.date_time,
            price=100000,
            type='Adult'
        )
        created_ids.append(t.id)

    Seat.objects.filter(id__in=seat_ids).update(is_available=False)
    
    return Response({
        'status': 'success', 
        'created_ticket_ids': created_ids
    }, status=http_status.HTTP_201_CREATED)


# ==================== OTHER VIEWS ====================

def get_seats(request, movie_id):
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