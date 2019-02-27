# -*- coding: utf-8 -*-


from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

class LogsConfig(AppConfig):
    name = 'logs'
    verbose_name = _('Event Logs')
