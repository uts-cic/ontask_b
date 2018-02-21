# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-06 11:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0006_auto_20171125_2052'),
        ('action', '0005_action_is_out'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='columns',
            field=models.ManyToManyField(related_name='actions_in', to='workflow.Column'),
        ),
    ]