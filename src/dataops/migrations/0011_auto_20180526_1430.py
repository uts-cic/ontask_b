# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-26 05:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataops', '0010_remove_pluginregistry_diagnostics'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pluginregistry',
            name='is_verified',
            field=models.BooleanField(default=False, verbose_name='Ready to run'),
        ),
    ]
