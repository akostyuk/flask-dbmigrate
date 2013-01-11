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

    def schemamigrate(self):
        old_model = schema.MetaData(bind=self.db.engine, reflect=True)
        if 'migrate_version' in old_model.tables:
            old_model.remove(old_model.tables['migrate_version'])
        if not self._is_changed(old_model, self.db.metadata):
            print('No Changes!')


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
def schemamigration():
    'Create migration'
    dbmigrate = DBMigrate(current_app)
    dbmigrate.schemamigrate()
