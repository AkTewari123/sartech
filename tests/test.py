import smtplib
from email.mime.text import MIMEText

sender = "reach.akshattewari@outlook.com"
receiver = "akkubear@gmail.com"
password = "NISHANTISSHORt@2"  # Regular Outlook.com password

msg = MIMEText("Hello from Python via Outlook SMTP!")
msg["Subject"] = "Test Email"
msg["From"] = sender
msg["To"] = receiver

with smtplib.SMTP("smtp.office365.com", 587) as server:
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, [receiver], msg.as_string())
