from flask import jsonify, request, render_template
from . import app, db
from .models import User, UserDevice, Templates, Notification
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
    json_data = request.get_json()
    title = json_data["Title"]
    message = json_data["Message"]
    
    user_ids = json_data["users"]
 
    if not title or not message or not user_ids:
        print("Error: Missing Title, Message, or user IDs")
        return jsonify({"error": "Missing Title, Message, or user IDs"}), 400
    notification = Notification(
        title=title, message=message, users=json.dumps(user_ids)
    )
    db.session.add(notification)
    db.session.commit()
 
    success_count, failure_count, bluboy_id_without_tokens, failing_bluboy_ids = send_notifications(title, message, user_ids)
    print("Notification has been inserted and sent successfully.")
    return jsonify(
        {
            "message": "Notification has been inserted and sent successfully.",
            "success_count": success_count,
            "failure_count": failure_count,
            "bluboy_id_without_tokens": bluboy_id_without_tokens,
            "failing_bluboy_ids": failing_bluboy_ids
        }
    )


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


@app.route("/")
def index():
    return render_template("index.html")


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