from flask import Flask, redirect, render_template, request, session, url_for
from typehints import *
import secrets
import show_data
import fetch_data
import mysql_connector as sql

app: Flask = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.before_request
def check_login() -> Response | None:
	if not session.get("logged_in") and request.endpoint != "login" and request.endpoint != "authenticate":
		return redirect(url_for("login"))
	return None

@app.route("/login")
def login() -> Response | str:
	if session.get("logged_in"):
		referrer = request.referrer
		if referrer:
			from urllib.parse import urlparse
			parsed_url = urlparse(referrer)
			if parsed_url.netloc == request.host:
				return redirect(referrer)
		return redirect(url_for("index"))
	return render_template("login.html", user="User", auth="/authenticate")

@app.route("/authenticate", methods=["POST"])
def authenticate() -> Response | str:
	if request.form.get("user") and request.form.get("password"):
		try:
			while True:
				try:
					sql.connect(request.form["user"], request.form["password"])
					break
				except sql.pymysql.err.OperationalError:
					return render_template("login.html", user="User", auth="/authenticate", error_message="Invalid username or password")
				except Exception:
					return render_template("failed.html", reason="Unknown error occurred")
			import views
			import triggers
			if sql.db_connector and sql.cursor:
				views.create_views(sql.db_connector, sql.cursor)
				triggers.create_triggers(sql.db_connector, sql.cursor)
				session["logged_in"] = True
			return redirect(url_for("index"))
		except Exception:
			return render_template("failed.html", reason="Unknown error occurred")
	return render_template("failed.html", reason="Login information not entered properly!")

@app.route("/faculty")
def log_faculty() -> Response | str:
	if not session.get("faculty") or not session.get("faculty_details"):
		return render_template("login.html", user="ID", userType="number", auth="/auth_faculty", role="faculty")
	return redirect(url_for("faculty_details"))

@app.route("/auth_faculty", methods=["POST"])
def auth_faculty() -> Response | str:
	if request.form.get("user") and request.form.get("password"):
		try:
			if sql.cursor and isinstance(request.form["user"], int):
				session["faculty_details"] = fetch_data.get_faculty_details(sql.cursor,
																			id=request.form["user"],
																			password=request.form["password"])
				session["faculty"] = True
			return redirect(url_for("faculty_details"))
		except AssertionError:
			return render_template("login.html", user="ID", userType="number", auth="/auth_faculty", role="faculty", error_message="Invalid ID or Password")
		except Exception:
			return render_template("login.html", user="ID", userType="number", auth="/auth_faculty", role="faculty", error_message="Invalid ID")
	return render_template("failed.html", error_message="Login information not entered properly!")

@app.route("/home")
@app.route("/")
def index() -> str:
	return render_template("index.html")

@app.route("/about")
def about() -> str:
	return render_template("about.html")

@app.route("/campus")
def show_campuses() -> str:
	if sql.cursor:
		return render_template("campus.html", campuses=show_data.get_campuses(sql.cursor))
	return render_template("failed.html", reason="Unknown error occurred")

@app.route("/department")
def show_departments() -> str:
	if sql.cursor:
		return render_template("department.html", departments=show_data.get_departments(sql.cursor))
	return render_template("failed.html", reason="Unknown error occurred")

@app.route("/programme")
def show_programmes() -> str:
	if sql.cursor:
		return render_template("programme.html", programmes=show_data.get_programmes(sql.cursor))
	return render_template("failed.html", reason="Unknown error occurred")

@app.route("/campus/<string:campus>")
def show_schools(campus: str) -> Response:
	if campus == "SASTRA": # for testing only
		return redirect("https://sastra.edu")
	return redirect(f"https://{campus.replace(' ', '').lower()}.sastra.edu")

@app.route("/faculty/details")
def faculty_details() -> str:
	if sql.cursor:
		if not session["faculty"] or not session["faculty_details"]:
			raise ValueError("Illegal access or value is missing.")
		faculty = session["faculty_details"]
		return render_template("faculty.html", faculty=faculty, campus=show_data.get_campus_name(sql.cursor, id=faculty["campus_id"]))
	return render_template("failed.html", reason="Unknown error occurred")

@app.errorhandler(404)
def page_not_found(error: NotFound) -> tuple[str, int]:
	print(type(error))
	return (render_template("404.html"), 404)

if __name__ == "__main__":
	app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPSONLY=True)
	app.run(host="0.0.0.0", port=5000, debug=False)
