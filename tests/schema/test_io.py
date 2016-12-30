""" Test schema IO

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2016-11-23
:Copyright: 2016, Karr Lab
:License: MIT
"""
from wc_utils.schema import core, utils
from wc_utils.schema.io import Reader, Writer, convert, create_template
from wc_utils.workbook.io import WorksheetStyle, read as read_workbook
import os
import shutil
import sys
import tempfile
import unittest


class Root(core.Model):
    id = core.StringAttribute(primary=True, unique=True)
    name = core.StringAttribute()

    class Meta(core.Model.Meta):
        attribute_order = ('id', 'name', )
        tabular_orientation = core.TabularOrientation.column


class Node(core.Model):
    id = core.SlugAttribute(primary=True)
    root = core.ManyToOneAttribute(Root, related_name='nodes')
    val1 = core.FloatAttribute()
    val2 = core.FloatAttribute()

    class Meta(core.Model.Meta):
        attribute_order = ('id', 'root', 'val1', 'val2', )


class OneToManyRowAttribute(core.OneToManyAttribute):
    pass


class OneToManyInlineAttribute(core.OneToManyAttribute):

    def serialize(self, value):
        return ', '.join([obj.id for obj in value])

    def deserialize(self, value, objects):
        if value:
            objs = []
            for id in value.split(', '):
                obj = OneToManyInline(id=id)
                if OneToManyInline not in objects:
                    objects[OneToManyInline] = {}
                objects[OneToManyInline][id] = obj
                objs.append(obj)

            return (objs, None)
        else:
            return (set(), None)


class Leaf(core.Model):
    id = core.StringAttribute(primary=True)
    nodes = core.ManyToManyAttribute(Node, related_name='leaves')
    val1 = core.FloatAttribute()
    val2 = core.FloatAttribute()
    onetomany_rows = OneToManyRowAttribute('OneToManyRow', related_name='leaf', related_none=False)
    onetomany_inlines = OneToManyInlineAttribute('OneToManyInline', related_name='leaf', related_none=False)

    class Meta(core.Model.Meta):
        attribute_order = (
            'id', 'nodes', 'val1', 'val2',
            'onetomany_rows', 'onetomany_inlines'
        )


class OneToManyRow(core.Model):
    id = core.SlugAttribute(primary=True)

    class Meta(core.Model.Meta):
        attribute_order = ('id',)


class OneToManyInline(core.Model):
    id = core.SlugAttribute(primary=False)

    class Meta(core.Model.Meta):
        attribute_order = ('id',)
        tabular_orientation = core.TabularOrientation.inline


class TestIo(unittest.TestCase):

    def setUp(self):
        self.root = root = Root(id='root', name=u'\u20ac')
        nodes = [
            Node(root=root, id='node_0', val1=1, val2=2),
            Node(root=root, id='node_1', val1=3, val2=4),
            Node(root=root, id='node_2', val1=5, val2=6),
        ]
        self.leaves = leaves = [
            Leaf(nodes=[nodes[0]], id='leaf_0_0', val1=7, val2=8),
            Leaf(nodes=[nodes[0]], id='leaf_0_1', val1=9, val2=10),
            Leaf(nodes=[nodes[1]], id='leaf_1_0', val1=11, val2=12),
            Leaf(nodes=[nodes[1]], id='leaf_1_1', val1=13, val2=14),
            Leaf(nodes=[nodes[2]], id='leaf_2_0', val1=15, val2=16),
            Leaf(nodes=[nodes[2]], id='leaf_2_1', val1=17, val2=18),
        ]
        leaves[0].onetomany_rows = [OneToManyRow(id='row_0_0'), OneToManyRow(id='row_0_1')]
        leaves[1].onetomany_rows = [OneToManyRow(id='row_1_0'), OneToManyRow(id='row_1_1')]
        leaves[2].onetomany_rows = [OneToManyRow(id='row_2_0'), OneToManyRow(id='row_2_1')]
        leaves[3].onetomany_rows = [OneToManyRow(id='row_3_0'), OneToManyRow(id='row_3_1')]
        leaves[4].onetomany_rows = [OneToManyRow(id='row_4_0'), OneToManyRow(id='row_4_1')]
        leaves[5].onetomany_rows = [OneToManyRow(id='row_5_0'), OneToManyRow(id='row_5_1')]

        leaves[0].onetomany_inlines = [OneToManyInline(id='inline_0_0'), OneToManyInline(id='inline_0_1')]
        leaves[1].onetomany_inlines = [OneToManyInline(id='inline_1_0'), OneToManyInline(id='inline_1_1')]
        leaves[2].onetomany_inlines = [OneToManyInline(id='inline_2_0'), OneToManyInline(id='inline_2_1')]
        leaves[3].onetomany_inlines = [OneToManyInline(id='inline_3_0'), OneToManyInline(id='inline_3_1')]
        leaves[4].onetomany_inlines = [OneToManyInline(id='inline_4_0'), OneToManyInline(id='inline_4_1')]
        leaves[5].onetomany_inlines = [OneToManyInline(id='inline_5_0'), OneToManyInline(id='inline_5_1')]

        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_write_read(self):
        # test integrity of relationships
        for leaf in self.leaves:
            for row in leaf.onetomany_rows:
                self.assertEqual(row.leaf, leaf)

        # write/read to/from Excel
        root = self.root
        objects = set((root, )) | root.get_related()
        objects = utils.group_objects_by_model(objects)

        filename = os.path.join(self.dirname, 'test.xlsx')
        Writer().run(filename, set((root,)), [Root, Node, Leaf, ])
        objects2 = Reader().run(filename, [Root, Node, Leaf, OneToManyRow])

        # validate
        all_objects2 = set()
        for model, model_objects in objects2.items():
            all_objects2.update(model_objects)
        self.assertEqual(core.Validator().run(all_objects2), None)

        # test objects saved and loaded correctly
        for model in objects.keys():
            self.assertEqual(len(objects2[model]), len(objects[model]),
                             msg='Different numbers of "{}" objects'.format(model.__name__))
        self.assertEqual(len(objects2), len(objects))

        root2 = objects2[Root].pop()

        filename2 = os.path.join(self.dirname, 'test2.xlsx')
        Writer().run(filename2, set((root2,)), [Root, Node, Leaf, ])
        original = read_workbook(filename)
        copy = read_workbook(filename2)
        self.assertEqual(copy, original)

        self.assertEqual(set([x.id for x in root2.nodes]), set([x.id for x in root.nodes]))
        self.assertEqual(root2, root)

        # unicode
        self.assertEqual(root2.name, u'\u20ac')

    def test_validation(self):
        t = Root(name='f')
        self.assertIn('value for primary attribute cannot be empty',
            t.validate().attributes[0].messages[0])

    @unittest.skip("error reporting formatting needs repair")
    def test_read_bad_headers(self):
        msgs = [
            "'Nodes': Empty header field in row 1, col E - delete empty column(s)",
            "'Nodes': Header 'y' does not match any attribute",
            "'Root': Empty header field in row 4, col A - delete empty row(s)",
            "'Root': Header 'x' does not match any attribute",]
        excel_fixture_filename = os.path.join(os.path.dirname(__file__), 'fixtures',
            'bad-headers.xlsx')
        with self.assertRaises(ValueError) as context:
            Reader().run(excel_fixture_filename, [Root, Node, Leaf, OneToManyRow])
        for msg in msgs:
            self.assertIn(msg, str(context.exception))

        msgs = [
            "'Nodes': Empty header field in row 1, col 5 - delete empty column(s)",
            "'Nodes': Header 'y' does not match any attribute",
            "'Root': Empty header field in row 4, col 1 - delete empty row(s)",
            "'Root': Header 'x' does not match any attribute",]
        csv_fixture_fileglob = os.path.join(os.path.dirname(__file__), 'fixtures',
            'bad-headers-*.csv')
        with self.assertRaises(ValueError) as context:
            Reader().run(csv_fixture_fileglob, [Root, Node, Leaf, OneToManyRow])
        for msg in msgs:
            self.assertIn(msg, str(context.exception))

        msgs = [
            "Duplicate, case insensitive, header fields: 'Root', 'root'",
            "Duplicate, case insensitive, header fields: 'good val', 'Good val', 'Good VAL'"]
        excel_fixture_filename = os.path.join(os.path.dirname(__file__), 'fixtures',
            'duplicate-headers.xlsx')
        with self.assertRaises(ValueError) as context:
            Reader().run(excel_fixture_filename, [Node])
        for msg in msgs:
            self.assertIn(msg, str(context.exception))

    @unittest.skip("error reporting formatting needs repair")
    def test_read_invalid_data(self):
        class Normal(core.Model):
            id = core.SlugAttribute()
            val = core.StringAttribute(min_length=2)

            class Meta(core.Model.Meta):
                attribute_order = ('id', 'val', )

        class Transposed(core.Model):
            id = core.SlugAttribute()
            val = core.StringAttribute(min_length=2)

            class Meta(core.Model.Meta):
                attribute_order = ('id', 'val', )
                tabular_orientation = core.TabularOrientation.column

        RE_msgs = [
            "Leaf: *\n +id:''\n +invalid-data.xlsx:Leaves:A6:\n +StringAttribute value for primary attribute cannot be empty",
            "Transposed:\n +val:'x'\n +invalid-data.xlsx:Transposed:C2:\n +Value must be at least 2 characters",]
        excel_fixture_filename = os.path.join(os.path.dirname(__file__), 'fixtures',
            'invalid-data.xlsx')
        with self.assertRaises(ValueError) as context:
            Reader().run(excel_fixture_filename, [Leaf, Normal, Transposed])
        for RE in RE_msgs:
            self.assertRegexpMatches(str(context.exception), RE)

        RE_msgs = [
            "Leaf: *\n +id:''\n +invalid-data-\*.csv:Leaves:6,1:\n +StringAttribute value for primary attribute cannot be empty",
            "Transposed:\n +val:'x'\n +invalid-data-\*.csv:Transposed:2,3:\n +Value must be at least 2 characters",]
        csv_fixture_fileglob = os.path.join(os.path.dirname(__file__), 'fixtures',
            'invalid-data-*.csv')
        with self.assertRaises(ValueError) as context:
            Reader().run(csv_fixture_fileglob, [Leaf, Normal, Transposed])
        for RE in RE_msgs:
            self.assertRegexpMatches(str(context.exception), RE)

    def test_create_worksheet_style(self):
        self.assertIsInstance(Writer.create_worksheet_style(Root), WorksheetStyle)

    def test_convert(self):
        filename_xls1 = os.path.join(self.dirname, 'test1.xlsx')
        filename_xls2 = os.path.join(self.dirname, 'test2_unreadable.xlsx')
        filename_csv = os.path.join(self.dirname, 'test-*.csv')

        models = [Root, Node, Leaf, ]
        Writer().run(filename_xls1, set((self.root,)), models)

        convert(filename_xls1, filename_csv, models)
        # this writes a workbook that Excel (Mac 2016) calls 'unreadable'
        # Excel also repairs the workbook and generates a "Repair result" xml file
        convert(filename_csv, filename_xls2, models)

    def test_create_template(self):
        filename = os.path.join(self.dirname, 'test3.xlsx')
        create_template(filename, [Root, Node, Leaf])
        objects = Reader().run(filename, [Root, Node, Leaf])
        self.assertEqual(objects, {
            Root: set(),
            Node: set(),
            Leaf: set(),
        })
        self.assertEqual(core.Validator().run([]), None)
