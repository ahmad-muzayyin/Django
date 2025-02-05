import os
import gdown
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Video, LiveStreamingSchedule
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout
from celery import shared_task
from datetime import datetime
from django.utils import timezone
import subprocess
from django.conf import settings
import pytz
import requests
import psutil  # Pastikan sudah install: pip install psutil
from django.contrib.auth import logout as auth_logout


# Halaman login
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')  # Setelah login, ke dashboard
            else:
                return HttpResponse("Login gagal. Silakan coba lagi.")
        else:
            return HttpResponse("Form tidak valid. Silakan coba lagi.")
    else:
        form = AuthenticationForm()
    return render(request, 'streaming/login.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user
    active_live_streams = LiveStreamingSchedule.objects.filter(status="Ongoing", video__user=user).count()
    scheduled_live_streams = LiveStreamingSchedule.objects.filter(status="Dijadwalkan", video__user=user).count()
    completed_live_streams = LiveStreamingSchedule.objects.filter(status="Dihentikan", video__user=user).count()
    uploaded_videos = Video.objects.filter(user=user).count()
    return render(request, 'streaming/dashboard.html', {'active_live_streams': active_live_streams, 'scheduled_live_streams': scheduled_live_streams, 'completed_live_streams': completed_live_streams, 'uploaded_videos': uploaded_videos})

from django.shortcuts import render
from .models import Video

def video_list(request):
    filter_option = request.GET.get('filter', 'all')  # Ambil filter dari query parameter
    if filter_option == 'live':
        videos = Video.objects.filter(livestreamingschedule__status='Ongoing')
    elif filter_option == 'scheduled':
        videos = Video.objects.filter(livestreamingschedule__status='Dijadwalkan')
    elif filter_option == 'completed':
        videos = Video.objects.filter(livestreamingschedule__status='Completed')
    else:
        videos = Video.objects.all()  # Ambil semua video jika tidak ada filter

    return render(request, 'streaming/video_list.html', {'videos': videos})

@login_required
def index(request):
    """Menampilkan halaman utama"""
    return render(request, 'streaming/index.html')

# Fungsi untuk menampilkan form input URL
@login_required
def add_video(request):
    if request.method == "POST":
        drive_link = request.POST['drive_link']
        file_name = f"{drive_link.split('/')[-2]}.mp4"  # Menggunakan ID link untuk penamaan file

        # Tidak ada perubahan pada bagian ini karena tidak ada instruksi untuk mengubahnya
        response = download_and_save_video(request, drive_link, file_name)
        if response.status_code == 200:
            # Menyimpan detail video ke database
            video_dir = os.path.join(settings.BASE_DIR, 'media/videos')
            file_path = os.path.join(video_dir, file_name)
            user = request.user if request.user.is_authenticated else None
            # Menggunakan user yang autentikasi untuk menghindari ValueError
            if user:
                video = Video(
                    drive_link=drive_link,
                    file_name=file_name,
                    user=user,  # Ambil objek User asli
                    size_video=os.path.getsize(file_path),
                    file_path=file_path,
                    link_video_id=drive_link.split('/d/')[1].split('/')[0]
                )
                video.save()
                return redirect('daftar_video')  # Mengarahkan ke daftar video setelah video berhasil ditambahkan
            else:
                return HttpResponse("Tidak ada pengguna yang terautentikasi.")
        else:
            return response

    return render(request, 'streaming/add_video.html')

# Fungsi untuk mendownload dan menyimpan video
@login_required
def download_and_save_video(request, drive_link, file_name):
    try:
        # Ekstrak fileId dari link
        file_id = drive_link.split('/d/')[1].split('/')[0]
        download_url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={settings.GOOGLE_API_KEY}'
        
        # Memastikan direktori 'media/videos' ada
        video_dir = os.path.join('media/videos')
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)

        # Path untuk menyimpan file
        file_path = os.path.join(video_dir, file_name)

        # Mengirim permintaan GET untuk mengunduh file
        response = requests.get(download_url, stream=True)

        # Mengecek jika request berhasil
        if response.status_code == 200:
            # Menyimpan video ke direktori lokal
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return HttpResponse(f'Video berhasil diunduh dan disimpan sebagai {file_name}.')
        else:
            return HttpResponse(f'Gagal mengunduh video. Error: {response.status_code}')
    except Exception as e:
        return HttpResponse(f'Terjadi kesalahan: {str(e)}')


@login_required
def daftar_video(request):
    videos = Video.objects.filter(user=request.user)
    return render(request, 'streaming/list_video.html', {'videos': videos})

@login_required
def live_list(request):
    live_streams = LiveStreamingSchedule.objects.filter(status="Live")
    return render(request, 'streaming/live_list.html', {'live_streams': live_streams})

@login_required
def edit_video(request, id):
    video = Video.objects.get(id=id)
    if request.method == 'POST':
        video.file_name = request.POST.get('file_name')
        video.save()
        return redirect('daftar_video')
    return render(request, 'streaming/edit_video.html', {'video': video})

@login_required
def delete_video(request, id):
    video = Video.objects.get(id=id)
    if video.file_path:
        os.remove(video.file_path)
    video.delete()
    return redirect('daftar_video')


from .tasks import start_scheduled_streaming
@login_required
def start_live(request, id):
    video = Video.objects.get(id=id)
    
    if request.method == 'POST':
        streaming_key = request.POST.get('streaming_key')
        start_time = request.POST.get('start_streaming')
        end_time = request.POST.get('end_streaming')

        def convert_to_datetime(value):
            if value:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M")
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
                dt = dt.astimezone(pytz.timezone('Asia/Jakarta'))
                dt = dt.replace(microsecond=0)  # Remove microseconds
                return dt
            return None

        start_time = convert_to_datetime(start_time)
        end_time = convert_to_datetime(end_time)

        live_schedule, created = LiveStreamingSchedule.objects.get_or_create(
            video=video,
            defaults={
                'streaming_key': streaming_key,
                'start_time': start_time,
                'end_time': end_time,
                'status': "Dijadwalkan"
            }
        )

        if not created:
            if live_schedule.streaming_key == streaming_key:
                live_schedule.status = "Ongoing"
                live_schedule.save()
                start_live_streaming(video, streaming_key)
            else:
                live_schedule.streaming_key = streaming_key
                live_schedule.save()
        else:
            if start_time and end_time:
                live_schedule.status = "Dijadwalkan"
                live_schedule.start_time = start_time
                live_schedule.end_time = end_time
                live_schedule.save()
            else:
                live_schedule.status = "Ongoing"
                live_schedule.save()
                start_live_streaming(video, streaming_key)

        return redirect('daftar_video')

    return HttpResponse("Invalid request", status=400)

@login_required
def edit_schedule(request, id):
    video = Video.objects.get(id=id)
    
    if request.method == 'POST':
        streaming_key = request.POST.get('streaming_key')
        start_time = request.POST.get('start_streaming')
        end_time = request.POST.get('end_streaming')

        def convert_to_datetime(value):
            if value:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M")
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
                dt = dt.astimezone(pytz.timezone('Asia/Jakarta'))
                dt = dt.replace(microsecond=0)  # Remove microseconds
                return dt
            return None

        start_time = convert_to_datetime(start_time)
        end_time = convert_to_datetime(end_time)

        live_schedule, created = LiveStreamingSchedule.objects.get_or_create(
            video=video,
            defaults={
                'streaming_key': streaming_key,
                'start_time': start_time,
                'end_time': end_time,
                'status': "Dijadwalkan"
            }
        )

        if not created:
            if live_schedule.streaming_key == streaming_key:
                live_schedule.status = "Ongoing"
                live_schedule.save()
                start_live_streaming(video, streaming_key)
            else:
                live_schedule.streaming_key = streaming_key
                live_schedule.save()
        else:
            if start_time and end_time:
                live_schedule.status = "Dijadwalkan"
                live_schedule.start_time = start_time
                live_schedule.end_time = end_time
                live_schedule.save()
            else:
                live_schedule.status = "Ongoing"
                live_schedule.save()
                start_live_streaming(video, streaming_key)

        return redirect('daftar_video')

    return HttpResponse("Invalid request", status=400)

import subprocess
import os
import signal

def start_live_streaming(video, streaming_key):
    if video.file_path:
        ffmpeg_command = [
            'ffmpeg',
            '-re',
            '-stream_loop', '-1',
            '-i', video.file_path,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-b:v', '2500k',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-f', 'flv',
            f'rtmp://a.rtmp.youtube.com/live2/{streaming_key}'
        ]
        
        process = subprocess.Popen(ffmpeg_command)
        pid_file = f'ffmpeg_pid_{video.id}.txt'
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))  # Simpan PID ke file
            
        print(f"Streaming dimulai dengan PID {process.pid}")
    else:
        print("Video file path is None")

def stop_live(request, live_id):
    try:
        live = LiveStreamingSchedule.objects.get(id=live_id)
        pid_file = f'ffmpeg_pid_{live.video.id}.txt'

        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # 🔍 Cek apakah proses masih berjalan
            if psutil.pid_exists(pid):
                print(f"🔴 Menghentikan proses dengan PID {pid}...")
                os.kill(pid, signal.SIGTERM)  # Gunakan SIGTERM agar lebih aman
                print(f"✅ Proses dengan PID {pid} berhasil dihentikan.")
            else:
                print(f"⚠️ Proses PID {pid} tidak ditemukan. Mungkin sudah mati.")

            os.remove(pid_file)  # Hapus file PID setelah proses dihentikan

        else:
            print("❌ PID file tidak ditemukan. Mungkin streaming sudah dihentikan.")

        # ✅ Perbarui status di database
        live.status = "Dihentikan"
        live.save()

        return redirect('daftar_video')

    except LiveStreamingSchedule.DoesNotExist:
        print("❌ Live streaming tidak ditemukan.")
        return HttpResponse("Live streaming tidak ditemukan.", status=404)
    except Exception as e:
        print(f"❌ Error saat menghentikan streaming: {e}")
        return HttpResponse(f"Error: {e}", status=500)
    

@login_required
def logout_view(request):
    auth_logout(request)  # Menggunakan fungsi logout dari Django
    return redirect('login')  # Mengarahkan pengguna ke halaman login