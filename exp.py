from werkzeug.security import generate_password_hash

# Replace 'YourPasswordHere' with the desired password
hashed_password = generate_password_hash('629744')
print(hashed_password)  # This will output the hashed password
