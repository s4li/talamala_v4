#!/usr/bin/env python3
"""
Test Script: Send all 16 notification types to a specific user.
Usage: python scripts/test_notifications.py [mobile]
Default mobile: 09123456789 (Super Admin)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal

# Import ALL models (required for SQLAlchemy relationship resolution — same as main.py)
from modules.user.models import User  # noqa
from modules.admin.models import SystemSetting, RequestLog  # noqa
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress  # noqa
from modules.catalog.models import Product, ProductCategory, ProductCategoryLink, ProductImage, CardDesign, PackageType, Batch  # noqa
from modules.inventory.models import Bar, BarImage, OwnershipHistory, DealerTransfer, ReconciliationSession, ReconciliationItem, CustodialDeliveryRequest  # noqa
from modules.cart.models import Cart, CartItem  # noqa
from modules.order.models import Order, OrderItem, OrderStatusLog  # noqa
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest  # noqa
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory  # noqa
from modules.dealer.models import DealerTier, DealerSale, BuybackRequest, SubDealerRelation, B2BOrder, B2BOrderItem  # noqa
from modules.ticket.models import Ticket, TicketMessage, TicketAttachment  # noqa
from modules.review.models import Review, ReviewImage, ProductComment, CommentImage, CommentLike  # noqa
from modules.dealer_request.models import DealerRequest, DealerRequestAttachment  # noqa
from modules.pricing.models import Asset  # noqa
from modules.rasis.models import RasisReceipt  # noqa
from modules.notification.models import Notification, NotificationPreference, NotificationType, NOTIFICATION_TYPE_LABELS  # noqa
from modules.notification.service import notification_service


def main():
    mobile = sys.argv[1] if len(sys.argv) > 1 else "09123456789"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.mobile == mobile).first()
        if not user:
            print(f"[ERROR] User with mobile {mobile} not found!")
            return

        print(f"\n{'='*60}")
        print(f"  Sending all 16 notification types to: {user.full_name} ({mobile})")
        print(f"  User ID: {user.id}")
        print(f"{'='*60}\n")

        test_cases = [
            {
                "type": NotificationType.ORDER_STATUS,
                "title": "تست: وضعیت سفارش",
                "body": "سفارش #999 لغو شد.",
                "link": "/orders",
                "sms_text": "طلاملا [تست]: سفارش #999 لغو شد.",
                "ref_type": "test_order_status",
            },
            {
                "type": NotificationType.ORDER_DELIVERY,
                "title": "تست: ارسال سفارش",
                "body": "سفارش #999 ارسال شد — کد رهگیری: 123456",
                "link": "/orders",
                "sms_text": "طلاملا [تست]: سفارش #999 ارسال شد. کد رهگیری: 123456",
                "ref_type": "test_order_delivery",
            },
            {
                "type": NotificationType.PAYMENT_SUCCESS,
                "title": "تست: پرداخت موفق",
                "body": "سفارش #999 با موفقیت پرداخت شد.",
                "link": "/orders",
                "sms_text": "طلاملا [تست]: سفارش #999 پرداخت شد.",
                "ref_type": "test_payment_success",
            },
            {
                "type": NotificationType.PAYMENT_FAILED,
                "title": "تست: پرداخت ناموفق",
                "body": "پرداخت سفارش #999 ناموفق بود.",
                "link": "/orders",
                "sms_text": None,  # in-app only
                "ref_type": "test_payment_failed",
            },
            {
                "type": NotificationType.WALLET_TOPUP,
                "title": "تست: شارژ کیف پول",
                "body": "کیف پول شما 500,000 تومان شارژ شد.",
                "link": "/wallet",
                "sms_text": "طلاملا [تست]: شارژ کیف پول 500,000 تومان انجام شد.",
                "ref_type": "test_wallet_topup",
            },
            {
                "type": NotificationType.WALLET_WITHDRAW,
                "title": "تست: درخواست برداشت تأیید شد",
                "body": "درخواست برداشت 1,000,000 تومان تأیید شد.",
                "link": "/wallet/withdraw",
                "sms_text": "طلاملا [تست]: درخواست برداشت 1,000,000 تومان تأیید شد.",
                "ref_type": "test_wallet_withdraw",
            },
            {
                "type": NotificationType.WALLET_TRADE,
                "title": "تست: خرید طلا",
                "body": "خرید 0.500 گرم طلا انجام شد.",
                "link": "/wallet/gold",
                "sms_text": "طلاملا [تست]: خرید 0.500 گرم طلا انجام شد.",
                "ref_type": "test_wallet_trade",
            },
            {
                "type": NotificationType.OWNERSHIP_TRANSFER,
                "title": "تست: انتقال مالکیت",
                "body": "شمش SERIAL001 با موفقیت منتقل شد.",
                "link": "/my-bars",
                "sms_text": "طلاملا [تست]: شمش SERIAL001 با موفقیت منتقل شد.",
                "ref_type": "test_ownership_transfer",
            },
            {
                "type": NotificationType.CUSTODIAL_DELIVERY,
                "title": "تست: تحویل امانی",
                "body": "شمش امانی شما با موفقیت تحویل داده شد.",
                "link": "/my-bars",
                "sms_text": "طلاملا [تست]: شمش امانی شما تحویل داده شد.",
                "ref_type": "test_custodial_delivery",
            },
            {
                "type": NotificationType.TICKET_UPDATE,
                "title": "تست: پاسخ تیکت",
                "body": "پشتیبانی به تیکت «تست» پاسخ داد.",
                "link": "/tickets",
                "sms_text": "طلاملا [تست]: پاسخ جدید تیکت #99",
                "ref_type": "test_ticket_update",
            },
            {
                "type": NotificationType.DEALER_SALE,
                "title": "تست: فروش POS",
                "body": "فروش شمش به مشتری تست با مبلغ 50,000,000 تومان ثبت شد.",
                "link": "/dealer/sales",
                "sms_text": "طلاملا [تست]: فروش POS به مبلغ 50,000,000 تومان ثبت شد.",
                "ref_type": "test_dealer_sale",
            },
            {
                "type": NotificationType.DEALER_BUYBACK,
                "title": "تست: بازخرید",
                "body": "بازخرید شمش SERIAL001 به مبلغ 48,000,000 تومان ثبت شد.",
                "link": "/dealer/buybacks",
                "sms_text": "طلاملا [تست]: بازخرید شمش SERIAL001 ثبت شد.",
                "ref_type": "test_dealer_buyback",
            },
            {
                "type": NotificationType.B2B_ORDER,
                "title": "تست: سفارش عمده تأیید شد",
                "body": "سفارش عمده #99 توسط مدیریت تأیید شد.",
                "link": "/dealer/b2b-orders",
                "sms_text": "طلاملا [تست]: سفارش عمده #99 تأیید شد.",
                "ref_type": "test_b2b_order",
            },
            {
                "type": NotificationType.DEALER_REQUEST,
                "title": "تست: درخواست نمایندگی",
                "body": "درخواست نمایندگی شما تأیید شد.",
                "link": "/dealer/dashboard",
                "sms_text": "طلاملا [تست]: درخواست نمایندگی شما تأیید شد!",
                "ref_type": "test_dealer_request",
            },
            {
                "type": NotificationType.REVIEW_REPLY,
                "title": "تست: پاسخ به نقد",
                "body": "پشتیبانی به نقد شما پاسخ داد.",
                "link": "/",
                "sms_text": "طلاملا [تست]: پشتیبانی به نقد شما پاسخ داد.",
                "ref_type": "test_review_reply",
            },
            {
                "type": NotificationType.SYSTEM,
                "title": "تست: پیام سیستمی",
                "body": "این یک پیام تست سیستمی است.",
                "link": None,
                "sms_text": "طلاملا [تست]: این یک پیام تست سیستمی است.",
                "ref_type": "test_system",
            },
        ]

        sent = 0
        for i, tc in enumerate(test_cases, 1):
            label = NOTIFICATION_TYPE_LABELS.get(tc["type"], tc["type"].value)
            print(f"[{i:2d}/16] {tc['type'].value:25s} ({label})", end=" ... ")

            try:
                notif = notification_service.send(
                    db, user.id,
                    notification_type=tc["type"],
                    title=tc["title"],
                    body=tc["body"],
                    link=tc["link"],
                    sms_text=tc["sms_text"],
                    reference_type=tc["ref_type"],
                    reference_id="test",
                )
                db.commit()
                status = "IN_APP" + (" + SMS" if tc["sms_text"] else "")
                print(f"OK ({status})")
                sent += 1
            except Exception as e:
                db.rollback()
                print(f"FAILED: {e}")

        print(f"\n{'='*60}")
        print(f"  Result: {sent}/16 notifications sent successfully")
        print(f"  Check console output above for SMS debug messages")
        print(f"  Check DB: SELECT * FROM notifications WHERE user_id={user.id} ORDER BY id DESC LIMIT 16;")
        print(f"{'='*60}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
