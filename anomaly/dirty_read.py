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

            query = "update account set balance = 10 where id = 1;"
            await cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

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

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()


registry.register("dirty-read", T1, T2, description="""
In this example, T1 updates de DB and, before it commits the transaction, T2 reads the same value.
If the DB accepts reading uncommitted data, it should read the value updated by T1 even though it wasn't commited yet.
Because of implementation details, this anomaly doesn't happen in PostgreSQL (regardless of the isolation level).
                  
┌────┐              ┌────┐             ┌────┐
│ T1 │              │ T2 │             │ DB │
└──┬─┘              └──┬─┘             └──┬─┘
   │                   │                  │
   ├─────────select balance──────────────►│
   │                   │                  │
   │                   ├──select balance─►│
   │                   │                  │
   ├────────update balance───────────────►│
   │                   │                  │
   ├────────select balance───────────────►│  T1 sees the updated value
   │                   │                  │
   │                   ├──select balance─►│  T2 sees the old value
   │                   │                  │
   │                   ├────commit───────►│
   │                   │                  │
   ├───────commit──────┼─────────────────►│
   │                   │                  │
""")
