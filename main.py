from flask import *
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from numpy import*
from recommender import*
app = Flask(__name__)
app.secret_key = 'random string'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE_URI = "C:/Users/skryn/OneDrive/Изображения/универ/диплом № 2/bookstore/books_db.sqlite"
from bandit import MultiArmedBandit
from  data_visualization import*
from bokeh.resources import CDN
def getLoginDetails():
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute("SELECT userId, firstName FROM users WHERE email = '" + session['email'] + "'")
            userId, firstName = cur.fetchone()
            session['userId'] = userId
            cur.execute("SELECT count(productId) FROM kart WHERE userId = " + str(userId))
            noOfItems = cur.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)
@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    genre_recomendations, genre_name = generate_random_genre_recommendations(DATABASE_URI)
    for i in range(len(genre_recomendations)):
        genre_recomendations[i] = truncate_title_in_tuple(genre_recomendations[i])
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        itemData1 = []
        if not loggedIn:
                itemData = generate_recommendations_for_new_user(DATABASE_URI)
                book_ids = [item['book_id'] for item in itemData]
                for i in book_ids:
                    cur.execute('SELECT id, title, price, author, cover_url, rating FROM books WHERE id =' + str(i))
                    itemData1.append(cur.fetchall())
                flattened_books = [book for sublist in itemData1 for book in sublist]
                books = [(id, title, price, author, url, round(rating)) for (id, title, price, author, url, rating) in
                         flattened_books]
                return render_template('index.html', loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems,
                                       itemData=books, genre_recomendations=genre_recomendations, genre_name=genre_name
                                       )
        else:
            bandit_weights = session.get('bandit_weights', {})
            itemData = hybrid_recommendation_system(
            DATABASE_URI, session['userId'],w1=bandit_weights.get('collaborative'), w2=bandit_weights.get('content'), lambda_val=bandit_weights.get('genre'))
            if not itemData:
                itemData = generate_recommendations_for_new_user(DATABASE_URI)
                book_ids = [item['book_id'] for item in itemData]
                for i in book_ids:
                        cur.execute('SELECT id, title, price, author, cover_url, rating FROM books WHERE id =' + str(i))
                        itemData1.append(cur.fetchall())
                flattened_books = [book for sublist in itemData1 for book in sublist]
                books = [(id, title, price, author, url, round(rating)) for (id, title, price, author, url, rating) in
                             flattened_books]
                return render_template('index.html', loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems,
                                       itemData=books, genre_recomendations=genre_recomendations, genre_name=genre_name
                                       )
            recommendation_sources = {}
            for i in itemData:
                recommendation_sources[i['book_id']] = i['source']
                log_event(user_id=session['userId'], event_type="view", event_data=str(i['book_id']),recommendation_type=i['source'])

                cur.execute('SELECT id, title, price, author, cover_url, rating FROM books WHERE id ='+str(i['book_id']))
                data=cur.fetchall()
                if len(data[0][1])<35:
                    itemData1.append(data)
                else:
                    data[0]=truncate_title_in_tuple(data[0])
                    itemData1.append(data)
            session['recommendation_sources'] = recommendation_sources
            added_book_ids = set()
            flattened_books = []
            for sublist in itemData1:
                for book in sublist:
                    book_id = book[0]  # Предполагаем, что ID книги - это первый элемент кортежа
                    if book_id not in added_book_ids:
                        flattened_books.append(book)
                        added_book_ids.add(book_id)
            books = [(id, title, price, author, url, round(rating)) for (id, title, price, author, url, rating) in flattened_books]
            return render_template('index.html', loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems,
                                   itemData=books, genre_recomendations=genre_recomendations, genre_name=genre_name
                                   )
def truncate_title_in_tuple(a_tuple):
    # Проверяем и обрезаем название, если оно длиннее 45 символов
    title = a_tuple[1]
    if len(title) > 35:
        title = title[:35]+'...'
    # Создаем новый кортеж с обрезанным названием
    new_tuple = (a_tuple[0], title) + a_tuple[2:]
    return new_tuple
@app.route("/add")
def addForm():
   return render_template('add.html')
@app.route("/AdminloginForm")
def AdminloginForm():
    if 'email' in session:
        return redirect(url_for('admin'))
    else:
        return render_template('adminLogin.html', error='')
def getrole(email):
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT roleId FROM users WHERE email = '" + str(email) + "'")
        roleId = cur.fetchone()[0]
    return roleId
@app.route("/Adminlogin", methods=['POST', 'GET'])
def Adminlogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if not is_valid(email, password):
            error = 'Invalid UserId / Password'
            flash("Невірний email або пароль")
            return render_template('adminLogin.html', error=error)
        if  getrole(email) == 2:
            session['email'] = email
            getLoginDetails()
            bandit = MultiArmedBandit(["collaborative", "content", "genre"], db_path=DATABASE_URI)
            bandit.load_user_weights_from_db(session['userId'])
            session['bandit_weights'] = bandit.get_weights()
            return redirect(url_for('admin'))
        else:
            error = 'Invalid role'
            flash("Акаунт не має доступу")
            return render_template('adminLogin.html', error=error)
@app.route("/Adminregister", methods=['GET', 'POST'])
def Adminregister():
    if request.method == 'POST':
        password = request.form['password']
        email = str(request.form['email'])
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        phone = request.form['phone']
        if checkUser(email):
            flash("Користувач з таким email вже існує")
            return render_template("Adminregister.html")
        else:
            with sqlite3.connect(DATABASE_URI) as con:
                # try:
                    cur = con.cursor()
                    cur.execute(
                        'INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city,  phone, roleId, collaborative_weight, content_weight, genre_weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (
                        hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode,
                        city, phone, 2,0.33,0.33,0.33))

                    con.commit()
                # except:
                #     con.rollback()
            con.close()
            return render_template("adminLogin.html")
@app.route("/AdminregisterationForm")
def AdminregistrationForm():
    return render_template("Adminregister.html")
@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    user_id = session['userId']
    with sqlite3.connect(DATABASE_URI) as con:
        cur = con.cursor()
        cur.execute("""
              SELECT b.id, b.title, b.author, b.price, b.cover_url
              FROM books b
              JOIN orders o ON b.id = o.productId
              WHERE o.userId = ?
              ORDER BY o.orderId DESC
              LIMIT 5
           """, (user_id,))
        recent_books = cur.fetchall()
    return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, recent_books=recent_books)
@app.route("/api/all-books", methods=["GET"])
def all_purchased_books():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    user_id = session['userId']
    with sqlite3.connect(DATABASE_URI) as con:
        cur = con.cursor()
        cur.execute("""
        SELECT b.id, b.title, b.author, b.price, b.cover_url
        FROM books b
        JOIN orders o ON b.id = o.productId
        WHERE o.userId = ?
        ORDER BY o.orderId DESC
    """, (user_id,))
        all_books = cur.fetchall()
    return jsonify(all_books)
@app.route("/account/profile/edit")
def editProfile():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT userId, email, firstName, lastName, address1, address2, zipcode, city,  phone FROM users WHERE email = '" +
            session['email'] + "'")
        profileData = cur.fetchone()
    conn.close()
    return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName,
                           noOfItems=noOfItems)
@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        with sqlite3.connect(DATABASE_URI) as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId, password FROM users WHERE email = '" + session['email'] + "'")
            userId, password = cur.fetchone()
            if (password == oldPassword):
                try:
                    cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
                    conn.commit()
                    msg = "Changed successfully"
                except:
                    conn.rollback()
                    msg = "Failed"
                return render_template("ProfileHome.html", msg=msg)
            else:
                msg = "Wrong password"
                flash("Невірний пароль")
        conn.close()
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")
@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        phone = request.form['phone']
        with sqlite3.connect(DATABASE_URI) as con:
            try:
                cur = con.cursor()
                cur.execute(
                    'UPDATE users SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?,  phone = ? WHERE email = ?',
                    (firstName, lastName, address1, address2, zipcode, city, phone, email))
                con.commit()
            except:
                con.rollback()
        con.close()
        return redirect(url_for('profileHome'))
@app.route("/loginForm", methods=['GET', 'POST'])
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')
@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if is_valid(email, password):
            session['email'] = email
            getLoginDetails()
            bandit = MultiArmedBandit(["collaborative", "content", "genre"], db_path=DATABASE_URI)
            bandit.load_user_weights_from_db(session['userId'])
            session['bandit_weights'] = bandit.get_weights()
            return redirect(url_for('root'))
        else:
            error = 'Invalid UserId / Password'
            flash("Невірний email або пароль")
            return render_template('login.html', error=error)
@app.route("/description")
def description():
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("storeDescription.html", loggedIn=loggedIn, firstName=firstName,
                           noOfItems=noOfItems)
@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    if 'email' in session:
        if session['recommendation_sources'].get(str(productId)):
            user_id = session.get('userId')
            recommendation_type = session['recommendation_sources'][str(productId)]
        # Логирование просмотра страницы продукта
            log_event(user_id=user_id, event_type="click", event_data=str(productId), recommendation_type=recommendation_type)
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, title, price, description, cover_url, rating, author   FROM books WHERE id = ' + productId)
        productData = cur.fetchone()
    conn.close()
    if 'email' in session:
        email = session['email']
        with sqlite3.connect(DATABASE_URI) as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
            userId = cur.fetchone()[0]
            cur.execute("SELECT rating FROM user_ratings WHERE user_id=? AND book_id=?", (userId, productId))
            user_rating = cur.fetchone()
            if user_rating:
                productData +=(user_rating[0],)
            else:
                productData +=(0,)
    else:
        productData +=(0,)
    genres=get_genres_by_book_index(productId)
    return render_template("productDescription.html", data=productData, loggedIn=loggedIn, firstName=firstName,
                           noOfItems=noOfItems,genres=genres)
@app.route('/addToCart', methods=['POST'])
def add_to_cart():
    if 'email' not in session:
        return jsonify({'redirect': url_for('loginForm')})
    else:
            productId = request.form['product_id']
            with sqlite3.connect(DATABASE_URI) as conn:
                cur = conn.cursor()
                cur.execute("SELECT userId FROM users WHERE email = '" + session['email'] + "'")
                userId = cur.fetchone()[0]
                try:
                    cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                    conn.commit()
                except:
                    conn.rollback()
            conn.close()
            response = {'status': 'success', 'message': 'Товар успішно дододано до кошика'}
            return jsonify(response)
@app.route('/cart_data', methods=['GET'])
def get_cart_data():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
    conn = sqlite3.connect(DATABASE_URI)
    cur = conn.cursor()
    cur.execute(
                "SELECT books.id, books.title, books.price FROM books, kart  WHERE books.id = kart.productId AND kart.userId = " + str(
                    userId))
    cart_items = cur.fetchall()
    total_price=0
    total_price = sum(item[2] for item in cart_items)
    items = [{'id': item[0],'name': item[1], 'price': item[2]} for item in cart_items]
    conn.close()
    return jsonify({'items': items, 'totalPrice': round(total_price,2)})
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    item_id = request.json['id']
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        try:
            cur.execute("DELETE FROM kart WHERE rowid IN (SELECT rowid FROM kart WHERE userId = ? AND productId = ? LIMIT 1)", (userId, item_id))
            conn.commit()
        except:
            conn.rollback()
    conn.close()
    return jsonify({'message': 'Товар успішно видалео з кошика.'})
@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    productId = int(request.args.get('productId'))
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        try:
            cur.execute("DELETE FROM kart WHERE userId = " + str(userId) + " AND productId = " + str(productId))
            conn.commit()
        except:
            conn.rollback()
    conn.close()
    return redirect(url_for('cart'))
@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))
def is_valid(email, password):
    con = sqlite3.connect(DATABASE_URI)
    cur = con.cursor()
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False
@app.route("/checkout", methods=['GET', 'POST'])
def payment():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        cur.execute(
            "SELECT books.id, books.title, books.price, books.cover_url FROM books, kart WHERE books.id = kart.productId AND kart.userId = " + str(
                userId))
        products = cur.fetchall()
    totalPrice = 0
    cur.execute("SELECT MAX(orderId) FROM Orders WHERE userId = ?", (userId,))
    last_order_id = cur.fetchone()[0]
    new_order_id = (last_order_id or 0) + 1
    order_items = []
    bandit_weights = session.get('bandit_weights')

    if bandit_weights:
        bandit = MultiArmedBandit(["collaborative", "content", "genre"], db_path=DATABASE_URI)

        # Загружаем текущее состояние счетчиков и значений из базы данных
        bandit.load_user_weights_from_db(userId)
    for row in products:
        totalPrice += row[2]
        book_id = row[0]
        if str(book_id) in session.get('recommendation_sources', {}):
            recommendation_type = session['recommendation_sources'][str(book_id)]
            log_event(userId, "purchase", str(book_id), recommendation_type)
            bandit.update(recommendation_type, 1.0)  # Награда за успешную покупку
        order_items.append((userId, row[0], new_order_id))
    cur.executemany("INSERT INTO Orders (userId, productId, orderId) VALUES (?, ?, ?)", order_items)
    cur.execute("DELETE FROM kart WHERE userId = " + str(userId))
    conn.commit()
    session['bandit_weights'] = bandit.get_weights()
    # Сохраняем обновленные веса в базе данных
    bandit.update_and_save_weights(userId)
    session['payd']=True
    return render_template("checkout.html", products=products, totalPrice=totalPrice, loggedIn=loggedIn,
                           firstName=firstName, noOfItems=noOfItems)
@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    if 'email' not in session:
        return jsonify(status="not_logged_in")
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
    book_id = request.form.get('book_id')
    rating = request.form.get('rating')
    user_id = session['userId']  # Отримайте ID поточного користувача
    cur.execute("SELECT rating FROM user_ratings WHERE user_id=? AND book_id=?", (user_id, book_id))
    existing_rating = cur.fetchone()
    if existing_rating:
        cur.execute("UPDATE user_ratings SET rating=? WHERE user_id=? AND book_id=?", (rating, user_id, book_id))
    else:
        cur.execute("INSERT INTO user_ratings (user_id, book_id, rating) VALUES (?, ?, ?)", (user_id, book_id, rating))
    cur.execute("SELECT AVG(rating) FROM user_ratings WHERE book_id=?", (book_id,))
    avg_rating = cur.fetchone()[0]
    cur.execute("UPDATE books SET rating=? WHERE id=?", (round(avg_rating,2), book_id))
    conn.commit()
    return jsonify(message="Rating updated successfully!")
def checkUser(email):
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT email  FROM users  WHERE users.email='" + email + "'")
        data = cursor.fetchall()
    if len(data)>0:
        return True
    return False
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Parse form data
        password = request.form['password']
        email = str(request.form['email'])
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        phone = request.form['phone']
        if checkUser(email):
            flash("Користувач з таким email вже існує")
            return render_template("register.html")
        else:
            with sqlite3.connect(DATABASE_URI) as con:
                #try:
                    cur = con.cursor()
                    cur.execute(
                        'INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, phone, roleId, collaborative_weight, content_weight, genre_weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?)',
                        (
                        hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode,
                        city,  phone, 1, 0.33, 0.33, 0.33))
                    con.commit()
                    msg = "Registered Successfully"
            con.close()
            return render_template("login.html", error=msg)
@app.route("/registerationForm")
def registrationForm():
    return render_template("register.html")
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(7):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans
@app.route('/handle_data', methods=['GET', 'POST'])
def search():
    data=[]
    loggedIn, firstName, noOfItems = getLoginDetails()
    if request.method == 'POST':
        found = str(request.form['query'])
    else:  # Если метод GET
        found = request.args.get('query')
    if len(found)<2:
        return render_template('search.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        cursor.execute("""
                SELECT DISTINCT b.id, b.title, b.price, b.author, b.cover_url, b.rating
                FROM books b
                LEFT JOIN book_genre_relations bg ON b.id = bg.book_id
                LEFT JOIN genres g ON bg.genre_id = g.id
                WHERE LOWER(b.title) LIKE ? OR LOWER(g.genre_name) LIKE ? OR LOWER(b.author) LIKE ?
                """, ('%' + found + '%', '%' + found + '%', '%' + found + '%'))
        data = cursor.fetchall()
    conn.close()
    flattened_books = [book for sublist in data for book in sublist]
    return render_template('search.html', found=found, itemData=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)
def get_genres_by_book_index(book_index):
    conn = sqlite3.connect(DATABASE_URI)
    cursor = conn.cursor()
    query = """
    SELECT g.genre_name
    FROM genres g
    JOIN book_genre_relations bg ON g.id = bg.genre_id
    WHERE bg.book_id = ?
    """
    cursor.execute(query, (book_index,))
    genres = cursor.fetchall()
    conn.close()
    return [genre[0] for genre in genres]
@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")
def get_all_genres():
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM genres;")
        genres = cur.fetchall()
        genres = [{'id': row[0], 'name': row[1]} for row in genres]
    return genres
def get_all_books():
    with sqlite3.connect(DATABASE_URI)  as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM books;")
        book_rows = cur.fetchall()
        # Преобразуем список кортежей в список словарей для удобного доступа по ключам
        books = [{
            'id': row[0],
            'name': row[1],
            'author': row[2],
            'description': row[3],
            'price': row[4],
            'rating': row[5],
            'cover_url': row[6]
        } for row in book_rows]
    return books
def add_book(title, author, description, price, cover_url, genres):
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO books (title, author, description, price, rating, cover_url)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (title, author, description, price, 0, cover_url))
        book_id = cur.lastrowid  # Получаем ID новой книги
        for genre_id in genres:
            cur.execute("""
                       INSERT INTO book_genre_relations (book_id, genre_id)
                       VALUES (?, ?);
                   """, (book_id, genre_id))
        conn.commit()
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    else:
        pie_chart_script, pie_chart_div = create_strategy_pie_chart(DATABASE_URI)
        bar_chart_script, bar_chart_div = create_conversion_bar_chart(DATABASE_URI)
        ctr_chart_script,ctr_chart_div =plot_ctr_by_recommendation_type(DATABASE_URI)
        js_resources = CDN.render_js()
        css_resources = CDN.render_css()
        name= getLoginDetails()[1]
        genres = get_all_genres()
        books = get_all_books()
        with sqlite3.connect(DATABASE_URI) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as count FROM users")
            countusers = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) as count FROM orders")
            countorders = cur.fetchone()[0]
            if request.method == 'POST':
                if 'add_product' in request.form:
                    genre_ids = request.form.getlist('genre')  # это список, так как <select> с multiple
                    title = request.form['title']
                    author = request.form['author']
                    description = request.form['description']
                    price = request.form['price']
                    cover_url = request.form['cover_url']
                    if not title or not author or not price or not description or not cover_url or not  genre_ids:
                        flash('Необхідно заповнити всі поля!')
                        return redirect(url_for('admin')+ '#add-product')
                    add_book(title, author,description,price,cover_url,genre_ids)
                    flash('Товар успішно додано!')
                    return redirect(url_for('admin')+ '#add-product')
                return redirect(url_for('admin'))
            return render_template('admin.html', name=name,user_count=countusers, order_count=countorders, genres=genres, books=books,
                           pie_chart_script=pie_chart_script,
                           pie_chart_div=pie_chart_div,
                           bar_chart_script=bar_chart_script,
                           bar_chart_div=bar_chart_div,
                                   js_resources=js_resources, css_resources=css_resources,ctr_chart_script=ctr_chart_script,ctr_chart_div=ctr_chart_div)
@app.route('/add_genre', methods=['POST'])
def add_genre():
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    if request.method == 'POST':
        genre_name = request.form['name']
        with sqlite3.connect(DATABASE_URI) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO genres (genre_name) VALUES (?)", (genre_name,))
            conn.commit()
        flash('Жанр успішно додано!')
        return redirect(url_for('admin')+ '#genres')
@app.route('/edit_genre/<int:genre_id>', methods=['GET', 'POST'])
def edit_genre(genre_id):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    if request.method == 'POST':
        new_genre_name = request.form['name']
        conn = sqlite3.connect(DATABASE_URI)
        cursor = conn.cursor()
        cursor.execute('UPDATE genres SET genre_name = ? WHERE id = ?', (new_genre_name, genre_id))
        conn.commit()
        conn.close()
        flash('Жанр успішно оновлено!')
    return redirect(url_for('admin')+ '#genres')
@app.route('/delete_genre/<int:genre_id>', methods=['POST'])
def delete_genre(genre_id):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM book_genre_relations WHERE genre_id = ?", (genre_id,))
        cursor.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
        conn.commit()
    flash('Жанр успішно видалено!')
    return redirect(url_for('admin')+ '#genres')
@app.route('/get-all-genres')
def get():
    genres = get_all_genres()
    return jsonify(genres)
@app.route('/get_product_data/<int:product_id>')
def get_product_data(product_id):
    product = get_product_by_id(product_id)
    return jsonify(product)
def get_product_by_id(product_id):
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM books WHERE id = ?;", (product_id,))
        book_data = cur.fetchone()
        if book_data:
            book = {
                'id': book_data[0],
                'title': book_data[1],
                'author': book_data[2],
                'description': book_data[3],
                'price': book_data[4],
                'rating': book_data[5],
                'image_url': book_data[6],
                'genre_ids': []}
            cur.execute("SELECT genre_id FROM book_genre_relations WHERE book_id = ?;", (product_id,))
            book['genre_ids'] = [genre_id[0] for genre_id in cur.fetchall()]
            return book
        else:
            return None  # Если книги с таким ID нет, возвращаем None
@app.route('/edit_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    title = request.form.get('title')
    author = request.form.get('author')
    description = request.form.get('description')
    price = request.form.get('price')
    image_url = request.form.get('image_url')
    update_product(product_id, title, author, description, price, image_url)
    success = True  # Предположим, что операция прошла успешно
    if success:
        flash('Книгу успішно оновлено!')
        return redirect(url_for('admin')+ '#edit-products')
    else:
        flash('Виникла помилка!', error_message)
        return jsonify({'message': 'Failed to update product'}), 500
@app.route('/delete-book/<int:book_id>', methods=['POST'])
def delete_product(book_id):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM book_genre_relations WHERE book_id = ?;", (book_id,))
        # Удаляем оценки, связанные с книгой
        cur.execute("DELETE FROM user_ratings WHERE book_id = ?;", (book_id,))
        # Удаляем записи из корзины или заказов, связанные с книгой
        cur.execute("DELETE FROM kart WHERE productId = ?;", (book_id,))
        cur.execute("DELETE FROM orders WHERE productId = ?;", (book_id,))
        # Удаляем книгу
        cur.execute("DELETE FROM books WHERE id = ?;", (book_id,))
    success = True  # Предположим, что операция прошла успешно
    if success:
        flash('Книгу успішно видалено!')
        return jsonify({'message': 'Book removed successfully'}), 200
    else:
        flash('Виникла помилка при видаленні книги!')
        return jsonify({'message': 'Failed to remove book'}), 500
@app.route('/add-genre-to-product/<int:product_id>/<int:genre_id>', methods=['POST'])
def add_genre_to_product(product_id, genre_id):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    # Здесь должна быть логика добавления жанра к товару в базе данных
    with sqlite3.connect(DATABASE_URI) as conn:
     cursor = conn.cursor()
     cursor.execute("INSERT INTO book_genre_relations (book_id, genre_id) VALUES (?, ?)", (product_id, genre_id))
     conn.commit()
    success = True  # Предположим, что операция прошла успешно
    if success:
        flash('Жанр додано до книги!')
        return jsonify({'message': 'Genre added successfully'}), 200
    else:
        flash('Виникла помилка при додаванні жанру  до книги!')
        return jsonify({'message': 'Failed to add genre'}), 500
@app.route('/remove-genre-from-product/<int:product_id>/<int:genre_id>', methods=['POST'])
def remove_genre_from_product(product_id, genre_id):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
      cursor = conn.cursor()
      cursor.execute("DELETE FROM book_genre_relations WHERE book_id = ? AND genre_id = ?", (product_id, genre_id))
      conn.commit()
    success = True  # Предположим, что операция прошла успешно
    if success:
        flash('Жанр видалено з книги!')
        return jsonify({'message': 'Genre removed successfully'}), 200
    else:
        flash('Виникла помилка при додаванні жанру  з книги!')
        return jsonify({'message': 'Failed to remove genre'}), 500
def update_product(book_id, title, author, description, price, cover_url):
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        fields_to_update = {}
        if title is not None:
            fields_to_update['title'] = title
        if author is not None:
            fields_to_update['author'] = author
        if description is not None:
            fields_to_update['description'] = description
        if price is not None:
            fields_to_update['price'] = price
        if cover_url is not None:
            fields_to_update['cover_url'] = cover_url
        update_query = "UPDATE books SET " + ", ".join([f"{k} = ?" for k in fields_to_update.keys()]) + " WHERE id = ?"
        cursor.execute(update_query, list(fields_to_update.values()) + [book_id])
        conn.commit()

def log_event(user_id, event_type, event_data, recommendation_type):
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO event_logs (user_id, event_type, event_data, recommendation_type) 
            VALUES (?, ?, ?, ?);
        """, (user_id, event_type, event_data, recommendation_type))
        conn.commit()
if __name__ == '__main__':
    app.run(debug=True)