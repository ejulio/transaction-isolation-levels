from anomaly.base import ConcurrentTransactionExample
from anomaly import registry


class T1(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select * from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            query = "update account set balance = 29 where id = 1;"
            await cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            query = "select * from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()


class T2(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select id, balance from account where balance > 30;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            query = "select id, balance from account where balance > 30;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()

registry.register("phantom-read", T1, T2, description="""
This example is quite similar to `non-repeatable-read`, but instead of reading an updated/outdated value,
it is reading a different result set (different evaluation of the `where` clause).

┌────┐              ┌────┐                         ┌────┐
│ T1 │              │ T2 │                         │ DB │
└──┬─┘              └──┬─┘                         └──┬─┘
   │                   │                              │
   ├─────────select balance──────────────────────────►│
   │                   │                              │
   │                   ├──select balance where───────►│
   │                   │                              │
   ├────────update balance───────────────────────────►│
   │                   │                              │
   ├────────select balance───────────────────────────►│  T1 sees the new result set
   │                   │                              │
   │                   ├──select balance where───────►│  T2 sees the new result set depending on the isolation level
   │                   │                              │
   │                   ├────commit───────────────────►│
   │                   │                              │
   ├───────commit──────┼─────────────────────────────►│
   │                   │                              │
""")
