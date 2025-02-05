import os
import django
import datetime
from datetime import datetime
import subprocess
import signal
import psutil

# Mengatur variabel lingkungan untuk pengaturan Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MultiLiveStreaming.settings')  # Ganti 'your_project' dengan nama proyek Anda

# Inisialisasi Django
django.setup()

import schedule
import time
from streaming.models import LiveStreamingSchedule  # Pastikan ini diimpor setelah django.setup()

def job():
    # Memulai streaming
    schedules = LiveStreamingSchedule.objects.filter(status="Dijadwalkan")
    for schedule in schedules:
        time_format = "%Y-%m-%d %H:%M:00"  # Contoh format: 2025-02-05 03:33:00
        
        # Mengonversi start_time dan waktu sekarang ke format yang sama
        formatted_start_time = schedule.start_time.strftime(time_format)
        formatted_now = datetime.now().strftime(time_format).split('.')[0]

        print(f"Schedule Start Time: {formatted_start_time} sekarang {formatted_now}")
        
        if formatted_start_time <= formatted_now:
            schedule.status = "Ongoing"
            schedule.save()
            ffmpeg_command = [
                'ffmpeg',
                '-re',
                '-stream_loop', '-1',
                '-i', schedule.video.file_path,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-b:v', '2500k',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-f', 'flv',
                f'rtmp://a.rtmp.youtube.com/live2/{schedule.streaming_key}'
            ]
            
            process = subprocess.Popen(ffmpeg_command)
            pid_file = f'ffmpeg_pid_{schedule.video.id}.txt'
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))  # Simpan PID ke file
                
            print(f"Streaming dimulai dengan PID {process.pid}")
            print(f"FFmpeg command: {' '.join(ffmpeg_command)}")

    # Menghentikan streaming
    ongoing_schedules = LiveStreamingSchedule.objects.filter(status="Ongoing")
    for schedule in ongoing_schedules:
        time_format = "%Y-%m-%d %H:%M:%S"  # Contoh format: 2025-02-05 03:33:00
        
        # Mengonversi start_time dan waktu sekarang ke format yang sama
        formatted_end_time = schedule.end_time.strftime(time_format)
        formatted_now = datetime.now().strftime(time_format)

        print(f"Schedule End Time: {formatted_end_time} sekarang {formatted_now}")

        if formatted_end_time <= formatted_now:
            pid_file = f'ffmpeg_pid_{schedule.video.id}.txt'

            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Cek apakah proses masih berjalan
                if psutil.pid_exists(pid):
                    print(f"🔴 Menghentikan proses dengan PID {pid}...")
                    os.kill(pid, signal.SIGTERM)  # Gunakan SIGTERM agar lebih aman
                    print(f"✅ Proses dengan PID {pid} berhasil dihentikan.")
                else:
                    print(f"⚠️ Proses PID {pid} tidak ditemukan. Mungkin sudah mati.")

                os.remove(pid_file)  # Hapus file PID setelah proses dihentikan

            else:
                print("❌ PID file tidak ditemukan. Mungkin streaming sudah dihentikan.")

            # Perbarui status di database
            schedule.status = "Dihentikan"
            schedule.save()
# Menjadwalkan tugas
schedule.every(10).seconds.do(job)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()