# transaction isolation levels

This project is a simple python setup to emulate some concurrency issues while working with PostgreSQL transactions and how
isolation levels behave in these scenarios.

The anomalies presented here are taken from [PostgewSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html):

- dirty read
A transaction reads an uncommitted value by another transaction

- nonrepeatable read
A transaction reads the same "variable" twice, but it has different values on each read (another transaction updated the value in between).

- phantom read
Similar to `nonrepetable read` but relies on a search condition (`where`), so the result set is different between reads because
another transaction commited a change.

- serialization anomaly
Transactions did not run in a serial manner, so there can be inconsistencies.

The table below, taken from PG's docs, shows how different isolation levels behave with different anomalies

|Isolation Level|Dirty Read|Nonrepeatable Read|Phantom Read|Serialization Anomaly|
|---------------|----------|------------------|------------|---------------------|
|Read uncommitted|Not in PG|Possible|Possible|Possible|
|Read committed|Not possible|Possible|Possible|Possible|
|Repeatable read|Not possible|Not possible|Not in PG|Possible|
|Serializable|Not possible|Not possible|Not possible|Not possible|

Note that some of the issues, like `Dirty Read` are not possible in PostgreSQL because of its internal implementation.

# Running

Start PostgreSQL in a Docker container
```
docker run \
-e POSTGRES_PASSWORD=a.test_password \
-e POSTGRES_DB=transaction_isolation_test \
-p 5432:5432 \
--rm \
--name pg_transaction_isolation_test \
postgres
```

Create a virtual env and install dependencies
```
python -m venv .venv
.venv/bin/activate
pip install -r requirements.txt
```

Run it
```
PG_CONNECTION_STRING="postgresql://postgres:a.test_password@localhost:5432/transaction_isolation_test" \
python main.py --anomaly=non-repeatable-read -l=read-committed
```

To get all examples
```
python main.py -h
```

# Details

In order to mock the concurrent states between two transactions, this project is using asynchronous routines and
`asyncio.Event` to coordinate between two transactions/"threads" `T1` and `T2`.
There no actual threads, since `asyncio` is not about them, but it should be enough to emulate the concurrent
interchange of statements of an application and the database to check how it behaves depending on the transaction isolation levels.

All examples are under `anomaly` and a new example can be added by just following any of the existing anomalies.
Basically, it involves creating two classes `T1` and `T2` and implementing the `run` method with the given login to run the example.
`yield_for_another_task` is used to coordinate between `T1` and `T2`.
Finally, the example just needs to be registered using `anomaly.registry.register` and then it should be available in the CLI.
Optionally, `anomaly.registry.register` accepts a `description` argument that can be used to provide a plain text and/or ASCII diagram
to explain the example and expected outcomes.

# Examples

Here is a list of all current examples and their outcomes for each isolation level

```
dirty-read : read-uncommitted
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[08:T2]: COMMIT
[09:T1]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

dirty-read : read-committed
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[08:T2]: COMMIT
[09:T1]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

dirty-read : repeatable-read
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[08:T2]: COMMIT
[09:T1]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

dirty-read : serializable
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[08:T2]: COMMIT
[09:T1]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

phantom-read : read-uncommitted
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: update account set balance = 29 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          29| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           2|          31| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          29|

phantom-read : read-committed
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: update account set balance = 29 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          29| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           2|          31| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          29|

phantom-read : repeatable-read
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: update account set balance = 29 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          29| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          29|

phantom-read : serializable
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: update account set balance = 29 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          29| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          29|

phantom-read-insert : read-uncommitted
This example is similar to `phantom-read`, but instead of updating a row, a new is added (the same would happend for `delete`).

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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: insert into account (balance) values (33);
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33|

phantom-read-insert : read-committed
This example is similar to `phantom-read`, but instead of updating a row, a new is added (the same would happend for `delete`).

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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: insert into account (balance) values (33);
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33|

phantom-read-insert : repeatable-read
This example is similar to `phantom-read`, but instead of updating a row, a new is added (the same would happend for `delete`).

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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: insert into account (balance) values (33);
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33|

phantom-read-insert : serializable
This example is similar to `phantom-read`, but instead of updating a row, a new is added (the same would happend for `delete`).

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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[05:T1]: insert into account (balance) values (33);
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33| 

[07:T1]: COMMIT
[08:T2]: select id, balance from account where balance > 30;
|          id|     balance|
|           1|          67|
|           2|          31| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          33|

non-repeatable-read : read-uncommitted
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T1]: COMMIT
[08:T2]: select balance from account where id = 1;
|     balance|
|          10| 

[09:T2]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read : read-committed
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T1]: COMMIT
[08:T2]: select balance from account where id = 1;
|     balance|
|          10| 

[09:T2]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read : repeatable-read
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T1]: COMMIT
[08:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[09:T2]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read : serializable
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          10| 

[07:T1]: COMMIT
[08:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[09:T2]: COMMIT
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read-snapshot : read-uncommitted
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[04:T1]: COMMIT
[05:T2]: select balance from account where id = 1;
|     balance|
|          10| 

[06:T2]: COMMIT
[07:T1]: END
[08:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read-snapshot : read-committed
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[04:T1]: COMMIT
[05:T2]: select balance from account where id = 1;
|     balance|
|          10| 

[06:T2]: COMMIT
[07:T1]: END
[08:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read-snapshot : repeatable-read
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[04:T1]: COMMIT
[05:T2]: select balance from account where id = 1;
|     balance|
|          10| 

[06:T2]: COMMIT
[07:T1]: END
[08:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

non-repeatable-read-snapshot : serializable
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[04:T1]: COMMIT
[05:T2]: select balance from account where id = 1;
|     balance|
|          10| 

[06:T2]: COMMIT
[07:T1]: END
[08:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

serialization-anomaly : read-uncommitted
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          10| 

[07:T1]: COMMIT
[08:T2]: select sum(balance) from account;
|         sum|
|          41| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

serialization-anomaly : read-committed
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          10| 

[07:T1]: COMMIT
[08:T2]: select sum(balance) from account;
|         sum|
|          41| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

serialization-anomaly : repeatable-read
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          10| 

[07:T1]: COMMIT
[08:T2]: select sum(balance) from account;
|         sum|
|          98| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

serialization-anomaly : serializable
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

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select * from account;
|          id|     balance|
|           1|          67|
|           2|          31| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: update account set balance = 10 where id = 1;
MODIFIED: 1 

[06:T1]: select * from account;
|          id|     balance|
|           2|          31|
|           1|          10| 

[07:T1]: COMMIT
[08:T2]: select sum(balance) from account;
|         sum|
|          98| 

[09:T2]: COMMIT
[10:T1]: END
[11:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          10|

serialization-anomaly-update : read-uncommitted
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ raises an error for `repeatable read` and `serializable`
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = balance - 33 where id = 1;
MODIFIED: 1 

[09:T2]: select balance from account where id = 1;
|     balance|
|          44| 

[10:T2]: COMMIT
[11:T2]: END
[12:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          44|

serialization-anomaly-update : read-committed
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ raises an error for `repeatable read` and `serializable`
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = balance - 33 where id = 1;
MODIFIED: 1 

[09:T2]: select balance from account where id = 1;
|     balance|
|          44| 

[10:T2]: COMMIT
[11:T2]: END
[12:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          44|

serialization-anomaly-update : repeatable-read
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ raises an error for `repeatable read` and `serializable`
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = balance - 33 where id = 1;
ERROR: could not serialize access due to concurrent update 

[09:T2]: ROLLBACK
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          77|

serialization-anomaly-update : serializable
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ raises an error for `repeatable read` and `serializable`
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = balance - 33 where id = 1;
ERROR: could not serialize access due to concurrent update 

[09:T2]: ROLLBACK
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          77|

serialization-anomaly-insert : read-uncommitted
In this example, both T1 and T2 are inserting a new value and computing an aggregate on top of `account`. Since the end result is not guaranteed,
the DB raises an error for `serializable`. `read committed` results in the expected outcome considering all rows and
`repeatable read` ignores the value added in T2.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   ├────────insert into account────────────────►│
   │                   │                        │
   │                   ├──insert into account──►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   │                   ├────commit─────────────►│
   │                   │                        │
   ├────────select sum(balance)────────────────►│ T1 fails for `serializable` isolation level
   │                   │                        │ `repetable read` shows the result without T2 inserted value (phantom read)
   ├───────commit/rollback─────────────────────►│ `read commiitted` shows the result with T2 inserted value
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select sum(balance) from account;
|         sum|
|          98| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: insert into account (balance) values (89);
MODIFIED: 1 

[06:T2]: insert into account (balance) values (12);
MODIFIED: 1 

[07:T2]: select sum(balance) from account;
|         sum|
|         110| 

[08:T2]: COMMIT
[09:T1]: select sum(balance) from account;
|         sum|
|         199| 

[10:T1]: COMMIT
[11:T2]: END
[12:T1]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          89|
|           4|          12|

serialization-anomaly-insert : read-committed
In this example, both T1 and T2 are inserting a new value and computing an aggregate on top of `account`. Since the end result is not guaranteed,
the DB raises an error for `serializable`. `read committed` results in the expected outcome considering all rows and
`repeatable read` ignores the value added in T2.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   ├────────insert into account────────────────►│
   │                   │                        │
   │                   ├──insert into account──►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   │                   ├────commit─────────────►│
   │                   │                        │
   ├────────select sum(balance)────────────────►│ T1 fails for `serializable` isolation level
   │                   │                        │ `repetable read` shows the result without T2 inserted value (phantom read)
   ├───────commit/rollback─────────────────────►│ `read commiitted` shows the result with T2 inserted value
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select sum(balance) from account;
|         sum|
|          98| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: insert into account (balance) values (89);
MODIFIED: 1 

[06:T2]: insert into account (balance) values (12);
MODIFIED: 1 

[07:T2]: select sum(balance) from account;
|         sum|
|         110| 

[08:T2]: COMMIT
[09:T1]: select sum(balance) from account;
|         sum|
|         199| 

[10:T1]: COMMIT
[11:T2]: END
[12:T1]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          89|
|           4|          12|

serialization-anomaly-insert : repeatable-read
In this example, both T1 and T2 are inserting a new value and computing an aggregate on top of `account`. Since the end result is not guaranteed,
the DB raises an error for `serializable`. `read committed` results in the expected outcome considering all rows and
`repeatable read` ignores the value added in T2.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   ├────────insert into account────────────────►│
   │                   │                        │
   │                   ├──insert into account──►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   │                   ├────commit─────────────►│
   │                   │                        │
   ├────────select sum(balance)────────────────►│ T1 fails for `serializable` isolation level
   │                   │                        │ `repetable read` shows the result without T2 inserted value (phantom read)
   ├───────commit/rollback─────────────────────►│ `read commiitted` shows the result with T2 inserted value
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select sum(balance) from account;
|         sum|
|          98| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: insert into account (balance) values (89);
MODIFIED: 1 

[06:T2]: insert into account (balance) values (12);
MODIFIED: 1 

[07:T2]: select sum(balance) from account;
|         sum|
|         110| 

[08:T2]: COMMIT
[09:T1]: select sum(balance) from account;
|         sum|
|         187| 

[10:T1]: COMMIT
[11:T2]: END
[12:T1]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           3|          89|
|           4|          12|

serialization-anomaly-insert : serializable
In this example, both T1 and T2 are inserting a new value and computing an aggregate on top of `account`. Since the end result is not guaranteed,
the DB raises an error for `serializable`. `read committed` results in the expected outcome considering all rows and
`repeatable read` ignores the value added in T2.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   ├────────insert into account────────────────►│
   │                   │                        │
   │                   ├──insert into account──►│
   │                   │                        │
   │                   ├──select sum(balance)──►│
   │                   │                        │
   │                   ├────commit─────────────►│
   │                   │                        │
   ├────────select sum(balance)────────────────►│ T1 fails for `serializable` isolation level
   │                   │                        │ `repetable read` shows the result without T2 inserted value (phantom read)
   ├───────commit/rollback─────────────────────►│ `read commiitted` shows the result with T2 inserted value
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select sum(balance) from account;
|         sum|
|          98| 

[04:T2]: select sum(balance) from account;
|         sum|
|          98| 

[05:T1]: insert into account (balance) values (89);
MODIFIED: 1 

[06:T2]: insert into account (balance) values (12);
MODIFIED: 1 

[07:T2]: select sum(balance) from account;
|         sum|
|         110| 

[08:T2]: COMMIT
[09:T1]: select sum(balance) from account;
ERROR: could not serialize access due to read/write dependencies among transactions
DETAIL:  Reason code: Canceled on identification as a pivot, during conflict out checking.
HINT:  The transaction might succeed if retried. 

[10:T1]: ROLLBACK
[11:T2]: END
[12:T1]: END
DB STATE: AFTER
|          id|     balance|
|           1|          67|
|           2|          31|
|           4|          12|

serialization-anomaly-select-update : read-uncommitted
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels. The particular issue here is that the balance was stored in a variable and then
used to update the row.

IMPORTANT: `serialization-anomaly-update` worked properly for `read committed` isolation level, but this one shows an inconsistent balance at the end.

┌────┐              ┌────┐                             ┌────┐
│ T1 │              │ T2 │                             │ DB │
└──┬─┘              └──┬─┘                             └──┬─┘
   │                   │                                  │
   ├─────────select balance──────────────────────────────►│
   │                   │                                  │
   │                   ├──select balance and store───────►│
   │                   │                                  │
   ├────────update balance───────────────────────────────►│
   │                   │                                  │
   ├────────select balance───────────────────────────────►│
   │                   │                                  │
   ├───────commit──────┼─────────────────────────────────►│
   │                   │                                  │
   │                   ├──update balance─────────────────►│ raises an error for `repeatable read` and `serializable`
   │                   │                                  │
   │                   ├──select balance─────────────────►│
   │                   │                                  │
   │                   ├────commit/rollback──────────────►│ results in an inconsistent balance for `read committed` and `read uncommitted`
   │                   │                                  │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 67 + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = 67 - 33 where id = 1;
MODIFIED: 1 

[09:T2]: select balance from account where id = 1;
|     balance|
|          34| 

[10:T2]: COMMIT
[11:T1]: END
[12:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          34|

serialization-anomaly-select-update : read-committed
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels. The particular issue here is that the balance was stored in a variable and then
used to update the row.

IMPORTANT: `serialization-anomaly-update` worked properly for `read committed` isolation level, but this one shows an inconsistent balance at the end.

┌────┐              ┌────┐                             ┌────┐
│ T1 │              │ T2 │                             │ DB │
└──┬─┘              └──┬─┘                             └──┬─┘
   │                   │                                  │
   ├─────────select balance──────────────────────────────►│
   │                   │                                  │
   │                   ├──select balance and store───────►│
   │                   │                                  │
   ├────────update balance───────────────────────────────►│
   │                   │                                  │
   ├────────select balance───────────────────────────────►│
   │                   │                                  │
   ├───────commit──────┼─────────────────────────────────►│
   │                   │                                  │
   │                   ├──update balance─────────────────►│ raises an error for `repeatable read` and `serializable`
   │                   │                                  │
   │                   ├──select balance─────────────────►│
   │                   │                                  │
   │                   ├────commit/rollback──────────────►│ results in an inconsistent balance for `read committed` and `read uncommitted`
   │                   │                                  │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 67 + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = 67 - 33 where id = 1;
MODIFIED: 1 

[09:T2]: select balance from account where id = 1;
|     balance|
|          34| 

[10:T2]: COMMIT
[11:T1]: END
[12:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          34|

serialization-anomaly-select-update : repeatable-read
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels. The particular issue here is that the balance was stored in a variable and then
used to update the row.

IMPORTANT: `serialization-anomaly-update` worked properly for `read committed` isolation level, but this one shows an inconsistent balance at the end.

┌────┐              ┌────┐                             ┌────┐
│ T1 │              │ T2 │                             │ DB │
└──┬─┘              └──┬─┘                             └──┬─┘
   │                   │                                  │
   ├─────────select balance──────────────────────────────►│
   │                   │                                  │
   │                   ├──select balance and store───────►│
   │                   │                                  │
   ├────────update balance───────────────────────────────►│
   │                   │                                  │
   ├────────select balance───────────────────────────────►│
   │                   │                                  │
   ├───────commit──────┼─────────────────────────────────►│
   │                   │                                  │
   │                   ├──update balance─────────────────►│ raises an error for `repeatable read` and `serializable`
   │                   │                                  │
   │                   ├──select balance─────────────────►│
   │                   │                                  │
   │                   ├────commit/rollback──────────────►│ results in an inconsistent balance for `read committed` and `read uncommitted`
   │                   │                                  │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 67 + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = 67 - 33 where id = 1;
ERROR: could not serialize access due to concurrent update 

[09:T2]: ROLLBACK
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          77|

serialization-anomaly-select-update : serializable
In this example, there is a concurrent update between T1 and T2 on the same record that could cause an issue dedending on how the transactions
are executed. Even though T1 commits the transaction before T2 performs the update, it still raises an error for
`repetable read` and `serializable` isolation levels. The particular issue here is that the balance was stored in a variable and then
used to update the row.

IMPORTANT: `serialization-anomaly-update` worked properly for `read committed` isolation level, but this one shows an inconsistent balance at the end.

┌────┐              ┌────┐                             ┌────┐
│ T1 │              │ T2 │                             │ DB │
└──┬─┘              └──┬─┘                             └──┬─┘
   │                   │                                  │
   ├─────────select balance──────────────────────────────►│
   │                   │                                  │
   │                   ├──select balance and store───────►│
   │                   │                                  │
   ├────────update balance───────────────────────────────►│
   │                   │                                  │
   ├────────select balance───────────────────────────────►│
   │                   │                                  │
   ├───────commit──────┼─────────────────────────────────►│
   │                   │                                  │
   │                   ├──update balance─────────────────►│ raises an error for `repeatable read` and `serializable`
   │                   │                                  │
   │                   ├──select balance─────────────────►│
   │                   │                                  │
   │                   ├────commit/rollback──────────────►│ results in an inconsistent balance for `read committed` and `read uncommitted`
   │                   │                                  │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = 67 + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T1]: COMMIT
[08:T2]: update account set balance = 67 - 33 where id = 1;
ERROR: could not serialize access due to concurrent update 

[09:T2]: ROLLBACK
[10:T2]: END
[11:T1]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          77|

serialization-anomaly-concurrent-update : read-uncommitted
This example is similar to `serialization-anomaly-update`, but here the updates are performed "at the same time", meaning that no transaction
has committed the value when the other one runs an `update` too.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ blocks because of the uncommitted `update` in T1
   │                   │                        │  then fails for `serializable` and `repetable read`
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T2]: update account set balance = balance - 33 where id = 1;
waiting... 

[08:T1]: COMMIT
[09:T1]: END
[10:T2]: update account set balance = balance - 33 where id = 1;
MODIFIED: 1 

[11:T2]: select balance from account where id = 1;
|     balance|
|          44| 

[12:T2]: COMMIT
[13:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          44|

serialization-anomaly-concurrent-update : read-committed
This example is similar to `serialization-anomaly-update`, but here the updates are performed "at the same time", meaning that no transaction
has committed the value when the other one runs an `update` too.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ blocks because of the uncommitted `update` in T1
   │                   │                        │  then fails for `serializable` and `repetable read`
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T2]: update account set balance = balance - 33 where id = 1;
waiting... 

[08:T1]: COMMIT
[09:T1]: END
[10:T2]: update account set balance = balance - 33 where id = 1;
MODIFIED: 1 

[11:T2]: select balance from account where id = 1;
|     balance|
|          44| 

[12:T2]: COMMIT
[13:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          44|

serialization-anomaly-concurrent-update : repeatable-read
This example is similar to `serialization-anomaly-update`, but here the updates are performed "at the same time", meaning that no transaction
has committed the value when the other one runs an `update` too.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ blocks because of the uncommitted `update` in T1
   │                   │                        │  then fails for `serializable` and `repetable read`
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T2]: update account set balance = balance - 33 where id = 1;
waiting... 

[08:T1]: COMMIT
[09:T1]: END
[10:T2]: update account set balance = balance - 33 where id = 1;
ERROR: could not serialize access due to concurrent update 

[11:T2]: ROLLBACK
[12:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          77|

serialization-anomaly-concurrent-update : serializable
This example is similar to `serialization-anomaly-update`, but here the updates are performed "at the same time", meaning that no transaction
has committed the value when the other one runs an `update` too.

┌────┐              ┌────┐                   ┌────┐
│ T1 │              │ T2 │                   │ DB │
└──┬─┘              └──┬─┘                   └──┬─┘
   │                   │                        │
   ├─────────select balance────────────────────►│
   │                   │                        │
   │                   ├──select balance───────►│
   │                   │                        │
   ├────────update balance─────────────────────►│
   │                   │                        │
   ├────────select balance─────────────────────►│
   │                   │                        │
   │                   ├──update balance───────►│ blocks because of the uncommitted `update` in T1
   │                   │                        │  then fails for `serializable` and `repetable read`
   │                   ├──select balance───────►│
   │                   │                        │
   │                   ├────commit/rollback────►│
   │                   │                        │
   ├───────commit──────┼───────────────────────►│
   │                   │                        │

DB STATE: BEFORE
|          id|     balance|
|           1|          67|
|           2|          31|

[01:T1]: BEGIN
[02:T2]: BEGIN
[03:T1]: select balance from account where id = 1;
|     balance|
|          67| 

[04:T2]: select balance from account where id = 1;
|     balance|
|          67| 

[05:T1]: update account set balance = balance + 10 where id = 1;
MODIFIED: 1 

[06:T1]: select balance from account where id = 1;
|     balance|
|          77| 

[07:T2]: update account set balance = balance - 33 where id = 1;
waiting... 

[08:T1]: COMMIT
[09:T1]: END
[10:T2]: update account set balance = balance - 33 where id = 1;
ERROR: could not serialize access due to concurrent update 

[11:T2]: ROLLBACK
[12:T2]: END
DB STATE: AFTER
|          id|     balance|
|           2|          31|
|           1|          77|


```