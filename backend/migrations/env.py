from alembic import context

from app import models
from app.database import engine

cible = models.Base.metadata


def lancer():
    # Connexion fournie par app/migrations.py au démarrage, sinon celle de DATABASE_URL (ligne de commande)
    connexion = context.config.attributes.get("connexion")
    if connexion is not None:
        context.configure(connection=connexion, target_metadata=cible, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    with engine.connect() as connexion:
        context.configure(connection=connexion, target_metadata=cible, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


lancer()
