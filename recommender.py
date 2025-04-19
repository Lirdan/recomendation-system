import pandas as pd
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
from sklearn.decomposition import TruncatedSVD
import random
def fetch_data_from_db(database_path):
    """Fetch necessary data from the database."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    orders_data = cursor.execute("SELECT userId, productId FROM orders;").fetchall()
    books_data = cursor.execute("SELECT * FROM books;").fetchall()

    conn.close()

    return orders_data, books_data


def get_books_dataframe(books_data):
    """Convert books data to a DataFrame."""
    return pd.DataFrame(books_data, columns=["book_id", "title", "author", "description", "price", "rating", "cover"])


def generate_recommendations_for_new_user(database_path, num_recommendations=5):
    """
    Recommend random high-rated books for new users without history.

    Selects books from the database with rating above a defined threshold
    and returns a random subset of them.

    Parameters:
        database_path (str): Path to SQLite database.
        num_recommendations (int): How many books to recommend.

    Returns:
        list[dict]: List of recommended books with book_id, title, and author.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    min_rating = 4  # Minimum rating threshold
    cursor.execute("SELECT * FROM books WHERE rating >= ?", (min_rating,))
    eligible_books = cursor.fetchall()

    # Pick N random books from the high-rated list
    random_recommendations = random.sample(eligible_books, min(num_recommendations, len(eligible_books)))

    conn.close()
    
    # Convert to readable dict format
    books_df = pd.DataFrame(random_recommendations,
                            columns=["book_id", "title", "author", "description", "price", "rating", "cover"])
    recommendations = books_df[["book_id", "title", "author"]].to_dict(orient='records')
    return recommendations

def generate_user_preference_recommendations(database_path, user_id, num_recommendations=10):
    """
    Recommend books based on user's preferred genres.

    This function analyzes the user's order history to identify the most frequent genres.
    It then ranks books from those genres based on a combination of genre frequency and book rating.

    Parameters:
        path (str): Path to the SQLite database.
        user_id (int): ID of the user to generate recommendations for.
        n (int): Number of books to recommend.

    Returns:
        DataFrame: Top-N recommended books based on genre preferences.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Try to fetch user's positively rated genres
    cursor.execute("""
        SELECT DISTINCT book_genre_relations.genre_id
        FROM book_genre_relations
        JOIN user_ratings ON book_genre_relations.book_id = user_ratings.book_id
        WHERE user_ratings.user_id = ? AND user_ratings.rating >= 3;
    """, (user_id,))
    rated_genres = [item[0] for item in cursor.fetchall()]

    # If no ratings, use genres from previously ordered books
    if not rated_genres:
        cursor.execute("""
            SELECT DISTINCT book_genre_relations.genre_id
            FROM book_genre_relations
            JOIN orders ON book_genre_relations.book_id = orders.productId
            WHERE orders.userId = ?;
        """, (user_id,))
        rated_genres = [item[0] for item in cursor.fetchall()]
    
    # If still no genres, return empty list
    if not rated_genres:
        conn.close()
        return []

    # Recommend books that match the user's favorite genres
    query = """
        SELECT books.id, books.title, books.author, COUNT(*) as genre_match_count
        FROM books
        JOIN book_genre_relations ON books.id = book_genre_relations.book_id
        WHERE book_genre_relations.genre_id IN ({})
        GROUP BY books.id, books.title, books.author
        ORDER BY genre_match_count DESC, books.rating DESC
        LIMIT {};
    """.format(','.join('?' for _ in rated_genres), num_recommendations)
    cursor.execute(query, rated_genres)
    recommendations = cursor.fetchall()
    conn.close()

    # Convert result to list of dicts
    return [{'book_id': rec[0], 'title': rec[1], 'author': rec[2]} for rec in recommendations]

def content_based_recommendations_optimized(orders_df, books_df, user_id):
    """
    Recommend books based on content similarity (description analysis).

    Uses TF-IDF vectorization and cosine similarity on book descriptions.
    Picks random N books that the user has read, then finds similar books
    by description.

    Parameters:
        orders_df (DataFrame): Order history (with columns: user_id, book_id).
        books_df (DataFrame): Book metadata (with descriptions).
        user_id (int): ID of the user to generate recommendations for.

    Returns:
        list[dict]: List of recommended books (book_id, title, author).
    """
    
    # Fill missing descriptions with empty strings
    book_descriptions = books_df["description"].fillna('')

    # Define stop words manually (can be improved using language-specific sets)
    ukrainian_stop_words = ["і", "та", "або", "але", "як", "що", "це", "у", "з", "на", "до", "при", "за", "про", "від"]
    
    # Create TF-IDF matrix from all descriptions
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(book_descriptions)
    
     # Compute cosine similarity between all book pairs
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    # Randomly select up to 10 books the user has read
    num_samples = min(10, len(orders_df[orders_df['user_id'] == user_id]))
    user_books = orders_df[orders_df['user_id'] == user_id]['book_id'].sample(num_samples).values

    # Set to store indices of similar books
    book_indices = set()

    for book_id in user_books:
        # Skip if book ID is missing from books_df
        if books_df[books_df["book_id"] == book_id].empty:
            continue
        # Get the index of the selected book in books_df
        idx = books_df[books_df["book_id"] == book_id].index[0]
        # Get similarity scores between this book and others
        sim_scores = list(enumerate(cosine_sim[idx]))
        # Sort by similarity (most similar first) and take top 10
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        book_indices.update([i[0] for i in sim_scores[1:10]])
    # Build result from selected similar books
    content_recs = books_df.iloc[list(book_indices)]
    recommendations = content_recs[["book_id", "title", "author"]].to_dict(orient='records')
    return recommendations


def collaborative_filtering_recommendations_optimized(user_item_matrix, books_df, user_id):
   """
    Recommend books using collaborative filtering (SVD).

    Applies matrix factorization (TruncatedSVD) to discover latent user preferences.
    Finds users similar to the target user and recommends books they prefer.

    Parameters:
        user_item_matrix (DataFrame): Pivot table (users × books), values = interaction count.
        books_df (DataFrame): Catalog of books.
        user_id (int): Target user ID.

    Returns:
        list[dict]: List of recommended books (book_id, title, author).
    """
    if user_id not in user_item_matrix.index:
        return []
    # Choose number of components for SVD
    n_components = min(user_item_matrix.shape) - 1  # This can be tuned for better results
    
    # Decompose the user-book matrix
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    user_latent_matrix = svd.fit_transform(user_item_matrix)

    # Compute user-to-user similarity
    user_similarity = cosine_similarity(user_latent_matrix)

    # Get index of current user
    user_idx = user_item_matrix.index.get_loc(user_id)

    # Find users most similar to current one
    sim_scores = list(enumerate(user_similarity[user_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    similar_users = [i[0] for i in sim_scores[1:10]]

    # Get books these users have interacted with
    similar_users_orders = user_item_matrix.iloc[similar_users]

    # Recommend top 10 books most common among similar users
    recommended_books = similar_users_orders.mean(axis=0).sort_values(ascending=False).head(10).index
    collaborative_recs = books_df[books_df["book_id"].isin(recommended_books)]
    recommendations = collaborative_recs[["book_id", "title", "author"]].to_dict(orient='records')
    return recommendations
def get_read_books(user_id, conn):
    """
    Get list of book IDs that the user has already read (from 'orders').

    Parameters:
        user_id (int): ID of the user.
        conn (sqlite3.Connection): Open SQLite connection.

    Returns:
        list[int]: List of book IDs already read by the user.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT productId FROM orders WHERE userId = ?", (user_id,))
    read_books = [item[0] for item in cursor.fetchall()]
    return read_books

def hybrid_recommendation_system(database_path, user_id, num_recommendations=10, w1=0.33, w2=0.33, lambda_val=0.34):
    """
    Combine collaborative, content-based, and genre-based recommendations.

    This function generates recommendations from all three strategies,
    filters out already read books, and merges them using provided weights.

    Parameters:
        database_path (str): Path to SQLite database.
        user_id (int): ID of the user.
        num_recommendations (int): Total number of books to recommend.
        w1 (float): Weight for collaborative strategy.
        w2 (float): Weight for content-based strategy.
        lambda_val (float): Weight for genre-based strategy.

    Returns:
        list[dict]: Combined recommendation list (with book_id and source).
    """
    # Step 1: Load raw data
    orders_data, books_data = fetch_data_from_db(database_path)
    orders_df = pd.DataFrame(orders_data, columns=["user_id", "book_id"])
    books_df = get_books_dataframe(books_data)
    user_item_matrix = pd.pivot_table(orders_df, index="user_id", columns="book_id", aggfunc=len, fill_value=0)

    # Step 2: Get books the user has already read
    with sqlite3.connect(database_path) as conn:
        read_books = get_read_books(user_id, conn)

    # Step 3: Generate raw recommendations
    collab_recs = [book['book_id'] for book in collaborative_filtering_recommendations_optimized(user_item_matrix, books_df, user_id) if book['book_id'] not in read_books]
    content_recs = [book['book_id'] for book in content_based_recommendations_optimized(orders_df, books_df, user_id) if book['book_id'] not in read_books]
    user_prefs = [book['book_id'] for book in generate_user_preference_recommendations(database_path, user_id) if book['book_id'] not in read_books]
    
    # Step 4: Allocate recommendation slots based on weights
    total_weight = w1 + w2 + lambda_val
    num_collab = int(num_recommendations * (w1 / total_weight))
    num_content = int(num_recommendations * (w2 / total_weight))
    num_genre = num_recommendations - (num_collab + num_content)  # The rest of the recommendations are assigned to genre preferences

    # Step 5: Select final recommendations
    selected_collab = collab_recs[:num_collab]
    selected_content = content_recs[:num_content]
    selected_genre = user_prefs[:num_genre]

    # Step 6: Combine into a single list with source tagging
    all_recs = [{'book_id': book_id, 'source': 'collaborative'} for book_id in selected_collab] + \
               [{'book_id': book_id, 'source': 'content'} for book_id in selected_content] + \
               [{'book_id': book_id, 'source': 'genre'} for book_id in selected_genre]

    return all_recs
def generate_random_genre_recommendations(database_path, num_recommendations=5):
   """
    Recommend random high-rated books from a randomly chosen genre.

    Useful for guest users or discovery mode.

    Parameters:
        database_path (str): Path to SQLite database.
        num_recommendations (int): Number of books to recommend.

    Returns:
        tuple: (List of books, genre name)
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Get all genres
    cursor.execute("SELECT * FROM genres;")
    all_genres = cursor.fetchall()
    genre_dict = {genre[0]: genre[1] for genre in all_genres}

    # Pick a random genre
    random_genre_id, random_genre_name = random.choice(all_genres)

    # Select top-rated books from this genre
    cursor.execute("""
        SELECT books.id, books.title, books.price, books.author, books.cover_url, CAST(ROUND(books.rating,0)AS INT)
        FROM books
        JOIN book_genre_relations ON books.id = book_genre_relations.book_id
        WHERE book_genre_relations.genre_id = ? AND books.rating >= 3.5
        ORDER BY books.rating DESC
        LIMIT ?;
    """, ( random_genre_id, num_recommendations))
    recommendations = cursor.fetchall()

    conn.close()
    return recommendations, random_genre_name
