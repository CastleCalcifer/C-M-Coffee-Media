import os
from flask import Flask, render_template, redirect, url_for, request
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from coffeeInfo import description_choice, popular_picks
from utilities import password_check, fav_or_unfav, favoriting_info, add_coffee_to_cart, add_book_to_cart, add_game_to_cart, add_new_comment, order_number_generator
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, HiddenField, TextAreaField, validators
from wtforms.validators import InputRequired, EqualTo
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_bcrypt import Bcrypt 

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir, 'data.sqlite')
app.config['SQL_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"] = "TEMP KEY"
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
db = SQLAlchemy(app)
Migrate(app, db)

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)


class Favorite(db.Model):
    __tablename__="Favorite"
    
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False) 
    coffee_id = db.Column(db.Integer, db.ForeignKey('Coffee.id'), nullable=False)
    #many to many relationship between user and coffee
    def __init__(self, user_id, coffee_id):
        self. user_id = user_id
        self. coffee_id = coffee_id

        
    def __repr__(self):
        return f"ID: {self.id} user_id: {self.user_id} coffee_id: {self.coffee_id}"
    
class User(UserMixin, db.Model):
    __tablename__="Users"
    
    id = db.Column(db.Integer, primary_key = True)
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    password = db.Column(db.Text)
    email = db.Column(db.Text, unique = True)
    coffees = db.relationship('Coffee', secondary=Favorite.__table__, backref='Users')
    cart = db.relationship('Cart', backref='user', uselist=False, lazy=True)
    admin = db.Column(db.Boolean, nullable=True)
    comments = db.relationship('Comment', back_populates='user', lazy=True)
    """
    line 34 creates a relationship between the user and the cart, backref='user' essentially creates a user attribute for the cart which lets a cart object access
    a user, uselist=False makes it a one-to-one relationship with cart, lazy=True means that cart items won't be loaded unless the cart is accessed
    """
    
    def __init__(self, first_name, last_name, password, email, admin):
        self.first_name = first_name
        self.last_name = last_name
        self.password = password
        self.email = email
        self.admin = admin
        
    def __repr__(self):
        return f"ID: {self.id} Name: {self.first_name} {self.last_name} Email: {self.email} Password: {self.password}"
    

"""
line 56, line 68, line76 creates a new column that allows item to be attached to a cart id (db.ForeignKey('Cart.id'))
(if i am understanding it correctly)
"""

class CartItem(db.Model):
    __tablename__ ='cart_items'

    id = db.Column(db.Integer, primary_key = True)
    coffee_id = db.Column(db.Integer, db.ForeignKey('Coffee.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('Book.id'))
    game_id = db.Column(db.Integer, db.ForeignKey('Videogame.id'))
    cart_id = db.Column(db.Integer, db.ForeignKey('Cart.id'))
    quantity = db.Column(db.Integer, default = 1)
    price = db.Column(db.Float)
    
    def __repr__(self):
        print(f"id: {self.id}, coffee_id {self.coffee_id}, book_id {self.book_id}, game_id {self.game_id}")
    
    
class Coffee(db.Model):
    __tablename__="Coffee"
    
    id = db.Column(db.Integer, primary_key = True)
    coffee_name = db.Column(db.Text, nullable = False)
    fav_count = db.Column(db.Integer)
    users = db.relationship('User', secondary=Favorite.__table__, backref='Coffee')
    stock = db.Column(db.Integer, nullable = False)
    carts = db.relationship('Cart', secondary=CartItem.__table__, back_populates='coffee_items', viewonly=True)
    description = db.Column(db.Text)
    image = db.Column(db.Text)
    comments = db.relationship('Comment', back_populates='coffee')
    def __init__(self, coffee_name, fav_count, stock, description, image):
        self.coffee_name =coffee_name
        self.fav_count = fav_count
        self.stock = stock
        self.description = description
        self.image = image
        
    
    def __repr__(self):
        return f"ID: {self.id} Name: {self.coffee_name} Fav: {self.fav_count}"
    

class Book(db.Model):
    __tablename__="Book"

    id = db.Column(db.Integer, primary_key = True)
    book_name = db.Column(db.Text, nullable = False)
    cart_id = db.Column(db.Integer, db.ForeignKey('Cart.id'), nullable=True)
    stock = db.Column(db.Integer, nullable = False)
    carts = db.relationship('Cart', secondary=CartItem.__table__, back_populates='book_items', viewonly=True)

class VideoGame(db.Model):
    __tablename__="Videogame"

    id = db.Column(db.Integer, primary_key = True)
    game_name = db.Column(db.Text, nullable = False)
    carts = db.relationship('Cart', secondary=CartItem.__table__, back_populates='game_items', viewonly=True)
    stock = db.Column(db.Integer, nullable = False)

class Cart(db.Model):
    __tablename__="Cart"
    
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    coffee_items = db.relationship('Coffee', secondary=CartItem.__table__, back_populates="carts", viewonly=True, lazy=True) 
    book_items = db.relationship('Book', secondary=CartItem.__table__, back_populates='carts', viewonly=True, lazy=True)
    game_items = db.relationship('VideoGame', secondary=CartItem.__table__, back_populates='carts', viewonly=True, lazy=True)
    orders = db.relationship('Order', back_populates='cart')

    """
    cart and the product models are linked by a table called CartItems
    """
    def __repr__(self):
        return f"cart_id: {self.id} user_id: {self.user_id}"

class Order(db.Model):
    __tablename__="orders"

    id = db.Column(db.Integer, primary_key = True)
    order_number = db.Column(db.Integer, default=None)
    cart_id = db.Column(db.Integer, db.ForeignKey('Cart.id'))
    cart = db.relationship('Cart', back_populates='orders')

class Comment(db.Model):
    __tablename__='Comments'

    id = db.Column(db.Integer, primary_key = True)

    summary = db.Column('Summary', db.String(100))
    comment = db.Column('Comment', db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    user = db.relationship('User', back_populates='comments', lazy=True)
    coffee_id = db.Column(db.Integer, db.ForeignKey('Coffee.id'))
    coffee = db.relationship('Coffee', back_populates='comments', lazy=True)



with app.app_context():
    db.create_all()

    #The next set of lines would be not be here in a live application, this is just for project purposes to make sure the database is initialized properly
    coffee = Coffee.query.filter_by(coffee_name='Second Breakfast').first()
    if not coffee:
        desc = description_choice("Second Breakfast")
        db.session.add(Coffee(coffee_name='Second Breakfast', fav_count=0, stock=10, description=desc[2], image=desc[1] ))
        desc = description_choice("The Roast of Leaves")
        db.session.add(Coffee(coffee_name='The Roast of Leaves', fav_count=0, stock = 10, description=desc[2], image=desc[1]))
        desc = description_choice("Mercer's Blend")
        db.session.add(Coffee(coffee_name="Mercer's Blend", fav_count=0, stock = 10, description=desc[2], image=desc[1]))
        desc = description_choice("The Silverhand Special")
        db.session.add(Coffee(coffee_name='The Silverhand Special', fav_count=0, stock = 10, description=desc[2], image=desc[1]))
        desc = description_choice("Western Nostalgia")
        db.session.add(Coffee(coffee_name='Western Nostalgia', fav_count=0, stock = 10, description=desc[2], image=desc[1]))
        desc = description_choice("Potion of Energy")
        db.session.add(Coffee(coffee_name='Potion of Energy', fav_count=0, stock = 10, description=desc[2], image=desc[1]))
        db.session.add(Book(book_name='The Lord of the Rings', stock = 10))
        db.session.add(Book(book_name='The House of Leaves', stock = 10))
        db.session.add(Book(book_name='Do Androids Dream of Electric Sheep?', stock = 10))
        db.session.add(VideoGame(game_name='Cyberpunk 2077', stock = 10))
        db.session.add(VideoGame(game_name='Red Dead Redemption 2', stock = 10))
        db.session.add(VideoGame(game_name='Minecraft', stock = 10))
        db.session.commit()
        
    admin_login = User.query.filter_by(email="admin@coffeeshop.com").first() 
    if not admin_login:
        hashed_admin = bcrypt.generate_password_hash("admin").decode('utf-8') 
        new_admin = User(first_name="admin", last_name="admin", password=hashed_admin, email="admin@coffeeshop.com", admin=True)
        db.session.add(new_admin)
        db.session.commit()
         # Create a cart for the new user
        newCart = Cart(user_id=new_admin.id)
        db.session.add(newCart)
                
        # Commit the transaction
        db.session.commit()


"""
The forms for the signin and signup methods
"""
class SignInForm(FlaskForm):
    email = StringField('Email:', validators = [InputRequired()])
    password = PasswordField('Password:', validators = [InputRequired()])
    submit = SubmitField('Sign In')

class SignUpForm(FlaskForm):
    email = StringField('Email:', validators = [InputRequired()])
    password = PasswordField('Password:', validators = [InputRequired()])
    confirm_password = PasswordField('Confirm Password:', validators=[InputRequired(), EqualTo('password', message='Passwords must be the same')])
    first_name = StringField('First Name:', validators = [InputRequired()])
    last_name = StringField('Last Name:', validators = [InputRequired()])
    submit = SubmitField('Sign Up')

class FavoriteButton(FlaskForm):
    field1 = HiddenField('Favorite Button')
    submit = SubmitField('Favorite')
    
"""Lord of the Rings"""
class SelectLotrItemsForm(FlaskForm):
    product_choice = SelectField(choices=[('Second Breakfast','Second Breakfast'), ('The Lord of the Rings','The Lord of the Rings')])
    submit = SubmitField('Add to Cart')

"""House of Leaves"""
class SelectHoLItemsForm(FlaskForm):
    product_choice = SelectField(choices=[('The Roast of Leaves','The Roast of Leaves'), ('The House of Leaves','The House of Leaves')])
    submit = SubmitField('Add to Cart')


"""Do Androids Dream of Electric Sheep?"""
class SelectAtMoMItemsForm(FlaskForm):
    product_choice = SelectField(choices=[("Mercer's Blend","Mercer's Blend"), ('Do Androids Dream of Electric Sheep?','Do Androids Dream of Electric Sheep?')])
    submit = SubmitField('Add to Cart')

class SelectCyberPunkItemsForm(FlaskForm):
    product_choice = SelectField(choices=[('The Silverhand Special','The Silverhand Special'), ('Cyberpunk 2077','Cyberpunk 2077')])
    submit = SubmitField('Add to Cart')

class SelectRDRItemsForm(FlaskForm):
    product_choice = SelectField(choices=[('Western Nostalgia','Western Nostalgia'), ('Red Dead Redemption 2','Red Dead Redemption 2')])
    submit = SubmitField('Add to Cart')

class SelectMCItemsForm(FlaskForm):
    product_choice = SelectField(choices=[('Potion of Energy','Potion of Energy'), ('Minecraft','Minecraft')])
    submit = SubmitField('Add to Cart')

class MyModelView(ModelView):
    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.admin:
                return True

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('index'))

class MyAdminView(AdminIndexView):
    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.admin:
                return True

    def inaccessible_callback(self, name, **kwargs): #any normal user that tries to access /admin immediately gets kick backed to the home page
        return redirect(url_for('index'))

#admin view initialization
admin = Admin(app, index_view=MyAdminView())
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Coffee, db.session))
admin.add_view(MyModelView(VideoGame, db.session))
admin.add_view(MyModelView(Book, db.session))
admin.add_view(MyModelView(Order, db.session))
admin.add_view(MyModelView(Comment, db.session))



class CreateCommentForm(FlaskForm):
    summary = TextAreaField('Summary', [validators.optional(), validators.length(max=100)])
    comment = TextAreaField('Comment', [validators.optional(), validators.length(max=500)])
    submit = SubmitField('Post Comment')

@login_manager.user_loader
def get_user(user_id):
    return User.query.get(user_id)

#Renders the home page
@app.route('/')
def index():
    '''
    Grabs the top 3 most popular coffee and displays them on the front page
    '''
    favorites = Coffee.query.order_by(desc(Coffee.fav_count)).all()
    popular1 = popular_picks(favorites[0].coffee_name) 
    popular2 = popular_picks(favorites[1].coffee_name)
    popular3 = popular_picks(favorites[2].coffee_name)
    return render_template('index.html', popular1=popular1, popular2=popular2, popular3=popular3)


#Sign In
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SignInForm()
    if form.validate_on_submit(): #User submits the form
        email = form.email.data
        password = form.password.data
        user = db.session.query(User).filter(User.email==email).first() #queries the database, looking if there is a combination in the database
        if user is not None: #Is there a user? If so check their password hash
            hash_check = bcrypt.check_password_hash(user.password, password) 
            if user.admin and hash_check: #is this person an admin? Sign them in and take them to admin view
                login_user(user)
                return redirect(url_for('admin.index'))
            elif hash_check:
                login_user(user)
                return redirect(url_for('CoffeeList'))
    elif request.method == 'GET':
        return render_template('signin.html', form=form) #User clicks navbar link
    return render_template('signin.html', error_message=Markup("<h2>Incorrect username or password"), form=form) #wrong username or password


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit(): #User submits the form
        first_name:str = form.first_name.data
        last_name:str = form.last_name.data
        email:str = form.email.data
        password:str = form.password.data
        confirm_password:str = form.confirm_password.data
        
        password_info:list = password_check(password, confirm_password) #located in utilities, checks if password meets requirements
        print(password_info)
        if password_info[0]: #password met requirements!
            try:
                password_hash = bcrypt.generate_password_hash(password).decode('utf-8') 
                new_user = User(first_name=first_name, last_name=last_name, password=password_hash, email=email, admin=False)
                db.session.add(new_user)
                db.session.flush()  # Ensure the user ID is available
                
                # Create a cart for the new user
                newCart = Cart(user_id=new_user.id)
                db.session.add(newCart)
                
                # Commit the transaction
                db.session.commit()
                return redirect(url_for('signin', error_message="Thank you, please sign in")) #redirects them to the sign in page, letting them know it worked
            except IntegrityError:
                print("email error")
                return render_template('signup.html', form=form, error_message=Markup("<h3 class='error_message'>Email already in database</h3>")) #email in database, try again
        else: #password failed, error message located in second element of list.
            print(f"form error {password_info}")
            return render_template('signup.html', form=form, error_message=password_info[1])
    elif request.method == 'GET':
        return render_template('signup.html', form=form)
        
    return render_template('signup.html', form=form, error_message=Markup("<h3 class='error_message'>Passwords did not match!</h3>"))

#A fun reference, should be removed later
@app.route('/secretpage', methods=['GET', 'POST'])
def secretpage():
        return render_template('secretpage.html', message=Markup(f"<h1>My name is Chris Houlihan. <br> This is my top secret page. <br> Keep it between us, OK?</h1>"))    

@app.route("/signout")
def signout():
    logout_user()
    return redirect(url_for("index"))

# renders the cart
@app.route('/cart')
@login_required
def cart():
    if current_user:
        coffee_class = Coffee
        book_class = Book
        game_class = VideoGame
        cart_items = CartItem.query.filter_by(cart_id=current_user.id).all()
        total = 0
        for item in cart_items:
            total = total + item.quantity * item.price
        return render_template('cart.html', total=total,
                               cart_items=cart_items,
                               coffee_class=coffee_class,
                               book_class=book_class,
                               game_class=game_class)
    else:
        return render_template('SecretPage.html')
    
@app.route("/delete-coffee/<int:coffee_id>", methods=['POST'])
@login_required
def delete_coffee(coffee_id):
    cart_item = CartItem.query.filter_by(cart_id=current_user.id, coffee_id=coffee_id).first_or_404()
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        db.session.commit()
    elif cart_item.quantity <= 1:
        db.session.delete(cart_item)
        db.session.commit()
    return redirect(url_for('cart'))

@app.route("/delete-book/<int:book_id>", methods=['POST'])
def delete_book(book_id):
    book_item = CartItem.query.filter_by(cart_id=current_user.id, book_id=book_id).first_or_404()
    if book_item.quantity > 1:
        book_item.quantity -= 1
        db.session.commit()
    elif book_item.quantity <= 1:
        db.session.delete(book_item)
        db.session.commit()
    return redirect(url_for('cart'))

@app.route("/delete-game/<int:game_id>", methods=['POST'])
def delete_game(game_id):
    game_item = CartItem.query.filter_by(cart_id=current_user.id, game_id=game_id).first_or_404()
    if game_item.quantity > 1:
        game_item.quantity -= 1
        db.session.commit()
    elif game_item.quantity <= 1:
        db.session.delete(game_item)
        db.session.commit()
    return redirect(url_for('cart'))

@app.route("/delete-cart-items", methods=['POST'])
def delete_cart_items():
    cart_items = CartItem.query.filter_by(cart_id=current_user.id).all()
    for item in cart_items:
        db.session.delete(item)
    db.session.commit()
    return(redirect(url_for('CoffeeList')))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    coffee_class = Coffee
    book_class = Book
    game_class = VideoGame
    cart_id = current_user.id
    new_order = Order(order_number=order_number_generator(Order), cart_id=cart_id)
    cart_items = CartItem.query.filter_by(cart_id=current_user.id)
    error_message = None
    for item in cart_items:
        if item.coffee_id is not None and Coffee.query.filter_by(id=item.coffee_id).first().stock <= 0:
            error_message = f"{Coffee.query.filter_by(id=item.coffee_id).first().coffee_name} is out of stock!"
        elif item.game_id is not None and VideoGame.query.filter_by(id=item.game_id).first().stock <= 0:
            error_message = f"{VideoGame.query.filter_by(id=item.game_id).first().game_name} is out of stock!"
        elif item.book_id is not None and Book.query.filter_by(id=item.book_id).first().stock <= 0:
            error_message = f"{Book.query.filter_by(id=item.book_id).first().book_name} is out of stock!"
        if error_message is not None:
            return render_template('checkout.html',  total=0,
                    cart_items=cart_items, 
                    coffee_class=coffee_class, 
                    book_class=book_class, 
                    game_class=game_class,
                    cart_id=cart_id,
                    error_message=error_message)
    db.session.add(new_order)
    db.session.commit()
    db.session.flush()
    if new_order.order_number == None or not cart_items:
        new_order.order_number = order_number_generator(Order)
        print(new_order.order_number)
        db.session.commit()
    order_number = new_order.order_number
    cart_items = CartItem.query.filter_by(cart_id=current_user.id)
    total = 0
    for item in cart_items:
            total = total + item.quantity * item.price
            for item in cart_items:
                if item.coffee_id is not None:
                    Coffee.query.filter_by(id=item.coffee_id).first().stock = Coffee.stock - item.quantity
                elif item.game_id is not None:
                    VideoGame.query.filter_by(id=item.game_id).first().stock = VideoGame.stock - item.quantity
                elif item.book_id is not None:
                    Book.query.filter_by(id=item.book_id).first().stock = Book.stock - item.quantity
    db.session.commit()
    return render_template('checkout.html',  total=total, 
                           order_number=order_number, 
                           cart_items=cart_items, 
                           coffee_class=coffee_class, 
                           book_class=book_class, 
                           game_class=game_class,
                           cart_id=cart_id)

@app.route('/CoffeeList')
def CoffeeList():
    return render_template('CoffeeList.html')

#Renders the coffee list

#favoriting_info and fav_or_unfav located in utilities.py
@app.route('/SecondBreakfast', methods=['GET', 'POST'])
def SecondBreakfast():
    drop_down = SelectLotrItemsForm(prefix='cart')
    coffee_id = Coffee.query.filter_by(coffee_name='Second Breakfast').first().id
    user = current_user
    favorite_button = FavoriteButton(prefix='favorite')
    current_coffee = db.session.query(Coffee).filter(Coffee.coffee_name=="Second Breakfast").first()
    if current_user.is_authenticated:
        favorite_info:list = favoriting_info(db, current_user, favorite_button, current_coffee) #index 0 is current_coffee row, index 1 is the modified favorite button
        fav_unfav_button = favorite_info[1]
    else:
        fav_unfav_button = ""
    if favorite_button.validate_on_submit():
        fav_or_unfav(db, favorite_info[1], favorite_info[0], current_user, Favorite, Coffee)
        
    if drop_down.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        product = drop_down.product_choice.data
        if product == 'Second Breakfast':
            add_coffee_to_cart(db, 'Second Breakfast', current_user.cart, Coffee, CartItem, 19.99)
        elif product == 'The Lord of the Rings':
            add_book_to_cart(db, 'The Lord of the Rings', current_user.cart, Book, CartItem, 89.99)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        add_new_comment(db, comment_form.summary.data, comment_form.comment.data, current_user, coffee_id, Comment)
    user_comments_list = Comment.query.filter_by(coffee_id=coffee_id).all()
    return render_template('CoffeePage.html', user=user, coffee_name=current_coffee.coffee_name, coffee_image=current_coffee.image, coffee_description=current_coffee.description, drop_down=drop_down, comment_form=comment_form, user_comments_list=user_comments_list, fav_unfav_button=fav_unfav_button, fav_number=current_coffee.fav_count)


@app.route('/TheRoastOfLeaves', methods=['GET', 'POST'])
def TheRoastOfLeaves():
    drop_down = SelectHoLItemsForm(prefix='cart')
    coffee_id = Coffee.query.filter_by(coffee_name='The Roast of Leaves').first().id
    favorite_button = FavoriteButton(prefix='favorite')
    current_coffee = db.session.query(Coffee).filter(Coffee.coffee_name=="The Roast of Leaves").first()
    if current_user.is_authenticated:
        favorite_info:list = favoriting_info(db, current_user, favorite_button, current_coffee) #index 0 is current_coffee row, index 1 is the modified favorite button
        fav_unfav_button = favorite_info[1]
    else:
        fav_unfav_button = "" #If the user is not logged in, it will throw a index out of bounds error
        
    if favorite_button.validate_on_submit():
        fav_or_unfav(db, favorite_info[1], favorite_info[0], current_user, Favorite, Coffee)
        
    if drop_down.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        product = drop_down.product_choice.data
        if product == 'The Roast of Leaves':
            add_coffee_to_cart(db, 'The Roast of Leaves', current_user.cart, Coffee, CartItem, 19.99)
        elif product == 'The House of Leaves':
            add_book_to_cart(db, 'The House of Leaves', current_user.cart, Book, CartItem, 29.99)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        add_new_comment(db, comment_form.summary.data, comment_form.comment.data, current_user, coffee_id, Comment)
    user_comments_list = Comment.query.filter_by(coffee_id=coffee_id).all()
    return render_template('CoffeePage.html', coffee_name=current_coffee.coffee_name, coffee_image=current_coffee.image, coffee_description=current_coffee.description, drop_down=drop_down, comment_form=comment_form, user_comments_list=user_comments_list, fav_unfav_button=fav_unfav_button, fav_number=current_coffee.fav_count)

@app.route('/MercersBlend', methods=['GET', 'POST'])
def MercersBlend():
    drop_down = SelectAtMoMItemsForm(prefix='cart')
    favorite_button = FavoriteButton(prefix='favorite')
    current_coffee = db.session.query(Coffee).filter(Coffee.coffee_name=="Mercer's Blend").first()
    if current_user.is_authenticated:
        favorite_info:list = favoriting_info(db, current_user, favorite_button, current_coffee) #index 0 is current_coffee row, index 1 is the modified favorite button
        fav_unfav_button = favorite_info[1]
    else:
        fav_unfav_button = ""   
    if favorite_button.validate_on_submit():
        fav_or_unfav(db, favorite_info[1], favorite_info[0], current_user, Favorite, Coffee)
        fav_unfav_button = favorite_info[1]
        
    coffee_id = Coffee.query.filter_by(coffee_name="Mercer's Blend").first().id
    if drop_down.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        product = drop_down.product_choice.data
        if product == "Mercer's Blend":
            add_coffee_to_cart(db, "Mercer's Blend", current_user.cart, Coffee, CartItem, 19.99)
        elif product == 'Do Androids Dream of Electric Sheep?':
            add_book_to_cart(db, 'Do Androids Dream of Electric Sheep?', current_user.cart, Book, CartItem, 25.99)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        add_new_comment(db, comment_form.summary.data, comment_form.comment.data, current_user, coffee_id, Comment)
    user_comments_list = Comment.query.filter_by(coffee_id=coffee_id).all()
    return render_template('CoffeePage.html', coffee_name=current_coffee.coffee_name, coffee_image=current_coffee.image, coffee_description=current_coffee.description, drop_down=drop_down, comment_form=comment_form, user_comments_list=user_comments_list, fav_unfav_button=fav_unfav_button, fav_number=current_coffee.fav_count)

@app.route('/TheSilverhandSpecial', methods=['GET', 'POST'])
def silver_hand_special():
    drop_down = SelectCyberPunkItemsForm(prefix='cart')

    coffee_id = Coffee.query.filter_by(coffee_name='The Silverhand Special').first().id
    favorite_button = FavoriteButton(prefix='favorite')
    current_coffee = db.session.query(Coffee).filter(Coffee.coffee_name=="The Silverhand Special").first()
    if current_user.is_authenticated:
        favorite_info:list = favoriting_info(db, current_user, favorite_button, current_coffee) #index 0 is current_coffee row, index 1 is the modified favorite button
        fav_unfav_button = favorite_info[1]
    else:
        fav_unfav_button = "" #If the user is not logged in, it will throw a index out of bounds error
        
    if favorite_button.validate_on_submit():
        fav_or_unfav(db, favorite_info[1], favorite_info[0], current_user, Favorite, Coffee)
        
    if drop_down.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        product = drop_down.product_choice.data
        if product == 'The Silverhand Special':
            add_coffee_to_cart(db, 'The Silverhand Special', current_user.cart, Coffee, CartItem, 19.99)
        elif product == 'Cyberpunk 2077':
            add_game_to_cart(db, 'Cyberpunk 2077', current_user.cart, VideoGame, CartItem, 59.99)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        add_new_comment(db, comment_form.summary.data, comment_form.comment.data, current_user, coffee_id, Comment)
    user_comments_list = Comment.query.filter_by(coffee_id=coffee_id).all()
    return render_template('CoffeePage.html', coffee_name=current_coffee.coffee_name, coffee_image=current_coffee.image, coffee_description=current_coffee.description, drop_down=drop_down, comment_form=comment_form, user_comments_list=user_comments_list, fav_unfav_button=fav_unfav_button, fav_number=current_coffee.fav_count)

@app.route('/WesternNostalgia', methods=['GET', 'POST'])
def western_nostalgia():
    drop_down = SelectRDRItemsForm(prefix='cart')

    coffee_id = Coffee.query.filter_by(coffee_name='Western Nostalgia').first().id
    favorite_button = FavoriteButton(prefix='favorite')
    current_coffee = db.session.query(Coffee).filter(Coffee.coffee_name=="Western Nostalgia").first()
    if current_user.is_authenticated:
        favorite_info:list = favoriting_info(db, current_user, favorite_button, current_coffee) #index 0 is current_coffee row, index 1 is the modified favorite button
        fav_unfav_button = favorite_info[1]
    else:
        fav_unfav_button = "" #If the user is not logged in, it will throw a index out of bounds error
        
    if favorite_button.validate_on_submit():
        fav_or_unfav(db, favorite_info[1], favorite_info[0], current_user, Favorite, Coffee)
        
    if drop_down.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        product = drop_down.product_choice.data
        if product == 'Western Nostalgia':
            add_coffee_to_cart(db, 'Western Nostalgia', current_user.cart, Coffee, CartItem, 19.99)
        elif product == 'Red Dead Redemption 2':
            add_game_to_cart(db, 'Red Dead Redemption 2', current_user.cart, VideoGame, CartItem, 59.99)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        add_new_comment(db, comment_form.summary.data, comment_form.comment.data, current_user, coffee_id, Comment)
    user_comments_list = Comment.query.filter_by(coffee_id=coffee_id).all()
    return render_template('CoffeePage.html', coffee_name=current_coffee.coffee_name, coffee_image=current_coffee.image, coffee_description=current_coffee.description, drop_down=drop_down, comment_form=comment_form, user_comments_list=user_comments_list, fav_unfav_button=fav_unfav_button, fav_number=current_coffee.fav_count)

@app.route('/PotionOfEnergy', methods=['GET', 'POST'])
def potion_of_energy():
    drop_down = SelectMCItemsForm(prefix='cart')

    coffee_id = Coffee.query.filter_by(coffee_name='Potion of Energy').first().id
    favorite_button = FavoriteButton(prefix='favorite')
    current_coffee = db.session.query(Coffee).filter(Coffee.coffee_name=="Potion of Energy").first()
    if current_user.is_authenticated:
        favorite_info:list = favoriting_info(db, current_user, favorite_button, current_coffee) #index 0 is current_coffee row, index 1 is the modified favorite button
        fav_unfav_button = favorite_info[1]
    else:
        fav_unfav_button = "" #If the user is not logged in, it will throw a index out of bounds error
        
    if favorite_button.validate_on_submit():
        fav_or_unfav(db, favorite_info[1], favorite_info[0], current_user, Favorite, Coffee)
        
    if drop_down.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        product = drop_down.product_choice.data
        if product == 'Potion of Energy':
            add_coffee_to_cart(db, 'Potion of Energy', current_user.cart, Coffee, CartItem, 19.99)
        if product == 'Minecraft':
            add_game_to_cart(db, 'Minecraft', current_user.cart, VideoGame, CartItem, 19.99)
    comment_form = CreateCommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("signin"))
        add_new_comment(db, comment_form.summary.data, comment_form.comment.data, current_user, coffee_id, Comment)
    user_comments_list = Comment.query.filter_by(coffee_id=coffee_id).all()
    return render_template('CoffeePage.html', coffee_name=current_coffee.coffee_name, coffee_image=current_coffee.image, coffee_description=current_coffee.description, drop_down=drop_down, comment_form=comment_form, user_comments_list=user_comments_list, fav_unfav_button=fav_unfav_button, fav_number=current_coffee.fav_count)

if __name__ == "__main__":
    app.run(debug=True)
