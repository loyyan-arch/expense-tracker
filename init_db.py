from sqlalchemy import inspect

from db import Base, engine
from models import Transaction, User


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("数据库中的表：", inspect(engine).get_table_names())