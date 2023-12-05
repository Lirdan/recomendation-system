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
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Получаем книги с рейтингом выше определённого порога
    min_rating = 4  # Можно настроить порог рейтинга
    cursor.execute("SELECT * FROM books WHERE rating >= ?", (min_rating,))
    eligible_books = cursor.fetchall()

    # Выбираем случайные книги из списка
    random_recommendations = random.sample(eligible_books, min(num_recommendations, len(eligible_books)))

    conn.close()
    books_df = pd.DataFrame(random_recommendations,
                            columns=["book_id", "title", "author", "description", "price", "rating", "cover"])
    recommendations = books_df[["book_id", "title", "author"]].to_dict(orient='records')
    return recommendations

def generate_user_preference_recommendations(database_path, user_id, num_recommendations=10):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Получаем оцененные жанры пользователя
    cursor.execute("""
        SELECT DISTINCT book_genre_relations.genre_id
        FROM book_genre_relations
        JOIN user_ratings ON book_genre_relations.book_id = user_ratings.book_id
        WHERE user_ratings.user_id = ? AND user_ratings.rating >= 3;
    """, (user_id,))
    rated_genres = [item[0] for item in cursor.fetchall()]

    # Получаем все жанры прочитанных книг пользователя, если нет оцененных
    if not rated_genres:
        cursor.execute("""
            SELECT DISTINCT book_genre_relations.genre_id
            FROM book_genre_relations
            JOIN orders ON book_genre_relations.book_id = orders.productId
            WHERE orders.userId = ?;
        """, (user_id,))
        rated_genres = [item[0] for item in cursor.fetchall()]

    # Выборка книг с максимальным совпадением жанров
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
    return [{'book_id': rec[0], 'title': rec[1], 'author': rec[2]} for rec in recommendations]

def content_based_recommendations_optimized(orders_df, books_df, user_id):
    """Optimized content-based recommendations."""
    book_descriptions = books_df["description"].fillna('')
    ukrainian_stop_words = ["і", "та", "або", "але", "як", "що", "це", "у", "з", "на", "до", "при", "за", "про", "від"]
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(book_descriptions)
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    num_samples = min(10, len(orders_df[orders_df['user_id'] == user_id]))
    user_books = orders_df[orders_df['user_id'] == user_id]['book_id'].sample(num_samples).values
    book_indices = set()
    for book_id in user_books:
        if books_df[books_df["book_id"] == book_id].empty:
            continue
        idx = books_df[books_df["book_id"] == book_id].index[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        book_indices.update([i[0] for i in sim_scores[1:10]])
    content_recs = books_df.iloc[list(book_indices)]
    recommendations = content_recs[["book_id", "title", "author"]].to_dict(orient='records')
    return recommendations


def collaborative_filtering_recommendations_optimized(user_item_matrix, books_df, user_id):
    """Optimized collaborative filtering recommendations."""
    if user_id not in user_item_matrix.index:
        return []
    n_components = min(user_item_matrix.shape) - 1  # This can be tuned for better results
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    user_latent_matrix = svd.fit_transform(user_item_matrix)
    user_similarity = cosine_similarity(user_latent_matrix)
    user_idx = user_item_matrix.index.get_loc(user_id)
    sim_scores = list(enumerate(user_similarity[user_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    similar_users = [i[0] for i in sim_scores[1:10]]
    similar_users_orders = user_item_matrix.iloc[similar_users]
    recommended_books = similar_users_orders.mean(axis=0).sort_values(ascending=False).head(10).index
    collaborative_recs = books_df[books_df["book_id"].isin(recommended_books)]
    recommendations = collaborative_recs[["book_id", "title", "author"]].to_dict(orient='records')
    return recommendations
def get_read_books(user_id, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT productId FROM orders WHERE userId = ?", (user_id,))
    read_books = [item[0] for item in cursor.fetchall()]
    return read_books

def hybrid_recommendation_system(database_path, user_id, num_recommendations=10, w1=0.33, w2=0.33, lambda_val=0.34):
    # Получение данных
    orders_data, books_data = fetch_data_from_db(database_path)
    orders_df = pd.DataFrame(orders_data, columns=["user_id", "book_id"])
    books_df = get_books_dataframe(books_data)
    user_item_matrix = pd.pivot_table(orders_df, index="user_id", columns="book_id", aggfunc=len, fill_value=0)

    with sqlite3.connect(database_path) as conn:
        read_books = get_read_books(user_id, conn)

    collab_recs = [book['book_id'] for book in collaborative_filtering_recommendations_optimized(user_item_matrix, books_df, user_id) if book['book_id'] not in read_books]
    content_recs = [book['book_id'] for book in content_based_recommendations_optimized(orders_df, books_df, user_id) if book['book_id'] not in read_books]
    user_prefs = [book['book_id'] for book in generate_user_preference_recommendations(database_path, user_id) if book['book_id'] not in read_books]
    # Распределение количества рекомендаций согласно весам
    total_weight = w1 + w2 + lambda_val
    num_collab = int(num_recommendations * (w1 / total_weight))
    num_content = int(num_recommendations * (w2 / total_weight))
    num_genre = num_recommendations - (num_collab + num_content)  # Остаток рекомендаций отводится под жанровые предпочтения

    selected_collab = collab_recs[:num_collab]
    selected_content = content_recs[:num_content]
    selected_genre = user_prefs[:num_genre]

    all_recs = [{'book_id': book_id, 'source': 'collaborative'} for book_id in selected_collab] + \
               [{'book_id': book_id, 'source': 'content'} for book_id in selected_content] + \
               [{'book_id': book_id, 'source': 'genre'} for book_id in selected_genre]

    return all_recs
def generate_random_genre_recommendations(database_path, num_recommendations=5):
    """Генерация случайных рекомендаций по случайному жанру."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM genres;")
    all_genres = cursor.fetchall()
    genre_dict = {genre[0]: genre[1] for genre in all_genres}

    # Выбор случайного жанра
    random_genre_id, random_genre_name = random.choice(all_genres)

    # Получение книг с высоким рейтингом в этом жанре
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