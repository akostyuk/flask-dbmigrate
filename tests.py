import os
import sys
import unittest

from flask import Flask
from flask.ext.script import Command, Manager

from .flask_dbmigrate import DBMigrate


def make_test_model(db):
    class Test(db.Model):
        __tablename__ = 'test'
        id = db.Column('test_id', db.Integer, primary_key=True)
        value1 = db.Column(db.String(60))

        def __init__(self, value1):
            self.value1 = value1
    return Test


class TestConfig(object):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_MIGRATE_REPO = os.path.dirname(__file__)


class TestCommand(Command):
    def run(self):
        print('test ok')


class TestDBMigrateSubManager(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestConfig)
        self.dbmigrate = DBMigrate(self.app)

    def tearDown(self):
        self.db.drop_all()

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
        dbmigrate_manager = Manager()
        dbmigrate_manager.add_command('test', TestCommand())

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmigrate_manager)

        sys.argv = ["manage.py", "dbmigrate", "test"]

        try:
            manager.run()
        except SystemExit, e:
            self.assertEquals(e.code, 0)

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("need to run in buffered mode")
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'test ok')

    def test_run_dbmigrate_submanager_dbcreate_command(self):
        pass

if __name__ == '__main__':
    assert not hasattr(sys.stdout, 'getvalue')
    unittest.main(module=__name__, buffer=True, exit=False)
