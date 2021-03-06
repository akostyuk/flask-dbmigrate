import os
import re
import sys
import unittest
import logging
from shutil import rmtree
from StringIO import StringIO

from flask import Flask
from flask.ext.script import Command, Manager
from flask.ext.sqlalchemy import SQLAlchemy

from sqlalchemy.engine.reflection import Inspector

from flask_dbmigrate import DBMigrate, ImproperlyConfigured
from flask_dbmigrate import manager as dbmanager


def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)


def make_test_model(db):
    class Test(db.Model):
        __tablename__ = 'test'
        id = db.Column('test_id', db.Integer, primary_key=True)
        column1 = db.Column(db.String(60))

        def __init__(self, column1):
            self.column1 = column1
    return Test


def with_database(test_method):
    def wrapper(self):
        self.dbmigrate.init()
        self.dbmigrate._upgrade()
        test_method(self)
        self.dbmigrate._drop()
    return wrapper


def with_database_changes(test_method):
    def wrapper(self):
        self.dbmigrate.init()
        self.dbmigrate._upgrade()

        self.app.db = SQLAlchemy(self.app)

        class Test(self.app.db.Model):
            __tablename__ = 'test'
            id = self.app.db.Column('test_id', self.app.db.Integer,
                primary_key=True)
            column1 = self.app.db.Column(self.app.db.String(60))
            column2 = self.app.db.Column(self.app.db.String(60))

            def __init__(self, column1):
                self.column1 = column1

        test_method(self)
        self.dbmigrate._drop()
    return wrapper


class TestConfig(object):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + rel('test.sqlite3')
    # SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_MIGRATE_REPO = rel('migrations')


class TestCommand(Command):
    def run(self):
        print('test ok')


class DBMigrateInitTestCase(unittest.TestCase):

    def test_dbmigrate_init_no_app(self):
        # DBMigrate always required app
        self.assertRaises(TypeError, DBMigrate)

    def test_dbmigrate_init_app_no_config(self):
        app = Flask(__name__)
        self.assertRaises(ImproperlyConfigured, DBMigrate, app=app)

    def test_dbmigrate_init_app_config(self):
        app = Flask(__name__)
        app.config.from_object(TestConfig)
        DBMigrate(app)


class DBMigrateSubManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.output = StringIO()
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()

    def test_add_dbmigrate_submanager(self):
        dbmigrate_manager = Manager()

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmigrate_manager)

        assert isinstance(manager._commands['dbmigrate'], Manager)
        self.assertEquals(dbmigrate_manager.parent, manager)
        self.assertEquals(dbmigrate_manager.get_options(),
            manager.get_options())

    def test_run_dbmigrate_test(self):
        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'test']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        assert 'test ok' in self.output.getvalue()


class DBMigrateCommandsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        self.app.config['SQLALCHEMY_MIGRATE_REPO'] += self.id()
        self.app.db = SQLAlchemy(self.app)
        self.Test = make_test_model(self.app.db)
        self.dbmigrate = DBMigrate(self.app)
        self.output = StringIO()
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()
        if os.path.exists(self.app.config['SQLALCHEMY_MIGRATE_REPO']):
            rmtree(self.app.config['SQLALCHEMY_MIGRATE_REPO'])
        if os.path.exists(rel('test.sqlite3')):
            os.remove(rel('test.sqlite3'))

    def test_init(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'init']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        self.assertTrue(os.path.exists(
            self.app.config['SQLALCHEMY_MIGRATE_REPO']))

        migration = os.path.join(self.app.config['SQLALCHEMY_MIGRATE_REPO'],
            'versions/001_initial.py')

        self.assertTrue(os.path.exists(migration))

        # drop
        self.dbmigrate._drop()

    def test_schemamigrate_no_repository(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'You have no database under version '
            'control. Try to "init" it first')

    @with_database
    def test_schemamigrate_no_changes(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'No Changes!')

    @with_database_changes
    def test_schemamigrate_with_changes(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        migration = os.path.join(self.app.config['SQLALCHEMY_MIGRATE_REPO'],
            'versions/002_auto_generated.py')

        self.assertTrue(os.path.exists(migration))

    @with_database_changes
    def test_schemamigrate_with_changes_named(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration', '-n',
        'migration_name']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        migration = os.path.join(self.app.config['SQLALCHEMY_MIGRATE_REPO'],
            'versions/002_migration_name.py')

        self.assertTrue(os.path.exists(migration))

    @with_database_changes
    def test_schemamigrate_with_changes_stdout(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration', '--stdout']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        output = sys.stdout.getvalue().strip()

        pattern = re.compile('^# __VERSION__: (?P<version>\d+)\n')
        self.assertTrue(re.search(pattern, output))

    def test_migrate_show_no_migrations(self):

        self.dbmigrate.init()

        migration = os.path.join(self.app.config['SQLALCHEMY_MIGRATE_REPO'],
            'versions/001_initial.py')
        if os.path.exists(migration):
            os.remove(migration)

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'migrate', '--show']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        assert 'No migrations!' in sys.stdout.getvalue().strip()
        self.dbmigrate._drop()

    @with_database_changes
    def test_migrate_show_with_migrations(self):

        self.dbmigrate.db = self.app.db
        self.dbmigrate.schemamigrate(migration_name='added_column2')

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'migrate', '--show']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        out = sys.stdout.getvalue().strip()
        assert '( ) 002_added_column2 (ver. 2)' in out

    @with_database_changes
    def test_migrate_upgrade(self):

        self.dbmigrate.db = self.app.db
        self.dbmigrate.schemamigrate(migration_name='added_column2')

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'migrate']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        assert self.dbmigrate._get_db_version() == \
            self.dbmigrate._get_repo_version()

        i = Inspector(self.dbmigrate.db.engine)

        # check if table "test" exist
        assert 'test' in i.get_table_names()

        # check if column "column2" exists in table "test"
        assert 'column2' in [c['name'] for c in i.get_columns('test')]

    @with_database
    def test_migrate_downgrade_to_0(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'migrate', '-v', '0']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        i = Inspector(self.dbmigrate.db.engine)

        # check if table "test" does not exist
        assert 'test' not in i.get_table_names()


class DBMigrateRelationshipsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        # Use unique repository for each test
        self.app.config['SQLALCHEMY_MIGRATE_REPO'] += self.id()
        self.app.db = SQLAlchemy(self.app)
        self.output = StringIO()
        sys.stdout = self.output

    def tearDown(self):
        self.dbmigrate._drop()
        self.output.close()
        if os.path.exists(self.app.config['SQLALCHEMY_MIGRATE_REPO']):
            rmtree(self.app.config['SQLALCHEMY_MIGRATE_REPO'])
        if os.path.exists(rel('test.sqlite3')):
            os.remove(rel('test.sqlite3'))

    def test_one_to_many_relationship(self):

        # initial "parent" table
        class Parent(self.app.db.Model):
            __tablename__ = 'parent'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)

        self.dbmigrate = DBMigrate(self.app)
        self.dbmigrate.init()
        self.dbmigrate._upgrade()

        # check that table "parent" has been properly created
        assert 'parent' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        self.app.db = SQLAlchemy(self.app)

        # add o2m rel to "child" table
        class Parent(self.app.db.Model):
            __tablename__ = 'parent'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)
            children = self.app.db.relationship("Child")

        class Child(self.app.db.Model):
            __tablename__ = 'child'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)
            parent_id = self.app.db.Column(self.app.db.Integer,
                self.app.db.ForeignKey('parent.id'))

        self.dbmigrate.db = self.app.db
        self.dbmigrate.schemamigrate(migration_name='added_child_table')
        self.dbmigrate._upgrade()

        # check that table "child" has been properly created
        assert 'child' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        # downgrade to 1
        self.dbmigrate.migrate(upgrade=False, version=1)

        # check that table "child" has been properly deleted
        assert 'child' not in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

    def test_many_to_one_relationship(self):

        # initial "parent" table
        class Parent(self.app.db.Model):
            __tablename__ = 'parent'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)

        self.dbmigrate = DBMigrate(self.app)
        self.dbmigrate.init()
        self.dbmigrate._upgrade()

        # check that table "parent" has been properly created
        assert 'parent' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        self.app.db = SQLAlchemy(self.app)

        # add m2o rel to "child" table
        class Parent(self.app.db.Model):
            __tablename__ = 'parent'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)
            child_id = self.app.db.Column(self.app.db.Integer,
                self.app.db.ForeignKey('child.id'))
            child = self.app.db.relationship("Child")

        class Child(self.app.db.Model):
            __tablename__ = 'child'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)

        self.dbmigrate.db = self.app.db
        self.dbmigrate.schemamigrate(migration_name='added_child_table')
        self.dbmigrate._upgrade()

        # check that table "child" has been properly created
        assert 'child' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        # downgrade to 1
        self.dbmigrate.migrate(upgrade=False, version=1)

        # check that table "child" has been properly deleted
        assert 'child' not in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

    def test_one_to_one_relationship(self):

        # initial "parent" table
        class Parent(self.app.db.Model):
            __tablename__ = 'parent'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)

        self.dbmigrate = DBMigrate(self.app)
        self.dbmigrate.init()
        self.dbmigrate._upgrade()

        # check that table "parent" has been properly created
        assert 'parent' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        self.app.db = SQLAlchemy(self.app)

        # add o2o rel to "child" table
        class Parent(self.app.db.Model):
            __tablename__ = 'parent'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)
            child = self.app.db.relationship("Child",
                uselist=False, backref="parent")

        class Child(self.app.db.Model):
            __tablename__ = 'child'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)

        self.dbmigrate.db = self.app.db
        self.dbmigrate.schemamigrate(migration_name='added_child_table')
        self.dbmigrate._upgrade()

        # check that table "child" has been properly created
        assert 'child' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        # downgrade to 1
        self.dbmigrate.migrate(upgrade=False, version=1)

        # check that table "child" has been properly deleted
        assert 'child' not in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

    def test_many_to_many_relationship(self):

        # initial "left" table
        class Parent(self.app.db.Model):
            __tablename__ = 'left'
            id = self.app.db.Column(self.app.db.Integer,
                primary_key=True)

        self.dbmigrate = DBMigrate(self.app)
        self.dbmigrate.init()
        self.dbmigrate._upgrade()

        # check that table "left" has been properly created
        assert 'left' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        self.app.db = SQLAlchemy(self.app)

        # add m2m rel to "child" table through "association"
        association_table = self.app.db.Table('association',
            self.app.db.Model.metadata,
            self.app.db.Column('left_id', self.app.db.Integer,
                self.app.db.ForeignKey('left.id')),
            self.app.db.Column('right_id', self.app.db.Integer,
                self.app.db.ForeignKey('right.id'))
        )

        class Parent(self.app.db.Model):
            __tablename__ = 'left'
            id = self.app.db.Column(self.app.db.Integer, primary_key=True)
            children = self.app.db.relationship("Child",
                secondary=association_table)

        class Child(self.app.db.Model):
            __tablename__ = 'right'
            id = self.app.db.Column(self.app.db.Integer, primary_key=True)

        self.dbmigrate.db = self.app.db
        self.dbmigrate.schemamigrate(migration_name='added_child_table')
        self.dbmigrate._upgrade()

        # check that table "association" has been properly created
        assert 'association' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()

        # check that table "right" has been properly created
        assert 'right' in Inspector(self.dbmigrate.db.engine
            ).get_table_names()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DBMigrateInitTestCase))
    suite.addTest(unittest.makeSuite(DBMigrateSubManagerTestCase))
    suite.addTest(unittest.makeSuite(DBMigrateCommandsTestCase))
    suite.addTest(unittest.makeSuite(DBMigrateRelationshipsTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
