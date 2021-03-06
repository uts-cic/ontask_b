# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.conf.urls import url

from . import views_action, views_condition, views_email

app_name = 'action'

urlpatterns = [
    #
    # Action CRUD
    #
    # List them all
    url(r'^$', views_action.action_index, name='index'),

    # Create an action of type 0: in, 1: Out
    url(r'^(?P<type>[01])/create/$',
        views_action.ActionCreateView.as_view(), name='create'),

    # Edit action Out
    url(r'^(?P<pk>\d+)/edit_out/$',
        views_action.edit_action_out,
        name='edit_out'),

    # Edit action In
    url(r'^(?P<pk>\d+)/edit_in/$',
        views_action.edit_action_in,
        name='edit_in'),

    # Update an action of type 0: in, 1: Out
    url(r'^(?P<pk>\d+)/(?P<type>[01])/update/$',
        views_action.ActionUpdateView.as_view(),
        name='update'),

    # Clone the action
    url(r'^(?P<pk>\d+)/clone/$', views_action.clone, name='clone'),

    # Nuke the action
    url(r'^(?P<pk>\d+)/delete/$', views_action.delete_action, name='delete'),

    # Run action in
    url(r'^(?P<pk>\d+)/run/$', views_action.run, name='run'),

    # Server side update of the run page for action in
    url(r'^(?P<pk>\d+)/run_ss/$', views_action.run_ss, name='run_ss'),

    # Run action in a row. Can be executed by the instructor or the
    # learner!!
    url(r'^(?P<pk>\d+)/run_row/$', views_action.run_row, name='run_row'),

    # Say thanks
    url(r'thanks/$', views_action.thanks, name='thanks'),

    # Preview content of the action out
    url(r'^(?P<pk>\d+)/(?P<idx>\d+)/preview/$',
        views_action.preview,
        name='preview'),

    # Allow url on/off toggle
    url(r'^(?P<pk>\d+)/showurl/$', views_action.showurl, name='showurl'),

    #
    # Serve the personalised content
    #
    url(r'^(?P<action_id>\d+)/serve/$', views_action.serve, name='serve'),

    #
    # FILTERS
    #
    url(r'^(?P<pk>\d+)/create_filter/$',
        views_condition.FilterCreateView.as_view(),
        name='create_filter'),

    url(r'^(?P<pk>\d+)/edit_filter/$',
        views_condition.edit_filter,
        name='edit_filter'),

    url(r'^(?P<pk>\d+)/delete_filter/$',
        views_condition.delete_filter,
        name='delete_filter'),

    #
    # CONDITIONS
    #
    url(r'^(?P<pk>\d+)/create_condition/$',
        views_condition.ConditionCreateView.as_view(),
        name='create_condition'),

    url(r'^(?P<pk>\d+)/edit_condition/$',
        views_condition.edit_condition,
        name='edit_condition'),

    url(r'^(?P<pk>\d+)/delete_condition/$',
        views_condition.delete_condition,
        name='delete_condition'),

    # Clone the condition
    url(r'^(?P<pk>\d+)/clone_condition/$',
        views_condition.clone,
        name='clone_condition'),

    #
    # Email
    #
    # Request data to send email
    url(r'^(?P<pk>\d+)/send_email/$',
        views_email.request_data,
        name="send_email"),

    # Preview emails
    url(r'^(?P<pk>\d+)/(?P<idx>\d+)/email_preview/$',
        views_email.preview,
        name='email_preview'),

]
