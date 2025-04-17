import os
from vanna.remote import VannaDefault

def connect(vn: VannaDefault):
    database_type = os.getenv("DATABASE_TYPE")

    if database_type == "snowflake":
        # Connect to Snowflake using environment variables
        vn.connect_to_snowflake(
            account=os.environ['SNOWFLAKE_ACCOUNT'],
            username=os.environ['SNOWFLAKE_USERNAME'],
            password=os.environ['SNOWFLAKE_PASSWORD'],
            database=os.environ['SNOWFLAKE_DATABASE'],
            warehouse=os.environ['SNOWFLAKE_WAREHOUSE'],
        )
    elif database_type == "sqlite":
        # Connect to SQLite using the database URL
        vn.connect_to_sqlite(os.getenv("DATABASE_URL"))
    else:
        raise ValueError(f"Unsupported database type: [{database_type}]")

    print(f"Connected to [{database_type}] database ...")
