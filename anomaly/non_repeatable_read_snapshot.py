from anomaly.base import ConcurrentTransactionExample
from anomaly import registry


class T1(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            await self.yield_for_another_task()

            query = "update account set balance = 10 where id = 1;"
            await cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")
            
            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()


class T2(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            await self.yield_for_another_task()

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()

registry.register("non-repeatable-read-snapshot", T1, T2, description="""
This example is similar to `non-repetable-read`, but it is intended to show when the DB takes the snapshop for repeatable reads.
For PostgreSQL, the value snapshot is taken on the first read (`select`), and not before `begin transaction`.
                  
┌────┐              ┌────┐             ┌────┐
│ T1 │              │ T2 │             │ DB │
└──┬─┘              └──┬─┘             └──┬─┘
   │                   │                  │
   ├─────────begin transaction───────────►│
   │                   │                  │
   │                   ├begin transaction►│
   │                   │                  │
   ├────────update balance───────────────►│
   │                   │                  │
   ├───────commit──────┼─────────────────►│
   │                   │                  │
   │                   ├──select balance─►│ # T2 sees the updated value, not the value before the transaction began
   │                   │                  │
   │                   ├────commit───────►│
   │                   │                  │
""")
