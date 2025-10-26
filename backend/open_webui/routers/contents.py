import json
import logging
from typing import Optional

from open_webui.models.contents import (
    ContentForm,
    ContentModel,
    Contents,
    ContentTitleIdResponse,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetContentList
############################


@router.get("/", response_model=list[ContentTitleIdResponse])
@router.get("/list", response_model=list[ContentTitleIdResponse])
async def get_session_user_content_list(
    user=Depends(get_verified_user), page: Optional[int] = None
):
    try:
        if page is not None:
            limit = 60
            skip = (page - 1) * limit

            return Contents.get_content_title_id_list_by_user_id(
                user.id, skip=skip, limit=limit
            )
        else:
            return Contents.get_content_title_id_list_by_user_id(user.id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CreateNewContent
############################


@router.post("/new", response_model=Optional[ContentModel])
async def create_new_content(form_data: ContentForm, user=Depends(get_verified_user)):
    try:
        content = Contents.insert_new_content(user.id, form_data)
        return content
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetAllContents
############################


@router.get("/all", response_model=list[ContentModel])
async def get_user_contents(user=Depends(get_verified_user)):
    return Contents.get_content_list_by_user_id(user.id)


############################
# GetContentById
############################


@router.get("/{id}", response_model=Optional[ContentModel])
async def get_content_by_id(id: str, user=Depends(get_verified_user)):
    content = Contents.get_content_by_id(id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if content.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    return content


############################
# UpdateContentById
############################


@router.post("/{id}", response_model=Optional[ContentModel])
async def update_content_by_id(
    id: str,
    form_data: ContentForm,
    user=Depends(get_verified_user),
):
    content = Contents.get_content_by_id(id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if content.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    content = Contents.update_content_by_id(id, form_data)
    return content


############################
# DeleteContentById
############################


@router.delete("/{id}", response_model=bool)
async def delete_content_by_id(id: str, user=Depends(get_verified_user)):
    content = Contents.get_content_by_id(id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if content.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    result = Contents.delete_content_by_id(id)
    return result


############################
# DeleteAllContents
############################


@router.delete("/", response_model=bool)
async def delete_all_user_contents(request: Request, user=Depends(get_verified_user)):
    result = Contents.delete_contents_by_user_id(user.id)
    return result

