from flask import Flask, render_template


app = Flask(__name__)


@app.route("/")
def home_page():
   return render_template("login.html")


@app.route("/create_account")
def movies_page():
    return render_template("create_account.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)