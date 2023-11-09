import psycopg

from anomaly.base import ConcurrentTransactionExample
from anomaly import registry


class T1(ConcurrentTransactionExample):

    async def run(self):
        async with self.conn.cursor() as cursor:
            await self.begin_transaction_with_isolation_level(cursor)

            query = "select balance from account where id = 1;"
            await cursor.execute(query)
            balances = await cursor.fetchall()
            self.print_query_result(query, balances)
            balance = balances[0]["balance"]

            await self.yield_for_another_task()

            query = f"update account set balance = {balance} + 10 where id = 1;"
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
            balances = await cursor.fetchall()
            self.print_query_result(query, balances)
            balance = balances[0]["balance"]

            await self.yield_for_another_task()

            try:
                query = f"update account set balance = {balance} - 33 where id = 1;"
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
            await self.yield_for_another_task()

registry.register("serialization-anomaly-select-update", T1, T2)
