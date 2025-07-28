from sqlalchemy.orm import Session
from sqlalchemy import or_
from authentication.authentication import pwd_context
from storage import db_models
from validation import schemas
from fastapi.encoders import jsonable_encoder


class DbManager:
    def __init__(self, db: Session, object_id, schema, update_schema, in_db_schema, db_model, user_id):
        self._db = db
        self._object_id = object_id,
        self._schema = schema
        self._update_schema = update_schema
        self._in_db_schema = in_db_schema
        self._db_model = db_model
        self._user_id = user_id


    def get_object(self):
        """
        Retrieve a single database object by its ID.
        """
        db_object = self._db.get(self._db_model, self._object_id)
        return db_object


    def get_objects_by_user(self):
        """
        Fetch all objects from the database associated with the current user.
        """
        objects = self._db.execute(self._db.query(self._db_model)\
                                   .where(self._db_model.user_id == self._user_id)).scalars()
        return objects


    def add_object(self, pydantic_object):
        """
        Add a new object to the database using data from a Pydantic model.
        """
        object_dict = pydantic_object.model_dump()
        object_dict.update({"user_id": self._user_id})
        db_object = self._db_model(**object_dict)
        self._db.add(db_object)
        self._db.commit()
        return db_object


    def delete_object(self):
        """
        Delete the specified object from the database.
        """
        db_object = self.get_object()
        self._db.delete(db_object)
        self._db.commit()


    def update_object(self, new_data):
        """
        Update an existing object in the database with new data.
        """
        db_object = self.get_object()
        db_object_dict = jsonable_encoder(db_object)
        pydantic_object = self._in_db_schema(**db_object_dict)
        updated_data = new_data.model_dump(exclude_unset=True)
        updated_pydantic_object = pydantic_object.model_copy(update=updated_data)
        for key, value in updated_pydantic_object.model_dump().items():
            setattr(db_object, key, value)
        self._db.commit()
        return updated_pydantic_object


class ClientManager(DbManager):
    def __init__(self, db, object_id, user_id):
        super().__init__(
            db=db,
            object_id=object_id,
            schema=schemas.Client,
            update_schema=schemas.ClientUpdate,
            in_db_schema=schemas.ClientInDb,
            db_model=db_models.Client,
            user_id=user_id
        )


    def client_in_database(self, client: schemas.ClientBase):
        """
        Check if a client with the same personal data already exists in the database.
        """
        return self._db.execute(self._db.query(self._db_model).where(
            self._db_model.firstname == client.firstname,
            self._db_model.second_name == client.second_name,
            self._db_model.lastname == client.lastname,
            self._db_model.birthdate == client.birthdate,
            self._db_model.user_id == self._user_id
        )).first()





class AddressManager(DbManager):
    def __init__(self, db, object_id, user_id=None, client_id=None):
        super().__init__(
            db=db,
            object_id=object_id,
            schema=schemas.Address,
            update_schema=schemas.AddressUpdate,
            in_db_schema=schemas.AddressInDb,
            db_model=db_models.Address,
            user_id=user_id
        )
        self._client_id = client_id


    def address_relate_to_client(self):
        """
        Retrieve the address associated with the current client ID.
        """
        address = self._db.execute(self._db.query(self._db_model)\
                                   .where(self._db_model.client_id == self._client_id)).first()
        return address


    def add_object(self, pydantic_object: schemas.Address):
        address_dict = pydantic_object.model_dump()
        address_dict.update({"client_id": self._client_id})
        address_db = self._db_model(**address_dict)
        self._db.add(address_db)
        self._db.commit()
        return address_db


class TemplateManager(DbManager):
    def __init__(self, db, object_id, user_id):
        super().__init__(
            db=db,
            object_id=object_id,
            schema=schemas.DocumentTemplate,
            update_schema=None,
            in_db_schema=schemas.DocumentTemplateInDb,
            db_model=db_models.DocumentTemplate,
            user_id=user_id
        )


    def template_in_database(self, template_name: str):
        """
        Check if a template with the given name exists for the user.
        """
        return self._db.execute(self._db.query(self._db_model)\
                          .where(
            self._db_model.template_name == template_name,
            self._db_model.user_id == self._user_id
        )).first()


    def template_path_in_db(self, template_path: str):
        """
        Check if a template with the given file path exists in the database.
        """
        return self._db.execute(self._db.query(self._db_model)\
                                .where(self._db_model.template_path == template_path)).first()


class UserManager(DbManager):
    def __init__(self, db, object_id):
        super().__init__(
            db=db,
            object_id=object_id,
            schema=schemas.User,
            update_schema=None,
            in_db_schema=schemas.UserInDB,
            db_model=db_models.User,
            user_id=None
        )


    def user_in_database(self, username_or_email):
        """
        Find a user by username or email. Set object ID if not previously set.
        """
        user = self._db.execute(self._db.query(self._db_model)\
                                .where(or_(
            self._db_model.username == username_or_email,
            self._db_model.email == username_or_email)))\
            .scalars().first()
        if user and self._object_id is None:
            self._object_id = user.id
        return user


    def add_object(self, pydantic_object: schemas.UserCreate):
        """
        Add a new user to the database with hashed password and default settings.
        """
        user_dict = pydantic_object.model_dump()
        hashed_password = pwd_context.hash(user_dict.get("password"))
        user_dict.update({"password": hashed_password, "disabled": False})
        user_db = self._db_model(**user_dict)
        self._db.add(user_db)
        self._db.commit()
        return user_db


    def update_object(self, new_data: schemas.UserUpdate):
        """
        Update user data, including optional password hashing.
        """
        db_object = self.get_object()
        db_object_dict = jsonable_encoder(db_object)
        pydantic_object = self._in_db_schema(**db_object_dict)
        if new_data.password:
            new_data.password = pwd_context.hash(new_data.password)
        updated_data = new_data.model_dump(exclude_unset=True)
        updated_pydantic_object = pydantic_object.model_copy(update=updated_data)
        for key, value in updated_pydantic_object.model_dump().items():
            setattr(db_object, key, value)
        self._db.commit()
        return updated_pydantic_object


class TokenManager(DbManager):
    def __init__(self, db, object_id, user_id):
        super().__init__(
            db=db,
            object_id=object_id,
            schema=None,
            update_schema=None,
            in_db_schema=None,
            db_model=db_models.UserToken,
            user_id=user_id
        )


    def get_object_by_name(self, name):
        token = self._db.query(self._db_model).where(
            self._db_model.token_name == name,
            self._db_model.user_id == self._user_id
        ).first()
        return token







