# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt

from action import settings
from django_auth_lti.decorators import lti_role_required
from ontask.permissions import UserIsInstructor
from ontask.tasks import increase_track_count


class HomePage(generic.TemplateView):
    template_name = "home.html"


class AboutPage(generic.TemplateView):
    template_name = "about.html"


class ToBeDone(UserIsInstructor, generic.TemplateView):
    template_name = "base.html"


@login_required
def entry(request):
    return redirect('workflow:index')


@csrf_exempt
@xframe_options_exempt
@lti_role_required(['Instructor', 'Student'])
def lti_entry(request):
    return redirect('workflow:index')


# No permissions in this URL as it is supposed to be wide open to track email
#  reads.
def trck(request):
    """
    Receive a request with a token from email read tracking
    :param request: Request object
    :return: Reflects in the DB the reception and (optionally) in the data 
    table of the workflow
    """

    # Push the tracking to the asynchronous queue
    increase_track_count.delay(request.method, request.GET)

    return HttpResponse(settings.PIXEL, content_type='image/png')


@login_required
@csrf_exempt
def keep_alive(request):
    return JsonResponse({})


def ontask_handler400(request):
    response = render(request, '400.html', {})
    response.status_code = 400
    return response


def ontask_handler403(request):
    response = render(request, '403.html', {})
    response.status_code = 403
    return response


def ontask_handler404(request):
    response = render(request, '404.html', {})
    response.status_code = 404
    return response


def ontask_handler500(request):
    response = render(request, '500.html', {})
    response.status_code = 500
    return response
