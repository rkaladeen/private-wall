from flask import Flask, render_template, request, redirect, flash, session
from mysqlconnection import connectToMySQL    # import the function that will return an instance of a connection
import re, datetime
from datetime import timedelta
from flask_bcrypt import Bcrypt
app = Flask(__name__)
app.secret_key = "abc123"
bcrypt = Bcrypt(app)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') 
PW_REGEX = re.compile(r'^(?=.*[A-Z])(?=.*\d)[a-zA-Z]\w{7,14}$')
ALL_LETTERS_REGEX = re.compile(r'^[A-Za-z]{1,}$')

######################### Messaging Application  ###########################
@app.route("/send", methods=['POST'])
def send():
  is_vaild = True
  if len(request.form['sent_message']) < 6:
    is_vaild = False
    flash("Please ensure your message has at least 5 characters",'sent-error')
  if is_vaild:
    query = "INSERT INTO messages (sender_id, recipient_id, message, created_at, updated_at) VALUES (%(s_id)s, %(r_id)s, %(sent_ms)s, NOW(), NOW());"
    data = {
      "s_id" : request.form['sender_id'],
      "r_id" : request.form['recipient_id'],
      "sent_ms" : str(request.form['sent_message'])
    }
    session['logged_in']['messages_sent'] += 1
    messages_count = session['logged_in']['messages_sent']
    flash(f"You have sent {messages_count} messages so far.", 'sent')

    mysql = connectToMySQL("cd_mysql_flask")
    mysql.query_db(query, data)

    return redirect("/welcome")
  flash("Messages must be more than 5 character long.", 'short-text')
  return redirect("/welcome")

@app.route("/delete-message/<message_id>")
def delMessage(message_id):
  if session['logged_in']['is_logged_in']:
    mysql = connectToMySQL("cd_mysql_flask")
    query = "DELETE FROM messages WHERE id = %(message_id)s"
    data = {
      "message_id": message_id
    }
    mysql.query_db(query, data)
    flash("Message Deleted!", 'message-delete')
    return redirect("/welcome")
  return redirect("/")


################################## LOGIN ##################################  
@app.route("/")
def index():
  return render_template("index.html")
 
@app.route("/logout")
def logout():
  session['register-dict'] = {}
  session['logged_in'] = { 
    "is_logged_in" : False, 
    "is_admin" : "", 
    "user_id" : None, 
    "user_name" : "", 
    "user_email" : "",
    "messages_sent" : 0,
    }
  # session['is_admin'] = ""
  # session['login-email'] = ""
  session['messages_sent'] = 0
  return redirect("/")
# When Login button is clicked on Index the following route is executed, then it redirects user to Welcome user page
@app.route("/login", methods = ['POST'])
def login():
  query = "SELECT id, first_name, email, password_hash, user_level FROM users WHERE email=%(email)s;"
  data = { "email" : request.form['login-email'] }
  
  session["logged_in['user_email']"] = request.form['login-email']

  mysql = connectToMySQL('cd_mysql_flask')
  user = mysql.query_db(query, data)
  
  if user != ():
    if bcrypt.check_password_hash(user[0]['password_hash'], request.form["login-password"]):
      session['logged_in'] = { 
        "is_logged_in" : True, 
        "is_admin" : user[0]['user_level'], 
        "user_id" : user[0]['id'], 
        "user_name" : user[0]['first_name'], 
        "user_email" : user[0]['email'],
        "messages_sent" : 0,
        "messages_rec" : 0
      }

      if session['logged_in']['is_admin'] == "Administrator":
        return redirect("/users")
      return redirect("/welcome")
      
  flash("The email or password you entered is incorrect, please try again!", 'failed')
  return redirect("/") # Is condition are false, user is redirected to login page (index.html)


@app.route("/welcome")
def welcome():
  if session['logged_in']['is_logged_in']:
    ############# Add query to render friends ###################
    user_query = "SELECT id, first_name, user_level FROM users WHERE user_level = 'User' AND id <> %(user_id)s ORDER BY first_name ASC;"
    data = { "user_id" : session['logged_in']['user_id'] }
    mysql = connectToMySQL('cd_mysql_flask')
    all_users = mysql.query_db(user_query, data) 

    ############# Add query to render messages ###################
    message_query = "SELECT users.first_name, messages.id, messages.sender_id , messages.message, messages.created_at FROM users LEFT JOIN messages ON users.id = recipient_id WHERE recipient_id = %(user_id)s ORDER BY messages.created_at DESC;"
    message_data = { "user_id" : session['logged_in']['user_id'] }
    
    mysql = connectToMySQL('cd_mysql_flask')
    my_messages = mysql.query_db(message_query, message_data)

    
    # Convert and calculates elaspse time on messages
    # session['ms_time_dict'] = {}
    # sent_time = my_messages[0]['created_at']
    # now = datetime.datetime.now()
    # elapsed_time = now - sent_time
    # time_in_sec = elapsed_time.seconds
    # if time_in_sec < 60:
      
    # print(time_in_sec)
    # # elapse_conv = elapsed_time.strftime('%H')
    # print(f"CREATED", {sent_time}, "ELAPSED", {elapsed_time})

    # Counter to check how many messages are sent to user
    session['logged_in']['messages_rec'] = len(my_messages)
   
    return render_template("welcome.html", users = all_users, messages = my_messages) 
  return redirect("/") # Redirects to index if user is not logged in

############################## REGISTER ###############################
@app.route("/register")
def register():
  return render_template("register.html")

@app.route("/registration", methods=["POST"])
def registration():
  is_valid = True
  if not ALL_LETTERS_REGEX.match(request.form["fname"]):
    is_valid = False
    flash("First name must contain at least two letters and contain only letters", 'fname')
  if not ALL_LETTERS_REGEX.match(request.form["lname"]):
    is_valid = False
    flash("Last name must contain at least two letters and contain only letters", 'lname')
  if not EMAIL_REGEX.match(request.form["email"]):
    is_valid = False
    flash("Invalid email address!", 'email')
  if not PW_REGEX.match(request.form["password"]):
    is_valid = False
    flash("The password's first character must be a letter, it must contain at least 8 characters and no more than 15 characters and no characters other than letters, numbers and the underscore may be used", 'password')
  if request.form["password"] != request.form["password-confirm"]:
    is_valid = False
    flash("Password must match", 'pw-confirm')

  if is_valid:
    query = "INSERT INTO users (first_name, last_name, email, password_hash,created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW());"
    
    pw_hash = bcrypt.generate_password_hash(request.form["password"])
    data = {
      "fn": request.form["fname"],
      "ln": request.form["lname"],
      "em": request.form["email"],
      "pw": pw_hash
    } 
    

    mysql = connectToMySQL("cd_mysql_flask")
    mysql.query_db(query, data)
    
    return redirect("/")
  session['register-dict'] = {
    "fn": request.form["fname"],
    "ln": request.form["lname"],
    "em": request.form["email"]
  }
  return redirect("/register")

@app.route("/email", methods=['POST'])
def email():
  found = False
  mysql = connectToMySQL('cd_mysql_flask')
  query = "SELECT email FROM users WHERE email = %(em)s;"
  data = { "em" : request.form['email'] }
  results = mysql.query_db(query, data)
  if results:
    found = True
  return render_template('partials/email.html', found = found)

@app.route("/usersearch")
def search():
  if request.args.get('username') != "":
    mysql = connectToMySQL("cd_mysql_flask")
    query = "SELECT * FROM users WHERE first_name LIKE %%(name)s;"
    data = { "name" : request.args.get('username') + "%" }
    results = mysql.query_db(query, data)
    print("TESTSTSTSTST",request.args.get('username'))
    return render_template("partials/search.html", users = results)
  return render_template("partials/search.html")
  
  

########################### ADMINISTRATIVE  ############################  

@app.route("/users")
def users():
  if session['logged_in']['is_admin'] == "Administrator":
    mysql = connectToMySQL('cd_mysql_flask')                      # call the function, passing in the name of our db
    users = mysql.query_db('SELECT * FROM users;')      # call the query_db function, pass in the query as a string
    print(users)
    return render_template("users.html", all_users = users)
  return redirect("/")
@app.route("/create")
def create():
  return render_template("create.html")


@app.route("/users/new", methods=["POST"])
def add_friend_to_db():
  is_valid = True
  if not ALL_LETTERS_REGEX.match(request.form["fname"]):
    is_valid = False
    flash("First name must contain at least two letters and contain only letters", 'fname')
  if not ALL_LETTERS_REGEX.match(request.form["lname"]):
    is_valid = False
    flash("Last name must contain at least two letters and contain only letters", 'lname')
  if not EMAIL_REGEX.match(request.form["email"]):
    is_valid = False
    flash("Invalid email address!", 'email')
  if not PW_REGEX.match(request.form["password"]):
    is_valid = False
    flash("The password's first character must be a letter, it must contain at least 8 characters and no more than 15 characters and no characters other than letters, numbers and the underscore may be used", 'password')

  if is_valid:
    query = "INSERT INTO users (first_name, last_name, email, password_hash, user_level,created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, %(admin)s,NOW(), NOW());"
    
    pw_hash = bcrypt.generate_password_hash(request.form["password"])
    data = {
      "fn": request.form["fname"],
      "ln": request.form["lname"],
      "em": request.form["email"],
      "pw": pw_hash,
      "admin": request.form["user_level"]
    }
    mysql = connectToMySQL("cd_mysql_flask")
    mysql.query_db(query, data)
    flash("User Successfully Added!", 'user-add')
    return redirect("/users")
  session['register-dict'] = {
    "fn": request.form["fname"],
    "ln": request.form["lname"],
    "em": request.form["email"]
  }
  return redirect("/create")

  # UPDATE renders route
@app.route("/update/<user_id>")
def updatePage(user_id):
  if session['logged_in']['is_admin'] == "Administrator":
    mysql = connectToMySQL('cd_mysql_flask') 
    query = "SELECT * FROM users WHERE id = %(id)s;"
    data = {
      "id": user_id
    }
    user_data = mysql.query_db(query, data) 

    return render_template("update.html", user = user_data)
  return redirect("/")
  # UPDATE Process route
@app.route("/users/<user>/edit", methods=["POST"])
def update(user):
  is_valid = True
  if len(request.form["fname-new"]) < 1:
    is_valid = False
    flash("Please enter a valid first name", 'fname')
  if len(request.form["lname-new"]) < 1:
    is_valid = False
    flash("Please enter a valid last name", 'lname')
  if not EMAIL_REGEX.match(request.form["email-new"]):
    is_valid = False
    flash("Invalid email address!", 'email')
  
  if is_valid:
    query = "UPDATE users SET first_name = %(fn_new)s, last_name = %(ln_new)s , email = %(em_new)s, user_level = %(ul_new)s, updated_at = NOW() WHERE id = %(id)s;"

    data = {
      "id": user,
      "fn_new": request.form["fname-new"],
      "ln_new": request.form["lname-new"],
      "em_new": request.form["email-new"],
      "ul_new": request.form["user_level-new"]
    }

    mysql = connectToMySQL("cd_mysql_flask")
    mysql.query_db(query, data)
    flash("User Information Updated!", 'user-update')
    return redirect(f"/users/{user}")
  return redirect(f"/update/{user}")
  # SHOW ROUTES
@app.route("/users/<user_id>")
def view(user_id):
  if session['logged_in']['is_admin'] == "Administrator":
    mysql = connectToMySQL('cd_mysql_flask') 
    query = "SELECT * FROM users WHERE id = %(id)s;"
    data = {
      "id": user_id
    }
    user_data = mysql.query_db(query, data) 

    return render_template("user.html", user = user_data)
  return redirect("/")  
@app.route("/users/<user_id>/destroy")
def delete(user_id):
  if session['logged_in']['is_admin'] == "Administrator":
    mysql = connectToMySQL("cd_mysql_flask")
    query = "DELETE FROM users WHERE id = %(id)s"
    data = {
      "id": user_id
    }
    mysql.query_db(query, data)
    flash("User Removed!", 'user-delete')
    return redirect("/users")
  return redirect("/")

if __name__ == "__main__":
  app.run(debug=True)

