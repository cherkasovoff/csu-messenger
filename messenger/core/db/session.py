from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

USER = getenv("POSTGRES_USER")
PASSWORD = getenv("POSTGRES_PASSWORD")
DB_PORT = getenv("DB_PORT")
DB_NAME = getenv("POSTGRES_DB")

#db_url = f"postgresql://{USER}:{PASSWORD}@postgres:{DB_PORT}/{DB_NAME}"
# db_url = "sqlite:///sqlite.db"
db_url = "mysql+pymysql://python-messenger:EyD8D/r2SldJuvY_@lanhost:3306/python-messenger"
engine = create_engine(db_url)
session = sessionmaker(engine)
