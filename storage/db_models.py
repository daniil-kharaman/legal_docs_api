from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import date
from storage.database import Base

relationship_user_kwargs = {
    'back_populates': 'user_data',
    'cascade': 'all, delete-orphan',
    'passive_deletes': True
}

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    full_name: Mapped[Optional[str]]
    password: Mapped[str]
    disabled: Mapped[bool]
    clients: Mapped['Client'] = relationship(**relationship_user_kwargs)
    templates: Mapped['DocumentTemplate'] = relationship(**relationship_user_kwargs)
    tokens: Mapped['UserToken'] = relationship(**relationship_user_kwargs)


class Client(Base):
    __tablename__ = "client"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    firstname: Mapped[str]
    second_name: Mapped[str]
    lastname: Mapped[str]
    birthdate: Mapped[date]
    phone_number: Mapped[Optional[str]]
    email: Mapped[Optional[str]]
    client_address: Mapped['Address'] = relationship(back_populates='client_data', cascade='all, delete-orphan')
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'))
    user_data: Mapped['User'] = relationship(back_populates='clients')


class Address(Base):
    __tablename__ = "address"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    house_number: Mapped[str]
    street: Mapped[str]
    city: Mapped[str]
    postal_code: Mapped[str]
    country: Mapped[str]
    state: Mapped[Optional[str]]
    client_id: Mapped[int] = mapped_column(ForeignKey('client.id'))
    client_data: Mapped['Client'] = relationship(back_populates='client_address')


class DocumentTemplate(Base):
    __tablename__ = "document_template"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_name: Mapped[str]
    template_path: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'))
    user_data: Mapped['User'] = relationship(back_populates='templates')


class UserToken(Base):
    __tablename__ = "user_token"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_name: Mapped[str]
    token_data: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'))
    user_data: Mapped['User'] = relationship(back_populates='tokens')
