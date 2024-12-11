from flask import Flask, redirect, url_for, session
from flask_mysqldb import MySQL
from final_project.blueprint_folder import create_blueprint
import MySQLdb

app = Flask(__name__, 
           static_folder='final_project/blueprint_folder/static')

# Session configuration
app.secret_key = 'your-secret-key-here'  # Required for session

# XAMPP MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'users_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL with error handling
mysql = MySQL(app)
app.extensions['mysql'] = mysql

# Test the connection within application context
with app.app_context():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        print("MySQL connection successful!")
    except MySQLdb.Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise Exception("Failed to connect to MySQL. Please check if XAMPP MySQL service is running and the database exists.")

# Register blueprint
auth_bp = create_blueprint()
app.register_blueprint(auth_bp, url_prefix='/auth')

# Root route redirects to login
@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)