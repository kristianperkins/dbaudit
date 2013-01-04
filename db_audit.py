#!/usr/bin/python   
from argparse import ArgumentParser
import sqlalchemy as sa
from ipydb import engine

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


audit_config = """
create table audit_config (
  context_param_name varchar(255) not null,
  context_param_value varchar(255) not null,
  description varchar(255) null
)
"""

audit_log = """
create table audit_log (
  id number(19) not null,
  statement_id number(19) not null,
  table_name varchar(255) not null,
  operation varchar(255) not null,
  primary_key_name varchar(255) not null,
  primary_key_value varchar(255) not null,
  column_name varchar(255) null,
  old_column_value varchar(255) null,
  new_column_value varchar(255) null,
  session_user varchar(255) null,
  server_host varchar(255) null,
  host varchar(255) null,
  ip_address varchar(255) null,
  created_dts timestamp(3) not null
)
"""

audit_log_seq = "create sequence audit_log_seq start with 1 increment by 1 minvalue 1"

audit_log_statement_seq = "create sequence audit_log_statement_seq start with 1 increment by 1 minvalue 1"

audit_log_trigger = """
create or replace trigger audit_log_cdts_i_trg
    before insert on audit_log
    referencing new as new old as old
    for each row
    begin
        :new.created_dts := systimestamp;
        select audit_log_seq.nextval into :new.id from dual;
    end;
"""

audit_ddl = [audit_config, audit_log, audit_log_seq, audit_log_statement_seq, audit_log_trigger]

audit_prefix_sql = """
create or replace trigger audit_trig_%s_%03d
    after insert or update or delete on %s
    for each row
    declare
        c numeric(19);
        statement numeric(19);
    begin
        select count(*) into c from audit_config ac where sys_context('USERENV', ac.context_param_name) like ac.context_param_value;
        if c > 0 then
          select audit_log_statement_seq.nextval into statement from dual;
          if inserting then"""
audit_insert_sql = """
            insert into audit_log (statement_id, table_name, operation, primary_key_name, primary_key_value, column_name, new_column_value, session_user, server_host, host, ip_address)
            values (statement, '%s', 'INSERT', '%s', :new.%s, '%s', cast(:new.%s as varchar2(255)), sys_context('USERENV', 'SESSION_USER'), sys_context('USERENV', 'SERVER_HOST'), sys_context('USERENV', 'HOST'), sys_context('USERENV', 'IP_ADDRESS'));"""
audit_if_updating = """
          elsif updating then"""
audit_update_sql = """
            if updating('%s') then
              insert into audit_log (statement_id, table_name, operation, primary_key_name, primary_key_value, column_name, old_column_value, new_column_value, session_user, server_host, host, ip_address)
              values (statement, '%s', 'UPDATE', '%s', :new.%s, '%s', cast(:old.%s as varchar2(255)), cast(:new.%s as varchar2(255)), sys_context('USERENV', 'SESSION_USER'), sys_context('USERENV', 'SERVER_HOST'), sys_context('USERENV', 'HOST'), sys_context('USERENV', 'IP_ADDRESS'));
            end if;"""
audit_delete_sql = """
          elsif deleting then
              insert into audit_log (statement_id, table_name, operation, primary_key_name, primary_key_value, session_user, server_host, host, ip_address)
              values (statement, '%s', 'DELETE', '%s', :old.%s, sys_context('USERENV', 'SESSION_USER'), sys_context('USERENV', 'SERVER_HOST'), sys_context('USERENV', 'HOST'), sys_context('USERENV', 'IP_ADDRESS'));
          end if;
        end if;
    end;
"""

trigger_name_prefix = "audit_"

def gen_audit_triggers(eng, **kwargs):
    print kwargs
    ignore_table_prefixes = ['audit_']
    if 'ignore_file' in kwargs:
        ignore_table_prefixes += open(kwargs['ignore_file']).read().splitlines()
    m = sa.MetaData()
    m.reflect(eng)
    print "-- finished reflecting"
    ignore_sql_types = [sa.types.BLOB, sa.types.CLOB]
    tables = ([t for t in m.sorted_tables if not any(t.name.startswith(pfx) for pfx in ignore_table_prefixes)])
    counter = 0
    with eng.connect() as con:
        audit_table_count = con.execute("select count(*) from all_tables where table_name = 'AUDIT_LOG'").fetchone()
        if audit_table_count[0] == 0:
            print 'creating audit_log and audit_config tables'
            [con.execute(ddl) for ddl in audit_ddl]
        for table in tables:
            if table.schema:
                print '-- ignoring table %s from schema %s' % (table.name, table.schema)
                continue
            counter += 1
            keys = list(table.primary_key.columns)
            if keys:
                key = keys[0]
                pk_name = key.name
                cols = [col for col in table.columns if col.name != pk_name and type(col.type) not in ignore_sql_types]
                if not cols:
                    cols = [key]
                prefix_chunk = audit_prefix_sql % (table.name[:15], counter, table.name)
                insert_chunk = ''.join(audit_insert_sql % (table.name, pk_name, pk_name, col.name, col.name) for col in cols)
                update_chunk = ''.join(audit_update_sql % (col.name, table.name, pk_name, pk_name, col.name, col.name, col.name) for col in cols)
                delete_chunk = audit_delete_sql % (table.name, pk_name, pk_name)
                trig_sql = ''.join([prefix_chunk, insert_chunk, audit_if_updating, update_chunk, delete_chunk])
                # print trig_sql
                print("creating trigger for table %s" % table.name)
                con.execute(trig_sql)
            else:
                print '-- skipping table with no primary keys: %s' % table.name

def remove_audit_triggers(eng):
    with eng.connect() as con:
        triggers = con.execute("select trigger_name from all_triggers where trigger_name like 'AUDIT_TRIG_%'")
        for t in list(triggers):
            print("dropping trigger %s" % t[0])
            con.execute('drop trigger %s' % t[0])

if __name__ == '__main__':
    args = parser.parse_args()
    eng = engine.from_config(args.configname)
    if args.rollback:
        remove_audit_triggers(eng)
    else:
        gen_audit_triggers(eng, **dict(vars(args)))

