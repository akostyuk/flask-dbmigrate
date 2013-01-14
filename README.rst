Flask-DBMigrate
===============

This is a simple wrapper for SQLAlchemy Migrate
tool http://code.google.com/p/sqlalchemy-migrate, that provide
schema change management for Flask and SQLAlchemy


Requirements
------------
- sqlalchemy <== 0.7.9
- sqlalchemy-migrate
- Flask-SQLAlchemy
- Flask-Script


Usage
-----

Flask-DBMigrate uses Flask-Script extension to run database schema
management commands.

Assume, you have an application somewhere in your project.
Also, you need to define required SQLAlchemy settings in your application:

.. code-block:: pycon

    from flask import Flask
    from flask.sqlalchemy import SQLAlchemy
    
    # test settings
    class MyAppSettings:
        DEBUG = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///test.sqlite3'
        SQLALCHEMY_MIGRATE_REPO = 'migrations'
    
    
    app = Flask(__name__)
    app.config.from_object(MyAppSettings)
    
    
    # Our test model
    class Test(app.db.Model):
        __tablename__ = 'test'
        id = app.db.Column('test_id', app.db.Integer, primary_key=True)
        column1 = app.db.Column(app.db.String(60))
        def __init__(self, column1):
            self.column1 = column1
    
    db = SQLAlchemy(app)
    
    # We need to place sqlalchemy object inside our app
    app.db =db

Next we can create our sub-manager for database schema management
commands, usually in the `manage.py` file:

.. code-block:: pycon

    from flask.ext.script import Manager
    from flask.ext.dbmigrate import manager as dbmanager
    
    from myapp import app
    
    manager = Manager(app)
    manager.add_command('dbmigrate', dbmanager)

Now we can use all the Flask-DBMigrate commands:

```shell
python manage.py dbmigrate init
python manage.py dbmigrate schemamigrate
python manage.py dbmigrate migrate --show
```
