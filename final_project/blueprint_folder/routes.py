from flask import render_template, request, redirect, url_for, session, make_response, current_app, jsonify
from flask_mysqldb import MySQL # type: ignore
from . import auth_bp
import MySQLdb.cursors 
import re
from datetime import datetime
import traceback
from functools import wraps
from flask import flash, abort

def validate_name(name):
    if not name:
        return "Name is required"
  
    name = ' '.join(name.split())
  
    if len(name) < 2:
        return "Name must be at least 2 characters long"
    
    if not re.match(r"^[A-Za-z\s.]+$", name):
        return "Name can only contain letters, spaces, and dots"
    

    if not any(c.isalpha() for c in name):
        return "Name must contain at least one letter"
    
    if '..' in name or '  ' in name:
        return "Name cannot contain consecutive dots or spaces"
    
    words = name.split()
    for word in words:
        if word.endswith('.'):
            if len(word) != 2 or not word[0].isupper():
                return "Initials must be a single capital letter followed by a dot"
            continue
            
        if len(word) < 2:
            return "Each word must be at least 2 letters long (except initials)"
        if not word[0].isupper():
            return "Each word must start with a capital letter"
        if not word[1:].islower():
            return "Only the first letter of each word should be capitalized"
        if len(word) > 20:
            return "Each word must be less than 20 characters"
    
    common_patterns = ['asd', 'qwe', 'zxc', 'dfg', 'jkl', 'ghj']
    lower_name = name.lower()
    for pattern in common_patterns:
        if pattern in lower_name:
            return "Please enter a valid name, not random letters"
    
    for i in range(len(name)-2):
        if name[i].isalpha() and name[i] == name[i+1] == name[i+2]:
            return "Name cannot contain three or more consecutive same letters"
    
    return None

def validate_email(email):
    if not email:
        return "Email is required"  # Checks if email is empty
    if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", email):
        return "Invalid email format"  # Checks email format
    if any(c.isupper() for c in email):
        return "Email should contain only lowercase letters"  # Checks for uppercase letters
    if not email.endswith('.com'):
        return "Email must end with .com"  # Checks domain ending
    return None

def validate_contact_number(number):
    if not number:
        return "Contact number is required"
    if not re.match(r"^(09|\+639)\d{9}$", number):
        return "Contact number must be in format 09XXXXXXXXX or +639XXXXXXXXX"
    return None

@auth_bp.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@auth_bp.route('/')
def home():
    if 'username' in session:
        mysql = current_app.extensions['mysql']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users_info WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        cursor.close()
        return render_template('home.html', user=user)
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin')
def admin():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    mysql = current_app.extensions['mysql']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users_info')
    users = cursor.fetchall()
    cursor.close()
    
    return render_template('admin.html', users=users)

@auth_bp.route('/add_user', methods=['POST'])
def add_user():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        mysql = current_app.extensions['mysql']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        firstname = request.form.get('firstname')
        middlename = request.form.get('middlename', '')
        lastname = request.form.get('lastname')
        birthday = request.form.get('birthday')
        age = request.form.get('age')
        address = request.form.get('address')
        
        # Combine names into full_name
        full_name = f"{firstname} {middlename + ' ' if middlename else ''}{lastname}".strip()
        
        # Debug log
        print(f"Attempting to add user with username: {username}")
        
        # Basic validation for other fields
        if not all([username, password, firstname, lastname, age, address]):
            cursor.close()
            return render_template('admin.html', error="Required fields cannot be empty!")
        
        # Validate full name
        name_error = validate_name(full_name)
        if name_error:
            cursor.close()
            return render_template('admin.html', error=f"Name Error: {name_error}")
        
        # Validate email
        email_error = validate_email(email)
        if email_error:
            cursor.close()
            return render_template('admin.html', error=f"Email Error: {email_error}")
        
        # Check if username exists
        cursor.execute('SELECT COUNT(*) as count FROM users_info WHERE username = %s', (username,))
        result = cursor.fetchone()
        print(f"Username check result: {result}")  # Debug log
        
        if result and result['count'] > 0:
            cursor.close()
            return render_template('admin.html', error="Username already exists!")
        
        # Check if email exists
        cursor.execute('SELECT COUNT(*) as count FROM users_info WHERE email = %s', (email,))
        result = cursor.fetchone()
        print(f"Email check result: {result}")  # Debug log
        
        if result and result['count'] > 0:
            cursor.close()
            return render_template('admin.html', error="Email already exists!")
        
        # Convert birthday string to MySQL date format if provided
        birthday_date = None
        if birthday:
            try:
                birthday_date = datetime.strptime(birthday, '%Y-%m-%d').date()
            except ValueError:
                cursor.close()
                return render_template('admin.html', error="Invalid birthday format")
        
        # Insert new user
        insert_query = '''
            INSERT INTO users_info 
            (username, password, email, full_name, birthday, age, address) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        insert_values = (username, password, email, full_name, birthday_date, age, address)
        
        print(f"Executing insert query: {insert_query}")  # Debug log
        print(f"Insert values: {insert_values}")  # Debug log
        
        cursor.execute(insert_query, insert_values)
        mysql.connection.commit()
        
        # Get updated user list
        cursor.execute('SELECT * FROM users_info')
        users = cursor.fetchall()
        cursor.close()
        
        return render_template('admin.html', users=users, success="User added successfully!")
        
    except Exception as e:
        print(f"Error adding user: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        if cursor:
            cursor.close()
        return render_template('admin.html', error=f"Failed to add user: {str(e)}")

@auth_bp.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        mysql = current_app.extensions['mysql']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('DELETE FROM users_info WHERE username = %s', (username,))
        mysql.connection.commit()
        
        cursor.execute('SELECT * FROM users_info')
        users = cursor.fetchall()
        cursor.close()
        
        return render_template('admin.html', users=users, success="User deleted successfully!")
        
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return render_template('admin.html', error="Failed to delete user. Please try again.")

@auth_bp.route('/admin_update_user/<username>', methods=['POST'])
def admin_update_user(username):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    age = request.form.get('age')
    address = request.form.get('address')
    
    # Validate full name
    name_error = validate_name(full_name)
    if name_error:
        return render_template('admin.html', error=f"Full Name Error: {name_error}")
    
    # Validate email
    email_error = validate_email(email)
    if email_error:
        return render_template('admin.html', error=f"Email Error: {email_error}")
    
    # Basic validation for other fields
    if not all([age, address]):
        return render_template('admin.html', error="All fields are required!")
    
    try:
        mysql = current_app.extensions['mysql']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('''
            UPDATE users_info 
            SET full_name = %s, email = %s, age = %s, address = %s 
            WHERE username = %s
        ''', (full_name, email, age, address, username))
        
        mysql.connection.commit()
        
        cursor.execute('SELECT * FROM users_info')
        users = cursor.fetchall()
        cursor.close()
        
        return render_template('admin.html', users=users, success="User updated successfully!")
        
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return render_template('admin.html', error="Failed to update user. Please try again.")

@auth_bp.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    mysql = current_app.extensions['mysql']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users_info WHERE username = %s', (session['username'],))
    user = cursor.fetchone()
    cursor.close()
    
    return render_template('profile.html', user=user)

@auth_bp.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    birthday = request.form.get('birthday')
    contact_number = request.form.get('contact_number')
    age = request.form.get('age')
    address = request.form.get('address')
    
    # Validate inputs
    name_error = validate_name(full_name)
    if name_error:
        return render_template('profile.html', error=f"Full Name Error: {name_error}")
    
    email_error = validate_email(email)
    if email_error:
        return render_template('profile.html', error=f"Email Error: {email_error}")
    
    contact_error = validate_contact_number(contact_number)
    if contact_error:
        return render_template('profile.html', error=f"Contact Number Error: {contact_error}")
    
    if not all([birthday, age, address]):
        return render_template('profile.html', error="All fields are required!")
    
    try:
        # Convert birthday string to MySQL date format
        birthday_date = datetime.strptime(birthday, '%Y-%m-%d').date()
        
        mysql = current_app.extensions['mysql']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('''
            UPDATE users_info 
            SET full_name = %s, email = %s, birthday = %s, contact_number = %s, age = %s, address = %s 
            WHERE username = %s
        ''', (full_name, email, birthday_date, contact_number, age, address, session['username']))
        
        mysql.connection.commit()
        
        cursor.execute('SELECT * FROM users_info WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        cursor.close()
        
        return render_template('profile.html', user=user, success="Profile updated successfully!")
        
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        return render_template('profile.html', error="Failed to update profile. Please try again.")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('auth.home'))
    
    # Add CORS headers
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST')
        return response

    try:
        print("Login route accessed")  # Debug log
        print(f"Request method: {request.method}")  # Debug log
        print(f"Form data: {request.form}")  # Debug log

        if request.method == 'POST':
            # Get form data
            username = request.form.get('username')
            password = request.form.get('password')
            
            print(f"Login attempt - Username: {username}")  # Debug log
            
            if not username or not password:
                print("Missing username or password")  # Debug log
                return render_template('login.html', error="Username and password are required!")

            try:
                # Get MySQL connection
                mysql = current_app.extensions.get('mysql')
                if not mysql:
                    print("MySQL extension not found")  # Debug log
                    return render_template('login.html', error="Database configuration error")

                # Create cursor
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                print("Created cursor")  # Debug log

                try:
                    # Check if table exists
                    cursor.execute("SHOW TABLES LIKE 'users_info'")
                    if not cursor.fetchone():
                        print("Table 'users_info' does not exist!")  # Debug log
                        return render_template('login.html', error="Database configuration error")

                    # Check table structure
                    cursor.execute("DESCRIBE users_info")
                    columns = cursor.fetchall()
                    print(f"Table structure: {columns}")  # Debug log

                    # Perform login query
                    query = "SELECT * FROM users_info WHERE username = %s AND password = %s"
                    print(f"Executing query: {query} with username: {username}")  # Debug log
                    
                    cursor.execute(query, (username, password))
                    user = cursor.fetchone()
                    print(f"Query result: {user}")  # Debug log

                    if user:
                        session['username'] = username
                        print(f"Login successful for user: {username}")  # Debug log
                        return redirect(url_for('auth.home'))
                    else:
                        print("Invalid credentials")  # Debug log
                        return render_template('login.html', error="Invalid username or password!")

                except MySQLdb.Error as db_error:
                    print(f"MySQL Error: {str(db_error)}")  # Debug log
                    print(f"Error traceback: {traceback.format_exc()}")  # Debug log
                    return render_template('login.html', error=f"Database error: {str(db_error)}")
                finally:
                    cursor.close()

            except Exception as e:
                print(f"Connection error: {str(e)}")  # Debug log
                print(f"Error traceback: {traceback.format_exc()}")  # Debug log
                return render_template('login.html', error=f"Connection error: {str(e)}")

        # GET request - just render the login form
        return render_template('login.html')

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        print(f"Error traceback: {traceback.format_exc()}")  # Debug log
        return render_template('login.html', error=f"An unexpected error occurred: {str(e)}")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('auth.home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        birthday = request.form.get('birthday')
        contact_number = request.form.get('contact_number')
        age = request.form.get('age')
        address = request.form.get('address')
        
        # Validate inputs
        name_error = validate_name(full_name)
        if name_error:
            return render_template('register.html', error=f"Full Name Error: {name_error}")
        
        email_error = validate_email(email)
        if email_error:
            return render_template('register.html', error=f"Email Error: {email_error}")
        
        contact_error = validate_contact_number(contact_number)
        if contact_error:
            return render_template('register.html', error=f"Contact Number Error: {contact_error}")
        
        if not all([username, password, birthday, age, address]):
            return render_template('register.html', error="All fields are required!")
        
        try:
            # Convert birthday string to MySQL date format
            birthday_date = datetime.strptime(birthday, '%Y-%m-%d').date()
            
            mysql = current_app.extensions['mysql']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            cursor.execute('SELECT * FROM users_info WHERE username = %s', (username,))
            account = cursor.fetchone()
            
            if account:
                return render_template('register.html', error="Username already exists!")
            
            cursor.execute(
                'INSERT INTO users_info (username, password, email, full_name, birthday, contact_number, age, address) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (username, password, email, full_name, birthday_date, contact_number, age, address)
            )
            mysql.connection.commit()
            cursor.close()
            
            return render_template('login.html', message="Registration successful! Please login.")
            
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return render_template('register.html', error="Registration failed. Please try again.")
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    response = make_response(render_template('logout.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/blog')
@login_required
def blog():
    mysql = current_app.extensions['mysql']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT b.*, u.username FROM blog_posts b JOIN users_info u ON b.user_email = u.email ORDER BY created_at DESC')
    posts = cursor.fetchall()
    cursor.close()
    return render_template('blog.html', posts=posts)

@auth_bp.route('/blog/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required!', 'error')
            return redirect(url_for('auth.new_post'))
            
        mysql = current_app.extensions['mysql']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get user's email
        cursor.execute('SELECT email FROM users_info WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        
        cursor.execute(
            'INSERT INTO blog_posts (title, content, user_email, created_at) VALUES (%s, %s, %s, %s)',
            (title, content, user['email'], datetime.now())
        )
        mysql.connection.commit()
        cursor.close()
        
        flash('Post created successfully!', 'success')
        return redirect(url_for('auth.blog'))
        
    return render_template('blog_new.html')

@auth_bp.route('/blog/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    mysql = current_app.extensions['mysql']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get user's email
    cursor.execute('SELECT email FROM users_info WHERE username = %s', (session['username'],))
    current_user = cursor.fetchone()
    
    # Get post and check ownership
    cursor.execute('SELECT b.*, u.username FROM blog_posts b JOIN users_info u ON b.user_email = u.email WHERE b.id = %s', (post_id,))
    post = cursor.fetchone()
    
    if not post or post['user_email'] != current_user['email']:
        cursor.close()
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required!', 'error')
            return redirect(url_for('auth.edit_post', post_id=post_id))
        
        cursor.execute(
            'UPDATE blog_posts SET title = %s, content = %s, updated_at = %s WHERE id = %s',
            (title, content, datetime.now(), post_id)
        )
        mysql.connection.commit()
        cursor.close()
        
        flash('Post updated successfully!', 'success')
        return redirect(url_for('auth.blog'))
        
    return render_template('blog_edit.html', post=post)

@auth_bp.route('/blog/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    mysql = current_app.extensions['mysql']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get user's email
    cursor.execute('SELECT email FROM users_info WHERE username = %s', (session['username'],))
    current_user = cursor.fetchone()
    
    # Check post ownership
    cursor.execute('SELECT * FROM blog_posts WHERE id = %s', (post_id,))
    post = cursor.fetchone()
    
    if not post or post['user_email'] != current_user['email']:
        cursor.close()
        abort(403)
    
    cursor.execute('DELETE FROM blog_posts WHERE id = %s', (post_id,))
    mysql.connection.commit()
    cursor.close()
    
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('auth.blog'))