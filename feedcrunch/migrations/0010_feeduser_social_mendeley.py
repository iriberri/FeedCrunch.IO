# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-28 10:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedcrunch', '0009_feeduser-interest-Many2Many-Blankable'),
    ]

    operations = [
        migrations.AddField(
            model_name='feeduser',
            name='social_mendeley',
            field=models.URLField(blank=True, default='', max_length=60, null=True),
        ),
    ]
