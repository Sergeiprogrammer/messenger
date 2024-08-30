from flask import Flask, redirect, url_for, render_template, session, request
import sqlite3
import secrets

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def init_db():
    with sqlite3.connect('main.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member1 INTEGER,
                member2 INTEGER,
                FOREIGN KEY(member1) REFERENCES users(id),
                FOREIGN KEY(member2) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats_history (
                chat_id INTEGER,
                sender_id INTEGER,
                recipient_id INTEGER,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id),
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (recipient_id) REFERENCES users(id)
            )
        ''')
        conn.commit()


init_db()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        ip = request.remote_addr

        with sqlite3.connect('main.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
            user = cursor.fetchone()

        if user:
            session['user'] = user[0]
            session['ip'] = ip
            return redirect(url_for('index'))
        else:
            return "Неверные имя пользователя или пароль", 400

    return render_template('login.html')

@app.route('/logout')
def logout():
    try:
        session.clear()  # Очищаем сессию
        return "Все хорошо", 200
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

@app.route('/conversations')
def conversations():
    conn = sqlite3.connect('main.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM chats WHERE member1 = ? OR member2 = ?''', (session['user'], session['user']))
    messages = cursor.fetchall()
    cursor.execute("SELECT message FROM chats_history WHERE (sender_id = ? OR recipient_id = ?) ORDER BY timestamp DESC LIMIT 1", (session['user'], session['user']))
    last_message = cursor.fetchall()
    print(messages)
    conn.close()

    if not last_message:
        last_message = [None] * len(messages)  # or return an empty list []

    zipped_messages = list(zip(messages, last_message))

    return render_template('chat_history.html', zipped_messages=zipped_messages)
    
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user' in session:
        message = request.form.get('message')
        recipient_id = request.form.get('recipient_id')

        if not message or not recipient_id:
            return "Ошибка: не заполнены все поля", 400

        with sqlite3.connect('main.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM users WHERE id = ?
            ''', (recipient_id,))
            recipient_exists = cursor.fetchone()

            if not recipient_exists:
                return "Ошибка: получатель не существует", 400

            cursor.execute('''
                SELECT chat_id FROM chats 
                WHERE (member1 = ? AND member2 = ?) OR (member1 = ? AND member2 = ?)
            ''', (session['user'], recipient_id, recipient_id, session['user']))
            chat_record = cursor.fetchone()

            if not chat_record:
                cursor.execute('INSERT INTO chats (member1, member2) VALUES (?, ?)',
                               (session['user'], recipient_id))
                chat_id = cursor.lastrowid
            else:
                chat_id = chat_record[0]

            cursor.execute('''
                INSERT INTO chats_history (chat_id, sender_id, recipient_id, message) 
                VALUES (?, ?, ?, ?)
            ''', (chat_id, session['user'], recipient_id, message))
            conn.commit()

        return redirect(url_for('view_messages', chat_id=chat_id))
    else:
        return redirect(url_for('login'))

@app.route('/registrate', methods=['GET', 'POST'])
def registrate():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return "Ошибка: не заполнены все поля", 400

        with sqlite3.connect('main.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                           (username, password))
            conn.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/view_messages/<int:chat_id>')
def view_messages(chat_id):
    try:
        conn = sqlite3.connect('main.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.username, c.message, c.timestamp 
            FROM chats_history c 
            JOIN users u ON c.sender_id = u.id 
            WHERE c.chat_id = ?
        ''', (chat_id,))
        messages = cursor.fetchall()
        conn.close()

        print(f"Messages: {messages}")  # Debugging statement

        with sqlite3.connect('main.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT member1 , member2 FROM chats ''')
            chat_history = cursor.fetchall()
        if session['user'] not in chat_history[0]:
            messages = ["text","text"]
        else:
            pass
        return render_template('view_messages.html', messages=messages)
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
