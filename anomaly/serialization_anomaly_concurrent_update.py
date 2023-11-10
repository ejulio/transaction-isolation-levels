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

            await self.yield_for_another_task()

            await cursor.execute("commit;")
            self.print_text("COMMIT")


class T2(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            try:
                # this will lock because T1 and T2 are updating the same record at the same time (before COMMIT)
                query = "update account set balance = balance - 33 where id = 1;"
                awaitable = cursor.execute(query)
                self.print_text(query, "waiting...")
                await self.yield_for_another_task(awaitable)
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

registry.register("serialization-anomaly-concurrent-update", T1, T2, description="""
This example is similar to `serialization-anomaly-update`, but here the updates are performed "at the same time", meaning that no transaction
has committed the value when the other one runs an `update` too.

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
   │                   ├──update balance───────►│ blocks because of the uncommitted `update` in T1
   │                   │                        │  then fails for `serializable` and `repetable read`
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
""")
