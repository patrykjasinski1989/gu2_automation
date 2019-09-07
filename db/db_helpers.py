"""This module contains repeatable database operations."""
import cx_Oracle


def connect(db_name, db_config):
    """Return db connection if successful and raise an exception with database name if not."""
    try:
        return cx_Oracle.connect('{}/{}@{}'.format(db_config['user'], db_config['password'], db_config['server']))
    except cx_Oracle.DatabaseError as db_exception:
        db_exception.db_name = db_name
        raise db_exception


def execute_dml(connection, statement, expected_rowcount=1):
    """Execute the update statement and commit the transaction if row count is ok, otherwise roll back."""
    cursor = connection.cursor()
    cursor.execute(statement)
    if cursor.rowcount == expected_rowcount:
        connection.commit()
    else:
        connection.rollback()
    cursor.close()
    return cursor.rowcount
