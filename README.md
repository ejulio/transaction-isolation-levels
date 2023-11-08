psycopg cria uma transação por padrão em conn.cursor()

# docker run -e POSTGRES_PASSWORD=a.test_password -e POSTGRES_DB=transaction_isolation_test -p 5432:5432 --name pg_transaction_isolation_test postgres
# pip install psycopg
