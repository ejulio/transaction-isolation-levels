from base import ConcurrentTransactionExample


class T1(ConcurrentTransactionExample):

    async def run(self):
        with self.conn.cursor() as cursor:
            self.begin_transaction_with_isolation_level(cursor)

            query = "select * from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            await self.yield_for_another_task()

            query = "update account set balance = 10 where id = 1;"
            cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            query = "select * from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            cursor.execute("commit;")
            self.print_text("COMMIT")

            await self.yield_for_another_task()


class T2(ConcurrentTransactionExample):

    async def run(self):
        with self.conn.cursor() as cursor:
            self.begin_transaction_with_isolation_level(cursor)

            query = "select sum(balance) from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            await self.yield_for_another_task()

            query = "select sum(balance) from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()
