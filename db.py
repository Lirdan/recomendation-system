import sqlite3

# Путь к файлу базы данных
db_path = 'books_db.sqlite'

# SQL-запросы для создания таблиц
create_table_queries = [
    "CREATE TABLE genres (id INTEGER PRIMARY KEY, genre_name TEXT);",
    "CREATE TABLE book_genre_relations (book_id INTEGER, genre_id INTEGER);",
    "CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, author NUMERIC, description BLOB, price NUMERIC, rating REAL, cover_url TEXT);",
    "CREATE TABLE users (userId INTEGER PRIMARY KEY, password REAL, email NUMERIC, firstName TEXT, lastName TEXT, address1 TEXT, address2 TEXT, zipcode TEXT, city TEXT, phone TEXT, roleId INTEGER, collaborative_weight FLOAT, content_weight FLOAT, genre_weight FLOAT);",
    "CREATE TABLE kart (userId INTEGER, productId INTEGER);",
    "CREATE TABLE user_ratings (id INTEGER PRIMARY KEY, user_id INTEGER, book_id INTEGER, rating INTEGER);",
    "CREATE TABLE orders (userId INTEGER, productId INTEGER, orderId INTEGER);",
    "CREATE TABLE event_logs (id INTEGER PRIMARY KEY, user_id INTEGER, event_type TEXT, event_data TEXT, recommendation_type TEXT, event_timestamp DATETIME);",
    "CREATE TABLE sqlite_sequence (name, seq);"
]

def setup_database():
    # Подключение к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создание таблиц
    for query in create_table_queries:
        cursor.execute(query)


    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()