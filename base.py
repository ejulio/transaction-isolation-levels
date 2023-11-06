from abc import ABC, abstractmethod
from asyncio import Event, wait_for
from typing import Dict, List

from psycopg import Connection, Cursor, IsolationLevel


class ConcurrentTransactionExample(ABC):

    conn: Connection
    _isolation_level: IsolationLevel
    _self_event: Event
    _other_event: Event

    _global_printer_count: int = 0

    def __init__(self, conn: Connection, level: IsolationLevel, self_event: Event, other_event: Event):
        self.conn = conn
        self._isolation_level = level
        self._self_event = self_event
        self._other_event = other_event

    async def __call__(self):
        self.print_text(f"BEGIN")
        await self._wait()
        await self.run()
        self._done()
        self.print_text("END")

    @abstractmethod
    async def run(self):
        ...

    def begin_transaction_with_isolation_level(self, cursor: Cursor):
        cursor.execute("begin transaction")
        match self._isolation_level:
            case IsolationLevel.READ_UNCOMMITTED:
                cursor.execute("set transaction isolation level read uncommitted")
            case IsolationLevel.READ_COMMITTED:
                cursor.execute("set transaction isolation level read committed")
            case IsolationLevel.REPEATABLE_READ:
                cursor.execute("set transaction isolation level repeatable read")
            case IsolationLevel.SERIALIZABLE:
                cursor.execute("set transaction isolation level serializable")

    # syncing helpers

    async def _wait(self):
        await self._self_event.wait()

    def _done(self):
        self._other_event.set()

    async def yield_for_another_task(self):
        self._other_event.set()
        try:
            await wait_for(self._self_event.wait(), timeout=2)
        except TimeoutError:
            self.print_text("yield_to_other", "TIMEOUT")
        self._self_event.clear()

    # printing helpers

    def print_text(self, query: str, text: str | None = None) -> None:
        ConcurrentTransactionExample._global_printer_count += 1
        print(f"[{ConcurrentTransactionExample._global_printer_count:0>2}:{self.__class__.__name__}]: {query}")
        if text:
            print(text, "\n")

    def print_query_result(self, query: str, records: List[Dict]) -> None:
        ConcurrentTransactionExample._global_printer_count += 1
        print(f"[{ConcurrentTransactionExample._global_printer_count:0>2}:{self.__class__.__name__}]: {query}")
        print(format_table(records), "\n")


def format_table(records: List[Dict]) -> str:
    if not records:
        return "EMPTY"

    # https://stackoverflow.com/a/9536084
    # results in |{:<12}|{:<12}|...| to format as many fields as in the first record
    fmt = ("|{:>12}" * len(records[0])) + "|"
    formatted = fmt.format(*list(records[0].keys()))
    for record in records:
        values = map(lambda x: x if x is not None else "NULL", record.values())
        formatted += "\n" + fmt.format(*list(values))

    return formatted
