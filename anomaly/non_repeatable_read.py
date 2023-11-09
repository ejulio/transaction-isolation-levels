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

registry.register("non-repeatable-read", T1, T2, description="""
In this example, T2 reads the DB twice, but in between reads, T1 commits its transaction updating the value.
For `read uncommitted` (not supported by PostgreSQL) and `read committed` isolation levels, T2 will read 2 different values.
For `repeatable read` and `serializable` isolation levels, T2 will read the same [old] value, regardless if it was updated in between.
                  
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
   ├───────commit──────┼─────────────────►│
   │                   │                  │
   │                   ├──select balance─►│  T2 sees the old/new value depending on the isolation level
   │                   │                  │
   │                   ├────commit───────►│
   │                   │                  │
""")
