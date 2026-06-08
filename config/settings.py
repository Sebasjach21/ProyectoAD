import os

# -------------------------------------------------------------------
# Core environment configuration (Render / local)
# -------------------------------------------------------------------
# Database connection string – will fall back to the Supabase URL you provided
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.aifsfrslffnzfufodqwx:47OLPjn1vxbkbL6k@aws-1-us-west-2.pooler.supabase.com:5432/postgres"
)

# Twilio (WhatsApp) configuration
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

# Mailtrap / SMTP configuration (used for email invoices)
SMTP_SERVER = os.getenv("SMTP_SERVER", "sandbox.smtp.mailtrap.io").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525").strip())
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
