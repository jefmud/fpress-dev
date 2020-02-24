from werkzeug.security import generate_password_hash, check_password_hash

def create_user(DB, username, password, email='', is_admin=False, is_active=True, bio="", avatar=""):
    """create a user, hash the password"""
    # make sure username is UNIQUE
    u = DB.users.find_one({'username':username})
    if u:
        # user already exists, return None
        return None
    hashedpw = generate_password_hash(password)
    u = DB.users.insert_one({'username':username, 'password':hashedpw, 'is_admin':is_admin,
                             'email':email, 'is_active':is_active, 'bio':bio, 'avatar':avatar})
    return u

def createsuperuser(DB):
    """interactive CLI create user"""
    username = input("Enter the username: ")
    password = input("Enter the password: ")
    if create_user(DB, username=username, password=password, is_admin=True, is_active=True) is None:
        print("Username already exists, choose a new one.")
    else:
        print("User successfully created.")