from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
        return render_template("login.html")

@app.route('/create_account')
def create_account():
    return render_template('create_account.html')

@app.route('/forgot_pass')
def forgot_pass():
    return render_template('forgot_pass.html')

@app.route('/student.html')
def student():
    return render_template('student.html')

if __name__=="__main__":
        app.run(debug=True)