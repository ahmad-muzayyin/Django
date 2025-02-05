from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

class Video(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)  # ForeignKey ke User
    drive_link = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    size_video = models.BigIntegerField()
    file_path = models.TextField()
    link_video_id = models.CharField(max_length=255)

    def __str__(self):
        return self.file_name

class LiveStreamingSchedule(models.Model):
    video = models.OneToOneField('Video', on_delete=models.CASCADE)  # Kembalikan ke OneToOneField untuk konsistensi
    streaming_key = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[
        ('Dijadwalkan', 'Dijadwalkan'),
        ('Ongoing', 'Ongoing'),
        ('Selesai', 'Selesai')
    ])  # ✅ Perbaikan typo (tambahkan koma)

    def __str__(self):
        return f"Live {self.video.file_name} - {self.status}"
    def __str__(self):
        return f"Live {self.video.file_name} - {self.status}"

