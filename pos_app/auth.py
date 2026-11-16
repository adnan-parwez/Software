import json
import hashlib
from datetime import datetime

class UserManager:
    def __init__(self):
        self.users_file = "users.json"
        self.current_user = None
        self.load_users()

    def load_users(self):
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except FileNotFoundError:
            self.users = {
                "admin": {
                    "password": self.hash_password("admin123"),
                    "name": "Administrator",
                    "role": "admin",
                    "created": datetime.now().strftime("%Y-%m-%d")
                }
            }
            self.save_users()

    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_login(self, username, password):
        if username in self.users:
            stored = self.users[username]["password"]
            hashed_sha = self.hash_password(password)
            import hashlib as _hl
            hashed_md5 = _hl.md5(password.encode()).hexdigest()
            if stored in (hashed_sha, hashed_md5):
                self.current_user = {
                    "username": username,
                    "name": self.users[username]["name"],
                    "role": self.users[username]["role"]
                }
                return True
        return False

    def add_user(self, username, password, name, role):
        if username in self.users:
            return False, "Username already exists"
        self.users[username] = {
            "password": self.hash_password(password),
            "name": name, "role": role,
            "created": datetime.now().strftime("%Y-%m-%d")
        }
        self.save_users()
        return True, "User created successfully"

    def delete_user(self, username):
        if username == "admin":
            return False, "Cannot delete admin user"
        if username in self.users:
            del self.users[username]
            self.save_users()
            return True, "User deleted"
        return False, "User not found"

    def get_all_users(self):
        return [{"username": u, "name": d["name"], "role": d["role"], "created": d["created"]}
                for u, d in self.users.items()]