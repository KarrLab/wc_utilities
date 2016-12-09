""" Reading/writing schema objects to/from files

* Comma separated values (.csv)
* Excel (.xlsx)
* Tab separated values (.tsv)

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2016-11-23
:Copyright: 2016, Karr Lab
:License: MIT
"""

from itertools import chain
from natsort import natsorted, ns
from os.path import basename, dirname, splitext
from warnings import warn
from wc_utils.schema import utils
from wc_utils.schema.core import Model, Attribute, RelatedAttribute, Validator, TabularOrientation, InvalidObject
from wc_utils.util.list import transpose
from wc_utils.workbook.io import (get_writer, get_reader, WorkbookStyle, WorksheetStyle,
                                  Writer as BaseWriter, Reader as BaseReader,
                                  convert as base_convert)


class Writer(object):
    """ Write model objects to file(s) """

    def run(self, path, objects, models,
            title=None, description=None, keywords=None, version=None, language=None, creator=None):
        """ Write a set of model objects to an Excel file, with one worksheet for each model, or to
        a or set of .csv or .tsv files, with one file for each model

        Args:
            path (:obj:`str`): path to write file(s)
            objects (:obj:`set`): set of objects
            models (:obj:`list`): list of model, in the order that they should
                appear as worksheets; all models which are not in `models` will
                follow in alphabetical order
            title (:obj:`str`, optional): title
            description (:obj:`str`, optional): description
            keywords (:obj:`str`, optional): keywords
            version (:obj:`str`, optional): version
            language (:obj:`str`, optional): language
            creator (:obj:`str`, optional): creator
        """

        # get related objects
        more_objects = set()
        for obj in objects:
            more_objects.update(obj.get_related())

        # clean objects
        all_objects = objects | more_objects
        error = Validator().run(all_objects)

        if error:
            warnings.warn('Storage may be lossy because the objects are not valid:\n  {}'.format(
                str(error).replace('\n', '\n  ').rstrip()))

        # group objects by class
        grouped_objects = {}
        for obj in all_objects:
            if obj.__class__ not in grouped_objects:
                grouped_objects[obj.__class__] = set()
            grouped_objects[obj.__class__].add(obj)

        # get neglected models
        unordered_models = natsorted(set(grouped_objects.keys()).difference(set(models)),
                                     lambda model: model.Meta.verbose_name, alg=ns.IGNORECASE)

        # add sheets
        _, ext = splitext(path)
        writer_cls = get_writer(ext)
        writer = writer_cls(path,
                            title=title, description=description, keywords=keywords,
                            version=version, language=language, creator=creator)
        writer.initialize_workbook()

        for model in chain(models, unordered_models):
            if model.Meta.tabular_orientation == TabularOrientation.inline:
                continue

            if model in grouped_objects:
                objects = grouped_objects[model]
            else:
                objects = set()

            self.write_model(writer, model, objects)

        writer.finalize_workbook()

    def write_model(self, writer, model, objects):
        """ Write a set of model objects to a file

        Args:
            writer (:obj:`BaseWriter`): io writer
            model (:obj:`class`): model
            objects (:obj:`set` of `Model`): set of instances of `model`            
        """

        # attribute order
        attributes = [model.Meta.attributes[attr_name] for attr_name in model.Meta.attribute_order]

        # column labels
        headings = [[attr.verbose_name for attr in attributes]]

        # objects
        objects = natsorted(objects, lambda obj: obj.serialize(), alg=ns.IGNORECASE)

        data = []
        for obj in objects:
            obj_data = []
            for attr in attributes:
                obj_data.append(attr.serialize(getattr(obj, attr.name)))
            data.append(obj_data)

        # transpose data for column orientation
        style = self.create_worksheet_style(model)
        if model.Meta.tabular_orientation == TabularOrientation.row:
            self.write_sheet(writer,
                             sheet_name=model.Meta.verbose_name_plural,
                             data=data,
                             column_headings=headings,
                             style=style,
                             )
        else:
            self.write_sheet(writer,
                             sheet_name=model.Meta.verbose_name,
                             data=transpose(data),
                             row_headings=headings,
                             style=style,
                             )

    def write_sheet(self, writer, sheet_name, data, row_headings=None, column_headings=None, style=None):
        """ Write data to sheet

        Args:
            writer (:obj:`BaseWriter`): io writer
            sheet_name (:obj:`str`): sheet name
            data (:obj:`list` of `list` of `object`): list of list of cell values
            row_headings (:obj:`list` of `list` of `str`, optional): list of list of row headings
            column_headings (:obj:`list` of `list` of `str`, optional): list of list of column headings
            style (:obj:`WorksheetStyle`, optional): worksheet style
        """
        row_headings = row_headings or []
        column_headings = column_headings or []

        # merge data, headings
        for i_row, row_heading in enumerate(transpose(row_headings)):
            if i_row < len(data):
                row = data[i_row]
            else:
                row = []
                data.append(row)

            for val in row_heading:
                row.insert(0, val)

        for i_row in range(len(row_headings)):
            for column_heading in column_headings:
                column_heading.insert(0, None)

        content = column_headings + data

        # write content to worksheet
        writer.write_worksheet(sheet_name, content, style=style)

    @staticmethod
    def create_worksheet_style(model):
        """ Create worksheet style for model

        Args:
            model (:obj:`class`): model class

        Returns:
            :obj:`WorksheetStyle`: worksheet style
        """
        style = WorksheetStyle(
            head_row_font_bold=True,
            head_row_fill_pattern='solid',
            head_row_fill_fgcolor='CCCCCC',
            row_height=15,
        )

        if model.Meta.tabular_orientation == TabularOrientation.row:
            style.head_rows = 1
            style.head_columns = model.Meta.frozen_columns
        else:
            style.head_rows = model.Meta.frozen_columns
            style.head_columns = 1

        return style


class Reader(object):
    """ Read model objects from file(s) """

    def run(self, path, models):
        """ Read a set of model objects from file(s)

        Args:
            path (:obj:`str`): path to file(s)
            models (:obj:`list` of `class`): list of models

        Returns:
            :obj:`dict`: model objects grouped by `Model`

        Raises:
            :obj:`ValueError`: if file(s) contains extra sheets that don't correspond to one of `models` or if the data is not valid
        """
        _, ext = splitext(path)
        reader_cls = get_reader(ext)
        reader = reader_cls(path)

        # initialize reading
        workbook = reader.initialize_workbook()

        # check that models are defined for each worksheet
        sheet_names = set(reader.get_sheet_names())
        model_names = set()
        for model in models:
            if model.Meta.tabular_orientation == TabularOrientation.row:
                model_names.add(model.Meta.verbose_name_plural)
            else:
                model_names.add(model.Meta.verbose_name)
        extra_sheets = sheet_names.difference(model_names)
        if extra_sheets:
            raise ValueError('Models must be defined for the following worksheets: {}'.format(', '.join(extra_sheets)))

        # read objects
        attributes = {}
        data = {}
        errors = {}
        objects = {}
        for model in models:
            model_attributes, model_data, model_errors, model_objects = self.read_model(reader, model)
            if model_attributes:
                attributes[model] = model_attributes
            if model_data:
                data[model] = model_data
            if model_errors:
                errors[model] = model_errors
            if model_objects:
                objects[model] = model_objects

        if errors:
            msg = 'The model cannot be loaded because the spreadsheet contains error(s):'
            for model, model_errors in errors.items():
                msg += '\n  {}:'.format(model.__name__)
                for model_error in model_errors:
                    msg += '\n    {}'.format(str(model_error).replace('\n', '\n    '))
            raise ValueError(msg)

        # link objects
        objects_by_primary_attribute = {}
        for model, objects_model in objects.items():
            objects_by_primary_attribute[model] = {obj.get_primary_attribute(): obj for obj in objects_model}

        errors = {}
        for model, objects_model in objects.items():
            model_errors = self.link_model(model, attributes[model], data[model], objects_model,
                                           objects_by_primary_attribute)
            if model_errors:
                errors[model] = model_errors

        if errors:
            msg = 'The model cannot be loaded because the spreadsheet contains error(s):'
            for model, model_errors in errors.items():
                msg += '\n  {}:'.format(model.__name__)
                for model_error in model_errors:
                    msg += '\n    {}'.format(str(model_error).replace('\n', '\n    '))
            raise ValueError(msg)

        # convert to sets
        for model in models:
            if model in objects:
                objects[model] = set(objects[model])
            else:
                objects[model] = set()

        for model, model_objects in objects_by_primary_attribute.items():
            if model not in objects:
                objects[model] = set()
            objects[model].update(model_objects.values())

        # validate
        all_objects = set()
        for model in models:
            all_objects.update(objects[model])

        errors = Validator().clean(all_objects)
        if errors:
            raise ValueError(str(errors))

        # return
        return objects

    def read_model(self, reader, model):
        """ Read a set of objects from a file

        Args:
            reader (:obj:`BaseReader`): reader
            model (:obj:`class`): model

        Returns:
            :obj:`tuple` of
                `list` of `Attribute`,
                `list` of `list` of `object`,
                `list` of `str`,
                `list` of `Model`: tuple of
                * attribute order of `data`
                * a two-dimensional nested list of object data
                * a list of parsing errors
                * constructed model objects
        """
        if model.Meta.tabular_orientation == TabularOrientation.row:
            sheet_name = model.Meta.verbose_name_plural
        else:
            sheet_name = model.Meta.verbose_name

        if sheet_name not in reader.get_sheet_names():
            return ([], [], None, [])

        # get worksheet
        if model.Meta.tabular_orientation == TabularOrientation.row:
            data, _, headings = self.read_sheet(reader, sheet_name, num_column_heading_rows=1)
        else:
            data, headings, _ = self.read_sheet(reader, sheet_name, num_row_heading_columns=1)
            data = transpose(data)
        headings = headings[0]

        # get attributes order
        attributes = [model.Meta.attributes[attr_name] for attr_name in model.Meta.attribute_order]

        # sort attributes by header order
        attributes = []
        errors = []
        for verbose_name in headings:
            attr = utils.get_attribute_by_verbose_name(model, verbose_name)
            if attr is None:
                errors.append('Header "{}" does not match any attributes'.format(verbose_name))
            else:
                attributes.append(attr)

        if errors:
            return ([], [], errors, [])

        # read data
        objects = []
        errors = []
        for obj_data in data:
            obj = model()

            obj_errors = []
            for attr, attr_value in zip(attributes, obj_data):
                if not isinstance(attr, RelatedAttribute):
                    value, error = attr.deserialize(attr_value)
                    if error:
                        obj_errors.append(error)
                    else:
                        setattr(obj, attr.name, value)

            if obj_errors:
                errors.append(InvalidObject(obj, obj_errors))

            objects.append(obj)

        return (attributes, data, errors, objects)

    def read_sheet(self, reader, sheet_name, num_row_heading_columns=0, num_column_heading_rows=0):
        """ Read file into a two-dimensional list

        Args:
            reader (:obj:`BaseReader`): reader
            sheet_name (:obj:`str`): worksheet name
            num_row_heading_columns (:obj:`int`, optional): number of columns of row headings
            num_column_heading_rows (:obj:`int`, optional): number of rows of column headings

        Returns:
            :obj:`tuple`: 
                * `list` of `list`: two-dimensional list of table values
                * `list` of `list`: row headings
                * `list` of `list`: column_headings

        """
        data = reader.read_worksheet(sheet_name)

        # separate header rows
        column_headings = []
        for i_row in range(num_column_heading_rows):
            column_headings.append(data.pop(0))

        # separate header columns
        row_headings = []
        for i_col in range(num_row_heading_columns):
            row_heading = []
            row_headings.append(row_heading)
            for row in data:
                row_heading.append(row.pop(0))

            for column_heading in column_headings:
                column_headings.pop(0)

        return (data, row_headings, column_headings)

    def link_model(self, model, attributes, data, objects, objects_by_primary_attribute):
        """ Construct object graph

        Args:
            model (:obj:`class`): model
            attributes (:obj:`list` of `Attribute`): attribute order of `data`
            data (:obj:`list` of `list` of `object`): nested list of object data
            objects (:obj:`list`): list of model objects in order of `data`
            objects_by_primary_attribute (:obj:`dict` of `class`: `dict of `object`:`Model`): dictionary of model objects grouped by model

        Returns:
            :obj:`list` of `str`: list of parsing errors
        """

        errors = []
        for obj_data, obj in zip(data, objects):
            for attr, attr_value in zip(attributes, obj_data):
                if isinstance(attr, RelatedAttribute):
                    value, error = attr.deserialize(attr_value, objects_by_primary_attribute)
                    if error:
                        errors.append(error)
                    else:
                        setattr(obj, attr.name, value)

        return errors


def convert(source, destination, models=None):
    """ Convert among Excel (.xlsx), comma separated (.csv), and tab separated formats (.tsv)

    Args:
        source (:obj:`str`): path to source file
        destination (:obj:`str`): path to save converted file
        models (:obj:`list` of `class`, optional): list of models
    """
    models = models or []

    worksheet_order = []
    style = WorkbookStyle()
    for model in models:
        if model.Meta.tabular_orientation == TabularOrientation.row:
            name = model.Meta.verbose_name_plural
        else:
            name = model.Meta.verbose_name

        worksheet_order.append(name)
        style[name] = Writer.create_worksheet_style(model)

    base_convert(source, destination, worksheet_order=worksheet_order, style=style)


def create_template(path, models, title=None, description=None, keywords=None,
                    version=None, language=None, creator=None):
    """ Create a template for a model

    Args:
        path (:obj:`str`): path to write file(s)
        models (:obj:`list`): list of model, in the order that they should
            appear as worksheets; all models which are not in `models` will
            follow in alphabetical order
        title (:obj:`str`, optional): title
        description (:obj:`str`, optional): description
        keywords (:obj:`str`, optional): keywords
        version (:obj:`str`, optional): version
        language (:obj:`str`, optional): language
        creator (:obj:`str`, optional): creator
    """
    Writer().run(path, set(), models,
                 title=title, description=description, keywords=keywords,
                 version=version, language=language, creator=creator)
