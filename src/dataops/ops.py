# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import pandas as pd
from django.conf import settings

from action.models import Condition, Action
from dataops import formula_evaluation
from dataops.pandas_db import (
    create_table_name,
    create_upload_table_name,
    store_table,
    df_column_types_rename,
    load_table,
    get_table_data,
    is_table_in_db,
    get_table_queryset,
    pandas_datatype_names)
from table.models import View
from workflow.models import Workflow, Column


def is_unique_column(df_column):
    """

    :param df_column: Column of a pandas data frame
    :return: Boolean encoding if the column has unique values
    """
    return len(df_column.unique()) == len(df_column)


def are_unique_columns(data_frame):
    """

    :param data_frame: Pandas data frame
    :return: Array of Booleans stating of a column has unique values
    """
    return [is_unique_column(data_frame[x]) for x in list(data_frame.columns)]


def load_upload_from_db(pk):
    return load_table(create_upload_table_name(pk))


def store_table_in_db(data_frame, pk, table_name, temporary=False):
    """
    Update or create a table in the DB with the data in the data frame. It
    also updates the corresponding column information

    :param data_frame: Data frame to dump to DB
    :param pk: Corresponding primary key of the workflow
    :param table_name: Table to use in the DB
    :param temporary: Boolean stating if the table is temporary,
           or it belongs to an existing workflow.
    :return: If temporary = True, then return a list with three lists:
             - column names
             - column types
             - column is unique
             If temporary = False, return None. All this info is stored in
             the workflow
    """

    if settings.DEBUG:
        print('Storing table ', table_name)

    # get column names and types
    df_column_names = list(data_frame.columns)
    df_column_types = df_column_types_rename(data_frame)

    # if the data frame is temporary, the procedure is much simpler
    if temporary:
        # Get the if the columns have unique values per row
        column_unique = are_unique_columns(data_frame)

        # Store the table in the DB
        store_table(data_frame, table_name)

        # Return a list with three list with information about the
        # data frame that will be needed in the next steps
        return [df_column_names, df_column_types, column_unique]

    # We are modifying an existing DF

    # Get the workflow and its columns
    workflow = Workflow.objects.get(id=pk)
    wf_col_names = Column.objects.filter(
        workflow__id=pk
    ).values_list("name", flat=True)

    # Loop over the columns in the data frame and reconcile the column info
    # with the column objects attached to the WF
    for cname in df_column_names:
        # See if this is a new column
        if cname in wf_col_names:
            # If column already exists in wf_col_names, no need to do anything
            continue

        # Create the new column
        Column.objects.create(
            name=cname,
            workflow=workflow,
            data_type=pandas_datatype_names[
                data_frame[cname].dtype.name],
            is_key=is_unique_column(data_frame[cname]))

    # Get now the new set of columns with names
    wf_column_names = Column.objects.filter(
        workflow__id=pk).values_list('name', flat=True)

    # Reorder the columns in the data frame
    data_frame = data_frame[list(wf_column_names)]

    # Store the table in the DB
    store_table(data_frame, table_name)

    # Update workflow fields and save
    workflow.nrows = data_frame.shape[0]
    workflow.ncols = data_frame.shape[1]
    workflow.set_query_builder_ops()
    workflow.data_frame_table_name = table_name
    workflow.save()

    return None


def store_dataframe_in_db(data_frame, pk):
    """
    Given a dataframe and the primary key of a workflow, it dumps its content on
    a table that is rewritten every time.

    :param data_frame: Pandas data frame containing the data
    :param pk: The unique key for the workflow
    :return: Nothing. Side effect in the database
    """
    return store_table_in_db(data_frame, pk, create_table_name(pk))


def store_upload_dataframe_in_db(data_frame, pk):
    """
    Given a dataframe and the primary key of a workflow, it dumps its content on
    a table that is rewritten every time.

    :param data_frame: Pandas data frame containing the data
    :param pk: The unique key for the workflow
    :return: If temporary = True, then return a list with three lists:
             - column names
             - column types
             - column is unique
             If temporary = False, return None. All this infor is stored in
             the workflow
    """
    return store_table_in_db(data_frame,
                             pk,
                             create_upload_table_name(pk),
                             True)


def get_table_row_by_index(workflow, cond_filter, idx):
    """
    Select the set of elements in the row with the given index

    :param workflow: Workflow object storing the data
    :param cond_filter: Condition object to filter the data (or None)
    :param idx: Row number to get (first row is idx = 1)
    :return: A dictionary with the (column_name, value) data or None if the
     index is out of bounds
    """

    # Get the data
    data = get_table_data(workflow.id, cond_filter)

    # If the data is not there, return None
    if idx > len(data):
        return None

    return dict(zip(workflow.get_column_names(), data[idx - 1]))


def workflow_has_table(workflow_item):
    return is_table_in_db(create_table_name(workflow_item.id))


def workflow_id_has_table(workflow_id):
    return is_table_in_db(create_table_name(workflow_id))


def workflow_has_upload_table(workflow_item):
    return is_table_in_db(
        create_upload_table_name(workflow_item.id)
    )


def get_queryset_by_workflow(workflow_item):
    return get_table_queryset(create_table_name(workflow_item.id))


def get_queryset_by_workflow_id(workflow_id):
    return get_table_queryset(create_table_name(workflow_id))


def perform_dataframe_upload_merge(pk, dst_df, src_df, merge_info):
    """
    It either stores a data frame in the db (dst_df is None), or merges
    the two data frames dst_df and src_df and stores its content.

    :param pk: Primary key of the Workflow containing the data frames
    :param dst_df: Destination dataframe (already stored in DB)
    :param src_df: Source dataframe, stored in temporary table
    :param merge_info: Dictionary with merge options
    :return:
    """

    # STEP 1 Rename the column names.
    src_df = src_df.rename(
        columns=dict(zip(merge_info['initial_column_names'],
                         merge_info.get('autorename_column_names', None) or
                         merge_info['rename_column_names'])))

    # STEP 2 Drop the columns not selected
    columns_to_upload = merge_info['columns_to_upload']
    src_df.drop([n for x, n in enumerate(list(src_df.columns))
                 if not columns_to_upload[x]],
                axis=1, inplace=True)

    # If no dst_df is given, simply dump the frame in the DB
    if dst_df is None:
        store_dataframe_in_db(src_df, pk)
        return None

    # Step 3. Drop the columns that are going to be overriden.
    dst_df.drop(merge_info['override_columns_names'],
                inplace=True,
                axis=1)
    # Step 4. Perform the merge
    try:
        new_df = pd.merge(dst_df,
                          src_df,
                          how=merge_info['how_merge'],
                          left_on=merge_info['dst_selected_key'],
                          right_on=merge_info['src_selected_key'])
    except Exception as e:
        return 'Merge operation failed. Exception: ' + e.message

    # If the merge produced a data frame with no rows, flag it as an error to
    # prevent loosing data when there is a mistake in the key column
    if new_df.shape[0] == 0:
        return 'Merge operation produced a result with no rows'

    # For each column, if it is overriden, remove it, if not, check that the
    # new column is consistent with data_type, and allowed values,
    # and recheck its unique key status
    for col in Workflow.objects.get(pk=pk).columns.all():
        # If column is overriden, remove it
        if col.name in merge_info['override_columns_names']:
            col.delete()
            continue

        # New values in this column should be compatible with the current
        # column properties.
        # Condition 1: Data type
        if pandas_datatype_names[new_df[col.name].dtype.name] != col.data_type:
            return 'New values in column ' + col.name + ' are not of type ' \
                   + col.data_type

        # Condition 2: If there are categories, the new values should be
        # compatible with them.
        if col.categories and not all([x in col.categories
                                       for x in new_df[col.name]]):
            return 'New values in column ' + col.name + ' are not within ' \
                   + 'the categories ' + ', '.join(col.categories)

        # Condition 3:
        col.is_key = is_unique_column(new_df[col.name])

    # Store the result back in the DB
    store_dataframe_in_db(new_df, pk)

    # Operation was correct, no need to flag anything
    return None


def data_frame_add_empty_column(df, column_name, column_type, initial_value):
    """

    :param df: Data frame to modify
    :param column_name: Name of the column to add
    :param column_type: type of the column to add
    :param initial_value: initial value in the column
    :return: new data frame with the additional column
    """

    # How to add a new column with a specific data type in DataFrame
    # a = np.empty((10,), dtype=[('column_name', np.float64)])
    # b = np.empty((10,), dtype=[('nnn', np.float64)] (ARRAY)
    # pd.concat([df, pd.DataFrame(b)], axis=1)

    if not initial_value:
        # Choose the right numpy type
        if column_type == 'string':
            initial_value = ''
        elif column_type == 'integer':
            initial_value = 0
        elif column_type == 'double':
            initial_value = 0.0
        elif column_type == 'boolean':
            initial_value = False
        elif column_type == 'datetime':
            initial_value = pd.NaT
        else:
            raise ValueError('Type ' + column_type + ' not found.')

    # Create the empty column
    df[column_name] = initial_value

    return df


def rename_df_column(df, workflow, old_name, new_name):
    """
    Function to change the name of a column in the dataframe.

    :param df: dataframe
    :param workflow: workflow object that is handling the data frame
    :param old_name: old column name
    :param new_name: new column name
    :return: Workflow object updated
    """

    # Rename the appearances of the variable in all conditions/filters
    conditions = Condition.objects.filter(action__workflow=workflow)
    for cond in conditions:
        cond.formula = formula_evaluation.rename_variable(
            cond.formula, old_name, new_name)
        cond.save()

    # Rename the appearances of the variable in all actions
    for action_item in Action.objects.filter(workflow=workflow):
        action_item.rename_variable(old_name, new_name)

    # Rename the appearances of the variable in the formulas in the views
    for view in View.objects.filter(workflow=workflow):
        view.formula = formula_evaluation.rename_variable(
            view.formula,
            old_name,
            new_name
        )
        view.save()

    return df.rename(columns={old_name: new_name})


def detect_datetime_columns(data_frame):
    """
    Given a data frame traverse the columns and those that have type "string"
    try to see if it is of type datetime. If so, apply the translation.
    :param data_frame: Pandas dataframe to detect datetime columns
    :return:
    """
    # Strip white space from all string columns and try to convert to
    # datetime just in case
    for x in list(data_frame.columns):
        if data_frame[x].dtype.name == 'object':
            # Column is a string!
            data_frame[x] = data_frame[x].str.strip()

            # Try the datetime conversion
            try:
                series = pd.to_datetime(data_frame[x],
                                        infer_datetime_format=True)
                # Datetime conversion worked! Update the data_frame
                data_frame[x] = series
            except ValueError:
                pass
    return data_frame
