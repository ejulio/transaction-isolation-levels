from base import ConcurrentTransactionExample


class T1(ConcurrentTransactionExample):

    async def run(self):
        with self.conn.cursor() as cursor:
            self.begin_transaction_with_isolation_level(cursor)

            query = "select * from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            await self.yield_for_another_task()

            query = "insert into account (balance) values (33);"
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

            query = "select id, balance from account where balance > 30;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            await self.yield_for_another_task()

            query = "select id, balance from account where balance > 30;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()
