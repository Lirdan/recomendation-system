from flask import *
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from numpy import*
from recommender import*
import os
app = Flask(__name__)
app.secret_key = 'random string'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URI = os.path.join(BASE_DIR, 'books_db.sqlite')
from bandit import MultiArmedBandit
from  data_visualization import*
from bokeh.resources import CDN
def getLoginDetails():
    """
    Get current session login status and user metadata.

    Returns:
        tuple: (loggedIn, firstName, noOfItems) where:
            - loggedIn (bool): True if user is authenticated
            - firstName (str): First name of the user ('' if not logged in)
            - noOfItems (int): Number of items currently in the user's cart (0 if not logged in)
    """
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        # If no session email, treat as guest
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            # Fetch user ID and name
            cur.execute("SELECT userId, firstName FROM users WHERE email = '" + session['email'] + "'")
            userId, firstName = cur.fetchone()
            session['userId'] = userId
            # Count number of items in cart
            cur.execute("SELECT count(productId) FROM kart WHERE userId = " + str(userId))
            noOfItems = cur.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)

@app.route("/")
def root():
    """
    Main page of the bookstore with personalized or random recommendations.

    Returns:
        Rendered HTML template of the homepage with:
        - Recommended books (based on login status)
        - Random high-rated books from a random genre
        - Session-based tracking of recommendation source for logging

    Behavior:
        - If the user is not logged in, show random high-rated books
        - If logged in, show hybrid recommendations using bandit weights
        - Truncates long titles and avoids duplicate books
    """
    # Session + header info
    loggedIn, firstName, noOfItems = getLoginDetails()
    # Get random high-rated books by random genre
    genre_recomendations, genre_name = generate_random_genre_recommendations(DATABASE_URI)
    # Truncate titles in genre recommendations (if too long)
    for i in range(len(genre_recomendations)):
        genre_recomendations[i] = truncate_title_in_tuple(genre_recomendations[i])
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        itemData1 = []
        if not loggedIn:
                # Anonymous user → random popular books
                itemData = generate_recommendations_for_new_user(DATABASE_URI)
                book_ids = [item['book_id'] for item in itemData]
                # Load full book data by IDs
                for i in book_ids:
                    cur.execute('SELECT id, title, price, author, cover_url, rating FROM books WHERE id =' + str(i))
                    itemData1.append(cur.fetchall())
                # Flatten nested result
                flattened_books = [book for sublist in itemData1 for book in sublist]
                books = [(id, title, price, author, url, round(rating)) for (id, title, price, author, url, rating) in
                         flattened_books]
                 # Final structure for display
                return render_template('index.html', loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems,
                                       itemData=books, genre_recomendations=genre_recomendations, genre_name=genre_name
                                       )
        else:
            # Logged-in user → use hybrid recommender with bandit weights
            bandit_weights = session.get('bandit_weights', {})
            itemData = hybrid_recommendation_system(
            DATABASE_URI, session['userId'],w1=bandit_weights.get('collaborative'), w2=bandit_weights.get('content'), lambda_val=bandit_weights.get('genre'))
            # Fallback: if no recommendations, use random fallback
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
            # Log “view” events and build unique list
            recommendation_sources = {}
            for i in itemData:
                recommendation_sources[i['book_id']] = i['source']
                log_event(user_id=session['userId'], event_type="view", event_data=str(i['book_id']),recommendation_type=i['source'])
                # Fetch book row and truncate title if needed
                cur.execute('SELECT id, title, price, author, cover_url, rating FROM books WHERE id ='+str(i['book_id']))
                data=cur.fetchall()
                if len(data[0][1])<35:
                    itemData1.append(data)
                else:
                    data[0]=truncate_title_in_tuple(data[0])
                    itemData1.append(data)
            # Save sources in session for later use (click, purchase)
            session['recommendation_sources'] = recommendation_sources
            # Deduplicate final book list
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
    """
    Shortens long book titles to a maximum of 35 characters.

    Parameters:
        a_tuple (tuple): Book data tuple (id, title, ...)

    Returns:
        tuple: Updated tuple with the truncated title if it exceeds 35 characters.
    """
    title = a_tuple[1]
    # If the title is too long, truncate and append ellipsis
    if len(title) > 35:
        title = title[:35]+'...'
    # Rebuild the tuple with updated title
    new_tuple = (a_tuple[0], title) + a_tuple[2:]
    return new_tuple

@app.route("/add")
def addForm():
    """
    Displays the form for adding a new product.

    Returns:
        Rendered HTML template for product addition.
    """
   return render_template('add.html')

@app.route("/AdminloginForm")
def AdminloginForm():
    """
    Displays the admin login form.

    Returns:
        - Redirects to admin panel if already logged in.
        - Otherwise renders the admin login template.
    """
    if 'email' in session:
        # If already logged in, redirect to admin dashboard
        return redirect(url_for('admin'))
    else:
        return render_template('adminLogin.html', error='')
def getrole(email):
    """
    Retrieves the role ID associated with a user email.

    Parameters:
        email (str): User's email address.

    Returns:
        int: Role ID of the user (e.g., 1 = regular user, 2 = admin)
    """
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT roleId FROM users WHERE email = '" + str(email) + "'")
        roleId = cur.fetchone()[0]
    return roleId

@app.route("/Adminlogin", methods=['POST', 'GET'])
def Adminlogin():
    """
    Handles admin login requests.

    - Validates credentials
    - Checks admin role (roleId == 2)
    - Initializes bandit weights for the session

    Returns:
        - Redirects to admin dashboard on success
        - Renders login form with error on failure
    """
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Validate email and password
        if not is_valid(email, password):
            error = 'Invalid UserId / Password'
            flash("Невірний email або пароль")
            return render_template('adminLogin.html', error=error)
        # Check if user is an admin
        if  getrole(email) == 2:
            session['email'] = email
            getLoginDetails()
            # Load bandit weights from DB and save to session
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
    """
    Handles registration of a new admin user.

    - Validates form data
    - Checks for existing user by email
    - Creates new user with roleId = 2 (admin)
    - Initializes equal bandit weights

    Returns:
        - Renders the registration form again if the user already exists
        - Redirects to the admin login page upon successful registration
    """
    if request.method == 'POST':
        # Collect form data
        password = request.form['password']
        email = str(request.form['email'])
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        phone = request.form['phone']
        # Check if user with this email already exists
        if checkUser(email):
            flash("Користувач з таким email вже існує")
            return render_template("Adminregister.html")
        else:
              # Insert new admin user into the database
            with sqlite3.connect(DATABASE_URI) as con:
                try:
                    cur = con.cursor()
                    cur.execute(
                        'INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city,  phone, roleId, collaborative_weight, content_weight, genre_weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (
                        hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode,
                        city, phone, 2,0.33,0.33,0.33))  # default bandit weights

                    con.commit()
                except:
                     con.rollback()
            con.close()
            return render_template("adminLogin.html")

@app.route("/AdminregisterationForm")
def AdminregistrationForm():
    """
    Renders the admin registration form page.

    Returns:
        Rendered HTML template for admin registration.
    """
    return render_template("Adminregister.html")

@app.route("/account/profile")
def profileHome():
    """
    Displays the profile home page for the logged-in user.

    - Shows the 5 most recent books purchased by the user
    - Redirects to the homepage if user is not logged in

    Returns:
        Rendered HTML template with recent purchase history
    """
    if 'email' not in session:
        # Redirect guest to main page
        return redirect(url_for('root'))
    # Get basic user info from session
    loggedIn, firstName, noOfItems = getLoginDetails()
    user_id = session['userId']
    # Fetch 5 latest purchases
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
    """
    API endpoint that returns all books purchased by the logged-in user.

    - Requires user to be authenticated
    - Fetches full purchase history from database

    Returns:
        JSON: List of purchased books with ID, title, author, price, and cover URL
    """
    if 'email' not in session:
        # Redirect to homepage if user not logged in
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    user_id = session['userId']
    # Fetch purchase history
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
"""
    Renders the form to edit the current user's profile data.

    - Requires user to be logged in
    - Pre-fills the form with existing profile information

    Returns:
        Rendered HTML form for editing user profile
    """
    if 'email' not in session:
        # Redirect guest users to the homepage
        return redirect(url_for('root'))
    # Get session and cart info
    loggedIn, firstName, noOfItems = getLoginDetails()
     # Fetch user data from the database
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
    """
    Allows logged-in users to change their password.

    - GET: Displays password change form
    - POST: Validates old password, updates it if correct

    Returns:
        Rendered HTML template with success or error message
    """
    if 'email' not in session:    
        # Only available for logged-in users
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        # Get old and new passwords from form and Hash them using MD5
        oldPassword = request.form['oldpassword']
        oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        # Check and update password in DB
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
        # Show password change form
        return render_template("changePassword.html")
        
@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
     """
    Updates the user's profile information based on submitted form data.

    - Only available to logged-in users
    - Updates basic contact and address information

    Returns:
        Redirects to profile page after successful update
    """
    if request.method == 'POST':
        # Collect updated user profile data from the form
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        phone = request.form['phone']
        # Update user information in the database
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
    """
    Displays the login form for regular users.

    - If the user is already logged in, redirects to the homepage

    Returns:
        Rendered login form template or redirect
    """
    if 'email' in session:
        # User already authenticated
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')
        
@app.route("/login", methods=['POST', 'GET'])
def login():
    """
    Handles login for regular users.

    - Validates email and password
    - Loads bandit weights for personalized recommendations
    - Sets session variables

    Returns:
        Redirects to homepage on success,
        or re-renders login form with error message
    """
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Validate credentials
        if is_valid(email, password):
            session['email'] = email
            getLoginDetails()
            # Initialize and load bandit weights for this user
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
     """
    Renders the static page with information about the bookstore or platform.

    Returns:
        Rendered HTML template with current session context.
    """
    # Get login status and basic user/cart info
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("storeDescription.html", loggedIn=loggedIn, firstName=firstName,
                           noOfItems=noOfItems)

@app.route("/productDescription")
def productDescription():
     """
    Displays detailed information for a selected product.

    - Loads book metadata including title, price, description, rating, author, and genres
    - Checks if the user has rated the book before
    - Logs click events if the book was recommended by the system

    Returns:
        Rendered HTML template with book details and current session context.
    """
    # Get session and cart info
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    # If the user clicked on a recommendation, log the click
    if 'email' in session:
        if session['recommendation_sources'].get(str(productId)):
            user_id = session.get('userId')
            recommendation_type = session['recommendation_sources'][str(productId)]
            # Logging the product page view
            log_event(user_id=user_id, event_type="click", event_data=str(productId), recommendation_type=recommendation_type)
    # Get product details from database
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, title, price, description, cover_url, rating, author   FROM books WHERE id = ' + productId)
        productData = cur.fetchone()
    conn.close()
    # If logged in, fetch personal rating of the product (if exists)
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
                # Default rating = 0 for guests
                productData +=(0,)
    else:
        productData +=(0,)
    # Get list of genres for this book
    genres=get_genres_by_book_index(productId)
    return render_template("productDescription.html", data=productData, loggedIn=loggedIn, firstName=firstName,
                           noOfItems=noOfItems,genres=genres)

@app.route('/addToCart', methods=['POST'])
def add_to_cart():
    """
    Adds a selected product to the current user's cart.

    - Requires user to be logged in
    - Stores product in 'kart' table

    Returns:
        JSON response with success message or redirect if not logged in
    """
    # If not logged in, redirect to login form
    if 'email' not in session:
        return jsonify({'redirect': url_for('loginForm')})
    else:
            # Get product ID from form
            productId = request.form['product_id']
            with sqlite3.connect(DATABASE_URI) as conn:
                cur = conn.cursor()
                cur.execute("SELECT userId FROM users WHERE email = '" + session['email'] + "'")
                userId = cur.fetchone()[0]
                try:
                    # Insert product into cart (kart table)
                    cur.execute("INSERT INTO kart (userId, productId) VALUES (?, ?)", (userId, productId))
                    conn.commit()
                except:
                    conn.rollback()
            conn.close()
            response = {'status': 'success', 'message': 'Товар успішно дододано до кошика'}
            return jsonify(response)

@app.route('/cart_data', methods=['GET'])
def get_cart_data():
     """
    Retrieves all items currently in the logged-in user's cart.

    - Requires authentication
    - Returns cart contents and total price

    Returns:
        JSON response:
            - items: list of products in the cart
            - totalPrice: total cost of all items
    """
    # Redirect guest to login form
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    # Get user and session details
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    # Get user ID
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
    # Fetch items in the user's cart
    conn = sqlite3.connect(DATABASE_URI)
    cur = conn.cursor()
    cur.execute(
                "SELECT books.id, books.title, books.price FROM books, kart  WHERE books.id = kart.productId AND kart.userId = " + str(
                    userId))
    cart_items = cur.fetchall()
    # Calculate total price
    total_price=0
    total_price = sum(item[2] for item in cart_items)
    # Format response data
    items = [{'id': item[0],'name': item[1], 'price': item[2]} for item in cart_items]
    conn.close()
    return jsonify({'items': items, 'totalPrice': round(total_price,2)})

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    """
    Removes a single occurrence of a product from the user's cart.

    - Requires user to be logged in
    - Deletes one row from 'kart' table matching product and user

    Returns:
        JSON response confirming removal
    """
    item_id = request.json['id']
    # Redirect guest users to login page
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        try:
            # Delete one row from kart (LIMIT 1 behavior via rowid)
            cur.execute("DELETE FROM kart WHERE rowid IN (SELECT rowid FROM kart WHERE userId = ? AND productId = ? LIMIT 1)", (userId, item_id))
            conn.commit()
        except:
            conn.rollback()
    conn.close()
    return jsonify({'message': 'Товар успішно видалео з кошика.'})
    
@app.route("/removeFromCart")
def removeFromCart():
    """
    Removes a product from the user's cart (via query parameter).

    - Requires user to be logged in
    - Deletes the product from the 'kart' table by userId and productId

    Note:
        Similar to /remove_from_cart but uses GET and query params.

    Returns:
        Redirects back to cart page after deletion.
    """
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
    """
    Logs the user out of the current session.

    - Removes 'email' from session
    - Redirects to the homepage

    Returns:
        Redirect to root route (main page)
    """
    # Clear the user session (log out)
    session.pop('email', None)
    return redirect(url_for('root'))
    
def is_valid(email, password):
    """
    Validates a user's login credentials.

    - Compares the provided email and MD5-hashed password
      with entries in the 'users' table

    Parameters:
        email (str): User's email
        password (str): User's raw (unhashed) password

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    con = sqlite3.connect(DATABASE_URI)
    cur = con.cursor()
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    for row in data:
        # Hash input password for comparison
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False

@app.route("/checkout", methods=['GET', 'POST'])
def payment():
    """
    Processes the checkout and confirms the user's order.

    - Requires login
    - Calculates total price
    - Logs purchases for Bandit learning
    - Clears the user's cart
    - Updates Bandit weights and saves to DB

    Returns:
        Rendered confirmation page with order details
    """
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    # Get user and cart context
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        # Get user ID
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        # Fetch all products in user's cart
        cur.execute(
            "SELECT books.id, books.title, books.price, books.cover_url FROM books, kart WHERE books.id = kart.productId AND kart.userId = " + str(
                userId))
        products = cur.fetchall()
    totalPrice = 0
    # Determine next order ID
    cur.execute("SELECT MAX(orderId) FROM Orders WHERE userId = ?", (userId,))
    last_order_id = cur.fetchone()[0]
    new_order_id = (last_order_id or 0) + 1
    order_items = []
    # Load Bandit model if available in session
    bandit_weights = session.get('bandit_weights')
    if bandit_weights:
        bandit = MultiArmedBandit(["collaborative", "content", "genre"], db_path=DATABASE_URI)
        # Loading the current status of counters and values from the database
        bandit.load_user_weights_from_db(userId)
    # Process each product in cart
    for row in products:
        totalPrice += row[2]
        book_id = row[0]

        # If book was recommended, log purchase and reward bandit
        if str(book_id) in session.get('recommendation_sources', {}):
            recommendation_type = session['recommendation_sources'][str(book_id)]
            log_event(userId, "purchase", str(book_id), recommendation_type)
            bandit.update(recommendation_type, 1.0)  # Награда за успешную покупку
        order_items.append((userId, row[0], new_order_id))
    cur.executemany("INSERT INTO Orders (userId, productId, orderId) VALUES (?, ?, ?)", order_items)
    cur.execute("DELETE FROM kart WHERE userId = " + str(userId))
    conn.commit()
    # Save updated bandit weights to session and DB
    session['bandit_weights'] = bandit.get_weights()
    # Save order and clear cart
    bandit.update_and_save_weights(userId)
    session['payd']=True
    return render_template("checkout.html", products=products, totalPrice=totalPrice, loggedIn=loggedIn,
                           firstName=firstName, noOfItems=noOfItems)
    
@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    """
    Handles book rating submission by the logged-in user.

    - Inserts or updates the rating in 'user_ratings'
    - Recalculates and updates the book's average rating

    Returns:
        JSON response indicating success or if user is not logged in
    """
    if 'email' not in session:
        return jsonify(status="not_logged_in")

    # Get basic session data
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
    book_id = request.form.get('book_id')
    rating = request.form.get('rating')
    user_id = session['userId']  
    # Check if rating already exists
    cur.execute("SELECT rating FROM user_ratings WHERE user_id=? AND book_id=?", (user_id, book_id))
    existing_rating = cur.fetchone()
    if existing_rating:
        # Update existing rating
        cur.execute("UPDATE user_ratings SET rating=? WHERE user_id=? AND book_id=?", (rating, user_id, book_id))
    else:
         # Insert new rating
        cur.execute("INSERT INTO user_ratings (user_id, book_id, rating) VALUES (?, ?, ?)", (user_id, book_id, rating))
    # Update book's average rating
    cur.execute("SELECT AVG(rating) FROM user_ratings WHERE book_id=?", (book_id,))
    avg_rating = cur.fetchone()[0]
    cur.execute("UPDATE books SET rating=? WHERE id=?", (round(avg_rating,2), book_id))
    conn.commit()
    return jsonify(message="Rating updated successfully!")

def checkUser(email):
    """
    Checks whether a user with the given email already exists.

    Parameters:
        email (str): Email address to check

    Returns:
        bool: True if user exists, False otherwise
    """
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
     """
    Handles user registration.

    - Validates form input
    - Checks for existing user with the same email
    - Creates new user with default bandit weights

    Returns:
        - On success: redirects to login page with confirmation message
        - On failure: renders registration form with error
    """
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
            # Check for existing user
            flash("Користувач з таким email вже існує")
            return render_template("register.html")
        else:
            # Insert new user with default role and bandit weights
            with sqlite3.connect(DATABASE_URI) as con:
                #try:
                    cur = con.cursor()
                    cur.execute(
                        'INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, phone, roleId, collaborative_weight, content_weight, genre_weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?)',
                        (
                        hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode,
                        city,  phone, 1, 0.33, 0.33, 0.33)) # roleId = 1 → default user
                    con.commit()
                    msg = "Registered Successfully"
            con.close()
            # Redirect to login with confirmation
            return render_template("login.html", error=msg)
            
@app.route("/registerationForm")
def registrationForm():
    """
    Displays the user registration form.

    Returns:
        Rendered HTML template for registration.
    """
    return render_template("register.html")
    
def allowed_file(filename):
     """
    Checks if the uploaded file has an allowed image extension.

    Parameters:
        filename (str): Name of the file being uploaded

    Returns:
        bool: True if file extension is allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def parse(data):
    """
    Splits a flat list of data into chunks of 7 elements each.

    This is useful for formatting product listings into rows or pages.

    Parameters:
        data (list): A flat list of items (e.g., book records)

    Returns:
        list: A list of sublists, each with up to 7 elements
    """
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
    """
    Handles search queries for books by title, author, or genre.

    - Accepts both GET and POST requests
    - Requires at least 2 characters to perform a search
    - Performs case-insensitive partial matching in the database

    Returns:
        Rendered search results page with matching books or empty state.
    """
    data=[]
    loggedIn, firstName, noOfItems = getLoginDetails()
    # Get search query from form or URL
    if request.method == 'POST':
        found = str(request.form['query'])
    else:  
        found = request.args.get('query')
    # If query too short — show empty result
    if len(found)<2:
        return render_template('search.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)
    # Search by title, genre, or author
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
    """
    Retrieves a list of genre names associated with a given book.

    Parameters:
        book_index (int): ID of the book

    Returns:
        list: List of genre names (strings) for the book
    """
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
        """
    Renders the static 'Thank You' page after checkout.

    Returns:
        Rendered HTML thank you template.
    """

    return render_template("thankyou.html")

def get_all_genres():
    """
    Fetches all available genres from the database.

    Returns:
        list: List of dictionaries containing genre ID and name.
    """
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM genres;")
        genres = cur.fetchall()
        # Convert to list of dicts for easier frontend use
        genres = [{'id': row[0], 'name': row[1]} for row in genres]
    return genres
    
def get_all_books():
    """
    Fetches all books from the database.

    Returns:
        list: List of dictionaries with detailed book information.
    """
    with sqlite3.connect(DATABASE_URI)  as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM books;")
        book_rows = cur.fetchall()
        # Convert raw rows to list of dicts for easy access
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
    """
    Adds a new book to the database along with its genre relations.

    Parameters:
        title (str): Book title
        author (str): Author's name
        description (str): Short book description
        price (float or str): Price of the book
        cover_url (str): URL to the cover image
        genres (list): List of genre IDs to associate with the book

    Returns:
        None
    """
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        # Insert new book
        cur.execute("""
            INSERT INTO books (title, author, description, price, rating, cover_url)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (title, author, description, price, 0, cover_url))
         # Get the auto-generated book ID
        book_id = cur.lastrowid 
        # Insert genre relations
        for genre_id in genres:
            cur.execute("""
                       INSERT INTO book_genre_relations (book_id, genre_id)
                       VALUES (?, ?);
                   """, (book_id, genre_id))
        conn.commit()
        
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """
    Displays the admin dashboard.

    - Requires admin login (roleId = 2)
    - Shows user/order statistics
    - Renders visualizations (pie, bar, CTR)
    - Handles adding new products

    Returns:
        Rendered admin panel template with statistics and management forms.
    """
    # Check if user is logged in and has admin rights
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    else:
        # Generate visual analytics components
        pie_chart_script, pie_chart_div = create_strategy_pie_chart(DATABASE_URI)
        bar_chart_script, bar_chart_div = create_conversion_bar_chart(DATABASE_URI)
        ctr_chart_script,ctr_chart_div =plot_ctr_by_recommendation_type(DATABASE_URI)
         # Include necessary JS and CSS for Bokeh
        js_resources = CDN.render_js()
        css_resources = CDN.render_css()
        # Get admin name for display
        name= getLoginDetails()[1]
        # Load all genres and books for management view
        genres = get_all_genres()
        books = get_all_books()
        # Load basic statistics
        with sqlite3.connect(DATABASE_URI) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as count FROM users")
            countusers = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) as count FROM orders")
            countorders = cur.fetchone()[0]
            # Handle form submission for adding a new book
            if request.method == 'POST':
                if 'add_product' in request.form:
                    genre_ids = request.form.getlist('genre') 
                    title = request.form['title']
                    author = request.form['author']
                    description = request.form['description']
                    price = request.form['price']
                    cover_url = request.form['cover_url']
                    # Check if all fields are filled
                    if not title or not author or not price or not description or not cover_url or not  genre_ids:
                        flash('Необхідно заповнити всі поля!')
                        return redirect(url_for('admin')+ '#add-product')
                    # Add new book to the database
                    add_book(title, author,description,price,cover_url,genre_ids)
                    flash('Товар успішно додано!')
                    return redirect(url_for('admin')+ '#add-product')
                return redirect(url_for('admin'))
            # Render the admin dashboard template with all context
            return render_template('admin.html', name=name,user_count=countusers, order_count=countorders, genres=genres, books=books,
                           pie_chart_script=pie_chart_script,
                           pie_chart_div=pie_chart_div,
                           bar_chart_script=bar_chart_script,
                           bar_chart_div=bar_chart_div,
                                   js_resources=js_resources, css_resources=css_resources,ctr_chart_script=ctr_chart_script,ctr_chart_div=ctr_chart_div)

@app.route('/add_genre', methods=['POST'])
def add_genre():
    """
    Adds a new genre to the database.

    - Only accessible to authenticated admin users
    - Genre name is taken from the form input

    Returns:
        Redirects back to the admin page after insertion
    """
    # Ensure user is authenticated and has admin privileges
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    if request.method == 'POST':
        genre_name = request.form['name']
        # Insert the new genre into the genres table
        with sqlite3.connect(DATABASE_URI) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO genres (genre_name) VALUES (?)", (genre_name,))
            conn.commit()
        flash('Жанр успішно додано!')
        return redirect(url_for('admin')+ '#genres')
        
@app.route('/edit_genre/<int:genre_id>', methods=['GET', 'POST'])
def edit_genre(genre_id):
    """
    Updates the name of an existing genre.

    - Only accessible to authenticated admin users
    - Updates the genre name based on form input

    Parameters:
        genre_id (int): ID of the genre to be edited

    Returns:
        Redirects back to the admin page with a flash message
    """
    # Check if user is logged in and is an admin
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    if request.method == 'POST':
        # Update the genre name in the database
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
    """
    Deletes a genre and its relations from the database.

    - Only accessible to authenticated admin users
    - Removes the genre from the genres table
    - Also removes all related book-genre associations

    Parameters:
        genre_id (int): ID of the genre to delete

    Returns:
        Redirects to admin page with a success or error message
    """
    # Ensure admin access
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        # Delete all associations between this genre and books
        cursor.execute("DELETE FROM book_genre_relations WHERE genre_id = ?", (genre_id,))
        # Delete the genre itself
        cursor.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
        conn.commit()
    flash('Жанр успішно видалено!')
    return redirect(url_for('admin')+ '#genres')

@app.route('/get-all-genres')
def get():
    """
    API endpoint that returns all genres as JSON.

    Returns:
        JSON response with all available genres in the system.
    """
    genres = get_all_genres()
    return jsonify(genres)
    
@app.route('/get_product_data/<int:product_id>')
def get_product_data(product_id):
     """
    API endpoint that returns detailed data about a specific product.

    Parameters:
        product_id (int): ID of the product (book) to retrieve

    Returns:
        JSON response with product details or None if not found.
    """
    product = get_product_by_id(product_id)
    return jsonify(product)

def get_product_by_id(product_id):
    """
    Retrieves detailed information about a book by its ID.

    - Fetches book metadata from the 'books' table
    - Also fetches related genre IDs from 'book_genre_relations'

    Parameters:
        product_id (int): ID of the book to retrieve

    Returns:
        dict or None: Dictionary with book data and genre IDs, or None if not found.
    """
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        # Fetch book info from books table
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
            # Fetch associated genre IDs
            cur.execute("SELECT genre_id FROM book_genre_relations WHERE book_id = ?;", (product_id,))
            book['genre_ids'] = [genre_id[0] for genre_id in cur.fetchall()]
            return book
        else:
            return None  # No book with this ID found
            
@app.route('/edit_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    """
    Updates the book information in the database.

    - Only accessible to admin users
    - Receives updated book fields from the form

    Parameters:
        product_id (int): ID of the book to be updated

    Returns:
        JSON response indicating success or failure
    """
    # Ensure user is authenticated and has admin role
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    # Get updated fields from form
    title = request.form.get('title')
    author = request.form.get('author')
    description = request.form.get('description')
    price = request.form.get('price')
    image_url = request.form.get('image_url')
    # Perform update
    update_product(product_id, title, author, description, price, image_url)
    success = True  # Assume success for now
    if success:
        flash('Книгу успішно оновлено!')
        return redirect(url_for('admin')+ '#edit-products')
    else:
        flash('Виникла помилка!', error_message)
        return jsonify({'message': 'Failed to update product'}), 500
        
@app.route('/delete-book/<int:book_id>', methods=['POST'])
def delete_product(book_id):
    """
    Deletes a book and all its related data from the database.

    - Removes the book from 'books' table
    - Also removes related data: genres, ratings, orders, and cart entries

    Parameters:
        book_id (int): ID of the book to delete

    Returns:
        JSON response indicating success or failure
    """
    # Ensure admin access
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('AdminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
        cur = conn.cursor()
        # Remove book-genre relationships
        cur.execute("DELETE FROM book_genre_relations WHERE book_id = ?;", (book_id,))
        # Remove all user ratings for this book
        cur.execute("DELETE FROM user_ratings WHERE book_id = ?;", (book_id,))
        # Remove book from cart
        cur.execute("DELETE FROM kart WHERE productId = ?;", (book_id,))
        # Remove orders related to the book
        cur.execute("DELETE FROM orders WHERE productId = ?;", (book_id,))
        # Finally, delete the book itself
        cur.execute("DELETE FROM books WHERE id = ?;", (book_id,))
    success = True  # Assume deletion was successful
    if success:
        flash('Книгу успішно видалено!')
        return jsonify({'message': 'Book removed successfully'}), 200
    else:
        flash('Виникла помилка при видаленні книги!')
        return jsonify({'message': 'Failed to remove book'}), 500
        
@app.route('/add-genre-to-product/<int:product_id>/<int:genre_id>', methods=['POST'])
def add_genre_to_product(product_id, genre_id):
    """
    Associates a genre with a book.

    - Admin-only access
    - Inserts a new record into the book_genre_relations table

    Parameters:
        product_id (int): ID of the book
        genre_id (int): ID of the genre to associate

    Returns:
        JSON response with success or error message
    """
    # Ensure the user is authenticated and has admin role
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    # Add genre to the book in the relationship table
    with sqlite3.connect(DATABASE_URI) as conn:
     cursor = conn.cursor()
     cursor.execute("INSERT INTO book_genre_relations (book_id, genre_id) VALUES (?, ?)", (product_id, genre_id))
     conn.commit()
    success = True  # Assume success
    if success:
        flash('Жанр додано до книги!')
        return jsonify({'message': 'Genre added successfully'}), 200
    else:
        flash('Виникла помилка при додаванні жанру  до книги!')
        return jsonify({'message': 'Failed to add genre'}), 500
        
@app.route('/remove-genre-from-product/<int:product_id>/<int:genre_id>', methods=['POST'])
def remove_genre_from_product(product_id, genre_id):
    """
    Removes an associated genre from a specific book.

    - Admin-only access
    - Deletes the genre-book link from the book_genre_relations table

    Parameters:
        product_id (int): ID of the book
        genre_id (int): ID of the genre to remove

    Returns:
        JSON response indicating success or failure
    """
    # Ensure only admins can perform this action
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    # Perform deletion of the genre relation
    with sqlite3.connect(DATABASE_URI) as conn:
      cursor = conn.cursor()
      cursor.execute("DELETE FROM book_genre_relations WHERE book_id = ? AND genre_id = ?", (product_id, genre_id))
      conn.commit()
    success = True  # Assume deletion succeeded
    if success:
        flash('Жанр видалено з книги!')
        return jsonify({'message': 'Genre removed successfully'}), 200
    else:
        flash('Виникла помилка при додаванні жанру  з книги!')
        return jsonify({'message': 'Failed to remove genre'}), 500

def update_product(book_id, title, author, description, price, cover_url):
    """
    Updates the fields of a book record in the database.

    - Only accessible to admin users
    - Dynamically updates only the fields provided (non-None)

    Parameters:
        book_id (int): ID of the book to update
        title (str): New title (or None)
        author (str): New author (or None)
        description (str): New description (or None)
        price (str): New price (or None)
        cover_url (str): New image URL (or None)
    """
    # Admin access control
    if 'email' not in session or getrole(session["email"]) != 2:
        return render_template('adminLogin.html', error='')
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        fields_to_update = {}
        # Collect only the fields that are not None
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
        # Build and execute dynamic SQL update query
        update_query = "UPDATE books SET " + ", ".join([f"{k} = ?" for k in fields_to_update.keys()]) + " WHERE id = ?"
        cursor.execute(update_query, list(fields_to_update.values()) + [book_id])
        conn.commit()

def log_event(user_id, event_type, event_data, recommendation_type):
    """
    Logs user interaction events for analysis and bandit training.

    - Stores user activity (e.g., view, click, purchase) in the event_logs table
    - Helps track recommendation performance by strategy

    Parameters:
        user_id (int): ID of the user performing the action
        event_type (str): Type of event (e.g., 'view', 'click', 'purchase')
        event_data (str): Additional data, typically book ID
        recommendation_type (str): Strategy that generated the recommendation (e.g., 'collaborative')
    """
    with sqlite3.connect(DATABASE_URI) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO event_logs (user_id, event_type, event_data, recommendation_type) 
            VALUES (?, ?, ?, ?);
        """, (user_id, event_type, event_data, recommendation_type))
        conn.commit()
if __name__ == '__main__':
    app.run(debug=True)
