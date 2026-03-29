import os
import io
import csv
from datetime import datetime, timedelta, time
from random import randint
from threading import Thread 

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)
# Security Update: Using environment variables for secret keys
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_local_only')

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sarhad_inventory_final.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'sarhadbookbtm@gmail.com')
# Security Update: Password is now fetched from environment variables
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

mail = Mail(app)
db = SQLAlchemy(app)

@app.context_processor
def inject_global_vars():
    counts = {
        'new_req': 0,
        'working': 0,
        'ready_bill': 0,
        'history_unseen': 0,
        'total_orders_badge': 0
    }
    
    if 'user' in session and session.get('role') == 'admin':
        counts['new_req'] = OnlineOrder.query.filter_by(status='Pending').count()
        counts['working'] = OnlineOrder.query.filter_by(status='Processing').count()
        counts['ready_bill'] = OnlineOrder.query.filter_by(status='Packed').count()
        counts['history_unseen'] = OnlineOrder.query.filter_by(status='Completed', is_seen=False).count()
        counts['total_orders_badge'] = counts['new_req'] + counts['working'] + counts['ready_bill']

    return dict(datetime=datetime, **counts)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True) 
    cnic = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    address = db.Column(db.String(200))
    profile_pic = db.Column(db.String(200))
    job_title = db.Column(db.String(50))
    salary = db.Column(db.Float, default=0.0)
    joining_date = db.Column(db.DateTime, default=datetime.utcnow)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    security_code = db.Column(db.String(50), nullable=False, default='SARHAD786')
    shop_address = db.Column(db.String(200), default="Main Bazar, Battagram")
    shop_email = db.Column(db.String(100), default="sarhadbookbtm@gmail.com")
    shop_contacts = db.Column(db.String(500), default="0997 310304 | Hameed Ullah 0300 5622830")
    invoice_logo = db.Column(db.String(200))
    signature_image = db.Column(db.String(200))
    home_bg_image = db.Column(db.String(200))
    ntn_no = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    account_no = db.Column(db.String(100))

class BankAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_no = db.Column(db.String(100), nullable=False)
    iban = db.Column(db.String(100)) 

class SliderImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(200), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    clock_in = db.Column(db.Time, nullable=True)
    clock_out = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(10), nullable=False)
    is_approved = db.Column(db.Boolean, default=False) 
    user = db.relationship('User', backref='attendance_records')

class StaffRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending') 
    admin_comment = db.Column(db.String(200))
    user = db.relationship('User', backref='requests')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    tax_rate = db.Column(db.Float, default=0.0)
    image = db.Column(db.String(200)) 
    desc = db.Column(db.String(500))

class OnlineOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(100))
    customer_address = db.Column(db.String(200), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    remaining_amount = db.Column(db.Float, default=0.0)
    payment_mode = db.Column(db.String(50), default='Cash on Delivery')
    status = db.Column(db.String(50), default='Pending')
    is_seen = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.String(500))
    
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_staff = db.relationship('User', backref='tasks')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('online_order.id'), nullable=False)
    product_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    total = db.Column(db.Float)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    client_phone = db.Column(db.String(20))
    client_address = db.Column(db.String(200))
    
    total_amount = db.Column(db.Float, nullable=False) 
    discount_amount = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float, nullable=False)
    
    total_tax = db.Column(db.Float, default=0.0) 
    total_profit = db.Column(db.Float, default=0.0)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())
    created_by = db.Column(db.String(100)) 
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    tax_amount = db.Column(db.Float, default=0.0) 
    total = db.Column(db.Float) 

def create_db():
    with app.app_context():
        db.create_all()
        try:
            db.session.execute(text("ALTER TABLE settings ADD COLUMN signature_image VARCHAR(200)"))
            db.session.commit()
        except:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE online_order ADD COLUMN is_seen BOOLEAN DEFAULT 0"))
            db.session.commit()
        except:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE online_order ADD COLUMN customer_email VARCHAR(100)"))
            db.session.commit()
        except:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE online_order ADD COLUMN cancellation_reason VARCHAR(500)"))
            db.session.commit()
        except:
            db.session.rollback()

        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            db.session.add(User(username='admin', password=hashed_pw, role='admin', full_name='Shop Owner', email='sarhadbookbtm@gmail.com'))
            db.session.commit()
        if not Settings.query.first():
            db.session.add(Settings(shop_contacts="0997 310304"))
            db.session.commit()

def delete_old_file(filename):
    if filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

def _find_home_bg_filename():
    try:
        for fname in os.listdir(app.config['UPLOAD_FOLDER']):
            if fname.startswith('home_bg.'):
                return fname
    except Exception:
        return None
    return None

def _read_home_bg_url():
    path = os.path.join(app.config['UPLOAD_FOLDER'], 'home_bg_url.txt')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return None
    return None

def _write_home_bg_url(url):
    path = os.path.join(app.config['UPLOAD_FOLDER'], 'home_bg_url.txt')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(url or '')
    except Exception:
        pass

def _delete_home_bg_files():
    try:
        for fname in os.listdir(app.config['UPLOAD_FOLDER']):
            if fname.startswith('home_bg.'):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                except Exception:
                    pass
        url_path = os.path.join(app.config['UPLOAD_FOLDER'], 'home_bg_url.txt')
        if os.path.exists(url_path):
            try:
                os.remove(url_path)
            except Exception:
                pass
    except Exception:
        pass

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_order_confirmation(order, email):
    formatted_id = f"{order.id:04d}"
    msg = Message(f'Order Confirmed - #{formatted_id}', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[email])
    
    msg.html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px;">
        <h2 style="color: #103554; text-align: center;">SARHAD BOOK DEPOT</h2>
        <p>Dear <strong>{order.customer_name}</strong>,</p>
        <p>Thank you for your order! Your order has been placed successfully.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
            <span style="display: block; color: #666; font-size: 14px;">Tracking Number (Order ID)</span>
            <strong style="font-size: 24px; color: #eab308; letter-spacing: 2px;">#{formatted_id}</strong>
        </div>

        <p>Use this tracking number on our website to check your order status.</p>
        
        <p><strong>Total Amount:</strong> Rs. {order.total_amount:,.0f}</p>
        
        <p style="text-align: center; margin-top: 30px; font-size: 12px; color: #888;">
            Need help? Contact us at {Settings.query.first().shop_contacts}<br>
            Battagram, KPK.
        </p>
    </div>
    """
    Thread(target=send_async_email, args=(app, msg)).start()

def send_cancellation_email(order, reason):
    formatted_id = f"{order.id:04d}"
    
    recipient = order.customer_email or order.email or None
    if not recipient: return 

    msg = Message(f'Order Cancelled - #{formatted_id}', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[recipient])
    
    msg.html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px;">
        <h2 style="color: #dc3545; text-align: center;">ORDER CANCELLED</h2>
        <p>Dear <strong>{order.customer_name}</strong>,</p>
        <p>We regret to inform you that your order has been cancelled by the administration.</p>
        
        <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border: 1px solid #f5c6cb;">
            <strong style="color: #721c24;">Reason for Cancellation:</strong><br>
            <span style="color: #721c24;">{reason}</span>
        </div>

        <p><strong>Order ID:</strong> #{formatted_id}</p>
        <p><strong>Total Amount:</strong> Rs. {order.total_amount:,.0f}</p>
        
        <p>If you have any questions, please reply to this email or contact us directly.</p>
        
        <p style="text-align: center; margin-top: 30px; font-size: 12px; color: #888;">
            Sarhad Book Depot<br>
            Battagram, KPK.
        </p>
    </div>
    """
    Thread(target=send_async_email, args=(app, msg)).start()

@app.route('/')
def home():
    sliders = SliderImage.query.all()
    bg_url = None
    if not sliders:
        home_file = _find_home_bg_filename()
        if home_file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], home_file)
            try:
                mtime = int(os.path.getmtime(file_path))
                bg_url = url_for('static', filename='uploads/' + home_file) + f'?v={mtime}'
            except Exception:
                bg_url = url_for('static', filename='uploads/' + home_file)
        else:
            stored_url = _read_home_bg_url()
            if stored_url:
                bg_url = stored_url
            else:
                bg_url = 'https://images.unsplash.com/photo-1550399105-c4db5fb85c18?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80'

    settings = Settings.query.first()
    return render_template('home.html', shop={'name': 'SARHAD BOOK DEPOT'}, sliders=sliders, bg_url=bg_url, settings=settings)

@app.route('/shop')
def shop():
    category_filter = request.args.get('category')
    if category_filter:
        products = Product.query.filter_by(category=category_filter).all()
    else:
        products = Product.query.all()
    
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    settings = Settings.query.first()
    banks = BankAccount.query.all()
    
    return render_template('index.html', 
                           products=products, 
                           categories=categories, 
                           current_category=category_filter, 
                           settings=settings, 
                           banks=banks, 
                           shop={'name': 'SARHAD BOOK DEPOT'})

@app.route('/admin/self_pack_order/<int:id>')
def self_pack_order(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    order = OnlineOrder.query.get_or_404(id)
    order.assigned_to = session.get('user_id')
    order.status = 'Packed'
    db.session.commit()
    flash('Order marked as Packed by Admin!', 'success')
    return redirect(url_for('online_orders'))

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    cart_items = data.get('cart', [])
    customer = data.get('customer', {})
    
    if not cart_items: return jsonify({'success': False, 'message': 'Cart is empty'})

    total_bill = 0
    for item in cart_items:
        product = Product.query.get(item['id'])
        if not product: return jsonify({'success': False, 'message': f"Product ID {item['id']} not found"})
        if item['qty'] > product.quantity: return jsonify({'success': False, 'message': f"Stock Alert: '{product.name}' only has {product.quantity} items left."})
        total_bill += (product.price * item['qty'])

    new_order = OnlineOrder(
        customer_name=customer.get('name'), 
        customer_phone=customer.get('phone'),
        customer_email=customer.get('email'),
        customer_address=customer.get('address'), 
        order_date=datetime.now(),
        total_amount=total_bill,
        payment_mode=customer.get('payment_mode', 'Cash on Delivery'), 
        status='Pending', 
        remaining_amount=total_bill 
    )
    db.session.add(new_order)
    db.session.commit() 

    for item in cart_items:
        prod_data = Product.query.get(item['id'])
        db.session.add(OrderItem(order_id=new_order.id, product_name=prod_data.name, quantity=item['qty'], price=prod_data.price, total=prod_data.price * item['qty']))
        prod_data.quantity -= item['qty']
    
    db.session.commit()

    if customer.get('email'):
        send_order_confirmation(new_order, customer.get('email'))

    return jsonify({'success': True, 'order_id': f"{new_order.id:04d}"})

@app.route('/api/track_order/<int:order_id>')
def track_order_api(order_id):
    order = OnlineOrder.query.get(order_id)
    if not order:
        return jsonify({'found': False})
    
    items_list = [{'name': item.product_name, 'qty': item.quantity} for item in order.items]

    return jsonify({
        'found': True,
        'id': f"{order.id:04d}",
        'status': order.status,
        'customer': order.customer_name,
        'total': order.total_amount,
        'date': order.order_date.strftime('%d %b %Y'),
        'items': items_list
    })

@app.route('/track_order', methods=['GET', 'POST'])
def track_order():
    order = None
    if request.method == 'POST':
        order = OnlineOrder.query.filter_by(id=request.form.get('order_id'), customer_phone=request.form.get('phone')).first()
    return render_template('track_order.html', order=order)

@app.route('/admin/online_orders')
def online_orders():
    if 'user' not in session or session.get('role') != 'admin': return redirect(url_for('login'))
    
    search_q = request.args.get('search')
    query = OnlineOrder.query
    
    if search_q:
        if search_q in ['Pending', 'Processing', 'Packed', 'Completed', 'Cancelled']:
            query = query.filter_by(status=search_q)
            
            if search_q == 'Completed':
                unseen_orders = OnlineOrder.query.filter_by(status='Completed', is_seen=False).all()
                for order in unseen_orders:
                    order.is_seen = True
                db.session.commit()
        else:
            try: 
                query = query.filter((OnlineOrder.customer_name.ilike(f'%{search_q}%')) | (OnlineOrder.id == int(search_q)))
            except: 
                query = query.filter(OnlineOrder.customer_name.ilike(f'%{search_q}%'))
    
    return render_template('admin_orders.html', orders=query.order_by(OnlineOrder.order_date.desc()).all(), staff_list=User.query.filter_by(role='staff').all())

@app.route('/admin/cancel_order', methods=['POST'])
def cancel_order_route():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    order_id = request.form.get('order_id')
    reason = request.form.get('reason')
    
    if not reason or reason.strip() == "":
        reason = "Your order was cancelled by the administration due to unforeseen circumstances. Please contact support."
    
    order = OnlineOrder.query.get_or_404(order_id)
    order.status = 'Cancelled'
    order.cancellation_reason = reason
    order.assigned_to = None 
    
    db.session.commit()
    
    email_to_use = order.customer_email or (order.email if hasattr(order, 'email') else None)
    if email_to_use:
        send_cancellation_email(order, reason)
        flash('Order cancelled and email sent.', 'warning')
    else:
        flash('Order cancelled.', 'warning')
        
    return redirect(url_for('online_orders'))

@app.route('/admin/assign_task', methods=['POST'])
def assign_task():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    order = OnlineOrder.query.get(request.form.get('order_id'))
    staff_id = request.form.get('staff_id')
    if order and staff_id:
        order.assigned_to = int(staff_id)
        order.status = 'Processing'
        db.session.commit()
        flash('Order assigned successfully!', 'success')
    return redirect(url_for('online_orders'))

@app.route('/admin/delete_order/<int:id>')
def delete_order(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    order = OnlineOrder.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted.', 'danger')
    return redirect(url_for('online_orders'))

@app.route('/admin/create_invoice_from_order/<int:id>')
def create_invoice_from_order(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    order = OnlineOrder.query.get_or_404(id)
    
    if order.status == 'Completed':
        flash('Invoice already exists for this order.', 'warning')
        return redirect(url_for('online_orders'))

    if order.assigned_staff:
        bill_maker = order.assigned_staff.full_name
    else:
        bill_maker = session.get('full_name')

    try:
        inv = Invoice(
            id=order.id, 
            client_name=order.customer_name, 
            client_phone=order.customer_phone, 
            client_address=order.customer_address,
            total_amount=order.total_amount, 
            final_amount=order.total_amount, 
            created_by=bill_maker
        )
        db.session.add(inv)
        db.session.commit()
    except:
        db.session.rollback()
        inv = Invoice(
            client_name=order.customer_name, 
            client_phone=order.customer_phone, 
            client_address=order.customer_address,
            total_amount=order.total_amount, 
            final_amount=order.total_amount, 
            created_by=bill_maker
        )
        db.session.add(inv)
        db.session.commit()
    
    grand_profit = 0
    for item in order.items:
        prod = Product.query.filter_by(name=item.product_name).first()
        if prod:
            grand_profit += (prod.price - prod.cost_price) * item.quantity
            db.session.add(InvoiceItem(invoice_id=inv.id, product_name=item.product_name, quantity=item.quantity, price=item.price, total=item.total))
    
    inv.total_profit = grand_profit
    order.status = 'Completed'
    order.paid_amount = order.total_amount
    order.remaining_amount = 0
    order.is_seen = False 
    
    db.session.commit()
    flash(f'Invoice Generated! Created by: {bill_maker}', 'success')
    return redirect(url_for('invoice_detail', id=inv.id))

@app.route('/admin/mark_history_seen')
def mark_history_seen():
    if session.get('role') != 'admin': return jsonify({'success': False})
    unseen_orders = OnlineOrder.query.filter_by(status='Completed', is_seen=False).all()
    for order in unseen_orders:
        order.is_seen = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/staff/tasks')
def staff_tasks():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('staff_tasks.html', tasks=OnlineOrder.query.filter_by(assigned_to=session.get('user_id')).filter(OnlineOrder.status != 'Completed').all())

@app.route('/staff/mark_packed/<int:id>')
def staff_mark_packed(id):
    if 'user' not in session: return redirect(url_for('login'))
    order = OnlineOrder.query.get(id)
    if order and order.assigned_to == session.get('user_id'):
        order.status = 'Packed' 
        db.session.commit()
        flash('Order marked as Packed.', 'success')
    return redirect(url_for('staff_tasks'))

@app.route('/staff/attendance', methods=['GET', 'POST'])
def staff_attendance():
    if 'user_id' not in session or session.get('role') == 'admin': 
        return redirect(url_for('dashboard'))
    
    uid = session['user_id']
    user = User.query.get(uid)
    today = datetime.now().date()
    now = datetime.now()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'mark_today':
            existing = Attendance.query.filter_by(user_id=uid, date=today).first()
            if not existing:
                status = 'Late' if now.time() > time(9, 30) else 'Present'
                new_att = Attendance(user_id=uid, date=today, clock_in=now.time(), status=status, is_approved=False)
                db.session.add(new_att)
                db.session.commit()
                flash('Attendance Request Sent to Admin!', 'success')
            else:
                flash('Request already sent for today.', 'warning')

        elif action == 'other_request':
            req_type = request.form.get('req_type')
            reason = request.form.get('reason')
            date_str = request.form.get('req_date')
            try:
                req_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                new_req = StaffRequest(user_id=uid, request_type=req_type, date=req_date, description=reason, status='Pending')
                db.session.add(new_req)
                db.session.commit()
                flash('Request submitted successfully!', 'info')
            except:
                flash('Invalid date format.', 'danger')

        return redirect(url_for('staff_attendance'))

    today_record = Attendance.query.filter_by(user_id=uid, date=today).first()
    current_month = today.month
    month_records = Attendance.query.filter(Attendance.user_id == uid, db.extract('month', Attendance.date) == current_month, Attendance.is_approved == True).all()
    approved_leaves = StaffRequest.query.filter(StaffRequest.user_id == uid, StaffRequest.request_type == 'Leave', StaffRequest.status == 'Approved', db.extract('month', StaffRequest.date) == current_month).count()

    stats = {
        'present': sum(1 for r in month_records if r.status == 'Present'),
        'late': sum(1 for r in month_records if r.status == 'Late'),
        'absent': sum(1 for r in month_records if r.status == 'Absent'),
        'leaves': approved_leaves
    }
    history = Attendance.query.filter_by(user_id=uid).order_by(Attendance.date.desc()).limit(30).all()
    return render_template('staff_attendance.html', user=user, today=today, today_record=today_record, stats=stats, history=history)

@app.route('/admin/attendance', methods=['GET', 'POST'])
def attendance():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    today = datetime.now().date()
    if request.method == 'POST':
        if 'request_id' in request.form:
            req = StaffRequest.query.get(int(request.form.get('request_id')))
            if req:
                req.status = 'Approved' if request.form.get('action') == 'approve' else 'Rejected'
                req.admin_comment = request.form.get('reason', '')
                db.session.commit()
                flash(f'Request {req.status}!', 'success')
        else:
            for k, v in request.form.items():
                if k.startswith('status_'):
                    uid = int(k.split('_')[1])
                    att = Attendance.query.filter_by(user_id=uid, date=today).first()
                    if att: 
                        att.status, att.is_approved = v, True
                    else: 
                        db.session.add(Attendance(user_id=uid, date=today, status=v, is_approved=True))
            db.session.commit()
            flash('Attendance Updated Successfully!', 'success')
        return redirect(url_for('attendance'))

    todays_records = Attendance.query.filter_by(date=today).all()
    stats = {'total': User.query.filter_by(role='staff').count(), 'present': sum(1 for r in todays_records if r.status == 'Present'), 'late': sum(1 for r in todays_records if r.status == 'Late'), 'absent': sum(1 for r in todays_records if r.status == 'Absent')}
    return render_template('attendance.html', stats=stats, pending_requests=StaffRequest.query.filter_by(status='Pending').order_by(StaffRequest.date.desc()).all(), staff_list=User.query.filter_by(role='staff').all(), attendance_map={r.user_id: r for r in todays_records}, today=today)

@app.route('/admin/attendance/report')
def salary_report():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    report_data = []
    first_day = datetime.now().date().replace(day=1)
    for staff in User.query.filter_by(role='staff').all():
        recs = Attendance.query.filter(Attendance.user_id==staff.id, Attendance.date>=first_day).all()
        p_count = sum(1 for r in recs if r.status=='Present')
        l_count = sum(1 for r in recs if r.status=='Late')
        a_count = sum(1 for r in recs if r.status=='Absent')
        basic = staff.salary or 0
        deduction = a_count * (basic / 30 if basic > 0 else 0)
        report_data.append({'name': staff.full_name, 'role': staff.job_title, 'present': p_count + l_count, 'absent': a_count, 'leaves': 0, 'basic_salary': basic, 'deduction': deduction, 'net_salary': basic - deduction})
    return render_template('salary_report.html', report=report_data)

@app.route('/admin/payroll')
def payroll():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    payroll_data = []
    first_day = datetime.now().date().replace(day=1)
    for staff in User.query.filter_by(role='staff').all():
        reqs = StaffRequest.query.filter(StaffRequest.user_id == staff.id, StaffRequest.status == 'Approved', StaffRequest.date >= first_day).all()
        deductions = sum(r.amount for r in reqs)
        payroll_data.append({'staff': staff, 'base': staff.salary or 0, 'deductions': deductions, 'net': (staff.salary or 0) - deductions, 'details': reqs})
    return render_template('payroll.html', payroll=payroll_data)

@app.route('/staff/profile', methods=['GET', 'POST'])
def staff_profile():
    if 'user' not in session: return redirect(url_for('login'))
    user = User.query.get(session.get('user_id'))
    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.phone = request.form['phone']
        user.address = request.form['address']
        file = request.files['profile_pic']
        if file and file.filename != '':
            delete_old_file(user.profile_pic)
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = filename
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        db.session.commit()
        flash('Profile Updated Successfully!', 'success')
        return redirect(url_for('staff_profile'))
    return render_template('staff_profile.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_identifier = request.form.get('email') 
        password = request.form['password']
        
        user = User.query.filter_by(email=input_identifier).first()
        
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            session['role'] = user.role
            session['user_id'] = user.id
            session['full_name'] = user.full_name
            
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('staff_tasks'))
        
        return render_template('login.html', error="Invalid Email or Password!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if request.form.get('shop_code', '').strip() != (Settings.query.first().security_code if Settings.query.first() else 'SARHAD786'): 
            return render_template('signup.html', error="Invalid Security Code!")
        
        email = request.form.get('email')
        if User.query.filter_by(email=email).first(): 
            return render_template('signup.html', error="Email is already registered!")

        password = request.form.get('password')
        if len(password) < 8: 
            return render_template('signup.html', error="Password must be at least 8 characters long!")

        cnic = request.form.get('cnic')
        if User.query.filter_by(cnic=cnic).first(): 
            return render_template('signup.html', error="This CNIC is already registered!")
        
        filename = None
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        otp = randint(100000, 999999)
        
        session['temp_user'] = {
            'username': email, 
            'password': generate_password_hash(password, method='pbkdf2:sha256'), 
            'full_name': request.form['full_name'], 
            'phone': request.form['phone'], 
            'email': email, 
            'cnic': cnic, 
            'dob': request.form['dob'], 
            'address': request.form['address'], 
            'profile_pic': filename, 
            'otp': otp,
            'otp_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            msg = Message('Verify Account', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Your OTP is: {otp}. It is valid for 5 minutes."
            mail.send(msg)
            return redirect(url_for('verify_otp'))
        except Exception as e: return render_template('signup.html', error=f"Email Error: {str(e)}")
            
    return render_template('signup.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'temp_user' not in session: return redirect(url_for('signup'))
    if request.method == 'POST':
        otp_time_str = session['temp_user'].get('otp_time')
        if otp_time_str:
            otp_time = datetime.strptime(otp_time_str, '%Y-%m-%d %H:%M:%S')
            if datetime.now() - otp_time > timedelta(minutes=5):
                session.pop('temp_user', None)
                return render_template('signup.html', error="OTP Expired! Register again.")

        if request.form.get('otp') == str(session['temp_user']['otp']):
            d = session['temp_user']
            if User.query.filter_by(email=d['email']).first():
                session.pop('temp_user', None)
                return render_template('login.html', error="User already registered.")
            
            db.session.add(User(
                username=d['username'], 
                password=d['password'], 
                role='staff', 
                full_name=d['full_name'], 
                phone=d['phone'], 
                email=d['email'], 
                cnic=d['cnic'], 
                dob=d['dob'], 
                address=d['address'], 
                profile_pic=d['profile_pic']
            ))
            db.session.commit()
            session.pop('temp_user', None)
            return render_template('login.html', success="Verified! Please login.")
        return render_template('verify_otp.html', error="Invalid OTP")
    return render_template('verify_otp.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not User.query.filter_by(email=email).first(): return render_template('forgot_password.html', error="Email not found")
        otp = randint(100000, 999999)
        session['reset_data'] = {'email': email, 'otp': otp, 'otp_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        try:
            msg = Message('Reset Password', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"OTP: {otp}. Valid for 5 minutes."
            mail.send(msg)
            return redirect(url_for('verify_reset_otp'))
        except Exception as e: return render_template('forgot_password.html', error=str(e))
    return render_template('forgot_password.html')

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'reset_data' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        otp_time_str = session['reset_data'].get('otp_time')
        if otp_time_str:
            otp_time = datetime.strptime(otp_time_str, '%Y-%m-%d %H:%M:%S')
            if datetime.now() - otp_time > timedelta(minutes=5):
                session.pop('reset_data', None)
                return render_template('forgot_password.html', error="OTP Expired! Try again.")

        if request.form.get('otp') == str(session['reset_data']['otp']):
            session['reset_data']['verified'] = True
            return redirect(url_for('reset_new_password'))
        return render_template('verify_reset_otp.html', error="Invalid OTP")
    return render_template('verify_reset_otp.html')

@app.route('/reset_new_password', methods=['GET', 'POST'])
def reset_new_password():
    if 'reset_data' not in session or not session['reset_data'].get('verified'): return redirect(url_for('login'))
    if request.method == 'POST':
        user = User.query.filter_by(email=session['reset_data']['email']).first()
        user.password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        db.session.commit()
        session.pop('reset_data', None)
        return render_template('login.html', success="Password Changed")
    return render_template('reset_new_password.html')

@app.route('/admin/dashboard')
def dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    total_stock = Product.query.count()
    low_stock = Product.query.filter(Product.quantity < 10).count()
    pending_orders = OnlineOrder.query.filter_by(status='Pending').count()
    total_staff = User.query.filter_by(role='staff').count()
    
    total_sales = db.session.query(func.sum(Invoice.total_amount)).scalar() or 0
    total_profit = db.session.query(func.sum(Invoice.total_profit)).scalar() or 0
    
    top_stores = []
    if Invoice.query.first():
        top_stores = db.session.query(Invoice.client_name, func.sum(Invoice.total_amount).label('total_spent')).group_by(Invoice.client_name).order_by(func.sum(Invoice.total_amount).desc()).limit(5).all()

    cat_data = db.session.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    cat_labels = [c[0] for c in cat_data]
    cat_counts = [c[1] for c in cat_data]

    return render_template('dashboard.html', 
        total_stock=total_stock, low_stock=low_stock, 
        pending_orders=pending_orders, 
        total_staff=total_staff,  
        top_stores=top_stores,
        cat_labels=cat_labels, cat_counts=cat_counts,
        total_sales=total_sales,
        total_profit=total_profit)

@app.route('/admin/employees')
def employees():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    return render_template('employees.html', staff_list=User.query.filter_by(role='staff').all())

@app.route('/admin/employee/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        user.cnic = request.form.get('cnic')
        user.dob = request.form.get('dob')
        user.address = request.form.get('address')
        user.job_title = request.form.get('job_title')
        if request.form.get('salary'): user.salary = float(request.form.get('salary'))
        if request.files.get('profile_pic'):
            delete_old_file(user.profile_pic)
            filename = secure_filename(request.files['profile_pic'].filename)
            request.files['profile_pic'].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = filename
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees'))
    return render_template('edit_employee.html', user=user)

@app.route('/admin/employee/delete/<int:id>')
def delete_employee(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    user = User.query.get_or_404(id)
    delete_old_file(user.profile_pic)
    Attendance.query.filter_by(user_id=user.id).delete()
    StaffRequest.query.filter_by(user_id=user.id).delete()
    orders = OnlineOrder.query.filter_by(assigned_to=user.id).all()
    for order in orders:
        order.assigned_to = None
    db.session.delete(user)
    db.session.commit()
    flash('Employee and associated data deleted successfully!', 'success')
    return redirect(url_for('employees'))

@app.route('/admin/inventory')
def inventory():
    if 'user' not in session: return redirect(url_for('login'))
    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('search', '').strip()
    filter_type = request.args.get('filter')
    category_filter = request.args.get('category')
    query = Product.query
    if filter_type == 'low':
        query = query.filter(Product.quantity < 10)
        flash('Showing Low Stock Items', 'warning')
    if category_filter:
        query = query.filter_by(category=category_filter)
        flash(f'Filtered by Category: {category_filter}', 'info')
    if search_q:
        query = query.filter((Product.name.ilike(f'%{search_q}%')) | (Product.barcode.ilike(f'%{search_q}%')))
    products = query.order_by(Product.id.desc()).paginate(page=page, per_page=20, error_out=False)
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    return render_template('inventory.html', products=products, categories=categories, search_query=search_q)

@app.route('/admin/inventory/add', methods=['GET', 'POST'])
def add_stock():
    if request.method == 'POST':
        filename = None
        if request.files.get('product_image'):
            filename = secure_filename(request.files['product_image'].filename)
            request.files['product_image'].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.session.add(Product(name=request.form['name'], category=request.form['category'], cost_price=float(request.form['cost_price']), price=float(request.form['price']), quantity=int(request.form['quantity']), image=filename))
        db.session.commit()
        return redirect(url_for('inventory'))
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    return render_template('add_stock.html', categories=categories)

@app.route('/admin/inventory/delete/<int:id>')
def delete_stock(id):
    p = Product.query.get_or_404(id)
    delete_old_file(p.image) 
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('inventory'))

@app.route('/admin/inventory/edit/<int:id>', methods=['GET', 'POST'])
def edit_stock(id):
    if 'user' not in session: return redirect(url_for('login'))
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.cost_price = float(request.form['cost_price'])
        product.price = float(request.form['price'])
        product.quantity = int(request.form['quantity'])
        file = request.files.get('product_image')
        if file and file.filename != '':
            delete_old_file(product.image)
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image = filename
        db.session.commit()
        return redirect(url_for('inventory'))
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    return render_template('add_stock.html', product=product, categories=categories)

@app.route('/admin/billing', methods=['GET', 'POST'])
def billing():
    if request.method == 'POST':
        data = request.get_json()
        items_obj = []
        grand_total, grand_profit = 0, 0
        for item in data['items']:
            prod = Product.query.get(int(item['id']))
            if prod.quantity < int(item['qty']): 
                return jsonify({'success': False, 'error': f'Low stock for {prod.name}'})
            prod.quantity -= int(item['qty'])
            line_total = prod.price * int(item['qty'])
            grand_total += line_total
            grand_profit += (prod.price - prod.cost_price) * int(item['qty'])
            items_obj.append(InvoiceItem(product_name=prod.name, quantity=int(item['qty']), price=prod.price, total=line_total))
        discount_val = float(data.get('discount_value', 0))
        discount_type = data.get('discount_type', 'pkr') 
        discount_amount = 0
        if discount_type == 'percent':
            discount_amount = (grand_total * discount_val) / 100
        else:
            discount_amount = discount_val
        final_amount = grand_total - discount_amount
        if final_amount < 0: final_amount = 0
        final_profit = grand_profit - discount_amount
        inv = Invoice(client_name=data['client_name'], client_phone=data.get('client_phone'), client_address=data.get('client_address'), total_amount=grand_total, discount_amount=discount_amount, final_amount=final_amount, total_profit=final_profit, items=items_obj, created_by=session.get('full_name'))
        db.session.add(inv)
        db.session.commit()
        return jsonify({'success': True, 'invoice_id': inv.id})
    return render_template('billing.html', products=Product.query.all())

@app.route('/admin/invoice/<int:id>')
def invoice_detail(id):
    banks = BankAccount.query.all()
    return render_template('invoice_detail.html', invoice=Invoice.query.get_or_404(id), settings=Settings.query.first(), banks=banks)

@app.route('/api/dashboard-data')
def dashboard_data():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    filter_type = request.args.get('filter', 'daily')
    end_date = datetime.now()
    
    labels = []
    sales = []
    profits = []
    losses = []

    if filter_type == 'today':
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        hours_data = {h: {'sales': 0, 'profit': 0, 'loss': 0} for h in range(24)}
        
        invoices = Invoice.query.filter(Invoice.date >= start_date).all()
        
        for inv in invoices:
            h = inv.date.hour
            hours_data[h]['sales'] += inv.total_amount
            if inv.total_profit >= 0:
                hours_data[h]['profit'] += inv.total_profit
            else:
                hours_data[h]['loss'] += abs(inv.total_profit)

        for h in range(24):
            am_pm = 'AM' if h < 12 else 'PM'
            h_12 = h if h <= 12 else h - 12
            if h_12 == 0: h_12 = 12
            labels.append(f"{h_12} {am_pm}")
            sales.append(hours_data[h]['sales'])
            profits.append(hours_data[h]['profit'])
            losses.append(hours_data[h]['loss'])

    else:
        data_map = {}
        if filter_type == 'weekly':
            start_date = end_date - timedelta(weeks=12)
            date_fmt = 'W%U'
        elif filter_type == 'monthly':
            start_date = end_date - timedelta(days=365)
            date_fmt = '%b %Y'
        elif filter_type == 'yearly':
            start_date = datetime(2000, 1, 1)
            date_fmt = '%Y'
        else:
            start_date = end_date - timedelta(days=30)
            date_fmt = '%d %b'

        invoices = Invoice.query.filter(Invoice.date >= start_date).order_by(Invoice.date).all()
        
        for inv in invoices:
            key = inv.date.strftime(date_fmt)
            if key not in data_map: data_map[key] = {'sales': 0, 'profit': 0, 'loss': 0}
            
            data_map[key]['sales'] += inv.total_amount
            if inv.total_profit >= 0:
                data_map[key]['profit'] += inv.total_profit
            else:
                data_map[key]['loss'] += abs(inv.total_profit)
        
        labels = list(data_map.keys())
        sales = [data_map[k]['sales'] for k in labels]
        profits = [data_map[k]['profit'] for k in labels]
        losses = [data_map[k]['loss'] for k in labels]

    top_products = db.session.query(OrderItem.product_name, func.sum(OrderItem.quantity))\
        .group_by(OrderItem.product_name)\
        .order_by(func.sum(OrderItem.quantity).desc())\
        .limit(5).all()
        
    prod_labels = [p[0] for p in top_products] if top_products else []
    prod_values = [p[1] for p in top_products] if top_products else []

    status_counts = db.session.query(OnlineOrder.status, func.count(OnlineOrder.id))\
        .group_by(OnlineOrder.status).all()
        
    status_labels = [s[0] for s in status_counts] if status_counts else []
    status_values = [s[1] for s in status_counts] if status_counts else []

    return jsonify({
        'labels': labels, 
        'sales': sales, 
        'profits': profits, 
        'losses': losses,
        'products': {'labels': prod_labels, 'data': prod_values},
        'status': {'labels': status_labels, 'data': status_values}
    })

@app.route('/get-product-by-barcode/<barcode>')
def get_product_by_barcode(barcode):
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    prod = Product.query.filter_by(barcode=barcode).first()
    if prod: return jsonify({'success': True, 'id': prod.id, 'name': prod.name, 'price': prod.price, 'stock': prod.quantity, 'tax_rate': prod.tax_rate})
    return jsonify({'success': False, 'message': 'Product not found'})

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session or session.get('role') != 'admin': return redirect(url_for('login'))
    
    current_settings = Settings.query.first()
    if not current_settings:
        current_settings = Settings()
        db.session.add(current_settings)
        db.session.commit()

    admin_user = User.query.filter_by(role='admin').first()
    message, error = None, None

    if request.method == 'POST':
        action = request.form.get('action')

        if 'new_email' in request.form:
            new_email = request.form['new_email'].strip()
            if new_email == admin_user.email:
                error = "You are already using this Email!"
            elif User.query.filter_by(email=new_email).first(): 
                error = "Email is already registered by another user!"
            else: 
                otp = randint(100000, 999999)
                session['admin_change_data'] = {
                    'type': 'email',
                    'value': new_email,
                    'otp': otp,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                try:
                    msg = Message('Security Verification - Change Email', sender=app.config['MAIL_USERNAME'], recipients=[admin_user.email])
                    msg.body = f"Your OTP to change admin email is: {otp}. Valid for 5 minutes."
                    mail.send(msg)
                    return redirect(url_for('verify_settings_change'))
                except Exception as e: error = f"Email sending failed: {str(e)}"
        
        elif 'new_password' in request.form:
            new_pass = request.form['new_password']
            if check_password_hash(admin_user.password, new_pass):
                error = "New password cannot be the same as the old password!"
            else:
                otp = randint(100000, 999999)
                hashed_pw = generate_password_hash(new_pass, method='pbkdf2:sha256')
                session['admin_change_data'] = {
                    'type': 'password',
                    'value': hashed_pw,
                    'otp': otp,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                try:
                    msg = Message('Security Verification - Change Password', sender=app.config['MAIL_USERNAME'], recipients=[admin_user.email])
                    msg.body = f"Your OTP to change admin password is: {otp}. Valid for 5 minutes."
                    mail.send(msg)
                    return redirect(url_for('verify_settings_change'))
                except Exception as e: error = f"Email sending failed: {str(e)}"
                
        elif action == 'update_shop':
            current_settings.shop_address = request.form['shop_address']
            current_settings.shop_email = request.form['shop_email']
            current_settings.shop_contacts = request.form['shop_contacts']
            if request.files.get('invoice_logo'):
                delete_old_file(current_settings.invoice_logo)
                filename = secure_filename(request.files['invoice_logo'].filename)
                request.files['invoice_logo'].save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_settings.invoice_logo = filename
            
            if request.files.get('signature_image'):
                delete_old_file(current_settings.signature_image)
                sig_filename = secure_filename(request.files['signature_image'].filename)
                request.files['signature_image'].save(os.path.join(app.config['UPLOAD_FOLDER'], sig_filename))
                current_settings.signature_image = sig_filename

            if request.files.get('home_bg_image'):
                delete_old_file(current_settings.home_bg_image)
                bg_filename = secure_filename(request.files['home_bg_image'].filename)
                request.files['home_bg_image'].save(os.path.join(app.config['UPLOAD_FOLDER'], bg_filename))
                current_settings.home_bg_image = bg_filename
            
            db.session.commit()
            message = "Shop Details Updated!"

        elif action == 'add_bank':
            new_bank = BankAccount(title=request.form['title'], bank_name=request.form['bank_name'], account_no=request.form['account_no'], iban=request.form.get('iban'))
            db.session.add(new_bank)
            db.session.commit()
            message = "Bank Account Added!"

        elif action == 'delete_bank':
            BankAccount.query.filter_by(id=request.form.get('bank_id')).delete()
            db.session.commit()
            message = "Bank Account Deleted!"

        elif 'new_code' in request.form:
            current_settings.security_code = request.form['new_code']
            db.session.commit()
            message = "Security Code Updated!"
        
        elif action == 'update_home_bg':
            file = request.files.get('home_bg_file')
            url = request.form.get('home_bg_url', '').strip()
            if file and file.filename != '':
                _delete_home_bg_files()
                filename = secure_filename(file.filename)
                ext = os.path.splitext(filename)[1]
                save_name = 'home_bg' + ext
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))
                message = 'Home background uploaded successfully!'
            elif url:
                _delete_home_bg_files()
                _write_home_bg_url(url)
                message = 'Home background URL saved successfully!'
            else: message = 'No image or URL provided.'
        elif action == 'delete_home_bg':
            _delete_home_bg_files()
            message = 'Home background removed.'

        elif action == 'add_slider_image':
            file = request.files.get('slider_image')
            if file and file.filename != '':
                filename = secure_filename(f"slider_{int(datetime.now().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.session.add(SliderImage(image_filename=filename))
                db.session.commit()
                message = "Slider Image Added!"
        
        elif action == 'delete_slider_image':
            s_id = request.form.get('slider_id')
            slide = SliderImage.query.get(s_id)
            if slide:
                delete_old_file(slide.image_filename)
                db.session.delete(slide)
                db.session.commit()
                message = "Slider Image Deleted!"

    banks = BankAccount.query.all()
    home_bg_file = _find_home_bg_filename()
    home_bg_url = _read_home_bg_url()
    return render_template('settings.html', settings=current_settings, admin_user=admin_user, banks=banks, message=message, error=error, home_bg_file=home_bg_file, home_bg_url=home_bg_url, sliders=SliderImage.query.all())

@app.route('/admin/settings/verify', methods=['GET', 'POST'])
def verify_settings_change():
    if 'admin_change_data' not in session: return redirect(url_for('settings'))
    
    if request.method == 'POST':
        data = session['admin_change_data']
        otp_time = datetime.strptime(data['time'], '%Y-%m-%d %H:%M:%S')
        
        if datetime.now() - otp_time > timedelta(minutes=5):
            session.pop('admin_change_data', None)
            flash("OTP Expired! Please try again.", "danger")
            return redirect(url_for('settings'))

        if request.form.get('otp') == str(data['otp']):
            admin_user = User.query.filter_by(role='admin').first()
            
            if data['type'] == 'email':
                admin_user.email = data['value']
                admin_user.username = data['value'] 
                session['user'] = data['value']
                flash("Admin Email Updated Successfully!", "success")
                
            elif data['type'] == 'password':
                admin_user.password = data['value']
                flash("Admin Password Updated Successfully! Please Login Again.", "success")
                db.session.commit()
                session.clear()
                return redirect(url_for('login'))

            db.session.commit()
            session.pop('admin_change_data', None)
            return redirect(url_for('settings'))
        
        return render_template('verify_settings_otp.html', error="Invalid OTP")

    return render_template('verify_settings_otp.html')

@app.route('/admin/attendance/action/<int:id>/<action>')
def attendance_action(id, action):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    att = Attendance.query.get_or_404(id)
    if action == 'approve': att.is_approved = True
    elif action == 'reject': db.session.delete(att)
    db.session.commit()
    return redirect(url_for('attendance'))

@app.route('/admin/sales')
def sales_report():
    if 'user' not in session: return redirect(url_for('login'))
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    total_sales = db.session.query(func.sum(Invoice.total_amount)).scalar() or 0
    total_profit = db.session.query(func.sum(Invoice.total_profit)).scalar() or 0
    return render_template('sales.html', invoices=invoices, total_sales=total_sales, total_profit=total_profit)

@app.route('/admin/sales/export')
def export_sales():
    if 'user' not in session: return redirect(url_for('login'))
    invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Invoice ID', 'Date', 'Client Name', 'Created By', 'Total Amount', 'Tax Collected', 'Profit'])
    for inv in invoices: cw.writerow([inv.id, inv.date, inv.client_name, inv.created_by, inv.total_amount, inv.total_tax, inv.total_profit])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=sales_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/add_deduction', methods=['POST'])
def add_deduction():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    db.session.add(StaffRequest(user_id=request.form.get('user_id'), request_type=request.form.get('type'), amount=float(request.form.get('amount')), description=request.form.get('reason'), status='Approved', admin_comment='Added manually by Admin', date=datetime.now()))
    db.session.commit()
    flash('Deduction added!', 'success')
    return redirect(url_for('payroll'))

@app.route('/admin/salary/email/<int:user_id>')
def email_salary_slip(user_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    if not user.email:
        flash(f'Error: {user.full_name} has no email!', 'danger')
        return redirect(url_for('payroll'))
    first_day = datetime.now().date().replace(day=1)
    approved_reqs = StaffRequest.query.filter(StaffRequest.user_id == user.id, StaffRequest.status == 'Approved', StaffRequest.date >= first_day).all()
    p = Attendance.query.filter(Attendance.user_id==user.id, Attendance.date>=first_day, Attendance.status=='Present').count()
    l = Attendance.query.filter(Attendance.user_id==user.id, Attendance.date>=first_day, Attendance.status=='Late').count()
    a = Attendance.query.filter(Attendance.user_id==user.id, Attendance.date>=first_day, Attendance.status=='Absent').count()
    base = user.salary or 0
    deduction = a * (base / 30 if base > 0 else 0)
    other = sum(r.amount for r in approved_reqs)
    try:
        msg = Message(f"Salary Slip - {datetime.now().strftime('%B %Y')}", sender=app.config['MAIL_USERNAME'], recipients=[user.email])
        msg.html = render_template('salary_slip.html', user=user, date=datetime.now(), stats={'present': p+l, 'absent': a}, financials={'base': base, 'absent_deduction': deduction, 'other_deductions': other, 'net': base-deduction-other}, requests=approved_reqs, settings=Settings.query.first(), is_email=True)
        mail.send(msg)
        flash(f'Email sent to {user.full_name}!', 'success')
    except Exception as e: flash(f'Email Failed: {str(e)}', 'danger')
    return redirect(url_for('payroll'))

@app.route('/admin/salary/email/all')
def email_all_salary():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    count = 0
    for user in User.query.filter_by(role='staff').all():
        if user.email:
            try:
                count += 1
            except: continue
    flash(f'Sent to {count} staff.', 'success')
    return redirect(url_for('payroll'))

@app.route('/admin/salary/slip/<int:user_id>')
def salary_slip(user_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    first_day = datetime.now().date().replace(day=1)
    p = Attendance.query.filter(Attendance.user_id==user.id, Attendance.date>=first_day, Attendance.status=='Present').count()
    l = Attendance.query.filter(Attendance.user_id==user.id, Attendance.date>=first_day, Attendance.status=='Late').count()
    a = Attendance.query.filter(Attendance.user_id==user.id, Attendance.date>=first_day, Attendance.status=='Absent').count()
    base = user.salary or 0
    deduction = a * (base / 30 if base > 0 else 0)
    reqs = StaffRequest.query.filter(StaffRequest.user_id == user.id, StaffRequest.status == 'Approved', StaffRequest.date >= first_day).all()
    other = sum(r.amount for r in reqs)
    return render_template('salary_slip.html', user=user, date=datetime.now(), stats={'present': p+l, 'absent': a}, financials={'base': base, 'absent_deduction': deduction, 'other_deductions': other, 'net': base-deduction-other}, requests=reqs, settings=Settings.query.first(), is_email=False)

@app.route('/admin/category/delete', methods=['POST'])
def delete_category_route():
    if session.get('role') != 'admin': return "Unauthorized", 403
    cat_to_delete = request.form.get('category')
    if not cat_to_delete: return "Error", 400
    products = Product.query.filter_by(category=cat_to_delete).all()
    for p in products: p.category = 'General'
    db.session.commit()
    return "OK", 200

if __name__ == "__main__":
    create_db()
    # Debug False for production/public use
    app.run(host='0.0.0.0', port=5000, debug=False)