# app.py
# This is the main app of FlaskPress Alpha
import datetime
from flask import (abort, flash, Flask, g, redirect,
                   render_template, request, send_from_directory, session, url_for)

from flask_ckeditor import CKEditor
from flask_dropzone import Dropzone

from forms import UsernamePasswordForm, LoginForm, RegisterForm, HTMLPageForm, PageForm, CSRF
from initialize import initialize

import os

from tinymongo import TinyMongoClient, Query, where

from users import generate_password_hash

from utils import (slugify, login_required, form2object, object2form,
                   admin_required, token_generator, snippet)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_pyfile('app.cfg')
DB = TinyMongoClient().flaskpress


############### BLOG 2 META DEFAULTS #############
# once running, you can override these defaults
default_brand = "FlaskBlog"
default_about = """
<p>FlaskPress is an open-source micro content management system.
It is our hope it will be useful to someone in the community that have learned or are
discovering the excellence of Python and the Flask web framework.
</p>
<p>
FlaskPress leverages several Flask plugins and the simple TinyMongo to achieve a flat file storage system. The advantage of using
TinyMongo is simplicity and being a somewhat small/self-contained project.  The advantage of using Flask is it's unopinonated and
easy to deploy framework that is high extensible.
</p>
<p>
In addition, we leverage Jinja2 template language and we use the Bulma CSS framework for the front-end styling.  It should be relatively easy
for a developer to add their own templates and design framework, based on Skeleton, Bootstrap, Materialize, or some other excellent
framework.
</p>
<p>
We look forward to community involvement to add more to the project.
</p>
"""

###############
app = Flask(__name__)
app.secret_key = '&#*OnNyywiy1$#@'
app.config.from_pyfile('app.cfg')
HOST = '0.0.0.0'
PORT = 5000
DEBUG = False

### DATABASE
DB = TinyMongoClient().blog
initialize(DB)

### FILE UPLOADS PARAMETERS
dropzone = Dropzone()
dropzone.init_app(app)
# UPLOAD FOLDER will have to change based on your own needs/deployment scenario
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, './uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


@app.before_request
def before_request():
    """tasks before request is executed"""
    g.db = DB
    
    g.username = session.get('username')
    g.is_authenticated = session.get('is_authenticated')
    g.is_admin = session.get('is_admin')
    g.macro_csrf_token = token_generator(size=24)
    
    meta = g.db.meta.find_one()
    if meta:
        g.theme = meta.get('theme','default')
        g.brand = meta.get('brand', 'FlaskPress')
        g.navbackground = meta.get('navbackground', False)
        g.stylesheet = meta.get('stylesheet')
    else:
        g.theme = 'default'
        g.brand = 'FlaskPress'
        g.navbackground = False
        
    if g.stylesheet is None:
        g.stylesheet = "https://cdnjs.cloudflare.com/ajax/libs/bulma/0.8.0/css/bulma.min.css"

@app.after_request
def after_request(response):
    """tasks after request is executed"""
    return response

@app.route('/login', methods=['GET','POST'])
def login():
    """handle basic login"""
    if g.is_authenticated:
        flash('Please logout first', category='warning')
        return redirect(url_for('site'))

    form = UsernamePasswordForm()
    if form.validate_on_submit():
        # see if user exists
        user = g.db.users.find_one({'username':form.username.data})
        if user:
            if check_password_hash(user.get('password'), form.password.data):
                # inject session data
                session['username'] = form.username.data
                session['is_authenticated'] = True
                if user.get('is_admin'):
                    session['is_admin'] = True

                msg = "Welcome {}!".format(form.username.data)
                flash(msg, category="success")
                return redirect(url_for('site'))

        flash("Incorrect username or password",category="danger")

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash("You are now logged out!",category="info")
    return redirect(url_for('site'))


@app.route('/admin', methods=('GET','POST'), strict_slashes=False)
@admin_required
def admin():
    meta = g.db.meta.find_one()
    
    """view for basic admin tasks"""
    form = CSRF()
    if form.validate_on_submit():
        # get data from the form
        brand = request.form.get('brand')
        about = request.form.get('about')
        stylesheet = request.form.get('stylesheet')
        # set the global brand objects
        meta['brand'] = brand
        meta['stylesheet'] = stylesheet
        g.db.meta.update_one({'_id':meta.get('_id')}, meta)
    
    return render_template('admin.html', form=form)

@app.route('/admin/users', methods=('GET','POST'))
@admin_required
def admin_users():
    """view for administering users"""
    users = g.db.users.find()
    return render_template('users.html', users=users)

@app.route('/admin/user/add', strict_slashes=False)
@admin_required
def user_add():
    """ADMIN-ONLY view to add a user"""
    return redirect(url_for('user_edit'))

@app.route('/admin/user', methods=('GET','POST'), strict_slashes=False)
@app.route('/admin/user/<user_id>', methods=('GET','POST'))
@admin_required
def user_edit(user_id=None):
    """ADMIN-ONLY view to edit a user or create a user if no user_id supplied"""
    if user_id is None:
        user = {}
    else:
        user = g.db.users.find_one({'_id':user_id})
        if user is None:
            flash("No such user with id={}".format(user_id), "warning")
            return redirect(url_for('admin_user'))
    
    form = CSRF()
    if form.validate_on_submit():
        username = request.form.get('username')
        displayname = request.form.get('displayname')
        email = request.form.get('email')
        password = request.form.get('password')
        is_active = request.form.get('is_active') == 'on'
        is_admin = request.form.get('is_admin') == 'on'
        
        if len(username) > 0 and len(password) > 0:
            user['username'] = username
            user['displayname'] = displayname
            
            if user.get('password') != password:
                # password changed, rehash the password
                user['password'] = generate_password_hash(password)
            
            user['email'] = email
            user['is_active'] = is_active
            user['is_admin'] = is_admin
        
            if user_id:
                g.db.users.update_one({'_id':user_id}, user)
                flash("User information changed", category="success")
            else:
                g.db.users.insert_one(user)
                flash("New user created", category="success")
            return redirect(url_for('admin_users'))
        else:
            flash('Username and password must be filled in', category="danger")
    
    return render_template('user.html', user=user, form=form)

@app.route('/user_delete/<user_id>')
@app.route('/user_delete/<user_id>/<hard_delete>')
@admin_required
def user_delete(user_id, hard_delete=False):
    """delete a user. A soft delete only sets the is_active to false
    a hard_delete signal deletes the user and reassigns all the pages and files to the current ADMIN
    """
    edit_url = url_for('user_edit', user_id=user_id)
    user_key = {'_id':user_id}
    user = g.db.users.find_one(user_key)
    if user is None:
        flash('No user with id={}'.format(user_id), category="danger")
        return redirect('admin_user')
    
    if user['username'] != session.get('username'):
        if hard_delete:
            # reassign all pages to admin who is deleting
            pages = g.db.pages.find({'owner':user['username']})
            for page in pages:
                page['owner'] = session.get('username')
                g.db.pages.update_one({'_id':page['_id']}, page)
            
            g.db.users.remove(user_key)
            flash("User fully deleted, {} pages reassigned to {}.".format(len(pages), g.username), category="primary")
        else:
            user['is_active'] = False
            g.db.users.update_one(user_key, user)
            flash("User deactivated, but still present in database", category="primary")
    else:
        flash("CANNOT DELETE/DEACTIVATE an actively logged in account.", category="danger")
    
    # redirect to caller or index page if we deleted on an edit view
    if request.referrer == None or edit_url in request.referrer:
        return redirect(url_for('site'))
    else:
        return redirect(request.referrer)  

@app.route('/admin/pages', methods=('GET','POST'))
@admin_required
def admin_pages():
    """ADMIN-ONLY view to look at all pages.
    TODO: change view to support non-admin users
    """
    # find all pages
    pages = g.db.pages.find()
    return render_template('admin_pages.html', pages=pages)


@app.route('/file_delete/<file_id>')
@login_required
def file_delete(file_id):
    """view to delete an existing file object and physical file (owned by user)"""
    file_key = {'_id':file_id}
    f = g.db.files.find_one(file_key)
    if f is None:
        flash("Unable to locate file id={}".format(file_id), category="danger")
        return redirect(url_for('admin_files'))
    
    pathname = os.path.join(app.config['UPLOAD_FOLDER'], f.get('filepath'))
    if f.get('owner') == session['username'] or session['is_admin']:
        g.db.files.remove(file_key)
        try:
            os.remove(pathname)
            flash('File Successfully Deleted', category="success")
        except:
            flash("Error: problems removing physical file. Check log for details.", category="warning")
    else:
        flash('You are not authorized to remove this file.', category="danger")
    
    # handle redirect to referer
    if request.referrer == None:
        return redirect(url_for('index'))
    else:
        return redirect(url_for('admin_files'))  

@app.route('/file_edit/<file_id>', methods=['GET','POST'])
@admin_required
def file_edit(file_id):
    """view to allow edit/delete of a File resource"""
    file_key = {'_id':file_id}
    file = g.db.files.find_one(file_key)
    if file is None:
        flash("File with id={} was NOT found".format(file_id), category="danger")
  
    if request.method == 'POST':
        if file.get('owner')== session['username'] or session['is_admin']:
            title = request.form.get('title')
            if title:
                file['title'] = title
                g.db.files.update_one(file_key, file)
                flash("File information changed", category="success")
                return redirect(url_for('admin_files'))
            else:
                flash('Title must not be blank.', category="warning")
        else:
            flash("You are not authorized to edit/delete this object.", category="danger")
        
    return render_template('file_edit.html',file=file)
    
  
@app.route('/admin/files')
@admin_required
def admin_files():
    """ADMIN-ONLY view for all File resources
    TODO: change this view to support non-admin users
    """
    files = g.db.files.find()
    return render_template('admin_files.html', files=files)

@app.route('/_upload', methods=['GET', 'POST'])
@login_required
def file_upload_handler():
    """File upload handling"""
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            subfolder = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m/")
            pathname = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)

            # handle name collision if needed
            # filename will add integers at beginning of filename in dotted fashion
            # hello.jpg => 1.hello.jpg => 2.hello.jpg => ...
            # until it finds an unused name
            i=1
            while os.path.isfile(pathname):
                parts = filename.split('.')
                parts.insert(0,str(i))
                filename = '.'.join(parts)
                i += 1
                if i > 100:
                    # probably under attack, so just fail
                    raise ValueError("too many filename collisions, administrator should check this out")

                pathname = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)

            try:
                # ensure directory where we are storing exists, and create it
                directory = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
                if not os.path.exists(directory):
                    os.makedirs(directory)
                # finally, save the file AND create its resource object in database
                file.save(pathname)
                
                # put our file reference into the database
                local_filepath = os.path.join(subfolder, filename)
                url = url_for('file_uploads', path=local_filepath)
                file_object = {'title': filename, 'filepath': local_filepath, 'owner': g.username, 'url':url}
                g.db.files.insert(file_object)
                # check if we can find the object
                file_object = g.db.files.find_one(file_object)
                flash("File upload success")
                return redirect(url_for('file_edit', file_id=file_object['_id']))
            except Exception as e:
                print(e)
                flash("Something went wrong here-- please let administrator know", category="danger")
                raise ValueError("Something went wrong with file upload.")

    # TODO, replace with fancier upload drag+drop
    # session['no_csrf'] = True
    return redirect(url_for('admin_files'))

@app.route('/admin/firstuse', methods=('GET', 'POST'))
def admin_first_use():
    """view for first-use.  This view is triggered by EMPTY User table"""
    # this route should only work on empty user table
    if len(User.select()) > 0:
        abort(403) # forbidden
  
    errors = False
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        if len(username) == 0:
            errors = True
            flash("Username must be NON-NULL", category="danger")
            
        if len(password) == 0:
            errors = True
            flash("Password must be NON-NULL", category="danger")
            
        if password != confirm:
            errors = True
            flash("Password and Confirm must match", category="danger")
            
        if not(errors):
            User.create_user(username=username, password=password, is_admin=True)
            return redirect(url_for('login'))
    
    return render_template('first_use.html')

def allowed_file(filename):
    """return True if filename is allowed for upload, False if not allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<path:path>')
def file_uploads(path):
    """serve up a file in our uploads"""
    print("access path={}".format(path))
    return send_from_directory(app.config['UPLOAD_FOLDER'], path)


@app.route('/page/create', methods=['GET','POST'])
@app.route('/page/edit/<id>', methods=['GET','POST'])
@login_required
def page_edit(id=None):
    """edit or create a page"""
    if id is None:
        id = request.args.get('page_id')    

    page = g.db.pages.find_one({'_id':id})

    if id:
        # if page id was specified in the url and page does not exist, die 404
        if page is None:
            abort(404)
    else:
        # create a NEW page here
        page = {'owner':g.username}

    if page.get('owner') != g.username and not(g.is_admin):
        # if not authorized to edit the page, flash warn
        flash("You are not the page owner",category="danger")
        return redirect(url_for('site',path=page['slug']))    

    # maybe modify this if a different theme is being used
    page_template = 'page_edit.html'
    form = CSRF() # brings in only the CSRF protection of WTForms

    if form.validate_on_submit():
        # the only validation was that the CSRF token was good
        page['content'] = request.form.get('content')
        page['title'] = request.form.get('title')
        page['slug'] = request.form.get('slug')
        page['snippet'] = snippet(page['content'])
        page['is_published'] = request.form.get('is_published') == 'on'
        page['show_title'] = request.form.get('show_title') == 'on'
        page['show_nav'] = request.form.get('show_nav') == 'on'
        # page should be treated as a sidebar, this will come into play later
        page['is_sidebar'] = request.form.get('is_sidebar') == 'on'
        # this is the basic auxilliary CUSTOM content
        # e.g. a theme would have to support a custom template, for now, lets ignore this
        page['template'] = request.form.get('template')
        page['sidebar_right'] = request.form.get('sidebar_right')
        page['sidebar_left'] = request.form.get('sidebar_left')
        page['footer'] = request.form.get('footer')
        if id:
            page['modified_at'] = str(datetime.datetime.now())
        else:
            page['created_at'] = str(datetime.datetime.now())
      
        if not(page['slug']):
            page['slug'] = slugify(page['title'])
        if id:
            # for an existing page, we use update.
            g.db.pages.update_one({'_id':id}, page)
        else:
            # a new page is inserted into collection
            g.db.pages.insert_one(page)

        flash('Page saved.', category="info")
        # redirecting to a slug is equivalent to a path navigation on the site
        return redirect(url_for('site', path=page.get('slug')))


    templates = [('one_column','One column'), ('sidebar_left','Left Sidebar'), 
                 ('sidebar_right','Right Sidebar'), ('front_page','Front page'), ('sidebar_left_right','Sidebar Both')]
    return render_template(page_template, form=form, page=page, id=id, title="Edit page", templates=templates)

    
@app.route('/page/delete/<page_id>')
@login_required
def page_delete(page_id):
    pquery = {'_id':page_id}
    page = g.db.pages.find_one(pquery)
    
    if page.get('owner') != g.username or not(g.is_admin):
        abort(403)
        
    if page is None:
        abort(404)

    g.db.pages.delete_many(pquery)
    # move the deleted page into deleted collection!
    g.db.deleted.insert(page)

    g.db.meta.find_one()
    return redirect(url_for('site'))


@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        flash("the data validated", category="success")
    return render_template('generic_form_ckedit.html', form=form)

@app.route('/search')
def search():
    search_term = request.args.get('s','')
    pages = list(g.db.pages.find())
    found = []
    for page in pages:
        if search_term.lower() in page.get('content').lower():
            found.append(page)
            
    return render_template('search.html', search_term=search_term, pages=found)

@app.route('/upload')
@login_required
def file_upload():
    return render_template('upload_file.html')

# this is the general SITE route "catchment" for page view
@app.route("/")
@app.route("/<path:path>")
def site(path=None):
    """view for pages referenced via their slug (which can look like a path
    If you want to modify what happens when an empty path comes in
    See below, it is redirected to "index" view.  This can be changed via code below.
    """
    s = request.args.get('s')
    if s:
        return redirect( url_for('search', s=s) )

    if path is None:
        """modify here to change behavior of the home-index"""
        path = 'home'

    page = g.db.pages.find_one({'slug': path})
    if page is None:
        abort(404)
        
    ##### removed get shortcodes
    # shortcodes = find_shortcodes(page.get('content'))
    # modify page object with shortcode content directives, return new object
    # page = page_mod_shortcodes(page, shortcodes)
    if page.get('author') is None:
        page['author'] = None
    if page.get('date') is None:
        page['date'] = None
        
    page_template = 'themes/default/page.html'
    try:
        return render_template(page_template, page=page)
    except:
        flash("Template <{}> not found".format(page.get('template')), category="danger")
        return render_template('themes/default/page.html', page=page)


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG)