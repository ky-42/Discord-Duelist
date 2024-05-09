import datetime
import os
from pathlib import Path
from typing import Annotated, Optional, Tuple

import psycopg
import typer
from dotenv import load_dotenv
from rich import print

load_dotenv()

app = typer.Typer()


# -- Setup --


def create_migration_folder(migrations_folder: Path):
    """Creates the migration folder if it doesn't exist"""

    if not migrations_folder.exists():
        os.mkdir(migrations_folder)


def create_migration_table(conn: psycopg.Connection):
    """Creates a migration table in the db if it doesn't exist"""

    table = """
    CREATE TABLE IF NOT EXISTS migration (
        id SERIAL PRIMARY KEY,
        file_name VARCHAR(255) UNIQUE NOT NULL,
        run_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """

    with conn.cursor() as cur:
        cur.execute(table)
        conn.commit()


@app.command()
def setup(
    postgres_uri: Annotated[str, typer.Argument(envvar="POSTGRES_URI")],
    migrations_folder: Annotated[Path, typer.Argument(envvar="MIGRATIONS_DIR")],
):
    """Sets up the migration system.

    Creates or finds the migrations folder and creates the migration table in the db.
    """

    try:
        conn = psycopg.connect(postgres_uri)
    except psycopg.errors.OperationalError:
        print(
            f"\n[bold red]Could not connect to the database![/]\nMake sure the database is running and the POSTGRES_URI env variable is correct.\n"
        )
        exit()

    create_migration_folder(migrations_folder)
    create_migration_table(conn)


# -- New migrations --


@app.command()
def new_migration(
    migration_name: str,
    migrations_folder: Annotated[Path, typer.Argument(envvar="MIGRATIONS_DIR")],
):
    """Creates a new migration file in the migrations folder.

    Should be used to create all migration files.

    Args:
        name (str): name of the migration
    """

    if not migrations_folder.exists():
        print(
            f"\n[bold red]Migration folder not found![/]\nRun the [b]{setup.__name__}[/] command to setup migration folder.\n"
        )
        exit()

    file_name = (
        datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") + f"_{migration_name}.sql"
    )

    # Create an up script
    with open(os.path.join(migrations_folder, file_name), "w") as f:
        f.write("-- Write your migration script here")


# -- Run migrations --


def get_last_migration(
    conn: psycopg.Connection,
) -> Optional[Tuple[int, str, datetime.datetime]]:
    """Gets the last migration that was applied"""

    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT * FROM migration ORDER BY file_name DESC, run_on DESC, id DESC LIMIT 1"
            )
        except psycopg.errors.UndefinedTable:
            print(
                f"\n[bold red]Migration table not found![/]\nRun the [b]{setup.__name__}[/] command to setup migration table.\n"
            )
            exit()

        return cur.fetchone()


def get_migration_files(migrations_folder: Path) -> list[str]:
    """Returns sorted list of all migration files in the migrations folder"""

    if not migrations_folder.exists():
        print(
            f"\n[bold red]Migration folder not found![/]\nRun the [b]{setup.__name__}[/] command to setup migration folder.\n"
        )
        exit()

    # Creates lsit of all files in the migrations folder ending with .sql
    all_migrations = [
        file_path.name
        for file_path in migrations_folder.glob("*.sql")
        if file_path.is_file()
    ]
    all_migrations.sort()

    return all_migrations


@app.command()
def run_migrations(
    count: Annotated[int, typer.Argument()] = -1,
    migrations_folder: Annotated[Path, typer.Argument(envvar="MIGRATIONS_DIR")] = Path(
        "/not_set"
    ),
    postgres_uri: Annotated[str, typer.Argument(envvar="POSTGRES_URI")] = "",
):
    """Runs all unapplied migrations.

    If an error occurs during a migration, none of the migrations will be applied.

    Args:
        count (int): Number of migrations to run.
            Default is -1 which runs all migrations.
    """

    try:
        conn = psycopg.connect(postgres_uri)
    except psycopg.errors.OperationalError:
        print(
            f"\n[bold red]Could not connect to the database![/]\nMake sure the database is running and the POSTGRES_URI env variable is correct.\n"
        )
        exit()

    all_migration_files = get_migration_files(migrations_folder)
    most_recent_migration = get_last_migration(conn)

    # Gets the index of the most recent migration ran
    most_recent_migration_index = (
        -1
        if most_recent_migration is None
        else all_migration_files.index(most_recent_migration[1])
    )

    # Gets the index to run migrations up to
    run_till = (
        min(most_recent_migration_index + count + 1, len(all_migration_files))
        if count > -1
        else len(all_migration_files)
    )

    with conn.cursor() as cur:
        for migration in all_migration_files[
            most_recent_migration_index + 1 : run_till
        ]:
            # Run migrations up script and record it in the migration table.
            with open(
                os.path.join(migrations_folder, migration), "r"
            ) as migration_file:
                cur.execute(migration_file.read().encode("utf-8"))
                cur.execute(
                    "INSERT INTO migration (file_name) VALUES (%s)", (migration,)
                )

        conn.commit()


if __name__ == "__main__":
    app()
