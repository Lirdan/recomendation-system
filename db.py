import sqlite3

# Path to the SQLite database file
db_path = 'books_db.sqlite'

# List of SQL queries used to create necessary tables in the database
create_table_queries = [
    # Genre categories (e.g., fiction, fantasy)
    "CREATE TABLE genres (id INTEGER PRIMARY KEY, genre_name TEXT);",
    # Many-to-many relationship between books and genres
    "CREATE TABLE book_genre_relations (book_id INTEGER, genre_id INTEGER);",
    # Main book table
    "CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, author NUMERIC, description BLOB, price NUMERIC, rating REAL, cover_url TEXT);",
    # User table with login info and personalization weights
    "CREATE TABLE users (userId INTEGER PRIMARY KEY, password REAL, email NUMERIC, firstName TEXT, lastName TEXT, address1 TEXT, address2 TEXT, zipcode TEXT, city TEXT, phone TEXT, roleId INTEGER, collaborative_weight FLOAT, content_weight FLOAT, genre_weight FLOAT);",
    # Cart table storing items added to the shopping cart
    "CREATE TABLE kart (userId INTEGER, productId INTEGER);",
    # User-generated book ratings
    "CREATE TABLE user_ratings (id INTEGER PRIMARY KEY, user_id INTEGER, book_id INTEGER, rating INTEGER);",
    # Orders placed by users
    "CREATE TABLE orders (userId INTEGER, productId INTEGER, orderId INTEGER);",
    # Event logs for tracking views, clicks, and purchases
    "CREATE TABLE event_logs (id INTEGER PRIMARY KEY, user_id INTEGER, event_type TEXT, event_data TEXT, recommendation_type TEXT, event_timestamp DATETIME);",
    # SQLite internal sequence tracking table
    "CREATE TABLE sqlite_sequence (name, seq);"
]

def setup_database():
    """
    Initialize the SQLite database by creating all required tables.

    This function connects to the database and executes all the SQL statements
    defined in the `create_table_queries` list.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute each table creation query
    for query in create_table_queries:
        cursor.execute(query)


    # Save changes and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Only run setup if this script is executed directly
    setup_database()
