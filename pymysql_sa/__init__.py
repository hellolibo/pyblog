from pymysql_sa import base

def make_default_mysql_dialect():
    from sqlalchemy.dialects.mysql import base as mysql_base
    mysql_base.dialect = base.dialect

