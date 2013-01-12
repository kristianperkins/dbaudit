db-audit
========

Generate audit triggers on Oracle database which logs changes to the `audit_log` table.

Install Dependencies
--------------------

1. install oracle instant client (cx_Oracle)
2. install requirements:

        pip install -r requirements.txt

Configuration
-------------

db-audit uses the [ipydb](https://github.com/jaysw/ipydb) database configuration.  See the ipydb
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

    ./db-audit.py test1

This includes triggers names `audit_trig_...` as well as `audit_log`, `audit_config` tables and the
`audit_log_seq` sequence.

and to remove the triggers:

    ./db-audit.py -r test1

Acknowledgements
----------------

 * Inspired by a similar utility written by Paul Hipsley
 * Developed entirely in [ipython](http://ipython.org) using [ipydb](https://github.com/jaysw/ipydb)
