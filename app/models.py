from datetime import datetime

from sqlalchemy import DateTime, func, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(nullable=True)
    price_usd: Mapped[int | None] = mapped_column(nullable=True)
    odometer: Mapped[int | None] = mapped_column(nullable=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    phone_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    images_count: Mapped[int | None] = mapped_column(nullable=True)
    car_number: Mapped[str | None] = mapped_column(nullable=True)
    car_vin: Mapped[str | None] = mapped_column(nullable=True)
    datetime_found: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
