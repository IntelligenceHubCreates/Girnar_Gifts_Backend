# app/orders/email.py
"""
Order confirmation email via Resend.

Setup:
1. pip install resend   (already in requirements.txt)
2. Add to .env:  RESEND_API_KEY=re_xxxxxxxxxxxx
3. Add to .env:  ORDER_FROM_EMAIL=orders@girnargifts.com   (falls back to NEWSLETTER_FROM_EMAIL, then brand_support_email)
"""
from __future__ import annotations

import os
import logging

import resend

from app.settings import settings

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv(
    "ORDER_FROM_EMAIL",
    os.getenv("NEWSLETTER_FROM_EMAIL", settings.brand_support_email),
)
FROM_NAME = settings.brand_name
STORE_URL = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "https://girnargifts.com")


def send_order_confirmation_email(
    to_email: str,
    order_number: str,
    items: list[dict],
    subtotal: float,
    discount_amount: float,
    delivery_fee: float,
    total_amount: float,
    shipping_address: str,
    gift_message: str | None = None,
) -> None:
    """Fire-and-forget order confirmation email. Errors are logged, never raised."""
    if not resend.api_key:
        log.warning("[orders] RESEND_API_KEY not set — skipping order confirmation email")
        return
    try:
        resend.Emails.send({
            "from":    f"{FROM_NAME} <{FROM_EMAIL}>",
            "to":      [to_email],
            "subject": f"Your {FROM_NAME} order #{order_number} is confirmed! 🎁",
            "html":    _order_confirmation_html(
                order_number, items, subtotal, discount_amount,
                delivery_fee, total_amount, shipping_address, gift_message,
            ),
        })
        log.info("[orders] Order confirmation email sent to %s for order #%s", to_email, order_number)
    except Exception as exc:
        log.error("[orders] Failed to send order confirmation email to %s: %s", to_email, exc)


def _money(v: float) -> str:
    return f"₹{v:,.2f}"


def _item_rows_html(items: list[dict]) -> str:
    rows = []
    for it in items:
        name = it.get("name") or "Item"
        qty = it.get("quantity", 1)
        price = float(it.get("price", 0))
        line_total = price * qty
        image = it.get("image") or ""
        color = it.get("color")
        img_cell = (
            f'<img src="{image}" width="56" height="56" alt="" '
            f'style="border-radius:10px;object-fit:cover;display:block;">'
            if image else
            '<div style="width:56px;height:56px;border-radius:10px;background:#FFF7ED;"></div>'
        )
        color_line = (
            f'<div style="font-size:12px;color:#999;margin-top:2px;">Color: {color}</div>'
            if color else ""
        )
        rows.append(f"""
                <tr>
                  <td style="padding:12px 0;border-bottom:1px solid #f0f0f0;width:56px;">{img_cell}</td>
                  <td style="padding:12px 0 12px 14px;border-bottom:1px solid #f0f0f0;">
                    <div style="font-size:14px;color:#1a1a1a;font-weight:700;">{name}</div>
                    <div style="font-size:13px;color:#666;margin-top:2px;">Qty: {qty}</div>
                    {color_line}
                  </td>
                  <td style="padding:12px 0;border-bottom:1px solid #f0f0f0;text-align:right;
                             font-size:14px;color:#1a1a1a;font-weight:700;white-space:nowrap;">
                    {_money(line_total)}
                  </td>
                </tr>""")
    return "".join(rows)


def _summary_row(label: str, value: str, bold: bool = False, color: str = "#444") -> str:
    weight = "800" if bold else "600"
    size = "16px" if bold else "14px"
    return f"""
                <tr>
                  <td style="padding:4px 0;font-size:{size};color:{color};font-weight:{weight};">{label}</td>
                  <td style="padding:4px 0;font-size:{size};color:{color};font-weight:{weight};text-align:right;">{value}</td>
                </tr>"""


def _order_confirmation_html(
    order_number: str,
    items: list[dict],
    subtotal: float,
    discount_amount: float,
    delivery_fee: float,
    total_amount: float,
    shipping_address: str,
    gift_message: str | None,
) -> str:
    order_url = f"{STORE_URL}/account?tab=orders"
    summary_rows = _summary_row("Subtotal", _money(subtotal))
    if discount_amount:
        summary_rows += _summary_row("Discount", f"-{_money(discount_amount)}", color="#16A34A")
    summary_rows += _summary_row(
        "Delivery", "FREE" if not delivery_fee else _money(delivery_fee)
    )
    summary_rows += _summary_row("Total", _money(total_amount), bold=True)

    gift_block = ""
    if gift_message:
        gift_block = f"""
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#FFF7ED;border-radius:14px;padding:16px 20px;margin:0 0 24px;">
                <tr><td>
                  <div style="font-size:12px;font-weight:800;color:#F97316;text-transform:uppercase;
                              letter-spacing:0.5px;margin-bottom:6px;">Gift Message</div>
                  <div style="font-size:14px;color:#444;line-height:1.5;font-style:italic;">"{gift_message}"</div>
                </td></tr>
              </table>"""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Order Confirmed — {FROM_NAME}</title>
</head>
<body style="margin:0;padding:0;background:#f9f9f9;font-family:'Nunito',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9f9f9;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:20px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.07);max-width:560px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:#FEEAE4;padding:36px 40px;text-align:center;">
              <div style="font-size:48px;margin-bottom:8px;">🎉</div>
              <h1 style="margin:0;font-size:24px;font-weight:800;color:#1a1a1a;
                         font-family:'Nunito',Arial,sans-serif;">
                Your order is confirmed!
              </h1>
              <p style="margin:8px 0 0;font-size:14px;color:#666;">Order #{order_number}</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px;">
              <p style="margin:0 0 24px;font-size:16px;color:#444;line-height:1.6;">
                Thank you for shopping with <strong>{FROM_NAME}</strong>! We've received your order
                and it's being prepared. You'll get another email as soon as it ships.
              </p>

              {gift_block}

              <!-- Items -->
              <table width="100%" cellpadding="0" cellspacing="0">
                {_item_rows_html(items)}
              </table>

              <!-- Summary -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
                {summary_rows}
              </table>

              <!-- Shipping address -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#FFF7ED;border-radius:14px;padding:16px 20px;margin:28px 0;">
                <tr><td>
                  <div style="font-size:12px;font-weight:800;color:#F97316;text-transform:uppercase;
                              letter-spacing:0.5px;margin-bottom:6px;">Shipping To</div>
                  <div style="font-size:14px;color:#444;line-height:1.5;">{shipping_address}</div>
                </td></tr>
              </table>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center">
                    <a href="{order_url}"
                       style="display:inline-block;background:#F97316;color:#fff;
                              text-decoration:none;padding:14px 36px;border-radius:50px;
                              font-size:15px;font-weight:800;letter-spacing:0.3px;">
                      Track Your Order →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9f9f9;padding:24px 40px;text-align:center;
                       border-top:1px solid #eee;">
              <p style="margin:0;font-size:13px;color:#999;">
                Questions about your order? Contact us at
                <a href="mailto:{settings.brand_support_email}" style="color:#F97316;">{settings.brand_support_email}</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
