"""
Read ~/.db-connections file.

originally part of ipydb.
"""

import os
from configparser import ConfigParser
from urllib import parse

import sqlalchemy as sa

CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.db-connections')


def getconfigparser():
    cp = ConfigParser()
    cp.read(CONFIG_FILE)
    return cp


def getconfigs():
    """Return a dictionary of saved database connection configurations."""
    cp = getconfigparser()
    configs = {}
    default = None
    for section in cp.sections():
        conf = dict(cp.defaults())
        conf.update(dict(cp.items(section)))
        if conf.get('default'):
            default = section
        configs[section] = conf
    return default, configs


def from_config(configname=None):
    """Connect to a database based upon its `nickname`.

    See ipydb.magic.connect() for details.
    """
    default, configs = getconfigs()

    if not configname:
        raise ValueError('Configname is required')
    elif configname not in configs:
        raise ValueError(
            'Config name {0} not found.'.format(configname))
    else:
        config = configs[configname]
        connect_args = {}
        engine = from_url(make_connection_url(config),
                          connect_args=connect_args)
    return engine


def from_url(url, connect_args={}):
    """Connect to a database using an SqlAlchemy URL.

    Args:
        url: An SqlAlchemy-style DB connection URL.
        connect_args: extra argument to be passed to the underlying
                      DB-API driver.
    Returns:
        True if connection was successful.
    """
    url_string = url
    url = sa.engine.url.make_url(str(url_string))
    if url.drivername == 'oracle':
        # not sure why we need this horrible _cxmakedsn hack -
        # I think there's some weirdness
        # with cx_oracle/oracle versions I'm using.
        import cx_Oracle
        if not getattr(cx_Oracle, '_cxmakedsn', None):
            setattr(cx_Oracle, '_cxmakedsn', cx_Oracle.makedsn)

            def newmakedsn(*args, **kw):
                return cx_Oracle._cxmakedsn(*args, **kw).replace(
                    'SID', 'SERVICE_NAME')
            cx_Oracle.makedsn = newmakedsn
    elif url.drivername == 'mysql':
        import MySQLdb.cursors
        # use server-side cursors by default (does this work with myISAM?)
        connect_args = {'cursorclass': MySQLdb.cursors.SSCursor}
    engine = sa.engine.create_engine(url, connect_args=connect_args)
    return engine


def make_connection_url(config):
    """
    Returns an SqlAlchemy connection URL based upon values in config dict.

    Args:
        config: dict-like object with keys: type, username, password,
                host, and database.
    Returns:
        str URL which SqlAlchemy can use to connect to a database.
    """
    return sa.engine.url.URL(
        drivername=config.get('type'), username=config.get('username'),
        password=config.get('password'), host=config.get('host'),
        port=config.get('port') or None,
        database=config.get('database'),
        query=dict(parse.parse_qsl(config.get('query', ''))))

