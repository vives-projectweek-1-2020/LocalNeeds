from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def homepage():
	return render_template("index.html", myvariable="Hi")


if __name__ == "__main__":
    # here is starting of the development HTTP server
    app.run(host='0.0.0.0', port=8008)