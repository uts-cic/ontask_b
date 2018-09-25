# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime

import pytz
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings as ontask_settings
from django.contrib.auth import get_user_model
from django.core import signing

from action.models import Action
from action.ops import send_messages, send_json
from dataops import pandas_db
from logs.models import Log
from scheduler.models import ScheduledAction

logger = get_task_logger(__name__)


def get_execution_items(user_id, action_id, log_id):
    """
    Given a set of ids, get the objects from the DB
    :param user_id: User id
    :param action_id: Action id (to be executed)
    :param log_id: Log id (to store execution report)
    :return: (user, action, log)
    """

    # Get the objects
    user = get_user_model().objects.get(id=user_id)
    action = Action.objects.get(id=action_id)

    # Set the log in the action
    log_item = Log.objects.get(pk=log_id)
    if action.last_executed_log != log_item:
        action.last_executed_log = log_item
        action.save()

    # Update some fields in the log
    log_item.payload['datetime'] = \
        str(datetime.datetime.now(pytz.timezone(ontask_settings.TIME_ZONE)))
    log_item.payload['filter_present'] = action.get_filter() is not None
    log_item.save()

    return user, action, log_item


@shared_task
def send_email_messages(user_id,
                        action_id,
                        subject,
                        email_column,
                        from_email,
                        cc_email_list,
                        bcc_email_list,
                        send_confirmation,
                        track_read,
                        exclude_values,
                        log_id):
    """
    This function invokes send_messages in action/ops.py, gets the message
    that may be sent as a result, and records the appropriate events.

    :param user_id: Id of User object that is executing the action
    :param action_id: Id of Action object from where the messages are taken
    :param subject: String for the email subject
    :param email_column: Name of the column to extract email addresses
    :param from_email: String with email from sender
    :param cc_email_list: List of CC emails
    :param bcc_email_list: List of BCC emails
    :param send_confirmation: Boolean to send confirmation to sender
    :param track_read: Boolean to try to track reads
    :param exclude_values: List of values to exclude from the mailing
    :param log_id: Id of the log object where the status has to be reflected
    :return: bool stating if execution has been correct
    """

    # Get the objects
    user, action, log_item = get_execution_items(user_id, action_id, log_id)

    msg = 'Finished'
    to_return = True
    try:
        result = send_messages(user,
                               action,
                               subject,
                               email_column,
                               from_email,
                               cc_email_list,
                               bcc_email_list,
                               send_confirmation,
                               track_read,
                               exclude_values,
                               log_item)
        # If the result has some sort of message, push it to the log
        if result:
            msg = 'Incorrect execution: ' + str(result)
            logger.error(msg)
            to_return = False
    except Exception as e:
        msg = 'Error while executing send_messages: {0}'.format(e.message)
        logger.error(msg)
        to_return = False
    else:
        logger.info(msg)

    # Update the message in the payload
    log_item.payload['status'] = msg
    log_item.save()

    return to_return


@shared_task
def send_json_objects(user_id,
                      action_id,
                      token,
                      key_column,
                      exclude_values,
                      log_id):
    """
    This function invokes send_json in action/ops.py, gets the JSON objects
    that may be sent as a result, and records the appropriate events.

    :param user_id: Id of User object that is executing the action
    :param action_id: Id of Action object from where the messages are taken
    :param token: String to include as authorisation token
    :param key_column: Key column name to use to exclude elements (if needed)
    :param exclude_values: List of values to exclude from the mailing
    :param log_id: Id of the log object where the status has to be reflected
    :return: Nothing
    """

    # Get the objects
    user, action, log_item = get_execution_items(user_id, action_id, log_id)

    msg = 'Finished'
    to_return = True
    try:
        # If the result has some sort of message, push it to the log
        result = send_json(user,
                           action,
                           token,
                           key_column,
                           exclude_values,
                           log_item)
        if result:
            msg = 'Incorrect execution: ' + str(result)
            logger.error(msg)
            to_return = False

    except Exception as e:
        msg = 'Error while executing send_messages: {0}'.format(e.message)
        logger.error(msg)
        to_return = False
    else:
        logger.info(msg)

    # Update the message in the payload
    log_item.payload['status'] = msg
    log_item.save()

    return to_return

@shared_task
def execute_scheduled_actions(debug):
    """
    Function that selects the entries in the DB that are due, and proceed with
    the execution.

    :return:
    """
    # Get the current date/time
    now = datetime.datetime.now(pytz.timezone(ontask_settings.TIME_ZONE))

    # Get all the actions that are pending
    s_items = ScheduledAction.objects.filter(
        status=ScheduledAction.STATUS_PENDING,
        execute__lt=now + datetime.timedelta(minutes=1)
    )
    logger.info(str(s_items.count()) + ' actions pending execution')

    # If the number of tasks to execute is zero, we are done.
    if s_items.count() == 0:
        return

    for item in s_items:
        if debug:
            logger.info('Starting execution of task ' + str(item.id))

        # Set item to running
        item.status = ScheduledAction.STATUS_EXECUTING
        item.save()

        result = None
        #
        # EMAIL ACTION
        #
        if item.action.action_type == Action.PERSONALIZED_TEXT:
            subject = item.payload.get('subject', '')
            cc_email = item.payload.get('cc_email', [])
            bcc_email = item.payload.get('bcc_email', [])
            send_confirmation = item.payload.get('send_confirmation', False)
            track_read = item.payload.get('track_read', False)

            # Log the event
            log_item = Log.objects.register(
                item.user,
                Log.SCHEDULE_EMAIL_EXECUTE,
                item.action.workflow,
                {'action': item.action.name,
                 'action_id': item.action.id,
                 'bcc_email': bcc_email,
                 'cc_email': cc_email,
                 'email_column': item.item_column.name,
                 'execute': item.execute.isoformat(),
                 'exclude_values': item.exclude_values,
                 'from_email': item.user.email,
                 'send_confirmation': send_confirmation,
                 'status': 'Preparing to execute',
                 'subject': subject,
                 'track_read': track_read,
                 }
            )

            # Store the log event in the scheduling item
            item.last_executed_log = log_item
            item.save()

            result = send_email_messages(item.user.id,
                                         item.action.id,
                                         subject,
                                         item.item_column.name,
                                         item.user.email,
                                         cc_email,
                                         bcc_email,
                                         send_confirmation,
                                         track_read,
                                         item.exclude_values,
                                         log_item.id)

        #
        # JSON action
        #
        elif item.action.action_type == Action.PERSONALIZED_JSON:
            # Get the information from the payload
            token = item.payload['token']
            key_column = None
            if item.item_column:
                key_column = item.item_column.name

            # Log the event
            log_item = Log.objects.register(
                item.user,
                Log.SCHEDULE_JSON_EXECUTE,
                item.action.workflow,
                {'action': item.action.name,
                 'action_id': item.action.id,
                 'exclude_values': item.exclude_values,
                 'key_column': key_column,
                 'status': 'Preparing to execute',
                 'target_url': item.action.target_url})

            # Send the objects
            result = send_json_objects(item.user.id,
                                       item.action.id,
                                       token,
                                       key_column,
                                       item.exclude_values,
                                       log_item.id)

        if result:
            item.status = ScheduledAction.STATUS_DONE
        else:
            item.status = ScheduledAction.STATUS_DONE_ERROR

        if debug:
            logger.info('Status set to {0}'.format(item.status))

        # Save the new status in the DB
        item.save()


@shared_task
def increase_track_count(method, get_dict):
    """
    Function to process track requests asynchronously.

    :param method: GET or POST received in the request
    :param get_dict: GET dictionary received in the request
    :return: If correct, increases one row of the DB by one
    """

    if method != 'GET':
        # Only GET requests are accepted
        return

    # Obtain the track_id from the request
    track_id = get_dict.get('v', None)
    if not track_id:
        # No track id, nothing to do
        return

    # If the track_id is not correctly signed, finish.
    try:
        track_id = signing.loads(track_id)
    except signing.BadSignature:
        return

    # The request is legit and the value has been verified. Track_id has now
    # the dictionary with the tracking information

    # Get the objects related to the ping
    try:
        user = get_user_model().objects.get(email=track_id['sender'])
        action = Action.objects.get(pk=track_id['action'])
    except Exception:
        # Something went wrong (bad user or bad action)
        return

    # Extract the relevant fields from the track_id
    column_dst = track_id.get('column_dst', '')
    column_to = track_id.get('column_to', '')
    msg_to = track_id.get('to', '')

    log_payload = {'to': msg_to,
                   'email_column': column_to,
                   'column_dst': column_dst
                   }

    # If the track comes with column_dst, the event needs to be reflected
    # back in the data frame
    if column_dst:
        try:
            # Increase the relevant cell by one
            pandas_db.increase_row_integer(action.workflow.id,
                                           column_dst,
                                           column_to,
                                           msg_to)
        except Exception as e:
            log_payload['EXCEPTION_MSG'] = e.message
        else:
            # Get the tracking column and update all the conditions in the
            # actions that have this column as part of their formulas
            # FIX: Too aggressive?
            track_col = action.workflow.columns.get(name=column_dst)
            for action in action.workflow.actions.all():
                action.update_n_rows_selected(track_col)

    # Record the event
    Log.objects.register(user,
                         Log.ACTION_EMAIL_READ,
                         action.workflow,
                         log_payload)

    return
