# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProfileConfig(AppConfig):
    name = "profiles"
    verbose_name = _('User Profiles')

    def ready(self):
        # Needed so that the signal registration is done
        from . import signals  # noqa
