from .models import *
from .forms import *
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from datetime import datetime
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.sessions.models import Session
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.utils import timezone
from .models import Movie, Showtime
from .forms import BookTicketForm  

def homepage(request):
    if request.user.is_anonymous:
        return render(request, 'home.html') 
    # return HttpResponse(request.user)
    return book_ticket(request) # if user is logged in, redirect to book_ticket page
    
def book_ticket(request):
    username = request.user.username
    name = request.user.name
    age = request.user.age
    user_tickets = Ticket.objects.filter(user=request.user)
    for ticket in user_tickets:
        ticket.date_time = datetime.strptime(str(ticket.date_time).split('+')[0], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
    return render(request, 'book_ticket.html', {'username': username, 'name': name, 'age': age, 'user_tickets': user_tickets})
   
def user_login(request):
    show_login_form = True # to show login form 
    if request.method != 'POST':
        messages.error(request,"Vui lòng đăng nhập hoặc đăng ký để đặt vé")
        return render(request, 'home.html', {'show_login_form': show_login_form})
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('rememberMe')
        
        if remember_me == 'on':
            request.session.set_expiry(1209600) # remember user account for 14 days
        
        if not username or not password:
            messages.error(request, "Vui lòng nhập tên tài khoản và mật khẩu!")
            return render(request, 'home.html', {'show_login_form': show_login_form})
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_staff == True:
                return redirect('/admin/')
            return book_ticket(request)
        else:
            messages.error(request, "Tên tài khoản hoặc mật khẩu không đúng!")
            return render(request, 'home.html', {'show_login_form': show_login_form})
        
def user_logout(request):
    logout(request)
    return homepage(request)
    
def user_register(request):
    show_register_form = True # to show register form
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
            messages.error(request, "Tên đăng nhập đã tồn tại! Vui lòng chọn tên đăng nhập khác!")
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
        register_sucess = True # to show register success message
        show_register_form = False
        messages.success(request, "Đăng ký tài khoản thành công!")
        return render(request, 'home.html', {'register_sucess': register_sucess, 'show_register_form': show_register_form})
    else:
        return render(request, 'home.html', {'show_register_form': show_register_form})
    
def movie_schedule(request):
    now = timezone.now()

    upcoming = (Showtime.objects
                .select_related('movie','room')
                .filter(date_time__gte=now)
                .order_by('date_time'))

    past = (Showtime.objects
            .select_related('movie','room')
            .filter(date_time__lt=now)
            .order_by('-date_time')[:50])  # giới hạn 50 suất đã chiếu gần nhất
    form = BookTicketForm()
    return render(request, 'movie_schedule.html', {
        'upcoming': upcoming,
        'past': past,
        'form': form,
    })
def contact(request):
    return render(request, 'contact.html')

def movie_list(request):
    form = BookTicketForm()
    movies = Movie.objects.all()
    rooms = Room.objects.all()
    seats = Seat.objects.all()
    return render(request, 'movie_list.html', {'movies': movies, 'rooms': rooms, 'seats': seats, 'form': form})

def get_seats(request):
    room_id = request.GET.get('room_id')
    seats = Seat.objects.filter(room_id=room_id)
    return render(request, 'book_ticket/seat_selection.html', {'seats': seats})

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotAllowed
from django.contrib import messages

@login_required
def user_booking(request):
    if request.method == 'GET':
        movie_id = request.GET.get('movie_id')
        room_id  = request.GET.get('room_id')
        dt_str   = request.GET.get('date_time')  # 'YYYY-MM-DD HH:MM:SS'

        if not (movie_id and room_id and dt_str):
            messages.error(request, "Thiếu tham số đặt vé.")
            return redirect('movie_schedule')

        movie = get_object_or_404(Movie, id=movie_id)
        room  = get_object_or_404(Room, id=room_id)

        # Ghế còn trống cho đúng suất (movie, room, date_time)
        booked_ids = Ticket.objects.filter(
            movie_id=movie_id, room_id=room_id, date_time=dt_str
        ).values_list('seat_id', flat=True)

        seats = (Seat.objects
                 .filter(room=room, is_available=True)
                 .exclude(id__in=booked_ids)
                 .order_by('seat_number'))

        return render(request, 'book_ticket.html', {
            'movie': movie,
            'room': room,
            'date_time': dt_str,
            'seats': seats,
        })

    elif request.method == 'POST':
        # == GIỮ logic cũ của bạn, chỉ đổi key input cho khớp template ==
        room = Room.objects.get(id=request.POST.get('room_id'))
        type = request.POST.get('type')
        date_time = request.POST.get('date_time')
        movie = Movie.objects.get(id=request.POST.get('movie_id'))
        selected_seats = request.POST.getlist('selected_seats[]')
        selected_seats = list(set(selected_seats))

        user = request.user

        tickets = []
        for seat_id in selected_seats:
            seat = Seat.objects.get(id=seat_id)
            if Ticket.objects.filter(seat=seat, movie=movie, room=room, date_time=date_time).exists():
                continue
            ticket = Ticket(
                movie=movie, user=user, room=room, seat=seat,
                price=100000 if type == 'Adult' else 50000,
                type=type, date_time=date_time,
            )
            tickets.append(ticket)

        Ticket.objects.bulk_create(tickets)
        Seat.objects.filter(id__in=selected_seats).update(is_available=False)
        messages.success(request, "Đặt vé thành công!")
        return redirect('movie_schedule')

    else:
        return HttpResponseNotAllowed(['GET', 'POST'])
def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    showtimes = Showtime.objects.filter(movie=movie).order_by('date_time')
    return render(request, 'movie_detail.html', {'movie': movie, 'showtimes': showtimes})
# === JSON API cho Postman ===
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime

def api_movies(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    data = list(Movie.objects.values('id','title','genre','duration','director','release_date'))
    return JsonResponse({'results': data})

def api_showtimes(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    qs = Showtime.objects.select_related('movie','room').all()
    movie_id = request.GET.get('movie_id')
    room_id  = request.GET.get('room_id')
    date     = request.GET.get('date')  # YYYY-MM-DD

    if movie_id: qs = qs.filter(movie_id=movie_id)
    if room_id:  qs = qs.filter(room_id=room_id)
    if date:     qs = qs.filter(date_time__date=date)

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
    """
    Trả về danh sách seat_number đang trống cho 1 suất chiếu xác định bởi:
    ?movie_id=&room_id=&date_time=YYYY-MM-DD HH:MM:SS
    """
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    movie_id = request.GET.get('movie_id')
    room_id  = request.GET.get('room_id')
    dt_str   = request.GET.get('date_time')  # 'YYYY-MM-DD HH:MM:SS'
    if not (movie_id and room_id and dt_str):
        return JsonResponse({'detail': 'movie_id, room_id, date_time are required'}, status=400)

    # Ghế trong phòng đang đánh dấu available (theo schema hiện tại)
    room_seats = Seat.objects.filter(room_id=room_id, is_available=True).values('id','seat_number')
    room_seat_ids = [s['id'] for s in room_seats]

    # Ghế đã book trùng (movie, room, date_time)
    booked_ids = set(
        Ticket.objects.filter(
            movie_id=movie_id, room_id=room_id, date_time=dt_str
        ).values_list('seat_id', flat=True)
    )

    available = [s for s in room_seats if s['id'] not in booked_ids]
    seat_numbers = sorted([s['seat_number'] for s in available])
    return JsonResponse({'available_seats': seat_numbers})

@csrf_exempt
@transaction.atomic
def api_create_ticket(request):
    """
    POST JSON:
    {
      "user_id": 1,
      "movie_id": 2,
      "room_id": 3,
      "date_time": "2024-06-07 09:23:00",
      "seats": [1,2]   # danh sách seat_number
    }
    """
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    import json
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    required = ['user_id','movie_id','room_id','date_time','seats']
    if not all(k in payload for k in required):
        return JsonResponse({'detail': f'Missing fields. Required: {required}'}, status=400)

    user_id   = payload['user_id']
    movie_id  = payload['movie_id']
    room_id   = payload['room_id']
    dt_str    = payload['date_time']
    seats_req = payload['seats'] or []

    # Validate cơ bản
    if not CustomUser.objects.filter(id=user_id).exists():
        return JsonResponse({'detail': 'User not found'}, status=404)
    if not Movie.objects.filter(id=movie_id).exists():
        return JsonResponse({'detail': 'Movie not found'}, status=404)
    if not Room.objects.filter(id=room_id).exists():
        return JsonResponse({'detail': 'Room not found'}, status=404)
    if not Showtime.objects.filter(movie_id=movie_id, room_id=room_id, date_time=dt_str).exists():
        return JsonResponse({'detail': 'Showtime not found'}, status=404)
    if not isinstance(seats_req, list) or len(seats_req) == 0:
        return JsonResponse({'detail': 'seats must be a non-empty list of seat_number'}, status=400)

    # Ánh xạ seat_number -> seat_id (và đang available theo schema hiện tại)
    seats_qs = Seat.objects.select_for_update().filter(
        room_id=room_id, seat_number__in=seats_req, is_available=True
    )
    if seats_qs.count() != len(set(seats_req)):
        return JsonResponse({'detail': 'Some seats not found or not available in this room'}, status=400)

    # Chống double-booking trong cùng (movie,room,date_time)
    collisions = Ticket.objects.filter(
        movie_id=movie_id, room_id=room_id, date_time=dt_str,
        seat_id__in=seats_qs.values_list('id', flat=True)
    ).exists()
    if collisions:
        return JsonResponse({'detail': 'Some seats are already booked'}, status=409)

    # Tạo vé
    created_ids = []
    for seat in seats_qs:
        t = Ticket.objects.create(
            user_id=user_id, movie_id=movie_id, room_id=room_id,
            seat_id=seat.id, date_time=dt_str, price=100000, type='Adult'
        )
        created_ids.append(t.id)

    # (Giữ nguyên logic hiện tại của project) đánh dấu seat không còn available
    Seat.objects.filter(id__in=seats_qs.values_list('id', flat=True)).update(is_available=False)

    return JsonResponse({'status': 'success', 'created_ticket_ids': created_ids}, status=201)

