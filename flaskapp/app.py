from flask import Flask, render_template
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


if __name__ == "__main__":
    # here is starting of the development HTTP server
    app.run(host='127.0.0.1', port=8008)