import sys
import unittest

from flask import Flask
from flask.ext.script import Command, Manager


class TestCommand(Command):
    def run(self):
        print('test ok')


class TestDBMigrateSubManager(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(self)

    def test_add_dbmigrate_submanager(self):
        dbmigrate_manager = Manager()

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmigrate_manager)

        assert isinstance(manager._commands['dbmigrate'], Manager)
        assert dbmigrate_manager.parent == manager
        assert dbmigrate_manager.get_options() == manager.get_options()

    def test_run_dbmigrate_submanager_test_command(self):
        dbmigrate_manager = Manager()
        dbmigrate_manager.add_command('test', TestCommand())

        manager = Manager(self.app)
        manager.add_command('dbmigrate', dbmigrate_manager)

        sys.argv = ["manage.py", "dbmigrate", "test"]

        try:
            manager.run()
        except SystemExit, e:
            assert e.code == 0

        if not hasattr(sys.stdout, "getvalue"):
            self.fail("need to run in buffered mode")
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'test ok')

if __name__ == '__main__':
    assert not hasattr(sys.stdout, 'getvalue')
    unittest.main(module=__name__, buffer=True, exit=False)
