from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()

# Cek apakah User belum terdaftar, lalu register
from django.contrib.admin.sites import AlreadyRegistered

try:
    admin.site.register(User)
    admin.site.register(Video)
    admin.site.register(LiveStreamingSchedule)
except AlreadyRegistered:
    pass  # Jika sudah terdaftar, biarkan saja

