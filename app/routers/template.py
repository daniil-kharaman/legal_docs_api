from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from auth import user_login
from storage.data_manager import TemplateManager
from storage.database import get_db
from storage.templates_storage import save_file_in_s3, delete_file_s3, get_file_s3
from validation import schemas, validation
from validation.validation import db_connection_handler

router = APIRouter(
    prefix='/template',
    tags=['Templates']
)

@router.post(
    '/template/upload',
    response_model=schemas.DocumentTemplateInDb,
    summary="Upload document template",
)
def upload_template(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        file: Annotated[UploadFile, Depends(validation.validate_file)],
        template_name: Annotated[str, Depends(validation.validate_template_name)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Upload a new document template after validating the file and template name.
    """
    template_manager = TemplateManager(db=db, object_id=None, user_id=current_user.id)
    validation.validate_template(template_name, template_manager.template_in_database)
    object_key = f"document_templates/{str(current_user.id)}/{template_name}.docx"
    validation.validate_file_name(object_key, template_manager.template_path_in_db)
    parsed_template = validation.parse_template(file)
    template_schema = schemas.DocumentTemplate(template_name=template_name, template_path=object_key)
    save_file_in_s3(parsed_template, object_key)
    return template_manager.add_object(template_schema)


@router.get(
    '/template/{template_id}',
    response_model=schemas.DocumentTemplateInDb,
    summary="Get template details",
)
def get_template(
        template_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Retrieve a specific template by ID.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template = validation.get_template_from_db(template_id, template_manager.get_object)
    return template


@router.delete(
    '/template/{template_id}',
    response_model=schemas.DocumentTemplateInDb,
    summary="Delete document template",
)
def delete_template(
        template_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Delete a specific document template by ID.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template = validation.get_template_from_db(template_id, template_manager.get_object)
    delete_file_s3(template.template_path)
    template_manager.delete_object()
    return JSONResponse(
        content={"template": template.id, "message": "Template was successfully deleted"},
        status_code=200
    )


@router.patch(
    '/template/{template_id}',
    summary="Update template name"
)
def update_template(
        template_id: int,
        new_data: schemas.DocumentTemplateName,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Update the name of a specific document template by ID.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template = validation.get_template_from_db(template_id, template_manager.get_object)
    template_manager.update_object(new_data)
    return JSONResponse(
        content={"message": "Template was successfully updated"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.post(
    '/template/{template_id}/generate',
    summary="Generate document from template",
)
def generate_file(
        template_id: int,
        context: schemas.GenContext,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Generate a document file from a template using the provided context.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template_in_db = validation.get_template_from_db(template_id, template_manager.get_object)
    parsed_context = validation.parse_context(context, db)
    if not parsed_context:
        raise HTTPException(status_code=400, detail='Impossible to parse the context')
    template_stream = get_file_s3(template_in_db.template_path)
    rendered_template = validation.render_template(template_stream, parsed_context)
    if not rendered_template:
        raise HTTPException(status_code=400, detail='Impossible to render the template')
    headers = {
        "Content-Disposition": (
            f"attachment; filename={template_in_db.template_name}"
        )
    }
    return StreamingResponse(
        rendered_template,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers=headers
    )
