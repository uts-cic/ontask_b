# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-30 11:20
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('action', '0017_auto_20180523_1611'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='action',
            name='filter',
        ),
    ]
