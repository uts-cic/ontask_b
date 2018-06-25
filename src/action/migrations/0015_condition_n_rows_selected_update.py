# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-05-22 07:04
from __future__ import unicode_literals

from django.db import migrations

from action.models import Action


def update_n_rows_selected(apps, schema_editor):
    """
    Traverse all actions and update the number of rows selected by each
    condition

    :param apps:
    :param schema_editor:
    :return:
    """
    if schema_editor.connection.alias != 'default':
        return

    for action in Action.objects.all():
        action.update_n_rows_selected()


class Migration(migrations.Migration):
    dependencies = [
        ('action', '0014_condition_columns_update'),
    ]

    operations = [
        migrations.RunPython(update_n_rows_selected),
    ]
