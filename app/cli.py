import argparse
import getpass
import sys

from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal, init_db
from app.models import User
from app.security import hash_password


def create_admin(username: str, password: str) -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            existing.hashed_password = hash_password(password)
            db.commit()
            print(f"Contrasena actualizada para el usuario '{username}'.")
            return
        user = User(username=username, hashed_password=hash_password(password), is_admin=True)
        db.add(user)
        db.commit()
        print(f"Usuario administrador '{username}' creado correctamente.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Herramientas de administracion de WarCrafted-ControlP")
    subparsers = parser.add_subparsers(dest="action", required=True)

    create_parser = subparsers.add_parser("create-admin", help="Crea o actualiza el usuario administrador")
    create_parser.add_argument("--username", help="Nombre de usuario")
    create_parser.add_argument("--password", help="Contrasena (si se omite, se pedira de forma interactiva)")

    args = parser.parse_args()

    if args.action == "create-admin":
        username = args.username or input("Usuario administrador: ").strip()
        password = args.password or getpass.getpass("Contrasena: ")
        if not username or not password:
            print("Usuario y contrasena son obligatorios.", file=sys.stderr)
            sys.exit(1)
        create_admin(username, password)


if __name__ == "__main__":
    main()
