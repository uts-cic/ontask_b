# -*- coding: utf-8 -*-


from builtins import str
from builtins import map
from builtins import zip
import re
import string

from django.template import Context, Template, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

import dataops.formula_evaluation
from action.forms import EnterActionIn
from action.models import Condition, var_use_res
from dataops import pandas_db, ops
from workflow.models import Workflow

# Variable name to store the workflow ID in the context used to render a
# template
action_context_var = 'ONTASK_ACTION_CONTEXT_VARIABLE___'
viz_number_context_var = 'ONTASK_VIZ_NUMBER_CONTEXT_VARIABLE___'


def make_xlat(*args, **kwds):
    """
    Auxuliary function to define a translator that applies multiple character
    substitutions at once.

    Taken from "Python Cookbook, 2nd Edition by David Ascher, Anna Ravenscroft,
    Alex Martelli", Section 1.18

    :param args: Dictionary
    :param kwds:
    :return: A function that uses the given dictionary to apply multiple
    changes to a string
    """
    adict = dict(*args, **kwds)
    rx = re.compile('|'.join(map(re.escape, adict)))

    def one_xlat(match):
        return adict[match.group(0)]

    def xlat(text):
        return rx.sub(one_xlat, text)

    return xlat


# Dictionary to translate non alphanumeric symbols into alphanumeric pairs
# 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
# !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
# abcdefghijklmnopqrstuvwxyzABCDEFG
tr_item = make_xlat({
    '!': '_a', '"': '_b', '#': '_c', '$': '_d', '%': '_e', '&': '_f',
    "'": "_g", '(': '_h', ')': '_i', '*': '_j', '+': '_k', ',': '_l',
    '-': '_m', '.': '_n', '/': '_o', ':': '_p', ';': '_q', '<': '_r',
    '=': '_s', '>': '_t', '?': '_u', '@': '_v', '[': '_w', '\\': '_x',
    ']': '_y', '^': '_z', '_': '_0', '`': '_1', '{': '_2', '|': '_3',
    '}': '_4', '~': '_5', ' ': '_6',
})


def translate(varname):
    """
    Function that given a string representing a variable name applies a
    translation to each of the non alphanumeric characters in that name.
    Additionally, it needs to guarantee that the name starts with a letter
    (not a digit), and it detects and fixes this condition by introducing a
    prefix.

    :param varname: Variable name
    :return: New variable name starting with a letter followed only by
             letter, digit or _
    """

    # If the variable name is surrounded by quotes, we leave it untouched!
    # because it represents a literal
    if varname.startswith("'") and varname.endswith("'"):
        return varname

    if varname.startswith('"') and varname.endswith('"'):
        return varname

    # If the variable name starts with a non-letter or the prefix used to
    # force letter start, add a prefix.
    if not varname[0] in string.ascii_letters or varname.startswith('OT_'):
        varname = 'OT_' + varname

    # Return the new variable name surrounded by the detected marks.
    return tr_item(varname)


def render_template(template_text, context_dict, action=None):
    """
    Given a template text and a context, performs the rendering of the
    template using the django template mechanism but with an additional
    pre-processing to bypass the restriction imposed by Jinja/Django that the
    variable names must start with a letter followed by a letter, number or _.

    In OnTask, the variable names are: column names, attribute names,
    or condition names. It is too restrictive to propagate the restrictions
    imposed by Jinja variables all the way to these three components. To
    hide this from the users, there is a preliminary step in which those
    variables in the template and keys in the context that do not comply with
    the syntax restriction are renamed to compliant names.

    The problem:
    We are giving two objects: a string containing a template with two markup
    structures denoting the use of variables, and a dictionary that matches
    variables to values.

    The processing of the template is done through Django template engine
    (itself based in Jinja). The syntax for the variables appearing in the
    template is highly restrictive. It only allows names starting with a
    letter followed by letter, number or '_'. No other printable symbol is
    allowed. We want to relax this last restriction.

    The solution:
    1) Parse the template and detect the use of all variables.

    2) For each variable use, transform its name into a name that is legal
       for Jinja (starts with letter followed by letter, number or '_' *)

       The transformation is based on:
       - Every non-letter or number is replaced by '_' followed by a
         letter/number as specified by the dictionary below.

       - If the original variable does not start by a letter, insert a prefix.

    3) Apply the same transformation for the keys in the given dictionary

    4) Execute the new template with the new dictionary and return the result.

    :param template_text: Text in the template to be rendered
    :param context_dict: Dictionary used by Jinja to evaluate the template
    :param action: Action object to insert in the context in case it is
    needed by any other custom template.
    :return: The rendered template
    """

    # Steps 1 and 2. Apply the tranlation process to all variables that
    # appear in the the template text
    new_template_text = template_text
    for rexpr in var_use_res:
        new_template_text = rexpr.sub(
            lambda m: m.group('mup_pre') + \
                      translate(m.group('vname')) + \
                      m.group('mup_post'),
            new_template_text)
    # new_template_text = '{% load vis_include %}' + new_template_text

    # Step 3. Apply the translation process to the context keys
    new_context = dict([(translate(escape(x)), y)
                        for x, y in list(context_dict.items())])

    # If the number of elements in the two dictionaries is different, we have
    #  a case of collision in the translation. Need to stop immediately.
    assert len(context_dict) == len(new_context)

    if action_context_var in new_context:
        raise Exception(_('Name {0} is reserved.').format(action_context_var))
    new_context[action_context_var] = action

    if viz_number_context_var in new_context:
        raise Exception(_('Name {0} is reserved.').format(
            viz_number_context_var)
        )
    new_context[viz_number_context_var] = 0

    # Step 4. Return the redering of the new elements
    return Template(new_template_text).render(Context(new_context))


def evaluate_action(action, extra_string=None,
                    column_name=None,
                    exclude_values=None):
    """
    Given an action object and an optional string:
    1) Access the attached workflow
    2) Obtain the data from the appropriate data frame
    3) Loop over each data row and
      3.1) Evaluate the conditions with respect to the values in the row
      3.2) Create a context with the result of evaluating the conditions,
           attributes and column names to values
      3.3) Run the template with the context
      3.4) Run the optional string argument with the template and the context
      3.5) Select the optional column_name
    6) Return the resulting objects:
       List of (HTMLs body, extra string, column name value)
        or an error message

    :param action: Action object with pointers to conditions, filter,
                   workflow, etc.
    :param extra_string: An extra string to process (something like the email
           subject line) with the same dictionary as the text in the action.
    :param column_name: Column from where to extract the special value (
           typically the email address) and include it in the result.
    :param exclude_values: List of values in the column to exclude
    :return: list of lists resulting from the evaluation of the action
    """

    # Step 1: Get the workflow to access the data and prepare data
    workflow = Workflow.objects.get(pk=action.workflow.id)
    col_names = workflow.get_column_names()
    col_idx = -1
    if column_name and column_name in col_names:
        col_idx = col_names.index(column_name)

    # Step 2: Get the row of data from the DB
    cond_filter = action.get_filter()

    # Step 3: Get the table data
    result = []
    data_frame = pandas_db.get_subframe(workflow.id,
                                        cond_filter,
                                        workflow.get_column_names())

    for __, row in data_frame.iterrows():

        # Get the dict(col_name, value)
        row_values = dict(list(zip(col_names, row)))

        if exclude_values and col_idx != -1 and \
                str(row_values[column_name]) in exclude_values:
            # Skip the row with the col_idx value in exclude values
            continue

        # Step 3: Evaluate all the conditions
        condition_eval = {}
        for condition in Condition.objects.filter(
                action__id=action.id
        ).values('is_filter', 'formula', 'name'):
            if condition['is_filter']:
                # Filter can be skipped in this stage
                continue

            # Evaluate the condition
            condition_eval[condition['name']] = \
                dataops.formula_evaluation.evaluate(
                    condition['formula'],
                    dataops.formula_evaluation.NodeEvaluation.EVAL_EXP,
                    row_values)

        # Step 4: Create the context with the attributes, the evaluation of the
        # conditions and the values of the columns.
        attributes = workflow.attributes
        context = dict(dict(row_values, **condition_eval), **attributes)

        # Step 5: run the template with the given context
        # Render the text and append to result
        try:
            partial_result = [render_template(action.get_content(),
                                              context,
                                              action)]
        except Exception as e:
            return _('Syntax error detected in the action text. {0}').format(
                e
            )

        # If there is extra message, render with context and create tuple
        if extra_string:
            try:
                partial_result.append(render_template(extra_string, context))
            except Exception as e:
                return _('Syntax error detected in the subject. {0}').format(
                    e
                )

        # If column_name was given (and it exists), create a tuple with that
        # element as the third component
        if col_idx != -1:
            partial_result.append(row_values[col_names[col_idx]])

        # Append result
        result.append(partial_result)

    return result


def get_row_values(action, row_idx):
    """
    Given an action and a row index, obtain the appropriate row of values
    from the data frame.

    :param action: Action object
    :param row_idx: Row index to use for evaluation
    :return Dictionary with the data row
    """

    # Step 1: Get the row of data from the DB
    cond_filter = action.get_filter()

    # If row_idx is an integer, get the data by index, otherwise, by key
    if isinstance(row_idx, int):
        result = ops.get_table_row_by_index(action.workflow,
                                            cond_filter,
                                            row_idx)
    else:
        result = pandas_db.get_table_row_by_key(action.workflow,
                                                cond_filter,
                                                row_idx,
                                                action.workflow.get_column_names())
    return result


def evaluate_row_action_out(action, context, text=None):
    """
    Given an action object and a row index:
    1) Evaluate the conditions with respect to the values in the row
    2) Create a context with the result of evaluating the conditions,
       attributes and column names to values
    3) Run the template with the context
    4) Return the resulting object (HTML?)

    :param action: Action object with pointers to conditions, filter,
                   workflow, etc.
    :param context: dictionary with the pairs name, value for the columns,
    attributes and conditions (true/false)
    :param text: If given, the text is processed in the template, if not
    action_content is used
    :return: String with the HTML content resulting from the evaluation
    """

    # If context is None, propagate.
    if context is None:
        return None

    # Invoke the appropriate function depending on the action type
    if action.is_in:
        raise Exception(_('Incorrect type of action'))

    if text is None:
        # If the text is not given, take the one in the action
        text = action.get_content()

    # Run the template with the given context
    # First create the template with the string stored in the action
    try:
        result = render_template(text, context, action)
    except TemplateSyntaxError as e:
        return render_to_string('action/syntax_error.html', {'msg': e})

    return result


def evaluate_row_action_in(action, context):
    """
    Given an action IN object and a row index:
    1) Create the form and the context
    2) Run the template with the context
    3) Return the resulting object (HTML?)

    :param action: Action object.
    :param row_values: Dictionary with pairs name/value
    :return: String with the HTML content resulting from the evaluation
    """

    # Get the active columns attached to the action
    columns = [c for c in action.columns.all() if c.is_active]

    # Get the row values.
    selected_values = [context[c.name] for c in columns]

    form = EnterActionIn(None, columns=columns, values=selected_values)

    # Render the form
    return Template(
        """<div align="center">
             <p class="lead">{{ description_text }}</p>
             {% load crispy_forms_tags %}{{ form|crispy }}
           </div>"""
    ).render(Context({'form': form,
                      'description_text': action.description_text}))


def run(*script_args):
    """
    Script for testing purposes
    :param script_args:
    :return:
    """
    del script_args

    template = """
    hi --{{ one }}--
    --{% if var1 %}var1{% endif %}--
    --{% if var2 %}var2{% endif %}-- 
    --{% if !"# %}var3{% endif %}--
    --{% if $%& %}var4{% endif %}--
    --{% if '() %}var5{% endif %}--
    --{{ +,- }}--
    --{{ ./: }}--
    --{{ ;<= }}--
    --{{ >?@ }}--
    --{{ [\] }}--
    --{{ ^_` }}--
    --{{ {|}~ }}--
    --{{ this one has spaces }}--
    --{{ OT_ The prefix }}--
    --{{ OT_The prefix 2 }}--
    """

    template = '<p>Hi&nbsp;{{ !"#$%&amp;()*+,-./:;&lt;=&gt;?@[\\]^_`{|}~ }}</p>'

    context = {
        'one': 1,
        'var1': True,
        'var2': True,
        '!"#': True,
        '$%&': True,
        "'()": True,
        '+,-': 'var6',
        './:': 'var7',
        ';<=': 'var8',
        '>?@': 'var9',
        '[\]': 'var10',
        '^_`': 'var11',
        '{|}~': 'var12',
        'this one has spaces': 'The spaces are not a problem',
        'OT_ The prefix': 'Prefix solved.',
        'OT_The prefix 2': 'Prefix 2 solved',
        'The prefix 2': 'This should NOT appear. ERROR',
    }
    context = {
        '!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~': 'Carmelo Coton',
    }

    print((escape(list(context.items())[0][0])))
    print((render_template(template, context)))
