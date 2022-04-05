import datetime
import hashlib
import os
import stripe
import pymongo
import os

from flask import Flask, redirect, request, jsonify, json, abort
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token, JWTManager

app = Flask(__name__)
app.debug = True
CORS(app)
load_dotenv()

app.config['STRIPE_PUBLIC_KEY'] = 'pk_test_51KdFY6CBDTxkbXVTvYnNL56HRoRdGXGtdhwKnXC8UxyFvDDXB9u4dOciRMO59jL7eOOb7PAPiMjpx4qqrCzQZftL00RuNlUyo7'
app.config['STRIPE_SECRET_KEY'] = 'sk_test_51KdFY6CBDTxkbXVTszg9nk8fmvxXKSldW86vwu1D5YzZRTiQED4mxrPhBnO0vmt2SijTvgy7NiyI6PQ3kaX1ZBzv00JgNtF22T'

stripe.api_key = app.config['STRIPE_SECRET_KEY']

DOMAIN = 'http://localhost:5000'

input_json = 0
mongo = os.environ.get("mongodb+srv://pkazala:Legopepe1235@vue-shop.nuexl.mongodb.net/vue-shop?retryWrites=true&w=majority")
client = pymongo.MongoClient(mongo)
db = client["vue-shop"]

jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = '192492109249032057'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

print("All good")

@app.route('/')
def welcome():
	return 'Welcome to the flask server for the vue-shop web application!'

@app.route('/getProducts', methods=['GET'])
def get_products():
    products = []
    col = db["products"]
    cursor = col.find({})
    for document in cursor:
        document.pop('_id')
        products. append(document)
    return json.dumps(products)

@app.route('/register', methods=['POST'])
def register():
    col = db["users"]
    new_user = request.get_json()
    #Encrypting user's password
    new_user['password'] = hashlib.sha256(new_user['password'].encode('utf-8')).hexdigest()
    doc = col.find_one({'username': new_user['username']})
    if not doc:
        col.insert_one(new_user)
        return jsonify({'message': 'User registered succesfully'}), 201
    else:
        return jsonify({'message': 'Username already exists'}), 409

@app.route('/login', methods=['POST'])
def login():
    col = db["users"]
    login_details = request.get_json()
    user = col.find_one({'username': login_details['username']})
    if user:
        encrypted_password = hashlib.sha256(login_details['password'].encode('utf-8')).hexdigest()
        if encrypted_password == user['password']:
            access_token = create_access_token(identity=user['username'])
            return jsonify(access_token=access_token), 200
    return jsonify({'message': 'The username or password is incorrect'}), 401


@app.route('/getData', methods=['POST'])
def update_amount():
    global input_json
    input_json = request.get_json()
    print(input_json)
    return jsonify(input_json)

@app.route('/payment_webhook', methods=['POST'])
def payment_webhook():
    print("Webhook for payment was sent")
    if request.content_length > 1024 * 1024:
        print('Request too big')
        abort(400)
    record = request.get_data()
    header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = 'whsec_dc6cc8c2dd57ec53722326c1cb825b0667953f9815de965404710e5db7ca28f9'
    event = None

    try:
        event = stripe.Webhook.construct_event(
            record, header, endpoint_secret
        )
    except ValueError as e:
        print('Invalid payload')
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        print('Invalid signature')
        return {}, 400
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        keys = ['status','payment_status','amount_total','payment_intent','customer_details']
        for key in keys:
            print(session[key])

    return {}


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        shipping_address_collection={
            'allowed_countries': ['GB', 'US'],
        },
        shipping_options=[
            {
                'shipping_rate_data': {
                    'type': 'fixed_amount',
                    'fixed_amount': {
                        'amount': 0,
                        'currency': 'usd',
                    },
                    'display_name': 'Free shipping',
                    # Delivers between 3-5 business days
                    'delivery_estimate': {
                        'minimum': {
                            'unit': 'business_day',
                            'value': 3,
                        },
                        'maximum': { 
                            'unit': 'business_day',
                            'value': 5,
                        },
                    }
                }
            },
            {
                'shipping_rate_data': {
                    'type': 'fixed_amount',
                    'fixed_amount': {
                        'amount': 500,
                        'currency': 'usd',
                    },
                    'display_name': 'DHL shipping',
                    # Delivers between 5-7 business days
                    'delivery_estimate': {
                        'minimum': {
                            'unit': 'business_day',
                            'value': 1,
                        },
                        'maximum': {
                            'unit': 'business_day',
                            'value': 2,
                        },
                    }
                }
            },
        ],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Checkout items',
                },
                'unit_amount': input_json['total'] * 100,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url="http://localhost:8080/success",
        cancel_url="http://localhost:8080/cart",
    )

    return redirect(session.url, code=303)

if __name__ == '__main__':
    app.run()
