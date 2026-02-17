"""
Review Module - Admin Routes
================================
Manage reviews and comments from admin panel.
"""

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
# List (tabs: reviews / comments)
# ==========================================

@router.get("", response_class=HTMLResponse)
async def review_list(
    request: Request,
    tab: str = Query("reviews"),
    page: int = Query(1),
    search: str = Query(""),
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
):
    per_page = 30
    reviews, comments = [], []
    total = 0

    if tab == "comments":
        comments, total = review_service.list_comments_admin(db, page=page, per_page=per_page, search=search)
    else:
        reviews, total = review_service.list_reviews_admin(db, page=page, per_page=per_page, search=search)

    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse("admin/reviews/list.html", {
        "request": request, "user": user, "active_page": "reviews",
        "tab": tab, "reviews": reviews, "comments": comments,
        "page": page, "total_pages": total_pages, "search": search,
    })


# ==========================================
# Review Detail
# ==========================================

@router.get("/{review_id}", response_class=HTMLResponse)
async def review_detail(
    request: Request,
    review_id: int,
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
):
    review = review_service.get_review(db, review_id)
    if not review:
        return RedirectResponse("/admin/reviews", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/reviews/detail.html", {
        "request": request, "user": user, "active_page": "reviews",
        "view_type": "review", "review": review, "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Reply to Review
# ==========================================

@router.post("/{review_id}/reply")
async def reply_review(
    request: Request,
    review_id: int,
    reply_text: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
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
async def delete_review(
    request: Request,
    review_id: int,
    csrf_token: str = Form(""),
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
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
async def comment_detail(
    request: Request,
    comment_id: int,
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
):
    comment = review_service.get_comment(db, comment_id)
    if not comment:
        return RedirectResponse("/admin/reviews?tab=comments", status_code=302)

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
        "request": request, "user": user, "active_page": "reviews",
        "view_type": "comment", "comment": comment, "replies": replies,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Admin Reply to Comment
# ==========================================

@router.post("/comments/{comment_id}/reply")
async def reply_comment(
    request: Request,
    comment_id: int,
    reply_text: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    comment = review_service.get_comment(db, comment_id)
    if not comment:
        return RedirectResponse("/admin/reviews?tab=comments", status_code=302)

    result = review_service.add_comment(
        db, product_id=comment.product_id, customer_id=None,
        sender_name=user.username or "مدیریت",
        body=reply_text, sender_type=CommentSenderType.ADMIN,
        parent_id=comment_id,
    )
    if result["success"]:
        db.commit()
    return RedirectResponse(f"/admin/reviews/comments/{comment_id}", status_code=302)


# ==========================================
# Delete Comment
# ==========================================

@router.post("/comments/{comment_id}/delete")
async def delete_comment(
    request: Request,
    comment_id: int,
    csrf_token: str = Form(""),
    user=Depends(require_permission("reviews")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = review_service.delete_comment(db, comment_id)
    if result["success"]:
        db.commit()
    return RedirectResponse("/admin/reviews?tab=comments", status_code=302)
