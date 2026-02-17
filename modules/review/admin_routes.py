"""
Review Module - Admin Routes
================================
Admin management of reviews and comments.
"""

from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.review.service import review_service
from modules.review.models import ProductComment, CommentSenderType

router = APIRouter(prefix="/admin/reviews", tags=["admin-reviews"])


# ==========================================
# List Reviews & Comments
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_review_list(
    request: Request,
    tab: str = Query("reviews"),
    search: str = Query(""),
    page: int = Query(1),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    per_page = 30
    reviews, reviews_total = [], 0
    comments, comments_total = [], 0

    if tab == "comments":
        comments, comments_total = review_service.list_comments_admin(
            db, page=max(1, page), per_page=per_page, search=search or None,
        )
    else:
        reviews, reviews_total = review_service.list_reviews_admin(
            db, page=max(1, page), per_page=per_page, search=search or None,
        )

    total = reviews_total if tab == "reviews" else comments_total
    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/list.html", {
        "request": request,
        "user": user,
        "active_page": "reviews",
        "tab": tab,
        "reviews": reviews,
        "reviews_total": reviews_total,
        "comments": comments,
        "comments_total": comments_total,
        "search": search,
        "page": page,
        "total_pages": total_pages,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Review Detail
# ==========================================

@router.get("/{review_id}", response_class=HTMLResponse)
async def admin_review_detail(
    request: Request,
    review_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    review = review_service.get_review(db, review_id)
    if not review:
        return RedirectResponse("/admin/reviews?error=نظر+یافت+نشد", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/detail.html", {
        "request": request,
        "user": user,
        "active_page": "reviews",
        "review": review,
        "comment": None,
        "view_type": "review",
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Admin Reply to Review
# ==========================================

@router.post("/{review_id}/reply")
async def admin_reply_review(
    request: Request,
    review_id: int,
    reply_text: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    csrf_check(request, csrf_token)
    result = review_service.admin_reply_review(db, review_id, reply_text)
    if result["success"]:
        db.commit()
    return RedirectResponse(f"/admin/reviews/{review_id}", status_code=302)


# ==========================================
# Delete Review
# ==========================================

@router.post("/{review_id}/delete")
async def admin_delete_review(
    request: Request,
    review_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    csrf_check(request, csrf_token)
    result = review_service.delete_review(db, review_id)
    if result["success"]:
        db.commit()
    return RedirectResponse("/admin/reviews", status_code=302)


# ==========================================
# Comment Detail
# ==========================================

@router.get("/comments/{comment_id}", response_class=HTMLResponse)
async def admin_comment_detail(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    comment = review_service.get_comment(db, comment_id)
    if not comment:
        return RedirectResponse("/admin/reviews?tab=comments&error=نظر+یافت+نشد", status_code=302)

    # Load replies
    replies = (
        db.query(ProductComment)
        .options(joinedload(ProductComment.customer), joinedload(ProductComment.images))
        .filter(ProductComment.parent_id == comment_id)
        .order_by(ProductComment.created_at.asc())
        .all()
    )

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/detail.html", {
        "request": request,
        "user": user,
        "active_page": "reviews",
        "review": None,
        "comment": comment,
        "replies": replies,
        "view_type": "comment",
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Admin Reply to Comment (as admin comment)
# ==========================================

@router.post("/comments/{comment_id}/reply")
async def admin_reply_comment(
    request: Request,
    comment_id: int,
    reply_text: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    csrf_check(request, csrf_token)

    comment = review_service.get_comment(db, comment_id)
    if not comment:
        return RedirectResponse("/admin/reviews?tab=comments", status_code=302)

    result = review_service.add_comment(
        db,
        product_id=comment.product_id,
        customer_id=None,
        sender_name=user.username or "پشتیبانی",
        body=reply_text,
        sender_type=CommentSenderType.ADMIN,
        parent_id=comment_id,
    )
    if result["success"]:
        db.commit()
    return RedirectResponse(f"/admin/reviews/comments/{comment_id}", status_code=302)


# ==========================================
# Delete Comment
# ==========================================

@router.post("/comments/{comment_id}/delete")
async def admin_delete_comment(
    request: Request,
    comment_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reviews")),
):
    csrf_check(request, csrf_token)
    result = review_service.delete_comment(db, comment_id)
    if result["success"]:
        db.commit()
    return RedirectResponse("/admin/reviews?tab=comments", status_code=302)
