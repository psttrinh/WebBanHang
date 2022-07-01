from itertools import product

from flask import Flask, render_template, flash, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from wtforms.widgets import TextArea
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_ckeditor import CKEditor, CKEditorField
import smtplib

# create a flask instance
app = Flask(__name__)
# Add CKEditor
ckeditor = CKEditor(app)
# Add Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# Secret key!
app.config['SECRET_KEY'] = "my super secret key that no onw supposed to know"
# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask_Login Stuff
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# Create Login Form
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


# Create A Search Form
class SearchForm(FlaskForm):
    searched = StringField("Searched", validators=[DataRequired()])
    submit = SubmitField("Submit")


# Pass Stuff To Navbar
@app.context_processor
def base():
    form = SearchForm()
    return dict(form=form)


# Create Admin page
@app.route('/admin')
@login_required
def admin():
    id = current_user.id
    if id == 1:
        render_template("admin.html")
    else:
        flash("Sorry you must be the Admin to access this page")
        return redirect(url_for('dashboard'))
    return render_template("admin.html")


# Create Search Funtion
@app.route('/search_product', methods=['GET', 'POST'])
def search():
    key = request.form['search']
    product_search = Product.query.all()
    key = key.lower()
    a = key.split(' ')
    print(type(a))
    return render_template('search_product.html', product=product_search, key=key, a=a)


# Create Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            if user.password == form.password.data:
                login_user(user)
                flash("Login Successfully!!")
                return redirect(url_for('dashboard'))
            else:
                flash("Cannot Log In")
        else:
            flash("That User doesn't exist")
    return render_template('login.html', form=form)


# Create Logout Page
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("You Have Been Logged Out!")
    return redirect(url_for('login'))


# Create Dashboard Page
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = UserForm()
    id = current_user.id
    name_to_update = Users.query.get_or_404(id)
    if request.method == "POST":
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        name_to_update.favorite_color = request.form['favorite_color']
        name_to_update.username = request.form['username']
        name_to_update.password = request.form['password']
        try:
            db.session.commit()
            flash("Updated Successfully!")
            return render_template("dashboard.html", form=form, name_to_update=name_to_update, id=id)
        except:
            flash("Error!")
            return render_template("dashboard.html", form=form, name_to_update=name_to_update, id=id)
    else:
        return render_template("dashboard.html", form=form, name_to_update=name_to_update, id=id)
    return render_template('dashboard.html')


# Create a Blog Post model
class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow())
    slug = db.Column(db.String(255))


# Create a Posts Form
class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    # content = StringField("Content", validators=[DataRequired()], widget=TextArea())
    content = CKEditorField('Content', validators=[DataRequired()])
    author = StringField("Author", validators=[DataRequired()])
    slug = StringField("Slug", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route('/posts/delete/<int:id>')
@login_required
def delete_post(id):
    post_to_delete = Posts.query.get_or_404(id)
    name = current_user.name
    if name == post_to_delete.post.author:
        try:
            db.session.delete(post_to_delete)
            db.session.commit()

            # Return a message
            flash("Blog Post Was Deleted!")
            # Grab all the ports from the database
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template("posts.html", posts=posts)
        except:
            # Return an error message
            flash("Whoop! There was a problem deleting post, try again...")

            # Grab all the ports from the database
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template("posts.html", posts=posts)
    else:
        # Return a message
        flash("You are Not Authorized to delete!")
        # Grab all the ports from the database
        posts = Posts.query.order_by(Posts.date_posted)
        return render_template("posts.html", posts=posts)


@app.route('/posts.html/')
@app.route('/posts/')
def posts():
    # Grab all the ports from the database
    # posts = Posts.query.order_by(Posts.date_posted)
    posts = Posts.query.order_by(Posts.date_posted.desc())
    page = request.args.get('page')
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    pages = posts.paginate(page=page, per_page=2)
    return render_template("posts.html", posts=posts, pages=pages)


@app.route('/posts/<int:id>')
def post(id):
    post = Posts.query.get_or_404(id)
    return render_template('post.html', post=post)


# @app.route('/detail.html')
@app.route('/detail/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('detail.html', product=product)


@app.route('/category/<string:type>')
def type_category(type):
    print(type)
    product = Product.query.all()
    return render_template('category.html', product=product, type=type)


@app.route('/posts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Posts.query.get_or_404(id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.author = form.author.data
        post.slug = form.slug.data
        post.content = form.content.data
        # Update Database
        db.session.add(post)
        db.session.commit()
        flash("Post Has Been Updated!")
        return redirect(url_for('post', id=post.id))
    if current_user.name == post.author:
        form.title.data = post.title
        form.author.data = post.author
        form.slug.data = post.slug
        form.content.data = post.content
        return render_template('edit_post.html', form=form)
    else:
        flash("You are Not Authorized To Edit This Post.")
        posts = Posts.query.order_by(Posts.date_posted)
        return render_template("posts.html", posts=posts)


# Add Post Page
@app.route('/add-post', methods=['GET', 'POST'])
# @login_required
def add_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Posts(title=form.title.data, content=form.content.data,
                     author=form.author.data, slug=form.slug.data)
        # Clear the form
        form.title.data = ''
        form.content.data = ''
        form.author.data = ''
        form.slug.data = ''

        # Add post data to database
        db.session.add(post)
        db.session.commit()

        # Return a message
        flash("Blog Post Submitted Successfully!")

    # Redirect to the webpage
    return render_template("add_post.html", form=form)


# Create model
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    favorite_color = db.Column(db.String(120))
    date_added = db.Column(db.DateTime, default=datetime.utcnow())

    # Create a String
    def __repr__(self):
        return '<Name %r>' % self.name


# Shop Form
@app.route('/', methods=['GET', 'POST'])
@app.route('/<int:page>', methods=['GET', 'POST'])
@app.route('/shop.html')
def shop():
    # product = Product.query.limit(9).all()
    # order_by(Product.id.desc())
    posts = Posts.query.order_by(Posts.date_posted.desc())
    page = request.args.get('page')
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    pages = posts.paginate(page=page, per_page=1)

    product = Product.query.order_by(Product.id.desc())
    product_page = request.args.get('product_page')
    if product_page and product_page.isdigit():
        product_page = int(product_page)
    else:
        product_page = 1
    product_pages = product.paginate(page=product_page, per_page=6)
    # # Search Product
    # if request.method == 'POST' and 'tag' in request.form:
    #     tag = request.form["tag"]
    #     search = "%{}%".format(tag)
    #     product = Product.query.filter(Product.name.like(search)).paginate(page=product_page, error_out=False)
    #     return render_template('shop.html', product=product, tag=tag)
    return render_template("shop.html",
                           product=product, product_pages=product_pages,
                           posts=posts, pages=pages)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(500), nullable=False)
    unitprice = db.Column(db.Text, nullable=False)
    detail = db.Column(db.String(500), nullable=False)
    picture = db.Column(db.String(500), nullable=False)
    picture1 = db.Column(db.String(500), nullable=False)
    quatity = db.Column(db.Integer, nullable=False)


@app.route('/delete/<int:id>')
def delete(id):
    user_to_delete = Users.query.get_or_404(id)
    name = None
    form = UserForm()
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User Deleted Successfully!!")

        our_users = Users.query.order_by(Users.date_added)
        return render_template("add_user.html",
                               form=form,
                               name=name,
                               our_users=our_users)
    except:
        flash("Whoops! There was a problem deleting user, try again...")
        return render_template("add_user.html",
                               form=form,
                               name=name,
                               our_users=our_users)


# create a form class
class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    username = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    favorite_color = StringField("Favorite Color", validators=[DataRequired()])
    submit = SubmitField("Submit")


# Update DB Record
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)
    if request.method == "POST":
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        name_to_update.favorite_color = request.form['favorite_color']
        name_to_update.username = request.form['username']
        name_to_update.password = request.form['password']
        try:
            db.session.commit()
            flash("Updated Successfully!")
            return render_template("update.html", form=form, name_to_update=name_to_update, id=id)
        except:
            flash("Error!")
            return render_template("update.html", form=form, name_to_update=name_to_update, id=id)
    else:
        return render_template("update.html", form=form, name_to_update=name_to_update, id=id)


# create a form class
class NamerForm(FlaskForm):
    name = StringField("What's Your Name", validators=[DataRequired()])
    submit = SubmitField("Submit")


# def index():
#     return "<h1>Hello World</h1>"

@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    name = None
    form = UserForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user is None:
            user = Users(username=form.username.data, password=form.password.data, name=form.name.data,
                         email=form.email.data, favorite_color=form.favorite_color.data)
            db.session.add(user)
            db.session.commit()
        name = form.name.data
        form.name.data = ''
        form.username.data = ''
        form.password.data = ''
        form.email.data = ''
        form.favorite_color.data = ''

        flash("User Added Successfully!")
    our_users = Users.query.order_by(Users.date_added)
    return render_template("add_user.html",
                           form=form,
                           name=name,
                           our_users=our_users)


# create a route decorator
@app.route('/index')
def index():
    first_name = "Noice"
    stuff = "This is Bold Text"
    # flash("Welcome To Our Website!")
    favorite_pizza = ["Pepperoni", "Cheese", "Mushrooms", 41]
    return render_template("index.html",
                           first_name=first_name,
                           stuff=stuff,
                           favorite_pizza=favorite_pizza)


# localhost:5000
@app.route('/user/<name>')
def user(name):
    return render_template("user.html", user_name=name)


# Create custom error pages
# Invalid URL
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Internal Server Error
@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500


# Create Name page
@app.route('/name', methods=['GET', 'POST'])
def name():
    name = None
    form = NamerForm()
    # Validate Form
    if form.validate_on_submit():
        name = form.name.data
        form.name.data = ''
        flash("Form Submitted Successfully!")
    return render_template("name.html",
                           name=name,
                           form=form)


@app.route('/contact')
@app.route('/contact.html')
def contact():
    return render_template('contactform.html')

 # Contact Funtion
@app.route('/formContact', methods=['GET', 'POST'])
def sendContactForm():
    name = request.form['fullname']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['msg']
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        # region Login
        # Mail cá nhân người dùng (công ty) -- password
        smtp.login('@gmail.com', '')
        # endregion
        subject = subject
        body = "Guess name: " + name + "\nEmail: " + email + "\n" + "Message: " + message
        # body = u' '.join((name, email, message)).encode('utf-8').strip()
        # body = r.join((name, '\n', email, '\n', message)).encode('utf-8').strip()
        msg = f'Subject: {subject}\n\n{body}'.encode('utf-8').strip()
        # mail người dùng (công ty) --- mail đến
        smtp.sendmail('@gmail.com', '@uef.edu.vn', msg)
    return redirect(url_for('contact'))


@app.route('/qrshow')
@app.route('/qrshow.html')
def showAR():
    return render_template('qrshow.html')


if __name__ == '__main__':
    app.jinja_env.cache = {}
    app.run(debug=True, threaded=True)
