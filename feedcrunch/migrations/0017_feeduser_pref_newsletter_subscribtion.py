# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-02 13:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedcrunch', '0016_feeduser_social_stackoverflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='feeduser',
            name='pref_newsletter_subscribtion',
            field=models.BooleanField(default=True),
        ),
    ]
