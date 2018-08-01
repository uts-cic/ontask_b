# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime

import pytz
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings as ontask_settings
from django.contrib.auth import get_user_model

import logs.ops
from action.models import Action
from action.ops import send_messages
from logs.models import Log
from scheduler.models import ScheduledEmailAction

logger = get_task_logger(__name__)


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
    :param log_id: Id of the log object where the status has to be reflected
    :return: Nothing
    """

    # Get the objects
    user = get_user_model().objects.get(id=user_id)
    action = Action.objects.get(id=action_id)

    # Get the log_item to modify the message
    log_item = Log.objects.get(pk=log_id)
    payload = log_item.get_payload()
    payload['status'] = 'Executing'
    log_item.set_payload(payload)
    log_item.save()

    msg = 'Finished'
    try:
        result = send_messages(user,
                               action,
                               subject,
                               email_column,
                               from_email,
                               cc_email_list,
                               bcc_email_list,
                               send_confirmation,
                               track_read)
        # If the result has some sort of message, push it to the log
        if result:
            msg = 'Incorrect execution: ' + str(result)
            logger.error(msg)

    except Exception as e:
        msg = 'Error while executing send_messages: {0}'.format(e.message)
        logger.error(msg)
    else:
        logger.info(msg)

    # Update the message in the payload
    payload['status'] = msg
    log_item.set_payload(payload)
    log_item.save()


@shared_task
def execute_email_actions(debug):
    """
    Function that selects the entries in the DB that are due, and proceed with
    the execution.

    :return:
    """
    # Get the current date/time
    now = datetime.datetime.now(pytz.timezone(ontask_settings.TIME_ZONE))

    # Get all the actions that are pending
    s_items = ScheduledEmailAction.objects.filter(
        type='email_send',
        status=0,  # Pending
        execute__lt=now
    )
    logger.info(str(s_items.count()) + ' actions pending execution')

    # If the number of tasks to execute is zero, we are done.
    if s_items.count() == 0:
        return

    for item in s_items:
        if debug:
            logger.info('Starting execution of task ' + str(item.id))

        # Set item to running
        item.status = 1  # Running

        # Execute an email task that contains:
        # - action id
        # - subject
        # - email column
        # - send_confirmation
        # - track_read

        # Get additional parameters for the log
        cc_email = [x.strip() for x in item.cc_email.split(',') if x]
        bcc_email = [x.strip() for x in item.bcc_email.split(',') if x]

        # Log the event
        log_id = logs.ops.put(item.user,
                              'schedule_email_execute',
                              item.action.workflow,
                              {'action': item.action.name,
                               'action_id': item.action.id,
                               'execute': item.execute.isoformat(),
                               'subject': item.subject,
                               'email_column': item.email_column.name,
                               'cc_email': cc_email,
                               'bcc_email': bcc_email,
                               'send_confirmation': item.send_confirmation,
                               'track_read': item.track_read,
                               'status': 'pre-execution'})

        send_email_messages(item.user.id,
                            item.action.id,
                            item.subject,
                            item.email_column.name,
                            item.user.email,
                            cc_email,
                            bcc_email,
                            item.send_confirmation,
                            item.track_read,
                            log_id)

        # Store the resulting message in the record
        item.message = \
            'Operation executed. Status available in Log {0}'.format(log_id)

        # Save the new status in the DB
        item.save()
