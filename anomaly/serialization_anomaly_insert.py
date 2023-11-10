import psycopg

from anomaly.base import ConcurrentTransactionExample
from anomaly import registry


class T1(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select sum(balance) from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            query = "insert into account (balance) values (89);"
            await cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            await self.yield_for_another_task()

            try:
                query = "select sum(balance) from account;"
                await cursor.execute(query)
                self.print_query_result(query, await cursor.fetchall())

                await cursor.execute("commit;")
                self.print_text("COMMIT")
            except psycopg.errors.SerializationFailure as exc:
                self.print_text(query, f"ERROR: {exc}")
                await cursor.execute("rollback;")
                self.print_text("ROLLBACK")

            await self.yield_for_another_task()


class T2(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select sum(balance) from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            query = "insert into account (balance) values (12);"
            await cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            query = "select sum(balance) from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()

registry.register("serialization-anomaly-insert", T1, T2, description="""
In this example, both T1 and T2 are inserting a new value and computing an aggregate on top of `account`. Since the end result is not guaranteed,
the DB raises an error for `serializable`. `read committed` results in the expected outcome considering all rows and
`repeatable read` ignores the value added in T2.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   ├────────insert into account────────────────►│
   │                   │                        │
   │                   ├──insert into account──►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   │                   ├────commit─────────────►│
   │                   │                        │
   ├────────select sum(balance)────────────────►│ T1 fails for `serializable` isolation level
   │                   │                        │ `repetable read` shows the result without T2 inserted value (phantom read)
   ├───────commit/rollback─────────────────────►│ `read commiitted` shows the result with T2 inserted value
   │                   │                        │
""")
