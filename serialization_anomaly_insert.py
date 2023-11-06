import psycopg

from base import ConcurrentTransactionExample


class T1(ConcurrentTransactionExample):

    async def run(self):
        with self.conn.cursor() as cursor:
            self.begin_transaction_with_isolation_level(cursor)

            query = "select sum(balance) from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            await self.yield_for_another_task()

            query = "insert into account (balance) values (89);"
            cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            await self.yield_for_another_task()

            try:
                query = "select sum(balance) from account;"
                cursor.execute(query)
                self.print_query_result(query, cursor.fetchall())

                cursor.execute("commit;")
                self.print_text("COMMIT")
            except psycopg.errors.SerializationFailure as exc:
                self.print_text(query, f"ERROR: {exc}")

            cursor.execute("rollback;")
            self.print_text("ROLLBACK")
            await self.yield_for_another_task()


class T2(ConcurrentTransactionExample):

    async def run(self):
        with self.conn.cursor() as cursor:
            self.begin_transaction_with_isolation_level(cursor)

            query = "select sum(balance) from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            await self.yield_for_another_task()

            query = "insert into account (balance) values (12);"
            cursor.execute(query)
            self.print_text(query, f"MODIFIED: {cursor.rowcount}")

            query = "select sum(balance) from account;"
            cursor.execute(query)
            self.print_query_result(query, cursor.fetchall())

            cursor.execute("commit;")
            self.print_text("COMMIT")
            await self.yield_for_another_task()
