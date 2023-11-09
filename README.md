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

## Running

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
python main.py --anomaly=non-repeatable-read -l=read-committed
```

To get all examples
```
python main.py -h
```
