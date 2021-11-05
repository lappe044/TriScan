from app import app

#how to run http://localhost:2000/
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=2000)