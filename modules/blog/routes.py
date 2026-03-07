"""
Blog Module - Public Routes
================================
Public-facing blog: article list, detail, category/tag filter, comments, sitemap.
"""

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import BASE_URL
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import get_current_active_user, require_login
from modules.blog.service import blog_service
from modules.cart.service import cart_service
from modules.notification.service import notification_service

router = APIRouter(tags=["blog"])


def _blog_context(request, db, user):
    """Build shared context for blog pages (cart count + notification badge for navbar)."""
    cart_count = 0
    notification_count = 0
    if user:
        _, cart_count = cart_service.get_cart_map(db, user.id)
        notification_count = notification_service.get_unread_count(db, user.id)
    return {
        "user": user,
        "cart_count": cart_count,
        "notification_count": notification_count,
    }


# ==========================================
# Article List
# ==========================================

@router.get("/blog", response_class=HTMLResponse)
async def blog_list(
    request: Request,
    page: int = Query(1, ge=1),
    category: str = Query(""),
    tag: str = Query(""),
    search: str = Query(""),
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    per_page = 12

    # Resolve category/tag filters
    category_id = None
    tag_id = None
    current_category = None
    current_tag = None

    if category:
        cat_obj = blog_service.get_category_by_slug(db, category)
        if cat_obj:
            category_id = cat_obj.id
            current_category = cat_obj

    if tag:
        tag_obj = blog_service.get_tag_by_slug(db, tag)
        if tag_obj:
            tag_id = tag_obj.id
            current_tag = tag_obj

    articles, total = blog_service.list_published(
        db, page=max(1, page), per_page=per_page,
        category_id=category_id, tag_id=tag_id,
        search=search.strip() or None,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)

    categories = blog_service.get_active_categories(db)
    tags = blog_service.list_tags(db)
    featured = blog_service.get_featured(db, limit=5)

    ctx = _blog_context(request, db, user)
    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("shop/blog/list.html", {
        "request": request,
        **ctx,
        "articles": articles,
        "categories": categories,
        "tags": tags,
        "featured": featured,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "current_category": current_category,
        "current_tag": current_tag,
        "search_query": search,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Category / Tag filter redirects
# ==========================================

@router.get("/blog/category/{slug}", response_class=HTMLResponse)
async def blog_category_redirect(slug: str):
    return RedirectResponse(f"/blog?category={slug}", status_code=302)


@router.get("/blog/tag/{slug}", response_class=HTMLResponse)
async def blog_tag_redirect(slug: str):
    return RedirectResponse(f"/blog?tag={slug}", status_code=302)


# ==========================================
# Article Detail
# ==========================================

@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_detail(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    article = blog_service.get_by_slug(db, slug)
    if not article:
        return RedirectResponse("/blog", status_code=302)

    # Atomic view count increment
    blog_service.increment_view(db, article.id)
    db.commit()

    # Related articles
    related = blog_service.get_related(db, article, limit=4)

    # Approved comments only
    approved_comments = [c for c in article.comments if c.is_approved]

    ctx = _blog_context(request, db, user)
    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("shop/blog/detail.html", {
        "request": request,
        **ctx,
        "article": article,
        "related": related,
        "comments": approved_comments,
        "BASE_URL": BASE_URL,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Submit Comment
# ==========================================

@router.post("/blog/{slug}/comment")
async def blog_submit_comment(
    request: Request,
    slug: str,
    body: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    csrf_check(request, csrf_token)

    article = blog_service.get_by_slug(db, slug)
    if not article:
        return RedirectResponse("/blog", status_code=302)

    blog_service.add_comment(db, article.id, user.id, body)
    db.commit()

    return RedirectResponse(
        f"/blog/{slug}?comment=submitted", status_code=303,
    )


# ==========================================
# XML Sitemap
# ==========================================

@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(db: Session = Depends(get_db)):
    """Dynamic XML sitemap with published articles and active categories."""
    articles = blog_service.get_sitemap_articles(db)
    categories = blog_service.get_sitemap_categories(db)

    urls = []
    # Main pages
    for path in ["/", "/blog", "/verify"]:
        urls.append(f"  <url><loc>{BASE_URL}{path}</loc></url>")

    # Articles
    for a in articles:
        lastmod = ""
        if a.updated_at:
            lastmod = f"<lastmod>{a.updated_at.strftime('%Y-%m-%d')}</lastmod>"
        urls.append(
            f"  <url><loc>{BASE_URL}/blog/{a.slug}</loc>{lastmod}</url>"
        )

    # Categories
    for c in categories:
        urls.append(
            f"  <url><loc>{BASE_URL}/blog/category/{c.slug}</loc></url>"
        )

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    return Response(content=xml, media_type="application/xml")
