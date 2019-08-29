"""This module contains repeatable database operations."""


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
