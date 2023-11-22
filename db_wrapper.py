import sqlite3
import hashlib
import time

#Splid clone
# the way it works is:
# 1 person pays something for a group of people
# the group of people then pay the person back
# we keep track of who owes who what

class User:
    def __init__(self, name, password) -> None:
        self.name = name #unique identifier
        self.owes = {} # {user: amount} means user owes me amount
        self.owed = {} # {user: amount} means i owe user amount
        self.balance = 0
        
        self.is_authenticated = True #for testing purposes always true
    
    def check_auth(self, password) -> bool:
        return self.password == hashlib.sha256(password.encode()).hexdigest()
    
    def __str__(self) -> str:
        return self.name
    
    def add_owes(self, owe: "Owes"):
        amount = owe.get_amount(self.name)
        self.owes[owe.sender] = amount
        self.balance -= amount
    
    def add_owed(self, owe: "Owes"):
        for user, amount_owed in owe.amounts.items():
            if user == self.name:
                continue
            self.owed[user] = amount_owed
        self.balance += owe.total
    
    def print_all_transactions(self):
        print(f"{self.name} owes:")
        for user, amount in self.owes.items():
            print(f"{user}: {amount}")
        print(f"{self.name} is owed:")
        for user, amount in self.owed.items():
            print(f"{user}: {amount}")
        print(f"{self.name} has a balance of {self.balance}")
    
    def update(self):
        #get all transactions from db
        transactions = db.get_owes(sender=self.name)
        for transaction in transactions:
            #transaction: (id, sender, receivers, amounts)
            receivers = transaction[2].split(",")
            amounts = transaction[3].split(",")
            amounts = {receivers[i]: float(amounts[i]) for i in range(len(receivers))}
            owe = Owes(transaction[1], amounts)
            self.add_owes(owe)
        
        transactions = db.get_owes(receiver=self.name)
        for transaction in transactions:
            #transaction: (id, sender, receivers, amounts)
            receivers = transaction[2].split(",")
            amounts = transaction[3].split(",")
            amounts = {receivers[i]: float(amounts[i]) for i in range(len(receivers))}
            owe = Owes(transaction[1], amounts)
            self.add_owed(owe)

#---

class Owes:
    def __init__(self, sender, amounts):
        self.sender = sender
        self.amounts: dict[User, float] = amounts # {user: amount}
        self.total = sum(amounts.values())
    
    def get_amount(self, user:str) -> float:
        return self.amounts.get(user, 0)

#---

class DataBase:
    def __init__(self) -> None:
        self.path = "./data/data.db"
        self.users = {} # {name: User}
        self.owes = []

        self.conn = sqlite3.connect(self.path)
        self.cursor = self.conn.cursor()
        
        self.create_tables_if_not_exists()
    
    def create_tables_if_not_exists(self):
        cmd = """
        CREATE TABLE IF NOT EXISTS users (
            name TEXT PRIMARY KEY,
            password TEXT NOT NULL
        );
        """
        self.cursor.execute(cmd)
        cmd = """
        CREATE TABLE IF NOT EXISTS owes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receivers TEXT NOT NULL,
            amounts TEXT NOT NULL
        );
        """
        self.cursor.execute(cmd)
        self.conn.commit()
    
    def add_user(self, name, password):
        cmd = """
        INSERT INTO users (name, password) VALUES (?, ?);
        """
        self.cursor.execute(cmd, (name, password))
        self.conn.commit()
    
    def add_owe(self, sender, receivers, amounts):
        cmd = """
        INSERT INTO owes (sender, receivers, amounts) VALUES (?, ?, ?);
        """
        self.cursor.execute(cmd, (sender, receivers, amounts))
        self.conn.commit()
    
    def update(self, verbose=False):
        t_start = time.time()
        cmd = "SELECT * FROM users;"
        self.cursor.execute(cmd)
        users = self.cursor.fetchall()
        self.users = {}
        for user in users:
            self.users[user[0]] = User(user[0], user[1])
        
        if verbose:
            print(f"Users loaded in {time_taken(t_start)}")
        
        t_start_2 = time.time()
        cmd = "SELECT * FROM owes;"
        self.cursor.execute(cmd)
        owes = self.cursor.fetchall()
        self.owes = []
        for owe in owes:
            sender = owe[1]
            receivers = owe[2].split(",")
            amounts = owe[3].split(",")
            amounts = {receivers[i]: float(amounts[i]) for i in range(len(receivers))}
            self.owes.append(Owes(sender, amounts))
        
        if verbose:
            print(f"Owes loaded in {time_taken(t_start_2)}")
            print(f"Total time taken: {time_taken(t_start)}")
            
    
    def get_user_by_name(self, name):
        cmd = """
        SELECT * FROM users WHERE name = ?;
        """
        self.cursor.execute(cmd, (name,))
        user = self.cursor.fetchone()
        if user is None:
            return None
        return User(user[0], user[1])
    
    def get_owes(self, **kwargs):
        #kwargs: sender, receiver, amount
        
        #if all of them are None, return None
        #if only one of them is valid, search db for that
        #if more than one is valid, search db for OR and for AND

        valid_dict = {
        }
        if "sender" in kwargs:
            valid_dict["sender"] = kwargs["sender"]
        if "receiver" in kwargs:
            valid_dict["receiver"] = kwargs["receiver"]
        if "amount" in kwargs:
            valid_dict["amount"] = kwargs["amount"]
        
        match len(valid_dict):
            case 0:
                cmd = "SELECT * FROM owes;"
                self.cursor.execute(cmd)
                return self.cursor.fetchall()
            case 1:
                cmd = f"SELECT * FROM owes WHERE {list(valid_dict.keys())[0]} = ?;"
                self.cursor.execute(cmd, (list(valid_dict.values())[0],))
                return self.cursor.fetchall()
            case 2:
                #return dict: {OR: [list of results], AND: [list of results]}
                cmd = f"SELECT * FROM owes WHERE {list(valid_dict.keys())[0]} = ? OR {list(valid_dict.keys())[1]} = ?;"
                self.cursor.execute(cmd, (list(valid_dict.values())[0], list(valid_dict.values())[1]))
                r_dict = {"OR": self.cursor.fetchall()}
                cmd = f"SELECT * FROM owes WHERE {list(valid_dict.keys())[0]} = ? AND {list(valid_dict.keys())[1]} = ?;"
                self.cursor.execute(cmd, (list(valid_dict.values())[0], list(valid_dict.values())[1]))
                r_dict["AND"] = self.cursor.fetchall()
                return r_dict
            case 3:
                #return dict: {OR: [list of results], AND: [list of results]}
                cmd = f"SELECT * FROM owes WHERE {list(valid_dict.keys())[0]} = ? OR {list(valid_dict.keys())[1]} = ? OR {list(valid_dict.keys())[2]} = ?;"
                self.cursor.execute(cmd, (list(valid_dict.values())[0], list(valid_dict.values())[1], list(valid_dict.values())[2]))
                r_dict = {"OR": self.cursor.fetchall()}
                cmd = f"SELECT * FROM owes WHERE {list(valid_dict.keys())[0]} = ? AND {list(valid_dict.keys())[1]} = ? AND {list(valid_dict.keys())[2]} = ?;"
                self.cursor.execute(cmd, (list(valid_dict.values())[0], list(valid_dict.values())[1], list(valid_dict.values())[2]))
                r_dict["AND"] = self.cursor.fetchall()
                return r_dict

def time_taken(t1:float) -> str:
    #beatufully format time taken
    t2 = time.time()
    t_delta = t2 - t1
    #adjust for time unit
    if t_delta < 1:
        t_delta *= 1000
        unit = "ms"
    elif t_delta > 60:
        t_delta /= 60
        unit = "min"
    elif t_delta > 3600:
        t_delta /= 3600
        unit = "hr"
    elif t_delta > 86400:
        t_delta /= 86400
        unit = "day"
    elif t_delta > 604800:
        t_delta /= 604800
        unit = "week"
    elif t_delta > 2628000:
        t_delta /= 2628000
        unit = "month"
    elif t_delta > 31536000:
        t_delta /= 31536000
        unit = "year"
    else:
        unit = "s"
    
    return f"{t_delta:.2f} {unit}"

#---

#generate random users and data
import random
import string

db = DataBase()

db.update(verbose=True)

users = db.users
usernames = list(users.keys())

num_transactions = 100000
for _ in range(num_transactions):
    t_start = time.time()
    sender = random.choice(usernames)
    receivers = random.choices(usernames, k=random.randint(1, 10))
    amounts = [random.randint(1, 100) for _ in range(len(receivers))]
    db.add_owe(sender, ",".join(receivers), ",".join(map(str, amounts)))
    percentage = _ / num_transactions * 100
    print(f"{_} / {num_transactions} ({percentage:.2f}%) in {time_taken(t_start)}")

db.update(verbose=True)

#select 10 random users

users = random.choices(list(db.users.values()), k=10)

for user in users:
    print(user)
    user.print_all_transactions()
    print()