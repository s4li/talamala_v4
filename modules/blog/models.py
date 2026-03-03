"""
Blog Module - Models
========================
Article publishing system with categories, tags, comments, and SEO.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Index,
    Boolean, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class ArticleStatus(str, enum.Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


# ==========================================
# Article Category
# ==========================================

class ArticleCategory(Base):
    __tablename__ = "article_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    articles = relationship("Article", back_populates="category")

    @property
    def published_count(self) -> int:
        if not self.articles:
            return 0
        return sum(1 for a in self.articles if a.status == ArticleStatus.PUBLISHED)

    def __repr__(self):
        return f"<ArticleCategory {self.name}>"


# ==========================================
# Article Tag
# ==========================================

class ArticleTag(Base):
    __tablename__ = "article_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)

    tag_links = relationship(
        "ArticleTagLink", back_populates="tag",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ArticleTag {self.name}>"


# ==========================================
# Article Tag Link (M2M junction)
# ==========================================

class ArticleTagLink(Base):
    __tablename__ = "article_tag_links"

    id = Column(Integer, primary_key=True)
    article_id = Column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tag_id = Column(
        Integer, ForeignKey("article_tags.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    article = relationship("Article", back_populates="tag_links")
    tag = relationship("ArticleTag", back_populates="tag_links")

    __table_args__ = (
        UniqueConstraint("article_id", "tag_id", name="uq_article_tag_link"),
    )


# ==========================================
# Article
# ==========================================

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, unique=True)
    excerpt = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    cover_image = Column(String(500), nullable=True)

    category_id = Column(
        Integer, ForeignKey("article_categories.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    status = Column(String(20), default=ArticleStatus.DRAFT, nullable=False)

    # SEO fields
    meta_title = Column(String(200), nullable=True)
    meta_description = Column(String(500), nullable=True)

    # Tracking
    view_count = Column(Integer, default=0, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)

    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    category = relationship("ArticleCategory", back_populates="articles")
    author = relationship("User", foreign_keys=[author_id])
    tag_links = relationship(
        "ArticleTagLink", back_populates="article",
        cascade="all, delete-orphan",
    )
    images = relationship(
        "ArticleImage", back_populates="article",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "ArticleComment", back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticleComment.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_article_status_published", "status", "published_at"),
    )

    # --- Display properties ---

    @property
    def status_label(self) -> str:
        return {
            ArticleStatus.DRAFT: "\u067e\u06cc\u0634\u200c\u0646\u0648\u06cc\u0633",
            ArticleStatus.PUBLISHED: "\u0645\u0646\u062a\u0634\u0631 \u0634\u062f\u0647",
            ArticleStatus.ARCHIVED: "\u0622\u0631\u0634\u06cc\u0648 \u0634\u062f\u0647",
        }.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return {
            ArticleStatus.DRAFT: "warning",
            ArticleStatus.PUBLISHED: "success",
            ArticleStatus.ARCHIVED: "secondary",
        }.get(self.status, "secondary")

    @property
    def tags(self):
        """List of ArticleTag objects."""
        return [link.tag for link in self.tag_links]

    @property
    def tag_ids(self):
        """List of tag IDs."""
        return [link.tag_id for link in self.tag_links]

    @property
    def author_name(self) -> str:
        if self.author:
            return self.author.full_name or "\u0646\u0648\u06cc\u0633\u0646\u062f\u0647"
        return "\u0646\u0648\u06cc\u0633\u0646\u062f\u0647"

    @property
    def comment_count(self) -> int:
        """Count of approved comments only."""
        if not self.comments:
            return 0
        return sum(1 for c in self.comments if c.is_approved)

    @property
    def seo_title(self) -> str:
        """Return meta_title if set, otherwise article title."""
        return self.meta_title or self.title

    @property
    def seo_description(self) -> str:
        """Return meta_description if set, otherwise excerpt truncated."""
        if self.meta_description:
            return self.meta_description
        if self.excerpt:
            return self.excerpt[:160]
        return ""

    def __repr__(self):
        return f"<Article #{self.id} [{self.status}] {self.title[:30]}>"


# ==========================================
# Article Image (inline images from TinyMCE)
# ==========================================

class ArticleImage(Base):
    __tablename__ = "article_images"

    id = Column(Integer, primary_key=True)
    article_id = Column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    file_path = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    article = relationship("Article", back_populates="images")


# ==========================================
# Article Comment
# ==========================================

class ArticleComment(Base):
    __tablename__ = "article_comments"

    id = Column(Integer, primary_key=True)
    article_id = Column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    article = relationship("Article", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_article_comment_article", "article_id"),
        Index("ix_article_comment_approved", "article_id", "is_approved"),
    )

    @property
    def user_name(self) -> str:
        if self.user:
            return self.user.full_name or "\u06a9\u0627\u0631\u0628\u0631"
        return "\u0646\u0627\u0634\u0646\u0627\u0633"

    def __repr__(self):
        return f"<ArticleComment #{self.id} approved={self.is_approved}>"
