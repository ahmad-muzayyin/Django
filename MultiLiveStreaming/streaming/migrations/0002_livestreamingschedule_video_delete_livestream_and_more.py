# Generated by Django 5.1.5 on 2025-02-04 04:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streaming', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LiveStreamingSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('streaming_key', models.CharField(max_length=255)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('Dijadwalkan', 'Dijadwalkan'), ('Ongoing', 'Ongoing'), ('Selesai', 'Selesai')], max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drive_link', models.CharField(max_length=255)),
                ('file_name', models.CharField(max_length=255)),
                ('size_video', models.BigIntegerField()),
                ('file_path', models.TextField()),
                ('link_video_id', models.CharField(max_length=255)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.DeleteModel(
            name='LiveStream',
        ),
        migrations.AddField(
            model_name='livestreamingschedule',
            name='video',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='streaming.video'),
        ),
    ]
