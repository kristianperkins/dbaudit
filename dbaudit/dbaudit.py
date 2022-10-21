#!/usr/bin/env python
from __future__ import print_function
from argparse import ArgumentParser

import sqlalchemy as sa
from jinja2 import Template

from . import engine

# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

parser = ArgumentParser(description="add auditing to db schema")
parser.add_argument("-p", "--prefix",
    help="Prefix for created triggers, default is audit_",
    dest="prefix")
parser.add_argument("-i", "--ignore-file",
    help="File containing table name prefixes to ignore",
    dest="ignore_file")
parser.add_argument("-r", "--rollback",
    help="Remove all triggers with name audit_trig_%% in the given environment",
    dest="rollback", default=False, action="store_true")
parser.add_argument("configname")

dry_run = False

audit_config = """
create table audit_config (
  context_param_name varchar(255) not null,
  context_param_value varchar(255) not null,
  description varchar(255) null
)
"""

audit_log = """
create table audit_log (
  id bigint identity primary key not null,
  statement_id int not null,
  table_name varchar(255) not null,
  operation varchar(255) not null,
  primary_key_name varchar(255) not null,
  primary_key_value varchar(255) not null,
  column_name varchar(255) null,
  old_column_value varchar(255) null,
  new_column_value varchar(255) null,
  session_usr varchar(255) null,
  server_host varchar(255) null,
  host varchar(255) null,
  ip_address varchar(255) null,
  created_date datetime2 not null
)
"""

audit_log_seq = "create sequence audit_log_seq start with 1 increment by 1 minvalue 1"

audit_log_statement_seq = "create sequence audit_log_statement_seq start with 1 increment by 1 minvalue 1"

audit_log_trigger = """
create or replace trigger audit_log_created_date_trig
    before insert on audit_log
    referencing new as new old as old
    for each row
    begin
        :new.created_date := systimestamp;
        select audit_log_seq.nextval into :new.id from dual;
    end;
"""

audit_ddl = [audit_config, audit_log, audit_log_statement_seq]

audit_trigger_template = Template("""
create or alter trigger audit_trig_{{ table_name }}
    on {{ table_name }}
    after insert, update, delete
as
declare @next_statement_id bigint;
declare @pk_value varchar(255)
declare @operation_type varchar(7) =
    case when exists(select * from inserted) and exists(select * from deleted)
        then 'UPDATE'
    when exists(select * from inserted)
        then 'INSERT'
    else
        'DELETE'
    end;
declare changes_cursor cursor for
select {{ pk_name }} from inserted
union
select {{ pk_name }} from deleted;
set @next_statement_id = next value for audit_log_statement_seq;
open changes_cursor;
fetch next from changes_cursor into @pk_value;
while @@fetch_status = 0
begin
    fetch next from changes_cursor into @pk_value;
    insert into audit_log (statement_id, table_name, operation, primary_key_name, primary_key_value, column_name, new_column_value, session_usr, server_host, host, ip_address, created_date)
                values (@next_statement_id, '{{ table_name }}', @operation_type, '{{ pk_name }}', @pk_value, 'column_name', cast('newval' as varchar(255)), session_user, 'SERVER_HOST', 'HOST', 'IP_ADDRESS', getdate());
    fetch next from changes_cursor into @pk_value;
end
close changes_cursor;
deallocate changes_cursor;""")

trigger_name_prefix = "audit_"

def gen_audit_triggers(eng, ignore_file):
    ignore_table_prefixes = ['audit_']
    if ignore_file:
        ignore_table_prefixes += open(ignore_file).read().splitlines()
    m = sa.MetaData()
    m.reflect(eng)
    print("-- finished reflecting")
    ignore_sql_types = [sa.types.BLOB, sa.types.CLOB]
    tables = ([t for t in m.sorted_tables if not any(t.name.startswith(pfx) for pfx in ignore_table_prefixes)])
    # print(tables, len(tables))
    counter = 0
    with eng.connect() as con:
        if not any([t.name.lower() == 'audit_log' for t in m.sorted_tables]):
            print('creating audit_log and audit_config tables')
            if not dry_run:
                [con.execute(ddl) for ddl in audit_ddl]
        else:
            print('-- skipping audit tables ddl, already found')
        for table in tables:
            if table.schema:
                print('-- ignoring table %s from schema %s' % (table.name, table.schema))
                continue
            counter += 1
            keys = list(table.primary_key.columns)
            if keys:
                key = keys[0]
                pk_name = key.name
                cols = [col for col in table.columns if col.name != pk_name and type(col.type) not in ignore_sql_types]
                if not cols:
                    cols = [key]
                trig_sql = audit_trigger_template.render(table_name=table.name, columns=table.columns, pk_name=pk_name)
                # print(trig_sql)
                print("creating trigger for table %s" % table.name)
                if not dry_run:
                    con.execute(trig_sql)
            else:
                print('-- skipping table with no primary keys: %s' % table.name)


def remove_audit_triggers(eng):
    with eng.connect() as con:
        triggers = con.execute("select name from sys.triggers where name like 'AUDIT_TRIG_%' order by name")
        trig_list = list(triggers)
        for t in trig_list:
            print("dropping trigger %s" % t[0])
            con.execute('drop trigger %s' % t[0])


def main():
    args = parser.parse_args()
    eng = engine.from_config(args.configname)
    if args.rollback:
        remove_audit_triggers(eng)
    else:
        gen_audit_triggers(eng, args.ignore_file)

if __name__ == '__main__':
    main()
