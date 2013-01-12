import os
import re
import sys
import unittest
from shutil import rmtree
from StringIO import StringIO

from flask import Flask
from flask.ext.script import Command, Manager
from flask.ext.sqlalchemy import SQLAlchemy

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
        test_method(self)
        self.dbmigrate._drop()
    return wrapper


def with_database_changes(test_method):
    def wrapper(self):
        self.dbmigrate.init()

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

    def test_run_dbmigrate_init(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'init']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        self.assertTrue(os.path.exists(
            self.app.config['SQLALCHEMY_MIGRATE_REPO']))

        # test if table test exist
        self.assertEquals(self.app.db.metadata.tables['test'].name,
            'test')

        # test insert
        test = self.Test('Test')
        self.app.db.session.add(test)
        self.app.db.session.commit()
        self.assertEqual(len(self.Test.query.all()), 1)

        # drop
        self.dbmigrate._drop()

    @with_database
    def test_run_dbmigrate_schemamigrate_no_changes(self):

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
    def test_run_dbmigrate_schemamigrate_with_changes(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        migration = os.path.join(self.app.config['SQLALCHEMY_MIGRATE_REPO'],
            'versions/001_auto_generated.py')

        self.assertTrue(os.path.exists(migration))

    @with_database_changes
    def test_run_dbmigrate_schemamigrate_with_changes_named(self):

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration', '-n',
        'migration_name']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        migration = os.path.join(self.app.config['SQLALCHEMY_MIGRATE_REPO'],
            'versions/001_migration_name.py')

        self.assertTrue(os.path.exists(migration))

    @with_database_changes
    def test_run_dbmigrate_schemamigrate_with_changes_stdout(self):
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

    def test_run_dbmigrate_migrate_show(self):
        pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DBMigrateInitTestCase))
    suite.addTest(unittest.makeSuite(DBMigrateSubManagerTestCase))
    suite.addTest(unittest.makeSuite(DBMigrateCommandsTestCase))
    return suite

if __name__ == '__main__':
    assert not hasattr(sys.stdout, 'getvalue')
    unittest.main(defaultTest='suite')
