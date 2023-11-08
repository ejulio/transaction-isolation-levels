import argparse
import asyncio

import psycopg
from psycopg.rows import dict_row

from base import format_table
import dirty_read
import non_repeatable_read
import non_repeatable_read_snapshot
import phantom_read
import phantom_read_insert
import serialization_anomaly
import serialization_anomaly_insert
import serialization_anomaly_update
import serialization_anomaly_concurrent_update
import serialization_anomaly_select_update


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--example",
        "-e",
        type=str,
        required=True,
        choices=[
            "dirty-read",
            "non-repeatable-read",
            "non-repeatable-read-snapshot",
            "phantom-read",
            "phantom-read-insert",
            "serialization-anomaly",
            "serialization-anomaly-insert",
            "serialization-anomaly-update",
            "serialization-anomaly-concurrent-update",
            "serialization-anomaly-select-update",
        ]
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
    async with (await connect() as c1, await connect() as c2):
        await create_tables(c1)
        t1_event = asyncio.Event()
        t1_event.set()
        t2_event = asyncio.Event()

        match args.isolation_level:
            case "read-uncommitted":
                isolation_level = psycopg.IsolationLevel.READ_UNCOMMITTED
            case "read-committed":
                isolation_level = psycopg.IsolationLevel.READ_COMMITTED
            case "repeatable-read":
                isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            case "serializable":
                isolation_level = psycopg.IsolationLevel.SERIALIZABLE

        match args.example:
            case "dirty-read":
                t1 = dirty_read.T1(c1, isolation_level, t1_event, t2_event)
                t2 = dirty_read.T2(c2, isolation_level, t2_event, t1_event)
            case "non-repeatable-read":
                t1 = non_repeatable_read.T1(c1, isolation_level, t1_event, t2_event)
                t2 = non_repeatable_read.T2(c2, isolation_level, t2_event, t1_event)
            case "non-repeatable-read-snapshot":
                t1 = non_repeatable_read_snapshot.T1(c1, isolation_level, t1_event, t2_event)
                t2 = non_repeatable_read_snapshot.T2(c2, isolation_level, t2_event, t1_event)
            case "phantom-read":
                t1 = phantom_read.T1(c1, isolation_level, t1_event, t2_event)
                t2 = phantom_read.T2(c2, isolation_level, t2_event, t1_event)
            case "phantom-read-insert":
                t1 = phantom_read_insert.T1(c1, isolation_level, t1_event, t2_event)
                t2 = phantom_read_insert.T2(c2, isolation_level, t2_event, t1_event)
            case "serialization-anomaly":
                t1 = serialization_anomaly.T1(c1, isolation_level, t1_event, t2_event)
                t2 = serialization_anomaly.T2(c2, isolation_level, t2_event, t1_event)
            case "serialization-anomaly-insert":
                t1 = serialization_anomaly_insert.T1(c1, isolation_level, t1_event, t2_event)
                t2 = serialization_anomaly_insert.T2(c2, isolation_level, t2_event, t1_event)
            case "serialization-anomaly-update":
                t1 = serialization_anomaly_update.T1(c1, isolation_level, t1_event, t2_event)
                t2 = serialization_anomaly_update.T2(c2, isolation_level, t2_event, t1_event)
            case "serialization-anomaly-concurrent-update":
                t1 = serialization_anomaly_concurrent_update.T1(c1, isolation_level, t1_event, t2_event)
                t2 = serialization_anomaly_concurrent_update.T2(c2, isolation_level, t2_event, t1_event)
            case "serialization-anomaly-select-update":
                t1 = serialization_anomaly_select_update.T1(c1, isolation_level, t1_event, t2_event)
                t2 = serialization_anomaly_select_update.T2(c2, isolation_level, t2_event, t1_event)

        await print_account(c1, "BEFORE")
        async with asyncio.TaskGroup() as tg:
            tg.create_task(t1())
            tg.create_task(t2())
        await print_account(c1, "AFTER")


async def connect() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(
        "postgresql://postgres:a.test_password@localhost:5432/transaction_isolation_test",
        row_factory=dict_row,
        autocommit=True,
    )


async def create_tables(conn: psycopg.AsyncConnection):
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


async def print_account(conn: psycopg.Connection, tag: str):
    async with conn.cursor() as cur:
        print("DB STATE:", tag)
        await cur.execute("select * from account;")
        print(format_table(await cur.fetchall()))
        print()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
