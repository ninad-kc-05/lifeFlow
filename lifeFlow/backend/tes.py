#mobile otp simulation for backend testing
import requests

print("=== SMS Gateway Configuration ===")

# 🔥 User enters full URL
raw_url = input("Enter Gateway URL (example http://10.142.117.231:8082/): ").strip()

# Remove http:// or https:// if present
clean_url = raw_url.replace("http://", "").replace("https://", "").rstrip("/")

# Rebuild properly
gateway_url = f"http://{clean_url}/"

token = input("Enter Gateway Token (from phone local): ").strip()

print("\n=== OTP Simulation (Backend Mode) ===")

to_number = input("Enter recipient number (+91...): ").strip()

# Simulate backend-generated OTP
otp = input("Enter OTP (simulate backend generated OTP): ").strip()

# OTP Message Template
message = f"""Dear Donor,

You are attempting to log in to the Blood Donation Management System.
Your One-Time \nPassword (OTP) is: {otp}.
This OTP is valid for 5 minutes.Please do not share this code with anyone.

- BDMS Team"""

headers = {
    "Authorization": token
}

payload = {
    "to": to_number,
    "message": message
}

print("\nSending OTP to:", to_number)
print("Using Gateway:", gateway_url)

try:
    response = requests.post(
        gateway_url,
        json=payload,
        headers=headers,
        timeout=10
    )

    print("Status Code:", response.status_code)
    print("Response Body:", response.text)

    if response.status_code == 200:
        print("✅ OTP sent successfully.")
    else:
        print("❌ Failed to send OTP.")

except Exception as e:
    print("⚠ Error:", str(e))