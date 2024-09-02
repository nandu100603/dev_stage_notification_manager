from firebase_admin import messaging
from sqlalchemy import text
from app import db
from datetime import datetime
import json

def send_notifications(title, message, bluboy_ids, username):
    print(
        "send_notifications called with title:",
        title,
        "message:",
        message,
        "bluboy_ids:",
        bluboy_ids,
        "username:",
        username
    )

    # Join the users and user_devices tables on user_id and filter by bluboy_id
    query = text(
        """
        SELECT u.bluboy_id, ud.device_token
        FROM users u
        LEFT JOIN user_devices ud ON u.user_id = ud.user_id
        WHERE u.bluboy_id IN :bluboy_ids
        """
    )

    # Execute the query with the bluboy_ids parameter
    result = db.session.execute(query, {"bluboy_ids": tuple(bluboy_ids)}).fetchall()

    # Extract tokens and track missing device tokens
    tokens = []
    bluboy_id_with_tokens = []
    bluboy_id_without_tokens = []

    for row in result:
        if row.device_token:
            tokens.append(row.device_token)
            bluboy_id_with_tokens.append(row.bluboy_id)
        else:
            bluboy_id_without_tokens.append(row.bluboy_id)

    print("Tokens fetched:", tokens)
    print("Bluboy IDs without device tokens:", bluboy_id_without_tokens)

    # Send notifications if there are any tokens
    if tokens:
        multicast_message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            tokens=tokens,
        )
        response = messaging.send_multicast(multicast_message)
        print("Success count:", response.success_count)
        print("Failure count:", (response.failure_count) + len(bluboy_id_without_tokens))

        # Identify and log failing tokens
        failing_bluboy_ids = []
        success_count = []
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                failing_bluboy_ids.append(bluboy_id_with_tokens[idx])
                print(f"Failed token: {tokens[idx]} - Error: {resp.exception}")
            else:
                success_count.append(bluboy_id_with_tokens[idx])
        print("Success Count ids", success_count)

        print("Bluboy IDs with invalid tokens:", failing_bluboy_ids)

        # Total failure count includes missing device tokens and invalid tokens
        total_failure_count = len(bluboy_id_without_tokens) + response.failure_count

        # Insert into Uninstalled table
        insert_query = text(
            """
            INSERT INTO Uninstalled (success_list, logout_list, uninstalled_list, timestamp)
            VALUES (:success_list, :logout_list, :uninstalled_list, :timestamp)
            """
        )
        db.session.execute(insert_query, {
            "success_list": json.dumps(success_count),
            "logout_list": json.dumps(bluboy_id_without_tokens),
            "uninstalled_list": json.dumps(failing_bluboy_ids),
            "timestamp": datetime.utcnow()
        })

        
        db.session.commit()

        return response.success_count, total_failure_count, bluboy_id_without_tokens, failing_bluboy_ids
    

    # Insert into Uninstalled table when there are no tokens
    insert_query = text(
        """
        INSERT INTO Uninstalled (success_list, logout_list, uninstalled_list, timestamp)
        VALUES (:success_list, :logout_list, :uninstalled_list, :timestamp)
        """
    )
    db.session.execute(insert_query, {
        "success_list": json.dumps([]),
        "logout_list": json.dumps(bluboy_id_without_tokens),
        "uninstalled_list": json.dumps([]),
        "timestamp": datetime.utcnow()
    })
    db.session.commit()

    return 0, len(bluboy_ids), bluboy_id_without_tokens, []
