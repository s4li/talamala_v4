"""
Blog Service - Business Logic
==================================
CRUD for articles, categories, tags, and comment moderation.
"""

import logging
from typing import List, Tuple, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from modules.blog.models import (
    Article, ArticleCategory, ArticleTag, ArticleTagLink,
    ArticleImage, ArticleComment, ArticleStatus,
)
from common.upload import save_upload_file
from common.helpers import now_utc

logger = logging.getLogger("talamala.blog")


class BlogService:

    # ------------------------------------------
    # Article CRUD
    # ------------------------------------------

    def list_articles_admin(
        self, db: Session, page: int = 1, per_page: int = 20,
        status: Optional[str] = None, category_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        """Admin list: all articles with filters. Returns (items, total)."""
        q = db.query(Article).options(
            joinedload(Article.category),
            joinedload(Article.author),
        )
        if status:
            q = q.filter(Article.status == status)
        if category_id:
            q = q.filter(Article.category_id == category_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(
                Article.title.ilike(term),
                Article.body.ilike(term),
            ))
        total = q.count()
        items = (
            q.order_by(Article.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def list_published(
        self, db: Session, page: int = 1, per_page: int = 12,
        category_id: Optional[int] = None, tag_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        """Public list: only published articles. Returns (items, total)."""
        q = db.query(Article).options(
            joinedload(Article.category),
            joinedload(Article.author),
            joinedload(Article.tag_links).joinedload(ArticleTagLink.tag),
        ).filter(Article.status == ArticleStatus.PUBLISHED)

        if category_id:
            q = q.filter(Article.category_id == category_id)
        if tag_id:
            q = q.join(ArticleTagLink).filter(ArticleTagLink.tag_id == tag_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(
                Article.title.ilike(term),
                Article.excerpt.ilike(term),
            ))
        total = q.count()
        items = (
            q.order_by(Article.published_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def get_by_id(self, db: Session, article_id: int) -> Optional[Article]:
        return db.query(Article).options(
            joinedload(Article.category),
            joinedload(Article.author),
            joinedload(Article.tag_links).joinedload(ArticleTagLink.tag),
            joinedload(Article.images),
        ).filter(Article.id == article_id).first()

    def get_by_slug(self, db: Session, slug: str) -> Optional[Article]:
        return db.query(Article).options(
            joinedload(Article.category),
            joinedload(Article.author),
            joinedload(Article.tag_links).joinedload(ArticleTagLink.tag),
            joinedload(Article.comments).joinedload(ArticleComment.user),
        ).filter(
            Article.slug == slug,
            Article.status == ArticleStatus.PUBLISHED,
        ).first()

    def create(
        self, db: Session, data: dict,
        cover_file: Optional[UploadFile] = None,
    ) -> Article:
        article = Article(
            title=data["title"].strip(),
            slug=data["slug"].strip().lower(),
            excerpt=data.get("excerpt", "").strip() or None,
            body=data["body"],
            category_id=data.get("category_id") or None,
            author_id=data.get("author_id"),
            status=data.get("status", ArticleStatus.DRAFT),
            meta_title=data.get("meta_title", "").strip() or None,
            meta_description=data.get("meta_description", "").strip() or None,
            is_featured=data.get("is_featured", False),
        )

        # Set published_at when publishing immediately
        if article.status == ArticleStatus.PUBLISHED:
            article.published_at = now_utc()

        db.add(article)
        db.flush()
        db.refresh(article)

        # Cover image
        if cover_file and cover_file.filename:
            path = save_upload_file(
                cover_file, subfolder="blog", max_size=(1200, 800),
            )
            if path:
                article.cover_image = path
                db.flush()

        # Tags (M2M)
        for tag_id in (data.get("tag_ids") or []):
            db.add(ArticleTagLink(
                article_id=article.id, tag_id=int(tag_id),
            ))
        if data.get("tag_ids"):
            db.flush()

        return article

    def update(
        self, db: Session, article_id: int, data: dict,
        cover_file: Optional[UploadFile] = None,
    ) -> Optional[Article]:
        article = self.get_by_id(db, article_id)
        if not article:
            return None

        was_not_published = article.status != ArticleStatus.PUBLISHED

        article.title = data["title"].strip()
        article.slug = data["slug"].strip().lower()
        article.excerpt = data.get("excerpt", "").strip() or None
        article.body = data["body"]
        article.category_id = data.get("category_id") or None
        article.status = data.get("status", article.status)
        article.meta_title = data.get("meta_title", "").strip() or None
        article.meta_description = data.get("meta_description", "").strip() or None
        article.is_featured = data.get("is_featured", False)

        # Set published_at when first published
        if (was_not_published
                and article.status == ArticleStatus.PUBLISHED
                and not article.published_at):
            article.published_at = now_utc()

        # Cover image
        if cover_file and cover_file.filename:
            path = save_upload_file(
                cover_file, subfolder="blog", max_size=(1200, 800),
            )
            if path:
                article.cover_image = path

        # Sync tags (M2M) -- delete old, add new
        if "tag_ids" in data:
            db.query(ArticleTagLink).filter(
                ArticleTagLink.article_id == article.id,
            ).delete()
            for tag_id in (data["tag_ids"] or []):
                db.add(ArticleTagLink(
                    article_id=article.id, tag_id=int(tag_id),
                ))

        db.flush()
        return article

    def delete(self, db: Session, article_id: int) -> bool:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return False
        db.delete(article)
        db.flush()
        return True

    def toggle_publish(self, db: Session, article_id: int) -> Optional[Article]:
        """Toggle between Draft and Published."""
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None
        if article.status == ArticleStatus.PUBLISHED:
            article.status = ArticleStatus.DRAFT
        else:
            article.status = ArticleStatus.PUBLISHED
            if not article.published_at:
                article.published_at = now_utc()
        db.flush()
        return article

    def increment_view(self, db: Session, article_id: int):
        """Atomic DB-level view count increment (no race condition)."""
        db.query(Article).filter(Article.id == article_id).update(
            {Article.view_count: Article.view_count + 1},
            synchronize_session=False,
        )
        db.flush()

    # ------------------------------------------
    # Categories
    # ------------------------------------------

    def list_categories(self, db: Session) -> List[ArticleCategory]:
        return (
            db.query(ArticleCategory)
            .order_by(ArticleCategory.sort_order)
            .all()
        )

    def get_active_categories(self, db: Session) -> List[ArticleCategory]:
        return (
            db.query(ArticleCategory)
            .filter(ArticleCategory.is_active == True)  # noqa: E712
            .order_by(ArticleCategory.sort_order)
            .all()
        )

    def get_category_by_slug(
        self, db: Session, slug: str,
    ) -> Optional[ArticleCategory]:
        return db.query(ArticleCategory).filter(
            ArticleCategory.slug == slug,
        ).first()

    def create_category(
        self, db: Session, name: str, slug: str,
        description: Optional[str] = None, sort_order: int = 0,
        is_active: bool = True,
    ) -> ArticleCategory:
        cat = ArticleCategory(
            name=name.strip(),
            slug=slug.strip().lower(),
            description=description,
            sort_order=sort_order,
            is_active=is_active,
        )
        db.add(cat)
        db.flush()
        return cat

    def update_category(
        self, db: Session, cat_id: int, name: str, slug: str,
        description: Optional[str] = None, sort_order: int = 0,
        is_active: bool = True,
    ) -> Optional[ArticleCategory]:
        cat = db.query(ArticleCategory).filter(
            ArticleCategory.id == cat_id,
        ).first()
        if not cat:
            return None
        cat.name = name.strip()
        cat.slug = slug.strip().lower()
        cat.description = description
        cat.sort_order = sort_order
        cat.is_active = is_active
        db.flush()
        return cat

    def delete_category(self, db: Session, cat_id: int):
        db.query(ArticleCategory).filter(
            ArticleCategory.id == cat_id,
        ).delete()
        db.flush()

    # ------------------------------------------
    # Tags
    # ------------------------------------------

    def list_tags(self, db: Session) -> List[ArticleTag]:
        return db.query(ArticleTag).order_by(ArticleTag.name).all()

    def get_tag_by_slug(
        self, db: Session, slug: str,
    ) -> Optional[ArticleTag]:
        return db.query(ArticleTag).filter(
            ArticleTag.slug == slug,
        ).first()

    def get_or_create_tag(
        self, db: Session, name: str, slug: str,
    ) -> ArticleTag:
        """Find existing tag or create new one."""
        existing = db.query(ArticleTag).filter(
            ArticleTag.slug == slug.strip().lower(),
        ).first()
        if existing:
            return existing
        tag = ArticleTag(name=name.strip(), slug=slug.strip().lower())
        db.add(tag)
        db.flush()
        return tag

    def delete_tag(self, db: Session, tag_id: int):
        db.query(ArticleTag).filter(ArticleTag.id == tag_id).delete()
        db.flush()

    # ------------------------------------------
    # Inline image upload (TinyMCE callback)
    # ------------------------------------------

    def save_inline_image(
        self, db: Session, upload_file: UploadFile,
    ) -> Optional[str]:
        """Save image uploaded via TinyMCE editor. Returns file path."""
        path = save_upload_file(
            upload_file, subfolder="blog", max_size=(1200, 1200),
        )
        return path

    # ------------------------------------------
    # Comments
    # ------------------------------------------

    def add_comment(
        self, db: Session, article_id: int, user_id: int, body: str,
    ) -> dict:
        if not body or not body.strip():
            return {"success": False, "message": "\u0645\u062a\u0646 \u0646\u0638\u0631 \u062e\u0627\u0644\u06cc \u0627\u0633\u062a"}
        comment = ArticleComment(
            article_id=article_id,
            user_id=user_id,
            body=body.strip(),
            is_approved=False,
        )
        db.add(comment)
        db.flush()
        return {"success": True, "comment": comment}

    def list_comments_admin(
        self, db: Session, page: int = 1, per_page: int = 30,
        approved: Optional[bool] = None, search: Optional[str] = None,
    ) -> Tuple[List[ArticleComment], int]:
        """Admin comment list with optional approval filter."""
        q = db.query(ArticleComment).options(
            joinedload(ArticleComment.article),
            joinedload(ArticleComment.user),
        )
        if approved is not None:
            q = q.filter(ArticleComment.is_approved == approved)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(ArticleComment.body.ilike(term))
        total = q.count()
        items = (
            q.order_by(ArticleComment.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def approve_comment(self, db: Session, comment_id: int) -> Optional[ArticleComment]:
        comment = db.query(ArticleComment).filter(
            ArticleComment.id == comment_id,
        ).first()
        if comment:
            comment.is_approved = True
            db.flush()
        return comment

    def reject_comment(self, db: Session, comment_id: int) -> bool:
        """Delete the comment (rejection = removal)."""
        comment = db.query(ArticleComment).filter(
            ArticleComment.id == comment_id,
        ).first()
        if comment:
            db.delete(comment)
            db.flush()
        return True

    # ------------------------------------------
    # SEO: Sitemap data
    # ------------------------------------------

    def get_sitemap_articles(self, db: Session) -> List[Article]:
        """Return published articles for sitemap generation."""
        return (
            db.query(Article)
            .filter(Article.status == ArticleStatus.PUBLISHED)
            .order_by(Article.published_at.desc())
            .all()
        )

    def get_sitemap_categories(self, db: Session) -> List[ArticleCategory]:
        """Return active categories for sitemap generation."""
        return (
            db.query(ArticleCategory)
            .filter(ArticleCategory.is_active == True)  # noqa: E712
            .order_by(ArticleCategory.sort_order)
            .all()
        )

    # ------------------------------------------
    # Related articles
    # ------------------------------------------

    def get_related(
        self, db: Session, article: Article, limit: int = 4,
    ) -> List[Article]:
        """Get related published articles by same category."""
        if not article.category_id:
            return []
        return (
            db.query(Article)
            .filter(
                Article.category_id == article.category_id,
                Article.id != article.id,
                Article.status == ArticleStatus.PUBLISHED,
            )
            .order_by(Article.published_at.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------
    # Featured articles
    # ------------------------------------------

    def get_featured(self, db: Session, limit: int = 5) -> List[Article]:
        """Get featured published articles for homepage/sidebar."""
        return (
            db.query(Article).options(
                joinedload(Article.category),
            )
            .filter(
                Article.status == ArticleStatus.PUBLISHED,
                Article.is_featured == True,  # noqa: E712
            )
            .order_by(Article.published_at.desc())
            .limit(limit)
            .all()
        )


blog_service = BlogService()
