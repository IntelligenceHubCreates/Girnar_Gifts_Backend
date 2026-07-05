from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.users import models as user_models
from app.products import models as product_models
from app.rating import models as rating_models
from app.favorite import models as favorite_models
from app.orders import models as orders_models
from app.cart import models as cart_models
from app.blog import models as blog_models
from app.coupons import models as coupons_models
from app.notifications import models as notifications_models
from app.returns import models as returns_models
from app.shipping import models as shipping_models
from app.store_settings import models as store_settings_models
# NewsletterSubscriber and PaymentOrder are defined inline in their routers
# modules (no separate models.py) - import those too so target_metadata sees them.
from app.newsletter import routers as newsletter_routers
from app.payments import routers as payments_routers
from app.models import Base
from app.settings import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Build the DB URL from app.settings (same postgres_* env vars the app itself
# uses via app/db.py), so migrations always target whatever database the app
# is configured for instead of the hardcoded value previously in alembic.ini.
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}",
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
