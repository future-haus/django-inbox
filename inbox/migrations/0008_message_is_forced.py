# Generated by Django 3.0.10 on 2020-10-06 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inbox', '0007_auto_20200521_1246'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_forced',
            field=models.BooleanField(default=False),
        ),
    ]
