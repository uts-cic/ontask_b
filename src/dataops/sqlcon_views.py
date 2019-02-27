# -*- coding: utf-8 -*-
from builtins import object
from collections import Counter

import django_tables2 as tables
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

import dataops.pandas_db
import logs
from dataops import ops, pandas_db
from dataops.forms import SQLConnectionForm, SQLRequestPassword
from dataops.models import SQLConnection
from logs.models import Log
from ontask import OnTaskDataFrameNoKey
from ontask.permissions import is_instructor, is_admin
from ontask.tables import OperationsColumn
from workflow.models import Workflow
from workflow.ops import get_workflow


class SQLConnectionTableAdmin(tables.Table):
    operations = OperationsColumn(
        verbose_name='',
        template_file='dataops/includes/partial_sqlconn_adminop.html',
        template_context=lambda record: {'id': record['id']}
    )

    def render_name(self, record):
        return format_html(
            """<a class="js-sqlconn-edit" href="#" data-url="{0}">{1}</a>""",
            reverse('dataops:sqlconn_edit', kwargs={'pk': record['id']}),
            record['name']
        )

    class Meta(object):
        model = SQLConnection
        fields = ('name', 'description_txt')
        sequence = ('name', 'description_txt', 'operations')
        attrs = {
            'class': 'table table-hover table-bordered',
            'style': 'width: 100%;',
            'id': 'sqlconn-admin-table'
        }


class SQLConnectionTableRun(tables.Table):
    operations = OperationsColumn(
        verbose_name='',
        template_file='dataops/includes/partial_sqlconn_runop.html',
        template_context=lambda record: {'id': record['id']}
    )

    def render_name(self, record):
        return format_html(
            '<a class="js-sqlconn-view" href="#" data-url="{0}">{1}'
            ' <span class="fa fa-eye"></span> </a>',
            reverse('dataops:sqlconn_view', kwargs={'pk': record['id']}),
            record['name']
        )

    class Meta(object):
        model = SQLConnection

        fields = ('name', 'description_txt')

        sequence = ('name', 'description_txt', 'operations')
        attrs = {
            'class': 'table table-hover table-bordered',
            'style': 'width: 100%;',
            'id': 'sqlconn-instructor-table'
        }


def save_conn_form(request, form, template_name):
    """
    Save the connection provided in the form
    :param request: HTTP request
    :param form: form object with the collected information
    :param template_name: To render the response
    :return: AJAX response
    """

    # AJAX response. Form is not valid until proven otherwise
    data = {'form_is_valid': False}

    # Type of event to record
    if form.instance.id:
        event_type = Log.SQL_CONNECTION_EDIT
        is_add = False
    else:
        event_type = Log.SQL_CONNECTION_CREATE
        is_add = True

    # If it is a POST and it is correct
    if request.method == 'POST' and form.is_valid():

        # Correct POST submission
        try:
            conn = form.save()
        except IntegrityError:
            form.add_error('name',
                           _('A connection with this name already exists'))
            data['html_form'] = render_to_string(
                template_name,
                {'form': form,
                 'id': form.instance.id,
                 'add': is_add},
                request=request
            )
            return JsonResponse(data)

        # Log the event
        Log.objects.register(
            request.user,
            event_type,
            None,
            {'name': conn.name,
             'description': conn.description_txt,
             'conn_type': conn.conn_type,
             'conn_driver': conn.conn_driver,
             'db_user': conn.db_user,
             'db_passwd': _('<PROTECTED>') if conn.db_password else '',
             'db_host': conn.db_host,
             'db_port': conn.db_port,
             'db_name': conn.db_name,
             'db_table': conn.db_table}
        )

        data['form_is_valid'] = True
        data['html_redirect'] = ''  # Refresh the page
        return JsonResponse(data)

    # Request is a GET
    data['html_form'] = render_to_string(
        template_name,
        {'form': form,
         'id': form.instance.id,
         'add': is_add},
        request=request
    )
    return JsonResponse(data)


@user_passes_test(is_admin)
def sqlconnection_admin_index(request):
    """
    Page to show and handle the SQL connections
    :param request: Request
    :return: Render the appropriate page.
    """
    wid = request.session.pop('ontask_workflow_id', None)
    # If removing workflow from session, mark it as available for sharing
    if wid:
        Workflow.unlock_workflow_by_id(wid)
    request.session.pop('ontask_workflow_name', None)

    return render(request,
                  'dataops/sql_connections_admin.html',
                  {'table': SQLConnectionTableAdmin(
                      SQLConnection.objects.all().values('id',
                                                         'name',
                                                         'description_txt'),
                      orderable=False)
                  })


@user_passes_test(is_instructor)
def sqlconnection_instructor_index(request):
    """
    Function that renders a page showing a table with the SQL connections.
    :param request:
    :return:
    """

    return render(
        request,
        'dataops/sql_connections.html',
        {'table': SQLConnectionTableRun(
            SQLConnection.objects.all().values('id', 'name', 'description_txt'),
            orderable=False
        )})


@user_passes_test(is_instructor)
def sqlconn_view(request, pk):
    """
    Show the DB connection in a modal

    :param request: Request object
    :param pk: Primary key of the SQL connection
    :return: AJAX response
    """

    # Initial value of the data to return as AJAX response
    data = {'form_is_valid': False}

    # Get the connection object
    c_obj = SQLConnection.objects.filter(pk=pk)
    if not c_obj:
        # Connection object not found, go to table of sql connections
        data['form_is_valid'] = True
        data['html_redirect'] = reverse('dataops:sqlconns_admin_index')
        return JsonResponse(data)

    data['html_form'] = render_to_string(
        'dataops/includes/partial_show_sql_connection.html',
        {'c_vals': c_obj.values()[0], 'id': c_obj[0].id, 'request': request}
    )
    return JsonResponse(data)


@user_passes_test(is_admin)
def sqlconn_add(request):
    """
    Create a new SQL connection processing the GET/POST requests

    :param request: Request object
    :return: AJAX response
    """

    # Create the form
    form = SQLConnectionForm(request.POST or None)

    return save_conn_form(request,
                          form,
                          'dataops/includes/partial_sqlconn_addedit.html')


@user_passes_test(is_admin)
def sqlconn_edit(request, pk):
    """

    :param request:
    :return:
    """

    # Get the connection
    conn = SQLConnection.objects.filter(pk=pk).first()
    if not conn:
        return JsonResponse(
            {'form_is_valid': True,
             'html_redirect': reverse('home')}
        )

    # Create the form
    form = SQLConnectionForm(request.POST or None, instance=conn)

    return save_conn_form(request,
                          form,
                          'dataops/includes/partial_sqlconn_addedit.html')


@user_passes_test(is_admin)
def sqlconn_clone(request, pk):
    """
    AJAX handshake to clone a SQL connection
    :param request: HTTP request
    :param pk: ID of the connection to clone.
    :return: AJAX response
    """
    # Data to send as JSON response, in principle, assume form is not valid
    data = {'form_is_valid': False}

    context = {'pk': pk}  # For rendering

    # Get the connection
    conn = SQLConnection.objects.filter(pk=pk).first()
    if not conn:
        # The view is not there. Redirect to workflow detail
        data['form_is_valid'] = True
        data['html_redirect'] = reverse('home')
        return JsonResponse(data)

    # Get the name of the connection to clone
    context['cname'] = conn.name

    if request.method == 'GET':
        data['html_form'] = render_to_string(
            'dataops/includes/partial_sqlconn_clone.html',
            context,
            request=request)

        return JsonResponse(data)

    # POST REQUEST

    # Get the new name appending as many times as needed the 'Copy of '
    new_name = 'Copy_of_' + conn.name
    while SQLConnection.objects.filter(name=new_name).exists():
        new_name = 'Copy_of_' + new_name

    # Proceed to clone the view
    old_name = conn.name
    conn.id = None
    conn.name = new_name
    conn.save()

    # Log the event
    Log.objects.register(
        request.user,
        Log.SQL_CONNECTION_CLONE,
        None,
        {'name': conn.name,
         'description': conn.description_txt,
         'conn_type': conn.conn_type,
         'conn_driver': conn.conn_driver,
         'db_user': conn.db_user,
         'db_passwd': _('<PROTECTED>') if conn.db_password else '',
         'db_host': conn.db_host,
         'db_port': conn.db_port,
         'db_name': conn.db_name,
         'db_table': conn.db_table})

    return JsonResponse({'form_is_valid': True, 'html_redirect': ''})


@user_passes_test(is_admin)
def sqlconn_delete(request, pk):
    """
    AJAX processor for the delete sql connection operation
    :param request: AJAX request
    :param pk: primary key for the sql connection
    :return: AJAX response to handle the form
    """

    # Get the connection
    conn = SQLConnection.objects.filter(pk=pk).first()
    if not conn:
        return JsonResponse(
            {'form_is_valid': True,
             'html_redirect': reverse('home')}
        )

    if request.method == 'POST':
        # Log the event
        Log.objects.register(
            request.user,
            Log.SQL_CONNECTION_DELETE,
            None,
            {'name': conn.name,
             'description': conn.description_txt,
             'conn_type': conn.conn_type,
             'conn_driver': conn.conn_driver,
             'db_user': conn.db_user,
             'db_passwd': _('<PROTECTED>') if conn.db_password else '',
             'db_host': conn.db_host,
             'db_port': conn.db_port,
             'db_name': conn.db_name,
             'db_table': conn.db_table}
        )

        # Perform the delete operation
        conn.delete()

        # In this case, the form is valid anyway
        return JsonResponse({'form_is_valid': True,
                             'html_redirect': reverse('home')})

    # This is a GET request
    return JsonResponse({
        'form_is_valid': False,
        'html_form': render_to_string(
            'dataops/includes/partial_sqlconn_delete.html',
            {'sqlconn': conn},
            request=request
        )
    })


@user_passes_test(is_instructor)
def sqlupload1(request, pk):
    """
    The four step process will populate the following dictionary with name
    upload_data (divided by steps in which they are set

    STEP 1:

    initial_column_names: List of column names in the initial file.

    column_types: List of column types as detected by pandas

    src_is_key_column: Boolean list with src columns that are unique

    step_1: URL name of the first step

    :param request: Web request
    :return: Creates the upload_data dictionary in the session
    """

    # Get the current workflow
    workflow = get_workflow(request)
    if not workflow:
        return redirect('home')

        # Get the connection
    conn = SQLConnection.objects.filter(pk=pk).first()
    if not conn:
        return redirect('dataops:sqlconns_instructor_index_instructor_index')

    form = None
    if conn.db_password:
        # The connection needs a password  to operate
        form = SQLRequestPassword(request.POST or None)

    context = {'form': form,
               'wid': workflow.id,
               'dtype': 'SQL',
               'dtype_select': _('SQL connection'),
               'prev_step': reverse('dataops:sqlconns_instructor_index'),
               'conn_type': conn.conn_type,
               'conn_driver': conn.conn_driver,
               'db_user': conn.db_user,
               'db_passwd': _('<PROTECTED>') if conn.db_password else '',
               'db_host': conn.db_host,
               'db_port': conn.db_port,
               'db_name': conn.db_name,
               'db_table': conn.db_table}

    # Process the initial loading of the form
    if request.method != 'POST' or (form and not form.is_valid()):
        return render(request, 'dataops/sqlupload1.html', context)

    read_pwd = None
    if form:
        read_pwd = form.cleaned_data['password']

    # Process SQL connection using pandas
    try:
        data_frame = pandas_db.load_df_from_sqlconnection(conn, read_pwd)
    except Exception as e:
        messages.error(request,
                       _('Unable to obtain data: {0}').format(e))
        return render(request, 'dataops/sqlupload1.html', context)

    try:
        # Verify the data frame
        pandas_db.verify_data_frame(data_frame)
    except OnTaskDataFrameNoKey as e:
        dup = [x for x, v in Counter(list(data_frame.columns)) if v > 1]
        messages.error(request, str(e) + ' (' + ','.join(dup) + ').')
        return render(request, 'dataops/sqlupload1.html', context)

    # Store the data frame in the DB.
    try:
        # Get frame info with three lists: names, types and is_key
        frame_info = ops.store_upload_dataframe_in_db(data_frame, workflow.id)
    except Exception as e:
        form.add_error(
            None,
            _('Sorry. The data from this connection cannot be processed.')
        )
        return render(request, 'dataops/sqlupload1.html', context)

    # Dictionary to populate gradually throughout the sequence of steps. It
    # is stored in the session.
    request.session['upload_data'] = {
        'initial_column_names': frame_info[0],
        'column_types': frame_info[1],
        'src_is_key_column': frame_info[2],
        'step_1': reverse('dataops:sqlupload1', kwargs={'pk': conn.id})
    }

    return redirect('dataops:upload_s2')
