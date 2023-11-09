import argparse
import asyncio
import sys
from os import environ

import psycopg
from psycopg.rows import dict_row

from anomaly.base import format_table
from anomaly import registry


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--anomaly",
        "-a",
        type=str,
        required=True,
        choices=registry.get_registered()
    )

    ap.add_argument(
        "--isolation-level",
        "-l",
        type=str,
        required=True,
        choices=[
            "read-uncommitted",
            "read-committed",
            "repeatable-read",
            "serializable"
        ]
    )

    return ap.parse_args()


async def main(args: argparse.Namespace):
    async with (await _connect() as c1, await _connect() as c2):
        await _create_tables(c1)

        isolation_level = _get_isolation_level(args.isolation_level)
        (T1, T2, description) = registry.resolve(args.anomaly)
        t1_event = asyncio.Event()
        t1_event.set()
        t2_event = asyncio.Event()
        t1 = T1(c1, isolation_level, t1_event, t2_event)
        t2 = T2(c2, isolation_level, t2_event, t1_event)

        if description:
            print(args.anomaly, ":", args.isolation_level)
            print(description)
            print()

        await _print_account(c1, "BEFORE")
        async with asyncio.TaskGroup() as tg:
            tg.create_task(t1())
            tg.create_task(t2())
        await _print_account(c1, "AFTER")


async def _connect() -> psycopg.AsyncConnection:
    connection_string = environ.get("PG_CONNECTION_STRING")
    if not connection_string:
        raise RuntimeError("Missing PG_CONNECTION_STRING env")

    return await psycopg.AsyncConnection.connect(
        connection_string,
        row_factory=dict_row,
        autocommit=True,
    )


async def _create_tables(conn: psycopg.AsyncConnection):
    async with conn.cursor() as c:
        await c.execute("drop table if exists account;")
        await c.execute("""
            create table account (
                id serial primary key,
                balance int not null
            );
        """)

        await c.execute("""
            insert into account (balance) values (67);
            insert into account (balance) values (31);
        """)


def _get_isolation_level(isolation_level: str) -> psycopg.IsolationLevel:
    match isolation_level:
        case "read-uncommitted":
            return psycopg.IsolationLevel.READ_UNCOMMITTED
        case "read-committed":
            return psycopg.IsolationLevel.READ_COMMITTED
        case "repeatable-read":
            return psycopg.IsolationLevel.REPEATABLE_READ
        case "serializable":
            return psycopg.IsolationLevel.SERIALIZABLE
        case _:
            raise ValueError(f"Unknown isolation level {isolation_level}")


async def _print_account(conn: psycopg.Connection, tag: str):
    async with conn.cursor() as cur:
        print("DB STATE:", tag)
        await cur.execute("select * from account;")
        print(format_table(await cur.fetchall()))
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main(_parse_args()))
        sys.exit(0)
    except Exception as exc:
        print(exc)
        sys.exit(1)
