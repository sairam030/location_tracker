import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, redirect, request, render_template, session, jsonify

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure key

# Initialize Firebase Firestore
cred = credentials.Certificate("firebase/serviceAccountKey.json")  # Path to Firebase JSON Key
firebase_admin.initialize_app(cred)
db = firestore.client()  # Firestore database instance

# Home route (Signup/Login Page)
@app.route('/')
def index():
    return render_template('index.html')

# Route to Sign Up (Store User in Firestore with null location)
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']

    # Store user data in Firestore (Location is NULL initially)
    user_data = {
        "username": username,
        "password": password,  # Ideally, store hashed passwords (use bcrypt)
        "location": None  # Location is NULL
    }

    db.collection("users").document(username).set(user_data)
    
    return "User Registered Successfully!"

# Route to Login (Verify User)
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user_ref = db.collection("users").document(username).get()

    if user_ref.exists:
        user_data = user_ref.to_dict()
        if user_data["password"] == password:
            session['user'] = username  # Store session
            return render_template('dashboard.html', username=username, location=user_data["location"])
        else:
            return "Invalid Password"
    else:
        return "User Not Found"

@app.route('/update_location', methods=['POST'])
def update_location():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    username = session['user']
    data = request.json
    lat = data.get("latitude")
    lon = data.get("longitude")

    if lat and lon:
        location_data = {"latitude": lat, "longitude": lon}
        db.collection("users").document(username).update({"location": location_data})
        return jsonify({"message": "Location updated successfully!", "location": location_data})
    else:
        return jsonify({"error": "Invalid location data"}), 400
    
@app.route('/add_guardian', methods=['POST'])
def add_guardian():
    if 'user' not in session:  # ✅ Check if user is logged in
        return "Session expired. Please log in again.", 401

    user_email = session['user']  # ✅ Use the correct session key
    guardian_email = request.form['guardian_email']
    guardian_password = request.form['guardian_password']

    # Store guardian details and link them to the user
    db.collection('guardians').document(guardian_email).set({
        'email': guardian_email,
        'password': guardian_password,
        'user': user_email  # ✅ Link guardian to user
    })

    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return "Session expired. Please log in again.", 401

    username = session['user']
    
    # Fetch user details
    user_ref = db.collection("users").document(username).get()
    if not user_ref.exists:
        return "User data not found!", 404

    user_data = user_ref.to_dict()
    return render_template('dashboard.html', username=username, location=user_data.get("location", {}))


@app.route('/guardian_login', methods=['POST'])
def guardian_login():
    if request.method == 'POST':
        if 'email' not in request.form or 'password' not in request.form:
            return "Missing email or password", 400  # Early error handling

        guardian_email = request.form['email']  # ✅ Ensure correct name
        guardian_password = request.form['password']

        guardian_ref = db.collection("guardians").document(guardian_email).get()

        if guardian_ref.exists:
            guardian_data = guardian_ref.to_dict()
            if guardian_data["password"] == guardian_password:
                session['guardian'] = guardian_email  

                # Get the linked user
                user_email = guardian_data.get("user")
                print(f"Guardian {guardian_email} is linked to user {user_email}")

                user_ref = db.collection("users").document(user_email).get()

                if user_ref.exists:
                    user_data = user_ref.to_dict()

                    user_location = user_data.get("location", {})
                    user_lat = user_location.get("latitude", 0.0)
                    user_lng = user_location.get("longitude", 0.0)

                    return render_template(
                        'guardian_dashboard.html', 
                        user_name=user_email,  
                        user_lat=user_lat, 
                        user_lng=user_lng
                    )
                else:
                    print(f"Error: User {user_email} not found in Firestore!")
                    return "Assigned user not found.", 404
            else:
                return "Invalid Password", 401
        else:
            return "Guardian Not Found", 404

    return "Invalid Request", 405  # Handle wrong HTTP method



# Logout Route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
