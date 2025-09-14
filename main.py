from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import ImageUploadField
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import datetime
import os

# -----------------------
# Flask App Config
# -----------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey123"

# Upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -----------------------
# Database
# -----------------------
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    image = db.Column(db.String(200))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    item = db.relationship('MenuItem', backref=db.backref('orders', lazy=True))

with app.app_context():
    db.create_all()

# -----------------------
# Flask-Admin
# -----------------------
class MenuItemAdmin(ModelView):
    column_list = ('name', 'price', 'description', 'image')
    form_columns = ('name', 'price', 'description', 'image')
    
    form_overrides = {'image': ImageUploadField}
    form_args = {
        'image': {
            'label': 'Menu Image',
            'base_path': os.path.join(os.path.dirname(__file__), 'static/uploads'),
            'allow_overwrite': False,
            'namegen': lambda obj, file_data: datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file_data.filename)
        }
    }

    # Keep old image if no new file is uploaded
    def on_model_change(self, form, model, is_created):
        if not form.image.data and not is_created:
            form.image.data = model.image

admin = Admin(app, name="Smart Restaurant Admin", template_mode="bootstrap4")
admin.add_view(MenuItemAdmin(MenuItem, db.session))
admin.add_view(ModelView(Order, db.session))

# -----------------------
# Routes
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/menu")
def menu():
    items = MenuItem.query.all()
    return render_template("menu.html", items=items)

@app.route("/cart")
def cart():
    cart_items = session.get("cart", {})
    return render_template("cart.html", cart_items=cart_items)

# -----------------------
# Cart Routes
# -----------------------
@app.route("/add-to-cart/<int:item_id>", methods=["POST"])
def add_to_cart(item_id):
    item = MenuItem.query.get_or_404(item_id)
    quantity = int(request.get_json().get("quantity", 1)) if request.is_json else int(request.form.get("quantity", 1))

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    if str(item.id) in cart:
        cart[str(item.id)]["quantity"] += quantity
    else:
        cart[str(item.id)] = {
            "name": item.name,
            "price": item.price,
            "quantity": quantity,
            "image": item.image
        }

    session.modified = True

    if request.is_json:
        return jsonify({
            "success": True,
            "message": f"{item.name} added to cart!",
            "cart_count": sum(i['quantity'] for i in cart.values()),
            "new_item": {
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "quantity": quantity,
                "image": item.image
            }
        })
    return redirect(url_for("menu"))

@app.route("/update-cart/<int:item_id>", methods=["POST"])
def update_cart(item_id):
    change = int(request.form.get("change", 0))
    cart = session.get("cart", {})
    item_id_str = str(item_id)

    if item_id_str in cart:
        cart[item_id_str]["quantity"] += change
        if cart[item_id_str]["quantity"] <= 0:
            del cart[item_id_str]

    session["cart"] = cart
    session.modified = True
    return redirect(request.referrer or url_for("menu"))

@app.route("/remove-from-cart/<int:item_id>", methods=["POST"])
def remove_from_cart(item_id):
    cart = session.get("cart", {})
    item_id_str = str(item_id)
    
    item_name = ""
    if item_id_str in cart:
        item_name = cart[item_id_str]["name"]
        del cart[item_id_str]

    session["cart"] = cart
    session.modified = True

    return jsonify({
        "success": True,
        "message": f"'{item_name}' removed from cart.",
        "cart_count": sum(i['quantity'] for i in cart.values())
    })

@app.route("/clear-cart", methods=["POST"])
def clear_cart():
    session.pop("cart", None)
    return redirect(url_for("cart"))

# -----------------------
# Orders
# -----------------------
@app.route("/order/<int:item_id>", methods=['GET', 'POST'])
def order(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if request.method == "POST":
        customer_name = request.form['customer_name']
        quantity = int(request.form['quantity'])
        new_order = Order(customer_name=customer_name, item_id=item.id, quantity=quantity)
        db.session.add(new_order)
        db.session.commit()
        return redirect(url_for('orders'))
    return render_template("order.html", item=item)

@app.route("/orders")
def orders():
    all_orders = Order.query.all()
    return render_template("orders.html", orders=all_orders)

# -----------------------
# Run App
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
