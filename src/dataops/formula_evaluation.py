# -*- coding: utf-8 -*-


import itertools
from builtins import str

from django.utils.dateparse import parse_datetime
from django.utils.translation import ugettext_lazy as _, ugettext

from ontask import OnTaskException, fix_pctg_in_name


class NodeEvaluation:
    """
    Class to evaluate the nodes ina formula. The methods provide three types of
    evaluation: python expression, SQL query, and text rendering.
    """

    # Type of evaluations for this node
    EVAL_EXP = 0
    EVAL_SQL = 1
    EVAL_TXT = 2

    GET_CONSTANT_FN = {
        'integer': lambda x: int(x),
        'double': lambda x: float(x),
        'boolean': lambda x: x == 1,
        'string': lambda x: str(x),
        'datetime': lambda x: parse_datetime(x)
    }

    def __init__(self, node, given_variables=None):
        """
        Create the object with the given expression node and the variable value
        :param node: Formula leaf node
        :param given_variables: Dictionary with the pairs (varname, varvalue)
        to use to evaluate the expression
        """
        self.node = node
        self.given_variables = given_variables

    def get_constant(self):
        """
        Method to turn value (in node['value']) into the right constant (type
        in node['type'])
        :return: The right Python value
        """
        return self.GET_CONSTANT_FN.get(self.node['type'])(self.node['value'])

    def get_value(self):
        """
        Method to return the value to consider for the variable in
        node['field']
        :return: The value
        """

        # Get the variable name
        varname = self.node['field']

        varvalue = None
        if self.given_variables is not None:
            # If no value in dictionary, finish
            if varname not in self.given_variables:
                raise OnTaskException(
                    'No value found for variable {0}'.format(varname),
                    0
                )

            varvalue = self.given_variables.get(varname, None)

        return varvalue

    def get_evaluation(self, eval_type):
        """
        Evaluate the current node with the type of evaluation given
        :param eval_type: One of three: EVAL_EXP, EVAL_SQL or EVAL_TXT
        :return: The resulting expression, SQL query or text respectively
        """

        return getattr(self, '_op_' + self.node['operator'])(eval_type)

    def _op_equal(self, eval_type):
        """
        Process the equal operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue == constant

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])
            result = '("{0}"'.format(varname) + \
                     ' = %s) AND ("{0}" is not null)'.format(varname)
            result_fields = [str(constant)]

            return result, result_fields

        # Text evaluation
        return '{0} equal to {1}'.format(self.node['field'], constant)

    def _op_not_equal(self, eval_type):
        """
        Process the not equal operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue != constant

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])
            result = '("{0}"'.format(varname) + \
                     '!= %s) OR ("{0}" is null)'.format(varname)
            result_fields = [str(constant)]

            return result, result_fields

        # Text evaluation
        return '{0} not equal to {1}'.format(self.node['field'], constant)

    def _op_begins_with(self, eval_type):
        """
        Process the begins_with operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue.startswith(constant)

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     ' LIKE %s) AND ("{0}" is not null)'.format(varname)
            result_fields = [self.node['value'] + "%"]

            return result, result_fields

        # Text evaluation
        return '{0} starts with {1}'.format(self.node['field'], constant)

    def _op_not_begins_with(self, eval_type):
        """
        Process the not_begins_with operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and not varvalue.startswith(constant)

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     ' NOT LIKE %s) OR ("{0}" is null)'.format(varname)
            result_fields = [self.node['value'] + "%"]

            return result, result_fields

        # Text evaluation
        return '{0} does not start with {1}'.format(self.node['field'],
                                                    constant)

    def _op_contains(self, eval_type):
        """
        Process the contains operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue.find(constant) != -1

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     ' LIKE %s) AND ("{0}" is not null)'.format(varname)
            result_fields = ["%" + self.node['value'] + "%"]

            return result, result_fields

        # Text evaluation
        return '{0} contains {1}'.format(self.node['field'], constant)

    def _op_not_contains(self, eval_type):
        """
        Process the not_contains operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue.find(constant) == -1

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     ' NOT LIKE %s) OR ("{0}" is null)'.format(varname)
            result_fields = ["%" + self.node['value'] + "%"]

            return result, result_fields

        # Text evaluation
        return '{0} does not contain {1}'.format(self.node['field'], constant)

    def _op_ends_with(self, eval_type):
        """
        Process the ends_with operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue.endswith(constant)

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     ' LIKE %s) AND ("{0}" is not null)'.format(varname)
            result_fields = ["%" + self.node['value']]

            return result, result_fields

        # Text evaluation
        return '{0} ends with {1}'.format(self.node['field'], constant)

    def _op_not_ends_with(self, eval_type):
        """
        Process the not_ends_width operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and (not varvalue.endswith(constant))

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     ' NOT LIKE %s) OR ("{0}" is null)'.format(varname)
            result_fields = ["%" + self.node['value']]

            return result, result_fields

        # Text evaluation
        return '{0} does not end with {1}'.format(self.node['field'], constant)

    def _op_is_empty(self, eval_type):
        """
        Process the is_empty operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue == ''

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     " = '') OR (\"{0}\" is null)".format(varname)

            return result, []

        # Text evaluation
        return '{0} is empty'.format(self.node['field'])

    def _op_is_not_empty(self, eval_type):
        """
        Process the is_empty operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return (varvalue is not None) and varvalue != ''

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '("{0}"'.format(varname) + \
                     " != '') AND (\"{0}\" is not null)".format(varname)

            return result, []

        # Text evaluation
        return '{0} is not empty'.format(self.node['field'])

    def _op_is_null(self, eval_type):
        """
        Process the is_null operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return varvalue is None

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '(\"{0}\" is null)'.format(varname)

            return result, []

        # Text evaluation
        return '{0} is null'.format(self.node['field'])

    def _op_is_not_null(self, eval_type):
        """
        Process the is_not_null operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            return varvalue is not None

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '(\"{0}\" is not null)'.format(varname)

            return result, []

        # Text evaluation
        return '{0} is not null'.format(self.node['field'])

    def _op_less(self, eval_type):
        """
        Process the less operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            if self.node['type'] in ('integer', 'double', 'datetime'):
                return (varvalue is not None) and varvalue < constant
            raise Exception(
                ugettext(
                    'Evaluation error: Type {0} not allowed with operator LESS'
                ).format(self.node['type'])
            )

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '"{0}"'.format(varname) + ' < %s'
            result_fields = [str(constant)]

            return result, result_fields

        # Text evaluation
        return '{0} is less than {1}'.format(self.node['field'], constant)

    def _op_less_or_equal(self, eval_type):
        """
        Process the less_or_equal operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            if self.node['type'] in ('integer', 'double', 'datetime'):
                return (varvalue is not None) and varvalue <= constant
            raise Exception(
                ugettext(
                    'Evaluation error: Type {0} not allowed '
                    'with operator LESS OR EQUAL'
                ).format(self.node['type'])
            )

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '"{0}"'.format(varname) + ' <= %s'
            result_fields = [str(constant)]

            return result, result_fields

        # Text evaluation
        return '{0} is less than or equal to {1}'.format(self.node['field'],
                                                         constant)

    def _op_greater(self, eval_type):
        """
        Process the greater operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            if self.node['type'] in ('integer', 'double', 'datetime'):
                return (varvalue is not None) and varvalue > constant
            raise Exception(
                ugettext(
                    'Evaluation error: Type {0} not allowed '
                    'with operator GREATER'
                ).format(self.node['type'])
            )

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '"{0}"'.format(varname) + ' > %s'
            result_fields = [str(constant)]

            return result, result_fields

        # Text evaluation
        return '{0} is greater than {1}'.format(self.node['field'], constant)

    def _op_greater_or_equal(self, eval_type):
        """
        Process the greater_or_equal operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        constant = self.GET_CONSTANT_FN.get(
            self.node['type']
        )(self.node['value'])

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            if self.node['type'] in ('integer', 'double', 'datetime'):
                return (varvalue is not None) and varvalue >= constant
            raise Exception(
                ugettext(
                    'Evaluation error: Type {0} not allowed '
                    'with operator GREATER OR EQUAL'
                ).format(self.node['type'])
            )

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '"{0}"'.format(varname) + ' >= %s'
            result_fields = [str(constant)]

            return result, result_fields

        # Text evaluation
        return '{0} is greater than or equal to {1}'.format(self.node['field'],
                                                            constant)

    def _op_between(self, eval_type):
        """
        Process the between operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            if self.node['type'] not in ('integer', 'double', 'datetime'):
                raise Exception(
                    ugettext(
                        'Evaluation error: Type {0} not allowed '
                        'with operator BETWEEN'
                    ).format(self.node['type'])
                )
            left = self.GET_CONSTANT_FN[self.node['type']](
                self.node['value'][0]
            )
            right = self.GET_CONSTANT_FN[self.node['type']](
                self.node['value'][1]
            )

            return (varvalue is not None) and left <= varvalue <= right

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '"{0}"'.format(varname) + ' BETWEEN %s AND %s'
            result_fields = [str(self.node['value'][0]),
                             str(self.node['value'][1])]

            return result, result_fields

        # Text evaluation
        return '{0} is between {1} and {2}'.format(self.node['field'],
                                                   str(self.node['value'][0]),
                                                   str(self.node['value'][1]))

    def _op_not_between(self, eval_type):
        """
        Process the not_between operator
        :param eval_type: Type of evaluation
        :return: Boolean result, SQL query, or text result
        """

        if eval_type == self.EVAL_EXP:
            # Python evaluation
            varvalue = self.get_value()
            if self.node['type'] not in ('integer', 'double', 'datetime'):
                raise Exception(
                    ugettext(
                        'Evaluation error: Type {0} not allowed '
                        'with operator BETWEEN'
                    ).format(self.node['type'])
                )
            left = self.GET_CONSTANT_FN[self.node['type']](
                self.node['value'][0]
            )
            right = self.GET_CONSTANT_FN[self.node['type']](
                self.node['value'][1]
            )

            return (varvalue is not None) and not left <= varvalue <= right

        if eval_type == self.EVAL_SQL:
            # SQL evaluation
            varname = fix_pctg_in_name(self.node['field'])

            result = '"{0}"'.format(varname) + ' NOT BETWEEN %s AND %s'
            result_fields = [str(self.node['value'][0]),
                             str(self.node['value'][1])]

            return result, result_fields

        # Text evaluation
        return '{0} is not between {1} and {2}'.format(
            self.node['field'],
            str(self.node['value'][0]),
            str(self.node['value'][1])
        )


def has_variable(formula, variable):
    """
    Function that detects if a formula contains an ID. It traverses the
    recursive structure checking for the field "id" in the dictionaries.

    :param formula: node element at the top of the formula
    :param variable: ID to search for
    :return: Boolean encoding if formula has id.
    """

    if 'condition' in formula:
        # Node is a condition, get the values of the sub classes and take a
        # disjunction of the results.

        return any([has_variable(x, variable) for x in formula['rules']])

    return formula['id'] == variable


def get_variables(formula):
    """
    Return a list with the variable names in a formula
    :param formula:
    :return: list of strings (variable names)
    """

    if 'condition' in formula:
        return list(itertools.chain.from_iterable(
            [get_variables(x) for x in formula['rules']]
        ))

    return [formula['id']]


def rename_variable(formula, old_name, new_name):
    """
    Function that traverses the formula and changes the appearance of one
    variable. The renaming is done to the values of the id and field
     attributes.
    :param formula: Root node of the formula object
    :param old_name: Old variable name
    :param new_name: New variable name
    :return: The new modified formula.
    """

    # Trivial case of an empty formula
    if not formula:
        return formula

    if 'condition' in formula:
        # Recursive call
        formula['rules'] = [rename_variable(x, old_name, new_name)
                            for x in formula['rules']]
        return formula

    # Loop over the changes and apply them to this node
    if formula['id'] != old_name:
        # No need to rename this formula
        return formula

    formula['id'] = new_name
    formula['field'] = new_name

    return formula


def evaluate(node, eval_type, given_variables=None):
    """
    Given a node representing a formula, and a dictionary with (name, values),
    evaluates the expression represented by the node.
    :param node: Node representing the expression
    :param eval_type: Type of evaluation. See NodeEvaluation: EVAL_EXP is for
    a python expression, EVAL_SQL is a query, and EVAL_TXT a text representation
    of the formula
    :param given_variables: Dictionary (name, value) of variables
    :return: True/False, SQL query or text depending on eval_type
    """
    if 'condition' in node:
        # Node is a condition, get the values of the sub-clauses
        sub_clauses = [evaluate(x, eval_type, given_variables)
                       for x in node['rules']]

        # Now combine
        if eval_type == NodeEvaluation.EVAL_EXP:
            if node['condition'] == 'AND':
                result = all(sub_clauses)
            else:
                result = any(sub_clauses)

            if node.get('not', False):
                result = not result

            return result

        if eval_type == NodeEvaluation.EVAL_SQL:

            if not sub_clauses:
                # Nothing has been returned, so it is an empty query
                return '', []

            if node['condition'] == 'AND':
                result = '((' + \
                         ') AND ('.join([x for x, __ in sub_clauses]) + '))'
            else:
                result = '((' + \
                         ') OR ('.join([x for x, __ in sub_clauses]) + '))'
            result_fields = \
                list(itertools.chain.from_iterable(
                    [x for __, x in sub_clauses]))

            if node.get('not', False):
                result = '(NOT (' + result + '))'

            return result, result_fields

        # Text evaluation
        if len(sub_clauses) > 1:
            if node['condition'] == 'AND':
                result = '(' + \
                         ') AND ('.join([x for x in sub_clauses]) + ')'
            else:
                result = '(' + \
                         ') OR ('.join([x for x in sub_clauses]) + ')'
        else:
            result = sub_clauses[0]

        if node.get('not', False):
            result = 'NOT (' + result + ')'

        return result

    return NodeEvaluation(
        node,
        given_variables
    ).get_evaluation(eval_type)
