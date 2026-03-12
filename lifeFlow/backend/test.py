#email otp simulation for backend testing
import smtplib
from email.message import EmailMessage

# 🔥 Hardcoded Gmail credentials (TEST ONLY)
SENDER_EMAIL = "pushnotifications481312@gmail.com"
APP_PASSWORD = "app password"


print("=== BDMS Email OTP Simulation ===")

receiver_email = input("Enter recipient email: ").strip()

# 🔥 Simulate backend OTP
otp = input("Enter OTP (simulate backend generated OTP): ").strip()

# Create email
msg = EmailMessage()
msg["Subject"] = "BDMS Login OTP Verification"
msg["From"] = SENDER_EMAIL
msg["To"] = receiver_email

msg.set_content(f"""
Dear Donor,

You are attempting to log in to the Blood Donation Management System.

Your One-Time Password (OTP) is: {otp}

This OTP is valid for 5 minutes.
Do not share this OTP with anyone.

- BDMS Team
""")

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()

    print("✅ OTP Email sent successfully!")

except Exception as e:
    print("❌ Error:", str(e))
