"""
Flask-DBMigrate
---------------

Simple wrapper for SQLAlchemy-Migrate tool,
that provide schema change management for Flask project.
"""
from setuptools import setup


setup(
    name='Flask-DBMigrate',
    version='0.1',
    url='http://github.com/akostyuk/flask-dbmigrate/',
    license='Apache License 2.0',
    author='Alexey Kostyuk',
    author_email='unitoff@gmail.com',
    description='Database schema change management for Flask\SQLAlchemy',
    long_description=__doc__,
    py_modules=['flask_dbmigrate'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'sqlalchemy <= 0.7.9'
        'sqlalchemy-migrate',
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Script',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License, Version 2.0',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
