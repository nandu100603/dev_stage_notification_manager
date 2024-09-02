from firebase_admin import messaging
from sqlalchemy import text
from threading import Thread,get_ident
from app import db,app
from datetime import datetime
import json
import time
# import mysql.connector
from app.controllers.config import Config
# import pytz

notifier_threads = {}
all_users_while = text(
            f"""
            SELECT u.user_id, u.bluboy_id, ud.device_token
            FROM users u 
            LEFT JOIN user_devices ud ON u.user_id = ud.user_id 
            WHERE u.user_id > :last_id
            ORDER BY u.user_id
            LIMIT 450
            """
        )
bluboy_ids_while = text(
            f"""
            SELECT u.user_id, u.bluboy_id, ud.device_token
            FROM users u 
            LEFT JOIN user_devices ud ON u.user_id = ud.user_id 
            WHERE u.user_id > :last_id and u.bluboy_id in :bluboy_ids
            ORDER BY u.user_id
            LIMIT 450
            """
        )
user_ids_while = text(
            f"""
            SELECT u.user_id, u.bluboy_id, ud.device_token
            FROM users u 
            LEFT JOIN user_devices ud ON u.user_id = ud.user_id 
            WHERE u.user_id > :last_id and u.user_id in :user_ids
            ORDER BY u.user_id
            LIMIT 450
            """
        )
all_user_paginated = text(
        """
        SELECT u.user_id, u.bluboy_id, ud.device_token
        FROM users u 
        LEFT JOIN user_devices ud ON u.user_id = ud.user_id 
        ORDER BY u.user_id
        LIMIT 450
        """
    )
bluboy_ids_paginated = text(
        """
        SELECT u.user_id, u.bluboy_id, ud.device_token
        FROM users u 
        LEFT JOIN user_devices ud ON u.user_id = ud.user_id 
        WHERE u.bluboy_id in :bluboy_ids
        ORDER BY u.user_id
        LIMIT 450
        """
    )

user_ids_paginated = text(
        """
        SELECT u.user_id, u.bluboy_id, ud.device_token
        FROM users u 
        LEFT JOIN user_devices ud ON u.user_id = ud.user_id 
        WHERE u.user_id in :user_ids
        ORDER BY u.user_id
        LIMIT 450
        """
    )



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
# THREAD NOTIFIER

def getResult(thread_id):
    if thread_id in notifier_threads:
        thread_result = notifier_threads[thread_id]
        threads_info_arr = notifier_threads[thread_id].split('\n')
        if threads_info_arr[0] == "done":
            print("DELETING THREAD",thread_id)
            del notifier_threads[thread_id]
        return { "result": thread_result }
    else :
        return { "exists" : "false"}

def send_data_message(title, message, token):
        message = messaging.Message(
                    data={
                        'title': title,
                        'ticker': title,
                        'vibrate': '1',
                        'sound': '1',
                        'type': 'GENERAL',
                        'message': message
                    },
                    token=token,
                )
        try:
            # Send a message to the device corresponding to the provided
            # registration token.
            response = messaging.send(message)
            # Response is a message ID string.
            print('Successfully sent message:', response)
        except Exception as e:
            print(f"An error occurred: {e}")
            
def sendMessage(result,title,message,global_logout_ids,global_success_ids,global_uninstall_ids):
    tokens = []
    bluboy_id_with_tokens = []

    #EXTRACT TOKENS
    for row in result:
        if row.device_token:
            tokens.append(row.device_token)
            bluboy_id_with_tokens.append(row.bluboy_id)
        else:
            global_logout_ids.append(row.bluboy_id)

    # SEND MESSAGES  

    if tokens:
        print("SENDING pop-up message")
        
        inAppMessage = '{ "dialogtitle":"Refund Notification", "dialogmessage": \"' +  message + ' \"}'
        data_message = messaging.MulticastMessage(
                   data={
                        'title': "GameNavFragment",
                        'ticker': title,
                        'vibrate': '1',
                        'sound': '1',
                        'type': 'GENERAL',
                        'message': inAppMessage
                    },
                   tokens=tokens,
                )
        response1 = messaging.send_multicast(data_message)
        dataMessageSuccessCounter = 0
        for idx, resp in enumerate(response1.responses):
            if not resp.success:
                print(f"Failed token: {tokens[idx]} - Error: {resp.exception}")
            else:
                dataMessageSuccessCounter += 1
        print("SENT pop-up message to ", dataMessageSuccessCounter, " devices")
        
        multicast_message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            tokens=tokens,
        )
        print("SENDING")
        response = messaging.send_multicast(multicast_message)
        print("SENT")
        
        print("Success count:", response.success_count)
        print("Failure count:", len(result) - response.success_count)
        # Identify and log failing tokens
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                global_uninstall_ids.append(bluboy_id_with_tokens[idx])
                print(f"Failed token: {tokens[idx]} - Error: {resp.exception}")
            else:
                global_success_ids.append(bluboy_id_with_tokens[idx])
        
        return len(tokens)
    else:
        print("Success count:", 0)
        print("Failure count:", len(result))
        return 0
    
def create_parallel_notifier(title,message,username,userids=[],bluboyids=[]):
    
    print("CREATING THREAD")
    if len(userids) != 0 and len(bluboyids) != 0:
            print("CANNOT TRY WITH BOTH USERID AND BLUBOY ID AT ONCE")
            return
    thread = Thread(target = send_notification_paginated, args = (title,message,db,userids,bluboyids,notifier_threads,username))
    thread.daemon = True
    thread.start()
    
    #STORING VALUES IN DICT
    thread_id = thread.ident
    notifier_threads[thread_id] = f"ongoing\n0\n0\n0"
    print(notifier_threads)

    # RETURNING THE THREADS IDENTITY 
    return thread_id

def send_notification_paginated(title,message,db,user_ids,bluboy_ids,notifier_threads,username):
    with app.app_context():
        
        thread_id = get_ident()

        print("HELLO FROM THREAD")
        number_users_completed = 0

        global_uninstall_ids =[]
        global_success_ids =[]
        global_logout_ids =[]

        if len(user_ids) != 0: 
            result = db.session.execute(user_ids_paginated, {"user_ids": tuple(user_ids)}).fetchall()
        elif len(bluboy_ids) != 0:
            result = db.session.execute(bluboy_ids_paginated, {"bluboy_ids": tuple(bluboy_ids)}).fetchall()
        else: 
            result = db.session.execute(all_user_paginated).fetchall()
        
        # Printing Result of Sending Messages
        print("FIRST BATCH")    
        for row in result:
                print(row.user_id, row.bluboy_id)

        no_of_tokens = 0
        
        try:
            # SENDING THE MESSAGES
            no_of_tokens = sendMessage(result,title,message,global_logout_ids,global_success_ids,global_uninstall_ids)
        except Exception as e:
            print(f"An error occurred: {e}")

        # Counting number of Users with Tokens  
        number_users_completed += no_of_tokens

        #Storing Result in Dict
        notifier_threads[thread_id] = f"ongoing\n{number_users_completed}\n{len(global_success_ids)}\n{len(global_uninstall_ids)}"
        print(notifier_threads)

        # Sends Messages in paginated manner till no more are available
        while result :
            # Get Last User ID
            last_id = result[-1].user_id

            if len(user_ids) != 0:
                result = db.session.execute(user_ids_while, {"user_ids": tuple(user_ids),"last_id":last_id}).fetchall()
            elif len(bluboy_ids) != 0:
                result = db.session.execute(bluboy_ids_while, {"bluboy_ids": tuple(bluboy_ids),"last_id":last_id}).fetchall()
            else:
                result = db.session.execute(all_users_while,{"last_id":last_id}).fetchall()
            
            # result = db.session.execute(query).fetchall()
            print("NEXT BATCH")
            for row in result:
                print(row.user_id, row.bluboy_id) 
            
            #Send Messages
            no_of_tokens = sendMessage(result,title,message,global_logout_ids,global_success_ids,global_uninstall_ids)

            # Counting number of Users with Tokens  
            number_users_completed += no_of_tokens
            
            #Storing Result in Dict
            notifier_threads[thread_id] = f"ongoing\n{number_users_completed}\n{len(global_success_ids)}\n{len(global_uninstall_ids)}"
            print(notifier_threads)

        print("OPERATION DONE")
        print(
            " SUCCESSES:"
            ,len(global_success_ids)
            ," FAILURES:"
            ,len(global_logout_ids) + len(global_uninstall_ids)
        )


        #Storing result in dict
        notifier_threads[thread_id] = f"done\n{number_users_completed}\n{len(global_success_ids)}\n{len(global_uninstall_ids)}"
        print(notifier_threads)
        insert_query = text(
                """
                INSERT INTO Uninstalled (title,message,success_list, logout_list, uninstalled_list, sender, timestamp)
                VALUES (:title, :message, :success_list, :logout_list, :uninstalled_list,:sender, :timestamp)
                """
            )
        db.session.execute(insert_query, {
            "title":title,
            "message":message,
            "success_list": json.dumps(global_success_ids),
            "logout_list": json.dumps(global_logout_ids),
            "uninstalled_list": json.dumps(global_uninstall_ids),
            "sender":username,
            "timestamp": datetime.now()

        })
        db.session.commit()


#topics
def get_topics():
    conn = None
    topics = []
    try:
        db_config = Config().getDBConfig()
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT topic_name FROM Topics")  
        topics = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return [topic[0] for topic in topics]
 
def log_notification(topic_name, title, message_body,username):
    conn = None
    try:
        # GMT time
        gmt = pytz.timezone('GMT')
        now = datetime.now(gmt)
       
        # GMT to IST convrsion
        ist = pytz.timezone('Asia/Kolkata')
        ist_now = now.astimezone(ist)
        
        db_config = Config().getDBConfig()
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO TopicsLogs (topic_name, title, messageBody, timestamp,sender) VALUES (%s, %s, %s, %s,%s)",
            (topic_name, title, message_body, ist_now,username)
        )
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
 

##fro updating the user.txt when uploaded the csv filw with userids and devices tokens
def update_users_txt_and_send_notifications(title, message, user_ids, device_tokens,username):
    with app.app_context():
        succ_count=0
        failurecount=0
        success_user_ids = []
        failure_user_ids = []
        thread_id = get_ident()
        try:
            # Send notifications in batches of 450
            for i in range(0, len(device_tokens), 450):
                batch_tokens = device_tokens[i:i+450]
                batch_user_ids = user_ids[i:i+450]
                message = messaging.MulticastMessage(
                    notification=messaging.Notification(
                        title=title,
                        body=message,
                    ),
                    tokens=batch_tokens,
                )
                response = messaging.send_multicast(message)
                succ_count+=response.success_count
                failurecount+=response.failure_count
                for j, result in enumerate(response.responses):
                    if result.success:
                        success_user_ids.append(batch_user_ids[j])
                    else:
                        failure_user_ids.append(batch_user_ids[j])
                print("Success count:", response.success_count)
                print("Failure count:", (response.failure_count) )
                notifier_threads[thread_id] = f"ongoing\n{i+450}\n{succ_count}\n{failurecount}"

                print(f'Successfully sent batch {i // 450 + 1}: {response.success_count} messages')
            notifier_threads[thread_id] = f"done\n{len(device_tokens)}\n{succ_count}\n{failurecount}"
        except Exception as e:
            # Log the detailed error
            print(f"An error occurred while sending notifications: {str(e)}")
        
        success_List_query= text(
        """
        SELECT u.bluboy_id
        FROM users u
        WHERE u.user_id IN :user_ids
        ORDER BY u.user_id
        """
        )
        sucess_result = db.session.execute(success_List_query, {"user_ids": tuple(success_user_ids)}).fetchall()
        failure_List_query= text(
        """
        SELECT u.bluboy_id
        FROM users u
        WHERE u.user_id IN :user_ids
        ORDER BY u.user_id
        """
        )
        failure_result = db.session.execute(failure_List_query, {"user_ids": tuple(failure_user_ids)}).fetchall()
        success_bluboy_ids=[row[0] for row in sucess_result]
        failure_bluboy_ids = [row[0] for row in failure_result]

        insert_query = text(
                    """
                    INSERT INTO Uninstalled (title,message,success_list, logout_list, uninstalled_list, sender, timestamp)
                    VALUES (:title, :message, :success_list, :logout_list, :uninstalled_list,:sender, :timestamp)
                    """
                )
        db.session.execute(insert_query, {
                "title":title,
                "message":message,
                "success_list": json.dumps(success_bluboy_ids),
                "logout_list": json.dumps([]),
                "uninstalled_list": json.dumps(failure_bluboy_ids),
                "sender":username,
                "timestamp": datetime.now()

            })
        db.session.commit()


def add_thread(thread_id):
    thread_id = thread_id.ident
    notifier_threads[thread_id] = f"ongoing\n{0}\n{0}\n{0}"
    print(notifier_threads)