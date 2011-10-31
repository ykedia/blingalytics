#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Formats define how values in a report should be output for display to the
user. They generally take the underlying Python value and convert it into a
string appropriate for display in the given medium. For example, an internal
value of ``Decimal('9.99')`` might be converted to a display value of
``'$9.99'`` for monetary values.

All formatters accept the following optional keyword arguments:

* ``label``: A string that will be used as the label for the column, as
  returned by the
  :meth:`report_header <blingalytics.base.Report.report_header>` method. By
  default, this will be automatically generated based on the column name.
* ``align``: Either ``'left'`` or ``'right'``, used to determine the preferred
  alignment of the column data. If this is not supplied, the formatter will
  use its default alignment. Generally, number-type columns default to
  right-aligned, while other columns default to left-aligned.

.. note::

    Many of the formatters rely on Python's ``locale`` module to perform
    locale-dependent formatting. For example, if your locale is set to
    ``'en_US'``, monetary values will be formatted as ``'$1,234.00'``. If your
    locale is set to ``'en_GB'``, monetary values will be formatted as
    ``'£1,123.00'``. Your locale is set per Python thread, and should be
    set somewhere in your code that guarantees it will be run prior to any
    formatting operations. See Python's documentation for the ``locale``
    module for more.

Output formats
--------------

As a base, all formats have formatter functions defined for two types of
output: HTML and CSV. You can pass in ``'html'`` (the default) or ``'csv'``
as the format option to your report's
:meth:`report_rows <blingalytics.base.Report.report_rows>` and
:meth:`report_footer <blingalytics.base.Report.report_footer>` methods to
format the output appropriately.

But you are not limited to HTML and CSV output formatting. If you want to
format values differently for another medium, you can subclass any formats you
use and add a ``format_NAME`` method. For example, you could add a
``format_pdf`` method. You would then pass in ``'pdf'`` as the format option
to your report's :meth:`report_rows <blingalytics.base.Report.report_rows>`
and :meth:`report_footer <blingalytics.base.Report.report_footer>` methods.
See the docstring and code of the base ``Format`` class for more.
"""

import json
import locale

from blingalytics.utils import epoch


class Format(object):
    """
    Base class for formats.
    
    * label: A string that will be used as the label for the column. Optional,
      and if left as None a label will be automatically generated by the
      report's init method based on the format's column's name.
    * align: Either 'left' or 'right', used to determine the alignment of the
      output column. Optional, and each format type has its own default
      alignment. Generally, number-type columns default to right-aligned, and
      all other columns default to left-aligned.
    
    Subclasses should implement their own format methods. The format method
    is used as the default value formatter. You can also define as many
    format_OUTPUT methods as you like, where OUTPUT is the output type, such
    as 'html' or 'csv'. These methods are used if the formatted output varies
    between output types. The format methods should all handle a value of None
    and output an appropriate "blank" representation.
    
    Subclasses should also override the default_align and sort_alpha
    attributes, if appropriate. The default_align attribute should be either
    'left' or 'right' and determines whether, by default, the columns should
    be right-aligned or left-aligned.
    
    The sort_alpha attribute should be either True or False, and determines
    whether Redis will use alpha or numeric sorting for this column. See the
    util.cached_table module for more details.
    
    Subclasses may also override the header_info property, if appropriate.
    The report returns these property dicts as part of the table header
    information, and by default they contain column metadata for the column's
    label, alignment, hidden state and sortability.
    """
    default_align = 'left'
    sort_alpha = True

    def __init__(self, label=None, align=None):
        self.label = label
        self.align = align or self.default_align

    @property
    def header_info(self):
        info = {
            'label': self.label,
            'sortable': True,
            'data_type': self.__class__.__name__.lower(),
        }
        if self.align == 'right':
            info['className'] = 'num'
        return info

    def format(self, value):
        """Default format method simply stringifies the value."""
        if isinstance(value, basestring):
            return value.encode('utf-8')
        return str(value)

    def format_html(self, value):
        """
        By default, the HTML format method simply calls the format's basic
        format method. So if a format requires no HTML-specific formatting, it
        doesn't need to override this method.
        """
        return self.format(value)

    def format_csv(self, value):
        """
        By default, the CSV format method simply calls the format's basic
        format method. So if a format requires no CSV-specific formatting, it
        doesn't need to override this method.
        """
        return self.format(value)

    def format_raw(self, value):
        """
        Does no formatting whatsoever, and returns the Python value.
        """
        return value

class Hidden(Format):
    """
    No particular formatting is performed, and this column should be hidden
    from the end user. This column will be marked as hidden in the header data
    returned by your report's
    :meth:`report_header <blingalytics.base.Report.report_header>` method.

    A hidden column is used for the internal ID returned with each row. You
    could also use these yourself to, for example, pass along a URL that gets
    formatted into a nice-looking link with some front-end JavaScript.
    """
    sort_alpha = False

    @property
    def header_info(self):
        info = super(Hidden, self).header_info
        info['hidden'] = True
        return info

class Bling(Format):
    """
    Formats the column as monetary data. This is formatted as currency
    according to the thread-level locale setting. If being output for HTML,
    it will add grouping indicators (such as commas in the U.S.). If being
    output for CSV, it will not. By default, the column is right-aligned.

    For example, in the ``'en_US'`` locale, numbers will be formatted as
    ``'$1,234.56'`` for HTML or ``'$1234.56'`` for CSV.
    """
    default_align = 'right'
    sort_alpha = False

    def format_html(self, value):
        if value is None:
            value = 0
        return locale.currency(value, grouping=True)

    def format_csv(self, value):
        if value is None:
            value = 0
        return locale.currency(value)

    def format_xls(self, value):
        if value is None:
            value = 0
        return value

class Epoch(Format):
    """
    Formats the column as a date. Expects the underlying data to be stored as
    an integer number of days since the UNIX epoch. (This storage method works
    great in conjunction with a
    :class:`database.ColumnTransform <blingalytics.sources.database.ColumnTransform>`
    filter for doing timezone offsets.)
    
    This date is formatted according to the Python thread's ``locale``
    setting. For example, in the ``'en_US'`` locale, a date is formatted as
    '01/23/2011'. By default, the column is left-aligned.
    """
    sort_alpha = False

    def format(self, value):
        if value is None:
            return ''
        return epoch.hours_to_datetime(int(value) * 24).strftime(
            locale.nl_langinfo(locale.D_FMT))

class Date(Format):
    """
    Formats the column as a date. Expects the underlying data to be stored as
    a Python ``date`` or ``datetime`` object. This date is formatted according
    to the Python thread's ``locale`` setting. For example, in the ``'en_US'``
    locale, a date is formatted as '01/23/2011'. By default, the column is
    left-aligned.
    """
    sort_alpha = True

    def format(self, value):
        if value is None:
            return ''
        return value.strftime(locale.nl_langinfo(locale.D_FMT))

class Month(Format):
    """
    Formats the column as a month. Expects the underlying values to be Python
    ``datetime`` or ``date`` objects. For example, ``'Jan 2011'``.
    """
    sort_alpha = True

    def format(self, value):
        if value is None:
            return ''
        return value.strftime("%b %Y")

class Integer(Format):
    """
    Formats the data as an integer. This formatter accepts one additional
    optional argument:

    * ``grouping``: Whether or not the formatted value should have groupings
      (such as a comma in the U.S.) when output for HTML. For example, when
      representing the number of pageviews per month, you would probably want
      separators; however, for an database ID you probably don't. Defaults to
      ``True``.

    This formatting is based on the Python thread-level ``locale`` setting.
    For example, in the ``'en_US'`` locale, numbers will be formatted as
    ``'1,234'`` for HTML or ``'1234'`` for CSV. By default, the column is
    right-aligned.
    """
    default_align = 'right'
    sort_alpha = False

    def __init__(self, grouping=True, **kwargs):
        self.grouping = grouping
        super(Integer, self).__init__(**kwargs)

    def format_html(self, value):
        if value is None:
            value = 0
        try:
            return locale.format('%d', value, grouping=self.grouping)
        except TypeError:
            raise TypeError('Value was not an integer: %r' % value)

    def format_csv(self, value):
        if value is None:
            value = 0
        try:
            return locale.format('%d', value)
        except TypeError:
            raise TypeError('Value was not an integer: %r' % value)

    def format_xls(self, value):
        if value is None:
            value = 0
        if self.grouping:
            return value
        return str(value)

class Percent(Format):
    """
    Formats the data as a percent. This formatter accepts one additional
    optional argument:

    * ``precision``: The number of decimal places of precision that should be
      kept for display. Defaults to ``1``.

    This is formatted as a decimal number with a trailing percent sign. For
    example, numbers will be formatted as ``'12.3%'`` with a precision of
    ``1``. By default, this column is right-aligned.
    """
    default_align = 'right'
    sort_alpha = False

    def __init__(self, precision=1, **kwargs):
        self.precision = precision
        super(Percent, self).__init__(**kwargs)

    def format(self, value):
        if value is None:
            value = 0
        return locale.format('%%.%df' % self.precision, value) + '%'

    def format_xls(self, value):
        if value is None:
            value = 0
        return value / 100

class String(Format):
    """
    Formats column data as strings. Essentially, this will simply coerce
    values to strings. It also accepts a couple optional formatting
    parameters:

    * ``title``: If ``True``, will title-case the string. Defaults to
      ``False``.
    * ``truncate``: Set this to an integer value to truncate the string to
      that number of characters. Adds an ellipsis if truncation was performed.
      Defaults to not performing any truncation.
    
    This column is left-aligned by default.
    """
    sort_alpha = True

    def __init__(self, title=False, truncate=None, **kwargs):
        self.title = title
        if truncate is not None:
            try:
                self.truncate = int(truncate)
            except ValueError:
                raise ValueError('String formatter truncate value must be an integer.')
            if self.truncate < 1:
                raise ValueError('String formatter truncate value must be a positive integer.')
        self.truncate = truncate
        super(String, self).__init__(**kwargs)

    def format(self, value):
        if value is None:
            return ''
        if isinstance(value, basestring):
            value = value.encode('utf-8')
        else:
            value = str(value)
        if self.truncate is not None:
            if len(value) > self.truncate:
                if self.truncate > 3:
                    value = value[:self.truncate - 3] + '...'
                else:
                    value = value[:self.truncate]
        if self.title:
            value = value.title()
        return value

class Boolean(Format):
    """
    Formatter for boolean data. This coerces the value to a boolean, and then
    presents a string representation of whether it's true or false. It accepts
    one optional argument:

    * ``terms``: This is a tuple of three strings that determine how true,
      false, and null values will be represented, in that order. By default,
      it uses ``('Yes', 'No', '')``.
    
    This column is left-aligned by default.
    """
    sort_alpha = False

    def __init__(self, terms=('Yes', 'No', ''), **kwargs):
        self.true_term, self.false_term, self.none_term = terms
        super(Boolean, self).__init__(**kwargs)

    def format(self, value):
        if value is None:
            return self.none_term
        elif value:
            return self.true_term
        return self.false_term

class JSON(Format):
    """
    Arbitrary Python data, formatted as JSON.
    
    This simply runs json.dumps on the data, so you must ensure that it is
    JSON-encodable or you'll get a ValueError. This column is left-aligned by
    default.
    """
    sort_alpha = True

    def format(self, value):
        return json.dumps(value)
