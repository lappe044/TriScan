from flask import Flask, render_template, request, redirect

from app import app



@app.route("/")
def login():
    
    #email
    #password


    # if email is associate with student, render template student-index
    # if email is associate with faculty, render template faculty-index

    return render_template("/faculty.html")


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":

        req = request.form

        first_name = req["f_name"]
        last_name = req["l_name"]
        email = req["email"]
        password = req["password"]
        profession = req["profession"]

        print(first_name,last_name,email,password, profession)

        return redirect(request.url)

    return render_template("/create_account.html")





