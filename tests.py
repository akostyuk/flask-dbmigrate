import os
import sys
import unittest
from shutil import rmtree

from flask import Flask
from flask.ext.script import Command, Manager
from flask.ext.sqlalchemy import SQLAlchemy

from flask_dbmigrate import DBMigrate
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


class TestConfig(object):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + rel('test.sqlite3')
    # SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_MIGRATE_REPO = rel('migrations')


class TestCommand(Command):
    def run(self):
        print('test ok')


class TestDBMigrateSubManager(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        self.app.db = SQLAlchemy(self.app)
        self.Test = make_test_model(self.app.db)
        self.dbmigrate = DBMigrate(self.app)

    def tearDown(self):
        self.dbmigrate.db.drop_all()
        if os.path.exists(self.app.config['SQLALCHEMY_MIGRATE_REPO']):
            rmtree(self.app.config['SQLALCHEMY_MIGRATE_REPO'])
        if os.path.exists(rel('test.sqlite3')):
            os.remove(rel('test.sqlite3'))

    def test_add_dbmigrate_submanager(self):
        # check settings first
        self.assertIn('SQLALCHEMY_MIGRATE_REPO', self.app.config)

        dbmigrate_manager = Manager()

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmigrate_manager)

        self.assertIsInstance(manager._commands['dbmigrate'], Manager)
        self.assertEquals(dbmigrate_manager.parent, manager)
        self.assertEquals(dbmigrate_manager.get_options(),
            manager.get_options())

    def test_run_dbmigrate_submanager_test_command(self):
        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'test']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        if not hasattr(sys.stdout, 'getvalue'):
            self.fail('need to run in buffered mode')
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'test ok')

    def test_run_dbmigrate_init(self):
        self.dbmigrate._drop()
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
        self.assertEqual(self.app.db.metadata.tables['test'].name,
            'test')

        # test insert
        test = self.Test('Test')
        self.app.db.session.add(test)
        self.app.db.session.commit()
        self.assertEqual(len(self.Test.query.all()), 1)

        # drop
        self.dbmigrate._drop()

    def test_run_dbmigrate_schemamigrate_no_changes(self):
        self.dbmigrate.init()

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmanager)

        sys.argv = ['manage.py', 'dbmigrate', 'schemamigration']

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'No Changes!')

if __name__ == '__main__':
    assert not hasattr(sys.stdout, 'getvalue')
    unittest.main(module=__name__, buffer=True, exit=False)
