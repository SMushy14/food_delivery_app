from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Stall, MenuItem, Order, OrderItem
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bcrypt = Bcrypt(app)
db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Role required decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role != role:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('stall_owner_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    user = User.query.filter_by(email=email, role=role).first()
    
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        flash('Logged in successfully!', 'success')
        
        if user.role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('stall_owner_dashboard'))
    else:
        flash('Invalid email, password, or role', 'danger')
        return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    stall_name = request.form.get('stall_name')
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        flash('Email already registered', 'danger')
        return redirect(url_for('index'))
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    
    # If stall owner, create stall
    if role == 'stall_owner':
        new_stall = Stall(name=stall_name, owner_id=new_user.id)
        db.session.add(new_stall)
        db.session.commit()
    
    flash('Registration successful! Please login.', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/student')
@role_required('student')
def student_dashboard():
    stalls = Stall.query.limit(4).all()
    return render_template('student.html', stalls=stalls, user=current_user)

@app.route('/api/stalls/<int:stall_id>/menu')
@role_required('student')
def get_stall_menu(stall_id):
    stall = db.session.get(Stall, stall_id)
    if not stall:
        return jsonify({'error': 'Stall not found'}), 404
    
    menu_items = [{'id': item.id, 'name': item.name, 'price': item.price} for item in stall.menu_items]
    return jsonify({'menu': menu_items})

@app.route('/api/orders', methods=['POST'])
@role_required('student')
def create_order():
    data = request.get_json()
    stall_id = data.get('stall_id')
    items = data.get('items')
    
    if not stall_id or not items:
        return jsonify({'error': 'Missing data'}), 400
    
    total = sum(item['price'] * item['quantity'] for item in items)
    
    order = Order(
        user_id=current_user.id,
        stall_id=stall_id,
        total=total,
        status='pending'
    )
    db.session.add(order)
    db.session.commit()
    
    for item in items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item['id'],
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
    
    db.session.commit()
    
    return jsonify({'order_id': order.id, 'message': 'Order placed successfully'})

@app.route('/stall-owner')
@role_required('stall_owner')
def stall_owner_dashboard():
    stall = Stall.query.filter_by(owner_id=current_user.id).first()
    return render_template('stall_owner.html', stall=stall, user=current_user)

@app.route('/api/menu-items', methods=['POST'])
@role_required('stall_owner')
def add_menu_item():
    stall = Stall.query.filter_by(owner_id=current_user.id).first()
    if not stall:
        return jsonify({'error': 'Stall not found'}), 404
    
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    category = data.get('category', 'food')
    
    if not name or not price:
        return jsonify({'error': 'Missing data'}), 400
    
    menu_item = MenuItem(
        name=name,
        price=price,
        category=category,
        stall_id=stall.id
    )
    db.session.add(menu_item)
    db.session.commit()
    
    return jsonify({'id': menu_item.id, 'name': menu_item.name, 'price': menu_item.price})

@app.route('/api/menu-items/<int:item_id>', methods=['DELETE'])
@role_required('stall_owner')
def delete_menu_item(item_id):
    stall = Stall.query.filter_by(owner_id=current_user.id).first()
    if not stall:
        return jsonify({'error': 'Stall not found'}), 404
    
    menu_item = db.session.get(MenuItem, item_id)
    if not menu_item or menu_item.stall_id != stall.id:
        return jsonify({'error': 'Menu item not found'}), 404
    
    db.session.delete(menu_item)
    db.session.commit()
    
    return jsonify({'message': 'Menu item deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True)
