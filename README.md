dbaudit
========

Generate audit triggers on Oracle database which logs changes to the `audit_log` table.

Installation
------------

1. install oracle instant client and python driver (cx_Oracle)

    pip install cx_Oracle

2. install dbaudit using pip:

    pip install git+https://github.com/krockode/dbaudit

Configuration
-------------

dbaudit uses the [ipydb](https://github.com/jaysw/ipydb) database configuration.  See the ipydb
 [`~/.db-connections` file setup documentation](https://github.com/jaysw/ipydb#2-using-connect-and-a-db-connections-configuration-file)

###audit_config table###

Audit records will appear based on the configuration in the `audit_config` table.  The output of
[sys_context](http://docs.oracle.com/cd/B19306_01/server.102/b14200/functions165.htm) will have to
match a row in the `audit_config` table, for example the following will audit all data modified by
connections from 127.0.0.1:

    +--------------------+---------------------+---------------------------------------+
    | context_param_name | context_param_value | description                           |
    +--------------------+---------------------+---------------------------------------+
    | IP_ADDRESS         | 127.0.0.1           | Enable audit logging for ip 127.0.0.1 |

Usage
-----

To create audit DDL for the database test1 run:

    dbaudit test1

This includes triggers names `audit_trig_...` as well as `audit_log`, `audit_config` tables and the
`audit_log_seq` sequence.

and to remove the triggers:

    dbaudit -r test1

TODO
----

1. Add support for sql dialects other than pl-sql
    * MySQL
    * postgresql
    * tsql
    * others...
2. View/update `audit_config` from CLI
3. view recent `audit_log` summary/stats from CLI
4. More CLI options e.g. Specify trigger name prefix

Acknowledgements
----------------

 * Inspired by a similar utility written by Paul Hipsley
 * Developed entirely in [ipython](http://ipython.org) using [ipydb](https://github.com/jaysw/ipydb)
