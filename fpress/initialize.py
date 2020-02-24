# initialize.py
from users import create_user
from utils import token_generator

def initialize(DB):
    """initialize the app"""
    # this is called before the app starts
    # we're using a separte function because it has hashing and checking
    admin='admin'
    password = token_generator()
    password = 'admin'
    u  = create_user(DB, username=admin,
                     password=password,
                     is_admin=True)
    if u:
        # replace with a randomization
        print('WRITE THIS DOWN!')
        print('Admin user created. username={} password={}'.format(admin, password))
        
    # These are the default HOME and ABOUT pages-- can be easily changed later.
    # will not overwrite existing home and about pages.
    p = DB.pages.find_one({'slug':'home'})
    if p is None:
        # create only if page IS NOT present
        DB.pages.insert_one({'slug':'home', 'title':'Home', 'owner':'admin',
                             'content':'<b>Welcome, please change me.</b>  I am the <i>default</i> Home page!', 
                             'is_markdown':False, 'owner':'admin', 'show_nav':True, 'is_published': True})
        print("default HOME page created")
    p = DB.pages.find_one({'slug':'about'})
    if p is None:
        DB.pages.insert_one({'slug':'about', 'title':'About', 'owner':'admin',
                             'content':'<b>Welcome</b>, please change me.  I am the <i>default</i> boilerplate About page.',
                             'is_markdown':False, 'owner':'admin', 'show_nav':True, 'is_published': True})
        print("default ABOUT page created")
        
    m = DB.meta.find_one({})
    if m is None:
        DB.meta.insert_one({'brand':'FlaskPress', 'theme':'default'})