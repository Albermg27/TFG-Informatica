from database.session import engine, Base

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Base de datos reseteada")
    init_db()
    print("Base de datos creada")