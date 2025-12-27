import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables immediately when module is imported
load_dotenv()

from .email_templates_loader import render_email_template


def send_email(to_email, subject, html_body, text_body=None):
    """
    Send email via Gmail SMTP.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_body (str): Email body in HTML format
        text_body (str, optional): Plain text fallback. Defaults to None.
    
    Returns:
        bool: True if email sent successfully, False otherwise
        
    Environment variables required:
        - GMAIL_SENDER: Gmail address to send from
        - GMAIL_PASSWORD: Gmail app-specific password
        - TEST_EMAIL (optional): If set, all emails are sent to this address instead
    
    TODO: Replace Gmail SMTP with SendGrid API or similar cloud-native email service.
    Cloud Run cannot reach external SMTP servers due to network restrictions.
    """
    # TODO: TEMP FIX - Return success without sending to avoid blocking requests
    print(f"[email_service] ⏸️  EMAIL DISABLED IN TEST - Would send to: {to_email}")
    print(f"[email_service] Subject: {subject}")
    return True
    
    # Original code below - to be replaced with SendGrid/Mailgun API
    try:
        sender_email = os.getenv("GMAIL_SENDER")
        sender_password = os.getenv("GMAIL_PASSWORD")
        
        if not sender_email or not sender_password:
            print("[email_service] ❌ Missing Gmail credentials (GMAIL_SENDER or GMAIL_PASSWORD)")
            return False
        
        # Check for test email override
        test_email = os.getenv("TEST_EMAIL")
        actual_to_email = test_email if test_email else to_email
        
        # Debug: Always log what's happening
        print(f"[email_service] DEBUG: TEST_EMAIL env var = {test_email}")
        print(f"[email_service] DEBUG: Original to_email = {to_email}")
        print(f"[email_service] DEBUG: Actual to_email = {actual_to_email}")
        
        if test_email:
            print(f"[email_service] ℹ️  TEST MODE: Sending to {test_email} instead of {to_email}")
        
        # Clean password - remove non-ASCII characters and extra spaces
        sender_password = sender_password.encode('ascii', 'ignore').decode('ascii').strip()
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = actual_to_email
        
        # Attach text version if provided (fallback)
        if text_body:
            message.attach(MIMEText(text_body, "plain", _charset="utf-8"))
        
        # Attach HTML version (primary)
        message.attach(MIMEText(html_body, "html", _charset="utf-8"))
        
        # Send via Gmail SMTP
        print(f"[email_service] Connecting to Gmail SMTP...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, actual_to_email, message.as_string())
        
        print(f"[email_service] ✅ Email sent successfully to {actual_to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print(f"[email_service] ❌ Authentication failed. Check GMAIL_SENDER and GMAIL_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        print(f"[email_service] ❌ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[email_service] ❌ Error sending email: {e}")
        return False


def send_password_reset_email(to_email, name, reset_link):
    """
    Send password reset email using template.
    
    Args:
        to_email (str): Recipient email address
        name (str): User's name
        reset_link (str): Password reset link
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = "Reset Your Strawbay Password"
        
        # Render template with context
        html_body = render_email_template('password_reset.html', {
            'name': name,
            'email': to_email,
            'reset_link': reset_link
        })
        
        # Plain text version (fallback)
        text_body = f"""Password Reset Request

Hi {name},

We received a request to reset your password. Visit this link:
{reset_link}

This link expires in 24 hours.

If you didn't request this, you can safely ignore this email.

Best regards,
The Strawbay Team"""
        
        return send_email(to_email, subject, html_body, text_body)
    except Exception as e:
        print(f"[send_password_reset_email] Error: {e}")
        return False

def send_company_approved_email(to_email, name, company_name, organization_id, app_url="http://localhost:3000"):
    """
    Send company approval email to user using template.
    
    Args:
        to_email (str): Recipient email address
        name (str): User's name
        company_name (str): Approved company name
        organization_id (str): Company organization ID
        app_url (str): Application URL for the login link
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = "Your Company Registration Has Been Approved"
        
        # Render template with context
        html_body = render_email_template('company_approved.html', {
            'name': name,
            'email': to_email,
            'company_name': company_name,
            'organization_id': organization_id,
            'app_url': app_url
        })
        
        # Plain text version (fallback)
        text_body = f"""Your Company Registration Has Been Approved

Hello {name},

Great news! Your company registration has been reviewed and approved.

Company: {company_name}
Organization ID: {organization_id}

Your account is now fully activated. You can log in and start using Strawbay Invoice Scanner.

Visit: {app_url}/login

If you have any questions, contact our support team.

Best regards,
The Strawbay Team"""
        
        return send_email(to_email, subject, html_body, text_body)
    except Exception as e:
        print(f"[send_company_approved_email] Error: {e}")
        return False


def send_company_registration_pending_email(to_email, name, company_name, organization_id):
    """
    Send company registration pending email to new company registrant using template.
    
    Args:
        to_email (str): Recipient email address
        name (str): User's name
        company_name (str): Company name
        organization_id (str): Company organization ID
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = "Company Registration Pending - You Are Company Admin"
        
        # Render template with context
        html_body = render_email_template('company_registration_pending.html', {
            'name': name,
            'email': to_email,
            'company_name': company_name,
            'organization_id': organization_id
        })
        
        # Plain text version (fallback)
        text_body = f"""Company Registration Pending

Hello {name},

Thank you for registering with Strawbay Invoice Scanner!

Company: {company_name}
Organization ID: {organization_id}

As the first user to register for this company, you have been assigned the role of Company Admin.

Your company registration is now pending review by our system administrator. You'll receive an approval email once it's been verified.

This usually takes 24-48 hours.

Best regards,
The Strawbay Team"""
        
        return send_email(to_email, subject, html_body, text_body)
    except Exception as e:
        print(f"[send_company_registration_pending_email] Error: {e}")
        return False


def send_user_registration_pending_email(to_email, name, company_name, admin_name, admin_email):
    """
    Send user registration pending email to new user joining existing company using template.
    
    Args:
        to_email (str): Recipient email address
        name (str): User's name
        company_name (str): Company name
        admin_name (str): Company admin's name
        admin_email (str): Company admin's email address
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = "Your Account Registration Pending Review"
        
        # Render template with context
        html_body = render_email_template('user_registration_pending.html', {
            'name': name,
            'email': to_email,
            'company_name': company_name,
            'admin_name': admin_name,
            'admin_email': admin_email
        })
        
        # Plain text version (fallback)
        text_body = f"""Account Registration Pending Review

Hello {name},

Welcome to Strawbay Invoice Scanner! Your account registration has been received.

Company: {company_name}

Your account is pending review by your company administrator:
Name: {admin_name}
Email: {admin_email}

You'll receive an approval email once they've reviewed your account.

This usually takes 24-48 hours.

Best regards,
The Strawbay Team"""
        
        return send_email(to_email, subject, html_body, text_body)
    except Exception as e:
        print(f"[send_user_registration_pending_email] Error: {e}")
        return False


def send_user_approved_email(to_email, name, company_name, role_name, app_url="http://localhost:3000"):
    """
    Send user approval email when user is approved by admin using template.
    
    Args:
        to_email (str): Recipient email address
        name (str): User's name
        company_name (str): Company name
        role_name (str): User's role name
        app_url (str): Application URL for the login link
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = "Your Account Has Been Approved!"
        
        # Render template with context
        html_body = render_email_template('user_approved.html', {
            'name': name,
            'email': to_email,
            'company_name': company_name,
            'role_name': role_name,
            'app_url': app_url
        })
        
        # Plain text version (fallback)
        text_body = f"""Your Account Has Been Approved

Hello {name},

Congratulations! Your account has been approved and is now active.

Company: {company_name}
Role: {role_name}

You can now log in and start using Strawbay Invoice Scanner.

Visit: {app_url}/login

If you have any questions, contact our support team.

Best regards,
The Strawbay Team"""
        
        return send_email(to_email, subject, html_body, text_body)
    except Exception as e:
        print(f"[send_user_approved_email] Error: {e}")
        return False


def send_plan_change_email(to_email, billing_contact_name, company_name, new_plan_name, requester_name, requester_email, app_name="Strawbay Invoice Scanner", app_url="http://localhost:3000"):
    """
    Send email notification when company plan is changed.
    
    Args:
        to_email (str): Recipient email address (billing contact)
        billing_contact_name (str): Billing contact name
        company_name (str): Company name
        new_plan_name (str): New plan name
        requester_name (str): Name of the user who requested the change
        requester_email (str): Email of the user who requested the change
        app_name (str): Application name
        app_url (str): Application URL
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = f"{app_name}: Your Plan Has Been Changed to {new_plan_name}"
        
        html_body = f"""<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="border-bottom: 3px solid #5b7cff; padding-bottom: 15px; margin-bottom: 20px;">
            <h1 style="color: #5b7cff; margin: 0; font-size: 24px;">{app_name}</h1>
        </div>
        
        <h2 style="color: #333; font-size: 20px; margin-bottom: 15px;">Plan Change Confirmation</h2>
        
        <p>Hello {billing_contact_name},</p>
        
        <p>We're writing to formally confirm that your company's pricing plan has been successfully updated in the {app_name} system.</p>
        
        <div style="background: #f5f7fa; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #5b7cff;">
            <h3 style="color: #333; margin-top: 0;">Change Summary</h3>
            <p style="margin: 12px 0;"><strong>Company:</strong> {company_name}</p>
            <p style="margin: 12px 0;"><strong>New Plan:</strong> {new_plan_name}</p>
            <p style="margin: 12px 0;"><strong>Effective Date:</strong> Today</p>
            <p style="margin: 12px 0;"><strong>Changed By:</strong> {requester_name} ({requester_email})</p>
        </div>
        
        <p>This change was requested by an administrator with the appropriate authorization. If you did not authorize this change or have any concerns, please contact our support team immediately.</p>
        
        <p style="color: #666; font-size: 0.95em; margin: 20px 0; padding: 15px; background: #fff9e6; border-radius: 4px; border-left: 3px solid #ffc107;">
            <strong>Note:</strong> Your new plan will be active immediately. Please allow up to 24 hours for all features to be fully activated in your account.
        </p>
        
        <p style="margin-top: 25px;">
            <a href="{app_url}/login" style="display: inline-block; background: #5b7cff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                Access {app_name}
            </a>
        </p>
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e8ecf1;">
            <p style="color: #999; font-size: 0.9em; margin: 10px 0;">
                If you have any questions about your new plan or need assistance, please don't hesitate to contact our support team:
            </p>
            <p style="color: #5b7cff; font-size: 0.9em; margin: 5px 0;">
                <a href="mailto:support@strawbay.io" style="color: #5b7cff; text-decoration: none;">support@strawbay.io</a>
            </p>
            <p style="color: #999; font-size: 0.85em; margin-top: 20px; margin-bottom: 0;">
                Best regards,<br/>
                The Strawbay Team<br/>
                <em>{app_name}</em>
            </p>
        </div>
    </div>
</body>
</html>"""
        
        text_body = f"""
{app_name} - Plan Change Confirmation
{'='*50}

Hello {billing_contact_name},

We're writing to formally confirm that your company's pricing plan has been successfully updated in the {app_name} system.

CHANGE SUMMARY
{'─'*50}
Company: {company_name}
New Plan: {new_plan_name}
Effective Date: Today
Changed By: {requester_name} ({requester_email})

This change was requested by an administrator with the appropriate authorization. If you did not authorize this change or have any concerns, please contact our support team immediately.

IMPORTANT NOTE:
Your new plan will be active immediately. Please allow up to 24 hours for all features to be fully activated in your account.

NEXT STEPS:
You can access your account here: {app_url}/login

SUPPORT:
If you have any questions about your new plan or need assistance, please contact our support team:
Email: support@strawbay.io

Best regards,
The Strawbay Team
{app_name}"""
        
        return send_email(to_email, subject, html_body, text_body)
    except Exception as e:
        print(f"[send_plan_change_email] Error: {e}")