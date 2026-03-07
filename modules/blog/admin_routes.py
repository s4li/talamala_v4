"""
Blog Module - Admin Routes
================================
CRUD for articles, categories, tags, and comment moderation.
"""

from typing import Optional, List
from fastapi import (
    APIRouter, Request, Depends, Form, File, UploadFile, Query,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.blog.service import blog_service
from modules.blog.models import ArticleStatus

router = APIRouter(prefix="/admin/blog", tags=["admin-blog"])


# ==========================================
# Helper: template context
# ==========================================

def _ctx(request, user, **extra):
    csrf = new_csrf_token(request)
    data = {"request": request, "user": user, "csrf_token": csrf, **extra}
    return data, csrf


# ==========================================
# Article List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def blog_list(
    request: Request,
    page: int = Query(1, ge=1),
    status: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog")),
):
    per_page = 20
    articles, total = blog_service.list_articles_admin(
        db, page=page, per_page=per_page,
        status=status, category_id=category_id, search=search,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    categories = blog_service.list_categories(db)

    data, csrf = _ctx(
        request, user,
        articles=articles, categories=categories,
        page=page, total_pages=total_pages, total=total,
        current_status=status, current_category=category_id,
        search_query=search or "",
    )
    response = templates.TemplateResponse("admin/blog/list.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Article Create
# ==========================================

@router.get("/new", response_class=HTMLResponse)
async def blog_new_form(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="create")),
):
    categories = blog_service.list_categories(db)
    tags = blog_service.list_tags(db)
    data, csrf = _ctx(
        request, user,
        article=None, categories=categories, tags=tags,
        statuses=list(ArticleStatus),
    )
    response = templates.TemplateResponse("admin/blog/form.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/new")
async def blog_create(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    excerpt: str = Form(""),
    body: str = Form(""),
    category_id: str = Form(""),
    status: str = Form("Draft"),
    meta_title: str = Form(""),
    meta_description: str = Form(""),
    is_featured: Optional[str] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="create")),
):
    csrf_check(request, csrf_token)

    # Parse multi-value tag_ids from form
    form = await request.form()
    tag_ids = [int(v) for v in form.getlist("tag_ids") if str(v).isdigit()]

    cat_id = int(category_id) if category_id.strip().isdigit() else None

    try:
        article = blog_service.create(db, {
            "title": title,
            "slug": slug,
            "excerpt": excerpt,
            "body": body,
            "category_id": cat_id,
            "author_id": user.id,
            "status": status,
            "meta_title": meta_title,
            "meta_description": meta_description,
            "is_featured": is_featured == "on",
            "tag_ids": tag_ids,
        }, cover_file=cover_image)
        db.commit()
        return RedirectResponse(f"/admin/blog/{article.id}", status_code=303)
    except IntegrityError:
        db.rollback()
        # Re-render form with submitted data instead of redirect (preserves TinyMCE body)
        categories = blog_service.list_categories(db)
        tags = blog_service.list_tags(db)
        # Build a lightweight object mimicking article attributes
        form_article = type("FD", (), {
            "id": None, "title": title, "slug": slug, "excerpt": excerpt,
            "body": body, "category_id": cat_id, "status": status,
            "meta_title": meta_title, "meta_description": meta_description,
            "is_featured": is_featured == "on", "tag_ids": tag_ids,
            "cover_image": None, "images": [], "author_name": user.full_name,
            "seo_title": meta_title or title, "seo_description": meta_description or excerpt,
        })()
        data, csrf = _ctx(
            request, user,
            article=form_article, categories=categories, tags=tags,
            statuses=list(ArticleStatus),
            error="اسلاگ تکراری است. لطفاً یک اسلاگ متفاوت وارد کنید.",
        )
        response = templates.TemplateResponse("admin/blog/form.html", data)
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response


# ==========================================
# Categories & Tags Management
# ==========================================
# NOTE: These fixed-path routes MUST be defined before /{article_id}
# to prevent FastAPI from matching "categories"/"comments" as article_id.

@router.get("/categories", response_class=HTMLResponse)
async def blog_categories_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog")),
):
    categories = blog_service.list_categories(db)
    tags = blog_service.list_tags(db)
    data, csrf = _ctx(
        request, user, categories=categories, tags=tags,
    )
    response = templates.TemplateResponse("admin/blog/categories.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/categories/new")
async def blog_category_create(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_active: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="create")),
):
    csrf_check(request, csrf_token)
    try:
        blog_service.create_category(
            db, name=name, slug=slug,
            description=description or None,
            sort_order=sort_order,
            is_active=is_active == "on",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
    return RedirectResponse("/admin/blog/categories", status_code=303)


@router.post("/categories/{cat_id}/edit")
async def blog_category_update(
    request: Request,
    cat_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_active: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="edit")),
):
    csrf_check(request, csrf_token)
    try:
        blog_service.update_category(
            db, cat_id, name=name, slug=slug,
            description=description or None,
            sort_order=sort_order,
            is_active=is_active == "on",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
    return RedirectResponse("/admin/blog/categories", status_code=303)


@router.post("/categories/{cat_id}/delete")
async def blog_category_delete(
    request: Request,
    cat_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="full")),
):
    csrf_check(request, csrf_token)
    blog_service.delete_category(db, cat_id)
    db.commit()
    return RedirectResponse("/admin/blog/categories", status_code=303)


# ==========================================
# Tags
# ==========================================

@router.post("/tags/new")
async def blog_tag_create(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="create")),
):
    csrf_check(request, csrf_token)
    try:
        blog_service.get_or_create_tag(db, name=name, slug=slug)
        db.commit()
    except IntegrityError:
        db.rollback()
    return RedirectResponse("/admin/blog/categories", status_code=303)


@router.post("/tags/{tag_id}/delete")
async def blog_tag_delete(
    request: Request,
    tag_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="full")),
):
    csrf_check(request, csrf_token)
    blog_service.delete_tag(db, tag_id)
    db.commit()
    return RedirectResponse("/admin/blog/categories", status_code=303)


# ==========================================
# Comment Moderation
# ==========================================

@router.get("/comments", response_class=HTMLResponse)
async def blog_comments_page(
    request: Request,
    page: int = Query(1, ge=1),
    tab: str = Query("pending"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog")),
):
    per_page = 30
    approved = None
    if tab == "pending":
        approved = False
    elif tab == "approved":
        approved = True

    comments, total = blog_service.list_comments_admin(
        db, page=page, per_page=per_page,
        approved=approved, search=search,
    )

    # Counts for tab badges
    _, pending_count = blog_service.list_comments_admin(
        db, page=1, per_page=1, approved=False,
    )
    _, approved_count = blog_service.list_comments_admin(
        db, page=1, per_page=1, approved=True,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    data, csrf = _ctx(
        request, user,
        comments=comments, page=page,
        total_pages=total_pages, total=total,
        tab=tab, search_query=search or "",
        pending_count=pending_count,
        approved_count=approved_count,
    )
    response = templates.TemplateResponse("admin/blog/comments.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/comments/{comment_id}/approve")
async def blog_comment_approve(
    request: Request,
    comment_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="edit")),
):
    csrf_check(request, csrf_token)
    blog_service.approve_comment(db, comment_id)
    db.commit()
    return RedirectResponse("/admin/blog/comments?tab=pending", status_code=303)


@router.post("/comments/{comment_id}/reject")
async def blog_comment_reject(
    request: Request,
    comment_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="full")),
):
    csrf_check(request, csrf_token)
    blog_service.reject_comment(db, comment_id)
    db.commit()
    return RedirectResponse("/admin/blog/comments?tab=pending", status_code=303)


# ==========================================
# TinyMCE Image Upload (AJAX)
# ==========================================

@router.post("/upload-image")
async def upload_tinymce_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="create")),
):
    """AJAX endpoint for TinyMCE image uploads. CSRF via X-CSRF-Token header."""
    csrf_token = request.headers.get("X-CSRF-Token", "")
    csrf_check(request, csrf_token)

    path = blog_service.save_inline_image(db, file)
    if not path:
        return JSONResponse({"error": "Upload failed"}, status_code=400)
    db.commit()
    return JSONResponse({"location": f"/{path}"})


# ==========================================
# Article Edit (dynamic path - must be AFTER fixed paths)
# ==========================================

@router.get("/{article_id}", response_class=HTMLResponse)
async def blog_edit_form(
    request: Request,
    article_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog")),
):
    article = blog_service.get_by_id(db, article_id)
    if not article:
        return RedirectResponse("/admin/blog?error=not-found", status_code=302)

    categories = blog_service.list_categories(db)
    tags = blog_service.list_tags(db)
    data, csrf = _ctx(
        request, user,
        article=article, categories=categories, tags=tags,
        statuses=list(ArticleStatus),
    )
    response = templates.TemplateResponse("admin/blog/form.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{article_id}/edit")
async def blog_update(
    request: Request,
    article_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    excerpt: str = Form(""),
    body: str = Form(""),
    category_id: str = Form(""),
    status: str = Form("Draft"),
    meta_title: str = Form(""),
    meta_description: str = Form(""),
    is_featured: Optional[str] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="edit")),
):
    csrf_check(request, csrf_token)

    form = await request.form()
    tag_ids = [int(v) for v in form.getlist("tag_ids") if str(v).isdigit()]

    cat_id = int(category_id) if category_id.strip().isdigit() else None

    try:
        article = blog_service.update(db, article_id, {
            "title": title,
            "slug": slug,
            "excerpt": excerpt,
            "body": body,
            "category_id": cat_id,
            "status": status,
            "meta_title": meta_title,
            "meta_description": meta_description,
            "is_featured": is_featured == "on",
            "tag_ids": tag_ids,
        }, cover_file=cover_image)
        if not article:
            return RedirectResponse("/admin/blog?error=not-found", status_code=302)
        db.commit()
        return RedirectResponse(f"/admin/blog/{article_id}", status_code=303)
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            f"/admin/blog/{article_id}?error=slug-duplicate", status_code=303,
        )


# ==========================================
# Article Delete
# ==========================================

@router.post("/{article_id}/delete")
async def blog_delete(
    request: Request,
    article_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="full")),
):
    csrf_check(request, csrf_token)
    blog_service.delete(db, article_id)
    db.commit()
    return RedirectResponse("/admin/blog", status_code=303)


# ==========================================
# Toggle Publish
# ==========================================

@router.post("/{article_id}/toggle-publish")
async def blog_toggle_publish(
    request: Request,
    article_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("blog", level="edit")),
):
    csrf_check(request, csrf_token)
    blog_service.toggle_publish(db, article_id)
    db.commit()
    return RedirectResponse(f"/admin/blog/{article_id}", status_code=303)
