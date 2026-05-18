from database.session import engine, Base
import database.models

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    from database.seed import seed

    Base.metadata.drop_all(bind=engine)
    print("Base de datos reseteada")

    init_db()
    print("Base de datos creada")
    seed()