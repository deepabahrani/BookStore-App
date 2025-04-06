from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/bookstore'
app.permanent_session_lifetime = timedelta(days=7)

mongo = PyMongo(app)

# ---------------- Authentication Routes ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'username': request.form['username']})

        if existing_user is None:
            hashpass = generate_password_hash(request.form['password'])
            users.insert_one({'username': request.form['username'], 'password': hashpass})
            session['username'] = request.form['username']
            return redirect(url_for('dashboard'))
        flash('Username already exists!')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        user = users.find_one({'username': request.form['username']})

        if user and check_password_hash(user['password'], request.form['password']):
            session['username'] = request.form['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username/password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# ---------------- Dashboard ------------------
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        selected_genre = request.args.get('genre')
        if selected_genre and selected_genre != 'All':
            books = list(mongo.db.books.find({'genre': {'$regex': f'^{selected_genre}$', '$options': 'i'}}))
        else:
            books = list(mongo.db.books.find())

        genres_cursor = mongo.db.books.find({}, {'genre': 1})
        genres = sorted(set(book.get('genre', '').strip().capitalize() for book in genres_cursor if 'genre' in book))
        return render_template('dashboard.html', books=books, genres=genres, selected_genre=selected_genre)
    return redirect(url_for('login'))

# ---------------- Book CRUD ------------------
@app.route('/book/add', methods=['GET', 'POST'])
def add_book():
    if 'username' in session:
        if request.method == 'POST':
            books = mongo.db.books
            books.insert_one({
                'title': request.form['title'],
                'author': request.form['author'],
                'genre': request.form['genre'].strip().capitalize(),
                'description': request.form['description'],
                'price': float(request.form['price'])
            })
            return redirect(url_for('dashboard'))
        return render_template('add_book.html')
    return redirect(url_for('login'))

@app.route('/book/edit/<book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'username' in session:
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
        if request.method == 'POST':
            mongo.db.books.update_one({'_id': ObjectId(book_id)}, {'$set': {
                'title': request.form['title'],
                'author': request.form['author'],
                'genre': request.form['genre'].strip().capitalize(),
                'description': request.form['description'],
                'price': float(request.form['price'])
            }})
            return redirect(url_for('dashboard'))
        return render_template('edit_book.html', book=book)
    return redirect(url_for('login'))

@app.route('/book/delete/<book_id>')
def delete_book(book_id):
    if 'username' in session:
        mongo.db.books.delete_one({'_id': ObjectId(book_id)})
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ---------------- Cart ------------------
@app.route('/cart')
def view_cart():
    if 'username' in session:
        cart = mongo.db.carts.find_one({'username': session['username']})
        return render_template('cart.html', cart=cart or {'books': []})
    return redirect(url_for('login'))

@app.route('/cart/add/<book_id>')
def add_to_cart(book_id):
    if 'username' in session:
        book = mongo.db.books.find_one({'_id': ObjectId(book_id)})
        cart = mongo.db.carts.find_one({'username': session['username']})

        if not cart:
            mongo.db.carts.insert_one({'username': session['username'], 'books': [book]})
        else:
            if not any(str(b['_id']) == str(book['_id']) for b in cart['books']):
                mongo.db.carts.update_one({'username': session['username']}, {'$push': {'books': book}})
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/cart/remove/<book_id>')
def remove_from_cart(book_id):
    if 'username' in session:
        mongo.db.carts.update_one(
            {'username': session['username']},
            {'$pull': {'books': {'_id': ObjectId(book_id)}}}
        )
        return redirect(url_for('view_cart'))
    return redirect(url_for('login'))

# ---------------- Genre Filtering ------------------
@app.route('/genre/<genre_name>')
def filter_by_genre(genre_name):
    return redirect(url_for('dashboard', genre=genre_name))

if __name__ == '__main__':
    app.run(debug=True)
