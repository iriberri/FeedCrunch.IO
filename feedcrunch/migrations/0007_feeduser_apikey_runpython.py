# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-13 20:39
from __future__ import unicode_literals

from django.db import migrations, models
from feedcrunch.models import FeedUser
import uuid

def gen_uuid(apps, schema_editor):
    MyModel = apps.get_model('feedcrunch', 'feeduser')
    for row in FeedUser.objects.all():
        row.apikey = uuid.uuid4()
        row.save()

class Migration(migrations.Migration):

    dependencies = [
        ('feedcrunch', '0006_feeduser_apikey'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]
