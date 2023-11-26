import sqlite3

class DBWrapper:
    def __init__(self) -> None:
        self.path = "./data/database.db"
        self.conn = sqlite3.connect(self.path)
        self.cursor = self.conn.cursor()
        
        self.create_tables()
    
    def create_tables(self):
        cmd = """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL
        );"""
        self.cursor.execute(cmd)
        self.conn.commit()
        
        cmd = """CREATE TABLE IF NOT EXISTS owes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        );"""
        self.cursor.execute(cmd)
        self.conn.commit()
    
    def add_user(self, username, password, email):
        #check if username already exists
        cmd = """SELECT * FROM users WHERE username = ?;"""
        self.cursor.execute(cmd, (username,))
        if self.cursor.fetchone() is not None:
            return False
        
        cmd = """SELECT * FROM users WHERE email = ?;"""
        self.cursor.execute(cmd, (email,))
        if self.cursor.fetchone() is not None:
            return False
        
        cmd = """INSERT INTO users (username, password, email) VALUES (?, ?, ?);"""
        self.cursor.execute(cmd, (username, password, email))
        self.conn.commit()
        return True
    
    def change_password(self, user_id, new_password):
        cmd = """UPDATE users SET password = ? WHERE id = ?;"""
        self.cursor.execute(cmd, (new_password, user_id))
        self.conn.commit()
    
    def change_email(self, user_id, new_email):
        cmd = """UPDATE users SET email = ? WHERE id = ?;"""
        self.cursor.execute(cmd, (new_email, user_id))
        self.conn.commit()
    
    def delete_user(self, user_id):
        cmd = """DELETE FROM users WHERE id = ?;"""
        self.cursor.execute(cmd, (user_id,))
        self.conn.commit()
    
    def get_user_by_username(self, username) -> tuple[int, str, str, str]: #id, username, password, email
        cmd = """SELECT * FROM users WHERE username = ?;"""
        self.cursor.execute(cmd, (username,))
        return self.cursor.fetchone()
    
    def get_user_by_email(self, email):
        cmd = """SELECT * FROM users WHERE email = ?;"""
        self.cursor.execute(cmd, (email,))
        return self.cursor.fetchone()
    
    def get_user_by_id(self, id):
        cmd = """SELECT * FROM users WHERE id = ?;"""
        self.cursor.execute(cmd, (id,))
        return self.cursor.fetchone()
    
    def get_all_users(self):
        cmd = """SELECT * FROM users;"""
        self.cursor.execute(cmd)
        return self.cursor.fetchall()
    
    def get_num_users(self):
        cmd = "SELECT MAX(id) FROM users"
        self.cursor.execute(cmd)
        return self.cursor.fetchone()[0]
    
    
    
    # Owes functions
    
    def get_owes_by_sender_id(self, sender_id) -> list[tuple[int, int, int, float, str]]:
        cmd = """SELECT * FROM owes WHERE sender_id = ?;"""
        self.cursor.execute(cmd, (sender_id,))
        return self.cursor.fetchall()
    
    def get_owes_by_receiver_id(self, receiver_id) -> list[tuple[int, int, int, float, str]]: #id, sender_id, receiver_id, amount, description
        cmd = """SELECT * FROM owes WHERE receiver_id = ?;"""
        self.cursor.execute(cmd, (receiver_id,))
        return self.cursor.fetchall()
    
    def add_owe(self, sender_id, receiver_id, amount, description):
        cmd = """INSERT INTO owes (sender_id, receiver_id, amount, description) VALUES (?, ?, ?, ?);"""
        self.cursor.execute(cmd, (sender_id, receiver_id, amount, description))
        self.conn.commit()
    
    def delete_owe(self, id):
        cmd = """DELETE FROM owes WHERE id = ?;"""
        self.cursor.execute(cmd, (id,))
        self.conn.commit()

    def get_num_owes(self):
        cmd = "SELECT MAX(id) FROM owes"
        self.cursor.execute(cmd)
        return self.cursor.fetchone()[0]
    
    def get_sum_owes(self):
        cmd = "SELECT SUM(amount) FROM owes"
        self.cursor.execute(cmd)
        return self.cursor.fetchone()[0]


if __name__ == "__main__":
    print("This script is not meant to be run directly.")
    print("Please run the main.py script instead.")