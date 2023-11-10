import psycopg

from anomaly.base import ConcurrentTransactionExample
from anomaly import registry


class T1(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            query = "update account set balance = balance + 10 where id = 1;"
            await cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")

            await self.yield_for_another_task()


class T2(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            try:
                query = "update account set balance = balance - 33 where id = 1;"
                await cursor.execute(query)
                self.print_text(query, f"MODIFIED: {cursor.rowcount}")
            except psycopg.errors.SerializationFailure as exc:
                self.print_text(query, f"ERROR: {exc}")
                await cursor.execute("rollback;")
                self.print_text("ROLLBACK")
                return

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")

registry.register("serialization-anomaly-update", T1, T2, description="""
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ raises an error for `repeatable read` and `serializable`
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │
""")
