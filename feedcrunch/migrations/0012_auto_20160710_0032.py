# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-09 22:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedcrunch', '0011_feeduser_social_git'),
    ]

    operations = [
        migrations.AddField(
            model_name='feeduser',
            name='company_name',
            field=models.CharField(blank=True, default='Paradise Holy Inc.', max_length=80, null=True),
        ),
        migrations.AddField(
            model_name='feeduser',
            name='company_website',
            field=models.URLField(blank=True, default='http://www.feedcrunch.io/', max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='feeduser',
            name='description',
            field=models.TextField(blank=True, default='Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam dui nisl, aliquam nec quam nec, laoreet porta odio. Morbi ultrices sagittis ligula ut consectetur. Aenean quis facilisis augue. Vestibulum maximus aliquam augue, ut lobortis turpis euismod vel. Sed in mollis tellus, eget eleifend turpis. Vivamus aliquam ornare felis at dignissim. Integer vitae cursus eros, non dignissim dui. Suspendisse porttitor justo nec lacus dictum commodo. Sed in fringilla tortor, at pharetra tortor. Vestibulum tempor sapien id justo molestie imperdiet. Nulla efficitur mattis ante, nec iaculis lorem consequat in. Nullam sit amet diam augue. Nulla ullamcorper imperdiet turpis a maximus. Donec iaculis porttitor ultrices. Morbi lobortis dui molestie ullamcorper varius. Maecenas eu laoreet ipsum orci aliquam.', null=True),
        ),
        migrations.AddField(
            model_name='feeduser',
            name='job',
            field=models.CharField(blank=True, default='Chief Admission Officer at', max_length=80, null=True),
        ),
    ]