import subprocess
from django.http import JsonResponse
from streaming.models import LiveStreamingSchedule, Video
from django.utils import timezone
from celery import shared_task

def start_live_streaming(video, streaming_key):
    print(f"Streaming Data Sudah Diterima")
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

@shared_task(bind=True, max_retries=3)
def scheduled_streaming(self, video_id, streaming_key):
    try:
        print(f"Video ID: {video_id}, Streaming Key: {streaming_key}")
        video = Video.objects.get(id=video_id)
        start_live_streaming(video, streaming_key)
        print(f"Streaming Sudah Dimulai")
    except Video.DoesNotExist:
        print(f"Video dengan ID {video_id} tidak ditemukan.")
        raise self.retry(exc=Exception("Video tidak ditemukan"))
    except Exception as e:
        print(f"Error occurred: {e}")
        raise self.retry(exc=e)

def start_scheduled_streaming(video_id, streaming_key):
    print(f"Ada Dijadwal")
    try:
        schedule = LiveStreamingSchedule.objects.get(id=video_id)
        
        # Cek status dan waktu
        now = timezone.now()
        if schedule.status == "Dijadwalkan" and schedule.start_time <= now <= schedule.end_time:
            # Panggil tugas Celery untuk memulai streaming
            scheduled_streaming.delay(schedule.video.id, streaming_key)

            # Update status ke "Queued"
            schedule.status = "Queued"
            schedule.save()

            return JsonResponse({"message": "Streaming ditambahkan ke queue"})
        else:
            return JsonResponse({"error": "Streaming tidak dijadwalkan atau waktu tidak tepat"}, status=400)
    except LiveStreamingSchedule.DoesNotExist:
        return JsonResponse({"error": "Jadwal tidak ditemukan"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@shared_task
def check_scheduled_streamings():
    now = timezone.now()
    schedules = LiveStreamingSchedule.objects.filter(status="Dijadwalkan", start_time__lte=now)
    print(f"Schedules found: {schedules.count()}")