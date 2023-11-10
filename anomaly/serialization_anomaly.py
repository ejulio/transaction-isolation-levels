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

            query = "update account set balance = 10 where id = 1;"
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

            query = "select sum(balance) from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await self.yield_for_another_task()

            query = "select sum(balance) from account;"
            await cursor.execute(query)
            self.print_query_result(query, await cursor.fetchall())

            await cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()

registry.register("serialization-anomaly", T1, T2, description="""
This example behaves similarly to `non-repeatable-read` because T2 is just reading values, not performing any change.
So, there's no inconsistency in the end result besides reading new/old values that is handled ny `read commited` and `repeatable read`
isolation levels.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│  T1 sees the new result set
   │                   │                        │
   │                   ├──select sum(balance)──►│  T2 sees the new result set depending on the isolation level
   │                   │                        │
   │                   ├────commit─────────────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
""")
