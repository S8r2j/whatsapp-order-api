"""Privacy Policy page — served as HTML directly from the backend."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Pages"])

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Privacy Policy — WhatsApp Order Manager</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #f9fafb;
      color: #111827;
      line-height: 1.7;
    }

    header {
      background: #25D366;
      color: #fff;
      padding: 24px 0;
      text-align: center;
    }
    header h1 { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.5px; }
    header p  { font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }

    main {
      max-width: 760px;
      margin: 48px auto;
      padding: 0 24px 80px;
    }

    .card {
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      padding: 40px 48px;
    }

    .last-updated {
      display: inline-block;
      background: #f0fdf4;
      color: #15803d;
      font-size: 0.8rem;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 99px;
      margin-bottom: 32px;
    }

    h2 {
      font-size: 1.1rem;
      font-weight: 700;
      color: #111827;
      margin: 36px 0 10px;
      padding-bottom: 8px;
      border-bottom: 2px solid #f3f4f6;
    }
    h2:first-of-type { margin-top: 0; }

    p  { font-size: 0.95rem; color: #374151; margin-bottom: 12px; }
    ul { padding-left: 20px; margin-bottom: 12px; }
    li { font-size: 0.95rem; color: #374151; margin-bottom: 6px; }

    a  { color: #25D366; text-decoration: none; }
    a:hover { text-decoration: underline; }

    footer {
      text-align: center;
      font-size: 0.8rem;
      color: #9ca3af;
      margin-top: 48px;
    }
  </style>
</head>
<body>

<header>
  <h1>WhatsApp Order Manager</h1>
  <p>Privacy Policy</p>
</header>

<main>
  <div class="card">
    <span class="last-updated">Last updated: June 2025</span>

    <h2>1. Introduction</h2>
    <p>
      WhatsApp Order Manager ("we", "our", or "us") provides a platform that allows businesses
      ("Shops") to connect their WhatsApp Business Accounts and manage customer conversations
      and orders. This Privacy Policy explains how we collect, use, and protect your information
      when you use our service.
    </p>

    <h2>2. Information We Collect</h2>
    <p>We collect the following categories of information:</p>
    <ul>
      <li><strong>Account information:</strong> Business name, email address, and phone number provided during registration.</li>
      <li><strong>WhatsApp Business data:</strong> Access tokens, phone number IDs, and WhatsApp Business Account identifiers obtained through Meta's OAuth flow with your explicit consent.</li>
      <li><strong>Customer messages:</strong> Inbound and outbound WhatsApp messages processed through your connected business account to facilitate order management and customer service.</li>
      <li><strong>Order data:</strong> Product names, quantities, order status, and transaction notes created from customer interactions.</li>
      <li><strong>Usage data:</strong> Log data, API request metadata, and error reports used to operate and improve the service.</li>
    </ul>

    <h2>3. How We Use Your Information</h2>
    <ul>
      <li>To provide and operate the WhatsApp Order Manager service.</li>
      <li>To route and store WhatsApp messages between your business and your customers.</li>
      <li>To send automated and AI-generated replies on behalf of your business through your connected WhatsApp account.</li>
      <li>To display order and conversation history in your dashboard.</li>
      <li>To send daily order summary notifications to shop owners.</li>
      <li>To diagnose technical issues and improve platform performance.</li>
    </ul>

    <h2>4. WhatsApp and Meta Platform Data</h2>
    <p>
      Our platform integrates with the Meta (WhatsApp Business) API. When you connect your
      WhatsApp Business Account, we receive and store OAuth access tokens to send and receive
      messages on your behalf. These tokens are encrypted at rest using industry-standard
      encryption (AES-256 / Fernet). We do not share your WhatsApp credentials with any
      third party.
    </p>
    <p>
      Customer phone numbers and message content are encrypted in our database and are only
      accessible to the Shop that owns that WhatsApp connection.
    </p>

    <h2>5. Data Sharing</h2>
    <p>We do not sell, rent, or trade your personal information. We may share data only in the following limited circumstances:</p>
    <ul>
      <li><strong>Service providers:</strong> Trusted infrastructure providers (cloud hosting, database) who process data on our behalf under strict confidentiality agreements.</li>
      <li><strong>Legal requirements:</strong> If required by applicable law, court order, or governmental authority.</li>
      <li><strong>Business transfer:</strong> In the event of a merger, acquisition, or sale of assets, with notice provided to affected users.</li>
    </ul>

    <h2>6. Data Retention</h2>
    <p>
      We retain your account and message data for as long as your account is active. If you
      disconnect your WhatsApp account or delete your account, your data will be removed from
      our systems within 30 days, except where retention is required by law.
    </p>

    <h2>7. Security</h2>
    <p>
      We implement industry-standard security measures including encryption at rest for all
      sensitive fields (access tokens, phone numbers, message content), HTTPS for all data
      in transit, and access controls that ensure each shop can only access its own data.
    </p>

    <h2>8. Your Rights</h2>
    <p>You have the right to:</p>
    <ul>
      <li>Access the personal data we hold about you.</li>
      <li>Request correction of inaccurate data.</li>
      <li>Request deletion of your account and associated data.</li>
      <li>Revoke WhatsApp access at any time through the Settings page in our dashboard.</li>
      <li>Object to processing of your data in certain circumstances.</li>
    </ul>

    <h2>9. Cookies</h2>
    <p>
      Our dashboard may use session cookies and local storage solely to maintain your
      authenticated session. We do not use tracking or advertising cookies.
    </p>

    <h2>10. Children's Privacy</h2>
    <p>
      Our service is intended for business use and is not directed to individuals under
      the age of 18. We do not knowingly collect personal information from minors.
    </p>

    <h2>11. Changes to This Policy</h2>
    <p>
      We may update this Privacy Policy from time to time. We will notify registered users
      of material changes via email or an in-app notice. Continued use of the service after
      changes constitutes your acceptance of the updated policy.
    </p>

    <h2>12. Contact Us</h2>
    <p>
      If you have any questions about this Privacy Policy or wish to exercise your rights,
      please contact us at:
      <br /><br />
      <strong>Email:</strong> <a href="mailto:privacy@whatsappordermanager.com">privacy@whatsappordermanager.com</a>
    </p>
  </div>

  <footer>
    &copy; 2025 WhatsApp Order Manager. All rights reserved.
  </footer>
</main>

</body>
</html>"""


@router.get("/privacy-policy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_policy() -> HTMLResponse:
    return HTMLResponse(content=_HTML, status_code=200)
