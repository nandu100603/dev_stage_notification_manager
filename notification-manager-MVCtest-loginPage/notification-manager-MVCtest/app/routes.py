from flask import jsonify, request, render_template, session, redirect, url_for
from . import app, db
from .models import User, UserDevice, Templates, Notification,LoginUser
from .controllers.notification_controller import send_notifications
import json


@app.route("/templatesfetchfromdb", methods=["GET"])
def temp_fetch():
    print("Fetching templates from the database")
    template = Templates.query.all()
    temp_list = [{"title": i.title, "message": i.message} for i in template]
    print("Templates fetched:", temp_list)
    return jsonify(temp_list)


@app.route("/pushtemplatetodb", methods=["POST"])
def push_templates():
    json_data = request.get_json()
    print("Received JSON data for templates:", json_data)
    for temp_data in json_data["template"]:
        temp = Templates.query.filter_by(title=temp_data["title"]).first()
        if temp:
            print(f"Updating template with title: {temp_data['title']}")
            temp.message = temp_data["message"]
        else:
            print(f"Inserting new template with title: {temp_data['title']}")
            temp = Templates(title=temp_data["title"], message=temp_data["message"])
            db.session.add(temp)
    db.session.commit()
    return "Data has been inserted/updated successfully."


@app.route("/pushnotificationtodb", methods=["POST"])
def push_notifications():
    if "username" not in session:
        return jsonify({"error": "Unauthorized access"}), 403
 
    json_data = request.get_json()
    title = json_data["Title"]
    message = json_data["Message"]
    user_ids = json_data["users"]
    username = session["username"]
 
    if not title or not message or not user_ids:
        print("Error: Missing Title, Message, or user IDs")
        return jsonify({"error": "Missing Title, Message, or user IDs"}), 400
 
    notification = Notification(
        title=title, message=message, users=json.dumps(user_ids),sender=username
    )
    db.session.add(notification)
    db.session.commit()
 
    success_count, failure_count, bluboy_id_without_tokens, failing_bluboy_ids = send_notifications(title, message, user_ids,username)
    print("Notification has been inserted and sent successfully.")
    return jsonify(
        {
            "message": "Notification has been inserted and sent successfully.",
            "success_count": success_count,
            "failure_count": failure_count,
            "bluboy_id_without_tokens": bluboy_id_without_tokens,
            "failing_bluboy_ids": failing_bluboy_ids,
            "sent_by": username
        }
    )
 
# Other routes remain unchanged

@app.route("/notificationsfetchfromdb", methods=["GET"])
def fetch_notifications():
    print("Fetching notifications from the database")
    notifications = Notification.query.all()
    notifications_list = [
        {
            "notification_id": notification.notification_id,
            "title": notification.title,
            "message": notification.message,
            "users": notification.users,
            "timestamp": notification.timestamp,
        }
        for notification in notifications
    ]
    print("Notifications fetched:", notifications_list)
    return jsonify(notifications_list)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = LoginUser.query.filter_by(username=username, password=password).first()
        if user:
            session["username"] = user.username
            return redirect(url_for("index"))
        else:
            return "Invalid credentials, please try again."
    return render_template("login.html")
 
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))
 
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session["username"])

@app.route("/selecteduser", methods=["GET"])
def selected_user():
    print("Fetching selected users")

    users = User.query.with_entities(User.player_name, User.bluboy_id).all()

    # Construct the list of users in the desired format
    users_list = [
        {"player_name": user.player_name, "bluboy_id": user.bluboy_id} for user in users
    ]

    # Create the response dictionary
    response = {"users": users_list}
    # print("Selected users:", response)

    return jsonify(response)