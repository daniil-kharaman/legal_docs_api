from pydantic import BaseModel, Field, EmailStr, AfterValidator, model_validator
from datetime import date
from typing import Annotated
import phonenumbers

PATTERN_USER_FULLNAME = r'^(\p{L}+[\-\']?\p{L}+\s?)+$'
PATTERN_CLIENT = r'^\p{L}+[\-\']?\p{L}+$'
PATTERN_ADDRESS = r'^([\p{L}\d\'\-]+\s?)+$'
PATTERN_TEMPLATE = r'^([\p{L}\d\_\/\.]+\s?)+$'
CLIENT_KWARGS = {
    'min_length': 1,
    'max_length': 30,
    'pattern': PATTERN_CLIENT
}
CLIENT_KWARGS_DEFAULT_NONE = {
    'min_length': 1,
    'max_length': 30,
    'pattern': PATTERN_CLIENT,
    'default': None
}
ADDRESS_KWARGS = {
    'min_length': 1,
    'max_length': 50,
    'pattern': PATTERN_ADDRESS
}
ADDRESS_KWARGS_DEFAULT_NONE = {
    'min_length': 1,
    'max_length': 50,
    'pattern': PATTERN_ADDRESS,
    'default': None
}


def validate_phone_number(number):
    """
    Validate and format a phone number to E.164 format using the phonenumbers library.
    """
    try:
        phone_obj = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(phone_obj):
            raise ValueError("Wrong phone number")
        formatted_number = phonenumbers.format_number(
            phone_obj, phonenumbers.PhoneNumberFormat.E164
        )
        return formatted_number
    except phonenumbers.NumberParseException:
        raise ValueError("Wrong format of the phone number")


def validate_update_data(data, model_class):
    """
    Validate that the provided data contains only fields defined in the given Pydantic model.
    """
    if not data:
        raise ValueError('Wrong format of the data')
    valid_fields = set(model_class.model_fields.keys())
    for field in data:
        if field not in valid_fields:
            raise ValueError(f"Wrong field name {field}")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    disabled: bool


class UserInDB(User):
    id: int
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    password: str
    disabled: bool


class UserCreate(BaseModel):
    username: str = Field(max_length=30, pattern=r'^\w+$', examples=['johndoe3'])
    email: EmailStr
    full_name: str | None = Field(
        default=None,
        max_length=30,
        pattern=PATTERN_USER_FULLNAME,
        examples=['John Doe']
    )
    password: str = Field(max_length=50, pattern=r'^.+$', examples=['secret'])


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=30, pattern=r'^\w+$', examples=['johndoe3'])
    email: EmailStr | None = None
    full_name: str | None = Field(
        default=None,
        max_length=30,
        pattern=PATTERN_USER_FULLNAME,
        examples=['John Doe'],
    )
    password: str | None = Field(default=None, max_length=50, pattern=r'^.+$', examples=['secret'])

    @model_validator(mode='before')
    def validate_model_before(cls, data):
        validate_update_data(data, cls)
        return data


class ClientBase(BaseModel):
    firstname: str = Field(**CLIENT_KWARGS, examples=['John'])
    second_name: str = Field(**CLIENT_KWARGS, examples=['Charles'])
    lastname: str = Field(**CLIENT_KWARGS, examples=['Doe'])
    birthdate: date


class Client(ClientBase):
    phone_number: Annotated[str | None, AfterValidator(validate_phone_number)] = Field(
        default=None, examples=['+4915112534961']
    )
    email: EmailStr | None = None


class ClientUpdate(BaseModel):
    firstname: str | None = Field(**CLIENT_KWARGS_DEFAULT_NONE, examples=['John'])
    second_name: str | None = Field(**CLIENT_KWARGS_DEFAULT_NONE, examples=['Charles'])
    lastname: str | None = Field(**CLIENT_KWARGS_DEFAULT_NONE, examples=['Doe'])
    birthdate: date | None = None
    phone_number: Annotated[str | None, AfterValidator(validate_phone_number)] = Field(
        default=None, examples=['+4915112534961']
    )
    email: EmailStr | None = None

    @model_validator(mode='before')
    def validate_model_before(cls, data):
        validate_update_data(data, cls)
        return data


class ClientInDb(BaseModel):
    id: int
    firstname: str
    second_name: str
    lastname: str
    birthdate: date
    phone_number: str | None = None
    email: str | None = None


class ClientResponse(ClientInDb):
    client_address_id: int | None = None


class Address(BaseModel):
    house_number: str = Field(**ADDRESS_KWARGS, examples=['1600'])
    street: str = Field(**ADDRESS_KWARGS, examples=['Pennsylvania Avenue NW'])
    city: str = Field(**ADDRESS_KWARGS, examples=['Washington'])
    postal_code: str = Field(**ADDRESS_KWARGS, examples=['20500'])
    country: str = Field(**ADDRESS_KWARGS, examples=['United States'])
    state: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['District of Columbia'])


class AddressInDb(BaseModel):
    id: int
    client_id: int
    house_number: str
    street: str
    city: str
    postal_code: str
    country: str
    state: str | None = None


class AddressUpdate(BaseModel):
    house_number: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['1600'])
    street: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['Pennsylvania Avenue NW'])
    city: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['Washington'])
    postal_code: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['20500'])
    country: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['United States'])
    state: str | None = Field(**ADDRESS_KWARGS_DEFAULT_NONE, examples=['District of Columbia'])

    @model_validator(mode='before')
    def validate_model_before(cls, data):
        validate_update_data(data, cls)
        return data


class DocumentTemplate(BaseModel):
    template_name: str = Field(min_length=1, max_length=50, pattern=PATTERN_TEMPLATE, examples=['Power of Attorney'])
    template_path: str = Field(min_length=1, max_length=50, pattern=PATTERN_TEMPLATE)


class DocumentTemplateInDb(BaseModel):
    id: int
    template_name: str
    template_path: str


class GenContext(BaseModel):
    party_one_id: list[int] = Field(min_length=1)
    party_two_id: list[int] = Field(min_length=1)
    date: date


class DocumentTemplateName(BaseModel):
    template_name: str = Field(min_length=1, max_length=50, pattern=PATTERN_TEMPLATE, examples=['Power of Attorney'])


class DocumentTemplateFileName(BaseModel):
    file_name: str = Field(min_length=1, max_length=50, pattern=PATTERN_TEMPLATE, examples=['Power of Attorney'])


class UserRequestAI(BaseModel):
    user_request: str = Field(
        min_length=1,
        examples=['Send an email to John Doe 01.01.1990 that our appointment tomorrow at 9 AM will be cancelled.']
    )


class UserAuthToken(BaseModel):
    token_name: str
    token_data: str = Field(min_length=1)
    user_id: int
