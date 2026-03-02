"""
Review Module - Admin Routes
================================
Admin management of reviews and comments: list, detail, reply, delete.
"""

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_operator_or_admin
from modules.review.service import review_service
from modules.review.models import CommentSenderType

router = APIRouter(prefix="/admin/reviews", tags=["admin-reviews"])


# ==========================================
# Reviews & Comments List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_review_list(
    request: Request,
    tab: str = Query("comments", regex="^(comments|reviews)$"),
    page: int = Query(1, ge=1),
    search: str = Query(None),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    per_page = 30

    # Get counts for tab badges (per_page=1 to avoid loading all records)
    _, total_comments = review_service.list_comments_admin(db, page=1, per_page=1)
    _, total_reviews = review_service.list_reviews_admin(db, page=1, per_page=1)

    if tab == "comments":
        items, total = review_service.list_comments_admin(db, page=page, per_page=per_page, search=search)
    else:
        items, total = review_service.list_reviews_admin(db, page=page, per_page=per_page, search=search)

    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/list.html", {
        "request": request,
        "user": user,
        "tab": tab,
        "items": items,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "total_comments": total_comments,
        "total_reviews": total_reviews,
        "search_query": search or "",
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Comment Detail
# ==========================================

@router.get("/comment/{comment_id}", response_class=HTMLResponse)
async def admin_comment_detail(
    request: Request,
    comment_id: int,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    comment = review_service.get_comment(db, comment_id)
    if not comment:
        return RedirectResponse("/admin/reviews?error=نظر+یافت+نشد", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/detail.html", {
        "request": request,
        "user": user,
        "item": comment,
        "item_type": "comment",
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Review Detail
# ==========================================

@router.get("/review/{review_id}", response_class=HTMLResponse)
async def admin_review_detail(
    request: Request,
    review_id: int,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    review = review_service.get_review(db, review_id)
    if not review:
        return RedirectResponse("/admin/reviews?tab=reviews&error=نظر+یافت+نشد", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/detail.html", {
        "request": request,
        "user": user,
        "item": review,
        "item_type": "review",
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Admin Reply to Comment
# ==========================================

@router.post("/comment/{comment_id}/reply")
async def admin_reply_comment(
    request: Request,
    comment_id: int,
    body: str = Form(...),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    comment = review_service.get_comment(db, comment_id)
    if not comment:
        return RedirectResponse("/admin/reviews?error=نظر+یافت+نشد", status_code=302)

    admin_name = user.full_name or "پشتیبانی"
    result = review_service.add_comment(
        db, product_id=comment.product_id, customer_id=None,
        sender_name=admin_name, body=body,
        sender_type=CommentSenderType.ADMIN,
        parent_id=comment.id,
    )

    if result["success"]:
        # Notify comment author
        if comment.user_id:
            try:
                from modules.notification.service import notification_service
                from modules.notification.models import NotificationType
                notification_service.send(
                    db, comment.user_id,
                    notification_type=NotificationType.REVIEW_REPLY,
                    title="پاسخ به نظر شما",
                    body=f"پشتیبانی به نظر شما پاسخ داد.",
                    link=f"/product/{comment.product_id}",
                    sms_text=f"طلاملا: پشتیبانی به نظر شما پاسخ داد. talamala.com/product/{comment.product_id}",
                    reference_type="comment_reply", reference_id=str(comment_id),
                )
            except Exception:
                pass
        db.commit()
        return RedirectResponse(f"/admin/reviews/comment/{comment_id}?msg=پاسخ+ثبت+شد", status_code=302)

    db.rollback()
    return RedirectResponse(f"/admin/reviews/comment/{comment_id}?error={result['message']}", status_code=302)


# ==========================================
# Admin Reply to Review
# ==========================================

@router.post("/review/{review_id}/reply")
async def admin_reply_review(
    request: Request,
    review_id: int,
    body: str = Form(...),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    result = review_service.admin_reply_review(db, review_id, body)
    if result["success"]:
        # Notify review author
        review = review_service.get_review(db, review_id)
        if review and review.user_id:
            try:
                from modules.notification.service import notification_service
                from modules.notification.models import NotificationType
                notification_service.send(
                    db, review.user_id,
                    notification_type=NotificationType.REVIEW_REPLY,
                    title="پاسخ به نقد شما",
                    body=f"پشتیبانی به نقد شما پاسخ داد.",
                    link=f"/product/{review.product_id}",
                    sms_text=f"طلاملا: پشتیبانی به نقد شما پاسخ داد. talamala.com/product/{review.product_id}",
                    reference_type="review_reply", reference_id=str(review_id),
                )
            except Exception:
                pass
        db.commit()
        return RedirectResponse(f"/admin/reviews/review/{review_id}?msg=پاسخ+ثبت+شد", status_code=302)

    db.rollback()
    return RedirectResponse(f"/admin/reviews/review/{review_id}?error={result['message']}", status_code=302)


# ==========================================
# Delete Comment
# ==========================================

@router.post("/comment/{comment_id}/delete")
async def admin_delete_comment(
    request: Request,
    comment_id: int,
    csrf_token: str = Form(""),
    parent_id: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = review_service.delete_comment(db, comment_id)
    if parent_id and parent_id.isdigit():
        redirect_url = f"/admin/reviews/comment/{parent_id}"
    else:
        redirect_url = "/admin/reviews"
    if result["success"]:
        db.commit()
        return RedirectResponse(redirect_url + "?msg=نظر+حذف+شد", status_code=302)
    db.rollback()
    return RedirectResponse(redirect_url + "?error=" + result["message"], status_code=302)


# ==========================================
# Delete Review
# ==========================================

@router.post("/review/{review_id}/delete")
async def admin_delete_review(
    request: Request,
    review_id: int,
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = review_service.delete_review(db, review_id)
    if result["success"]:
        db.commit()
        return RedirectResponse("/admin/reviews?tab=reviews&msg=نظر+حذف+شد", status_code=302)
    db.rollback()
    return RedirectResponse("/admin/reviews?tab=reviews&error=" + result["message"], status_code=302)
