# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from . import views, resources, api

app_name = 'logs'

urlpatterns = [

    url(r'^show/$', views.show, name="show"),

    url(r'^(?P<pk>\d+)/view/$', views.view, name="view"),

    url(r'^(?P<pk>\d+)/export/$', resources.export, name="export"),

    url(r'^list/$', api.LogAPIList.as_view()),

]
