from flask import Flask, render_template
import sqlite3
app = Flask(__name__)

@app.route("/")
def index():
	return render_template("index.html", myvariable="Hi")

@app.route("/homepage")
def homepage():
	return render_template("homepage.html")

@app.route("/login")
def login():
	return render_template("login.html")

@app.route("/profile")
def profile():
	return render_template("profile.html")

@app.route("/categories")
def categories():
	return render_template("categories.html", categories=getcategories())

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
    app.run(host='127.0.0.1', port=8008)