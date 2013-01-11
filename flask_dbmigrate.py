import re
import os
from shutil import rmtree

from flask import current_app
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager

from sqlalchemy import schema

from migrate.versioning import api, schemadiff


class ImproperlyConfigured(Exception):
    pass


class DBMigrate(object):

    def __init__(self, app):
        self.app = app
        self.sqlalchemy_database_uri = self._get_db_uri()
        self.sqlalchemy_migration_path = self._get_migration_path()
        self.db = self._get_db_engine()

    def _get_db_uri(self):
        if not 'SQLALCHEMY_DATABASE_URI' in self.app.config:
            raise ImproperlyConfigured('Can not find '
                'SQLALCHEMY_DATABASE_URI in application configuration')
        else:
            return self.app.config['SQLALCHEMY_DATABASE_URI']

    def _get_migration_path(self):
        if not 'SQLALCHEMY_MIGRATE_REPO' in self.app.config:
            raise ImproperlyConfigured('Can not find '
                'SQLALCHEMY_MIGRATE_REPO in application configuration')
        else:
            return self.app.config['SQLALCHEMY_MIGRATE_REPO']

    def _get_db_engine(self):
        try:
            db = self.app.db
            if not isinstance(db, SQLAlchemy):
                raise ImproperlyConfigured('Can not find '
                    'SQLAlchemy engine')
            else:
                return db
        except AttributeError:
            return SQLAlchemy(self.app)

    def _is_changed(self, oldmodel, newmodel):
        '''Check if the model has been changed'''

        diff = schemadiff.SchemaDiff(oldmodel, newmodel)

        if diff.tables_different:
            return True
        else:
            return False

    def _migration_exist(self):
        '''Check if migration script already exist'''
        db_version = api.db_version(self.sqlalchemy_database_uri,
            self.sqlalchemy_migration_path) + 1
        scripts_dir = os.path.join(self.sqlalchemy_migration_path, 'versions')
        files = [f for f in os.listdir(scripts_dir) \
            if os.path.isfile(os.path.join(scripts_dir, f))]
        f = re.compile('^[0-9]+_.+\.py$')
        scripts = sorted(filter(f.search, files))
        if len(scripts) == 0:
            return False
        else:
            latest_script = os.path.join(scripts_dir, scripts[-1])
            with open(latest_script, 'rb') as s:
                first_line = s.readline()
            r = re.compile('^# __VERSION__: (?P<version>\d+)\n')
            m = re.match(r, first_line)
            if m:
                version = m.group('version')
                if int(version) != db_version:
                    return False
                else:
                    return True
            else:
                return False

    def _create_migration_script(self, migration_name, oldmodel, newmodel,
                                    stdout=False):
        '''Generate migration script'''
        version = api.db_version(self.sqlalchemy_database_uri,
            self.sqlalchemy_migration_path) + 1
        migration = '{0}/versions/{1:03}_{2}.py'.format(
            self.sqlalchemy_migration_path, version, migration_name)
        script = api.make_update_script_for_model(self.sqlalchemy_database_uri,
            self.sqlalchemy_migration_path, oldmodel, newmodel)
        header = '# __VERSION__: {0}\n'.format(version)
        script = header + script
        if stdout:
            print(script)
        else:
            with open(migration, 'wt') as f:
                f.write(script)
            print('New migration saved as {0}'.format(migration))
            print('To apply migration, run: "manage.py dbmigrate upgrade"')

    def _drop(self):
        self.db.drop_all()
        if os.path.exists(self.sqlalchemy_migration_path):
            rmtree(self.sqlalchemy_migration_path)

    def init(self):
        self.db.create_all()
        if not os.path.exists(self.sqlalchemy_migration_path):
            api.create(self.sqlalchemy_migration_path, 'database repository')
            api.version_control(self.sqlalchemy_database_uri,
                self.sqlalchemy_migration_path)
        else:
            api.version_control(self.sqlalchemy_database_uri,
                self.sqlalchemy_migration_path,
                api.version(self.sqlalchemy_migration_path))

    def schemamigrate(self, migration_name=None, stdout=None):
        old_model = schema.MetaData(bind=self.db.engine, reflect=True)
        if 'migrate_version' in old_model.tables:
            old_model.remove(old_model.tables['migrate_version'])
        if not self._is_changed(old_model, self.db.metadata):
            print('No Changes!')
        else:
            # check if migration script exists
            if self._migration_exist():
                print('No Changes!')
            else:
                # create migration
                self._create_migration_script(migration_name, old_model,
                    self.db.metadata)


manager = Manager(usage='Perform database schema change management')


@manager.command
def test():
    'Test command. Do nothing, just print "test ok"'
    print('test ok')


@manager.command
def init():
    'Initialize migration repository and create database'
    dbmigrate = DBMigrate(current_app)
    dbmigrate.init()


@manager.command
def schemamigration(migration_name='auto_generated', stdout=False):
    'Create migration'
    dbmigrate = DBMigrate(current_app)
    dbmigrate.schemamigrate(migration_name, stdout)
