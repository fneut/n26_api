import psycopg2


def create_staging_table(cursor):
    cursor.execute("""
    CREATE TABLE TRANSACTIONS(
        AMOUNT CHAR(100),
        MERCHANT_CITY CHAR(100),
        MERCHANT_NAME CHAR(100),
        MERCHANT_NAME_PREPROCESSED,
        PARTNER_NAME CHAR(100),
        CATEGORY CHAR(100),
        CATEGORY_PREPROCESSED CHAR(100),
        EXPENSE_TYPE CHAR(100),
        REFERENCE_TEXT TEXT,
        REFERENCE_TEXT_PREPROCESSED TEXT,
        TRANSACTION_DESCRIPTION_MERGED TEXT,
        CATEGORY_MODEL CHAR(100),
    )
    """
    )
    pass