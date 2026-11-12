from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .common import new_id, utcnow
from .users_model import Agency, User


class ReferralLink(Base):
    __tablename__ = "referral_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agency_id: Mapped[str] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_hint: Mapped[str] = mapped_column(String(12), default="")
    label: Mapped[str] = mapped_column(String(120), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    used_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    agency: Mapped[Agency] = relationship()
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    candidate: Mapped[User | None] = relationship(foreign_keys=[used_by])
