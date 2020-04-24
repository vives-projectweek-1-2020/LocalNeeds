# Python standard libraries
import json
import os
import sqlite3

# Third-party libraries
from flask import Flask, render_template, redirect, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
from db import init_db_command
from user import User

# .env
from dotenv import load_dotenv
load_dotenv('.env')

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

app = Flask(__name__)
app.secret_key = os.urandom(24)
db_name = "database/UberNeeds.db"

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# Naive database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route("/")
def homepage():
	return render_template("homepage.html", google_user=current_user)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/login")
def login():
	# return render_template("login.html")

	# Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("homepage"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("homepage"))

@app.route("/profile")
@login_required
def profile():
    services_info = get_categories()
    return render_template("profile.html", google_user=current_user, services=services_info[0], services_id=services_info[1], user_info=get_user_info())

def get_user_info():
    conn = sqlite3.connect("database/UberNeeds.db")
    cursor = conn.execute("select * from Users where id = ?", [current_user.id])
    data = []

    for row in cursor:
        data.append((row[1], row[2], row[3]))

    conn.close()
    return data[0]

@app.route("/save_user", methods=['POST'])
def save_user():
    tel = request.form['tel']
    postalcode = request.form['postalcode']
    city = request.form['city']

    email = current_user.email
    user_id = User.get_userid_by_email(email)
    add_user_info(user_id, postalcode, city, tel)

    services = request.form.getlist('service')

    return redirect(url_for("profile"))

def add_user_info(user_id, postalcode, city, tel):
    conn = sqlite3.connect(db_name)
    statement_insert = 'insert into Users values (?, ?, ?, ?)'
    statement_update = '''
        update Users set 
        PostalCode = ?,
        Location = ?,
        TelNumber = ?
        where Users.id = ?
    '''   

    try:
        conn.execute(statement_insert, [user_id, postalcode, city, tel])
    except sqlite3.IntegrityError:
        conn.execute(statement_update, [postalcode, city, tel, user_id])

    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(db_name)
    cursor = conn.execute("select * from Categories")
    services = []
    services_id = []

    for row in cursor:
        services.append(row[1])
        services_id.append(row[0])
    conn.close()

    return services, services_id

@app.route("/categoriesfeed/<category>")
def categoriesfeed(category):
    conn = sqlite3.connect(db_name)
    statement = '''
        select Users.*, avgrating from Users
        join UsersCategories on Users.id = UsersCategories.User_id
        join Categories on UsersCategories.Categorie_id = Categories.id
        where Categories.Name = ?
        order by AvgRating desc
    '''
    cursor = conn.execute(statement, [category])
    data = {}

    for row in cursor:
        userid = row[0]

        data[userid] = []
        for element in row:
            data[userid].append(element)

        GoogleUser = User.get(userid)
        data[userid].extend([GoogleUser.name, GoogleUser.email, GoogleUser.profile_pic])
    conn.close()
    return render_template("categoriesfeed.html", google_user=current_user, text=category, data=data)

@app.route("/about_us")
def aboutus():
	return render_template("about_us.html", google_user=current_user)

@app.route("/categories")
def categories():
	return render_template("categories.html", categories=getcategories(), google_user=current_user)

@app.route("/addcategorie")
def addcategorie():
	return render_template("addcategorie.html", google_user=current_user)

def getcategories():
	conn = sqlite3.connect("database/UberNeeds.db")
	cursor = conn.execute("select * from Categories")
	data = []

	for row in cursor:
		data.append({"name":row[1],
					"description": row[2]})
	conn.close()

	return data


if __name__ == "__main__":
    # here is starting of the development HTTP server
    # app.run(ssl_context=("cert.pem", "key.pem"), host='0.0.0.0', port=8008)
    app.run(ssl_context="adhoc", host='0.0.0.0', port=8008)