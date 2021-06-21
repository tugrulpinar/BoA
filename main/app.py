from flask import Flask, redirect, render_template, request, send_from_directory
from flask_session import Session
from helpers import apology
from tempfile import mkdtemp
import os
from brain import *

# Configure application
app = Flask(__name__)


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_COOKIE_SECURE"] = True
app.config["CLIENT_FILES"] = 'C:\\Users\\pc\\Desktop\\Projects\\BOA\\static\\client\\pdf'
# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"Server Error: {e}, route: {request.url}")
    return render_template("500.html")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        # get the text from the textarea
        text = request.form.get("textbox").strip()

        # ensure the user enters text
        if not text or text == "":
            return apology("Please enter text")

        case_law = get_case_law(text)

        # ensure the user enters valid case law
        if not case_law:
            FAILED_TO_FIND.clear()
            return apology("Please enter a valid input")

        names, opposer = get_names_opposer(case_law)

        # ensure the user enters valid input
        if not names or not opposer:
            FAILED_TO_FIND.clear()
            return apology("Please enter valid names")

        codes_list = get_code(opposer, names, case_law)

        # ensure the user enters valid case codes
        if not codes_list:
            FAILED_TO_FIND.clear()
            return apology("Please provide the case law codes")

        clean_names = get_clean_names(names, codes_list, case_law)
        combined = list(zip(clean_names, codes_list, case_law))
        file_folder, enc_name = generate_random_folder()

        global file_size, fails
        file_size, fails = collect_files(file_folder, combined)

        return redirect(f"/results/{enc_name}")
    else:
        return render_template("index.html")


@app.route("/results/<enc_name>", methods=["GET", "POST"])
def results(enc_name):
    if request.method == "POST":
        try:
            file_folder = os.path.join(app.config["CLIENT_FILES"], enc_name)
            return send_from_directory(file_folder, filename="BookOfAuthorities.pdf", as_attachment=True)
        except:
            return apology("File not found")
    else:
        return render_template("results.html", file_size=file_size, fails=fails, enc_name=enc_name)


if __name__ == "__main__":
    app.run(debug=True)
