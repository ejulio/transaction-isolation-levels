psycopg cria uma transação por padrão em conn.cursor()

# docker run -e POSTGRES_PASSWORD=a.test_password -e POSTGRES_DB=transaction_isolation_test -p 5432:5432 --name pg_transaction_isolation_test postgres
# pip install psycopg

TODO:

- [ ] serialization_anomaly_update move commit later to lock the transaction
- [ ] serialization_anomaly_select_update select value and then use it in update