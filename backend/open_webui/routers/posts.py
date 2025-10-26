import json
import logging
from typing import Optional

from open_webui.models.posts import (
    PostForm,
    PostModel,
    Posts,
    PostTitleIdResponse,
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
# GetPostList
############################


@router.get("/", response_model=list[PostTitleIdResponse])
@router.get("/list", response_model=list[PostTitleIdResponse])
async def get_session_user_post_list(
    user=Depends(get_verified_user), page: Optional[int] = None
):
    try:
        if page is not None:
            limit = 60
            skip = (page - 1) * limit

            return Posts.get_post_title_id_list_by_user_id(
                user.id, skip=skip, limit=limit
            )
        else:
            return Posts.get_post_title_id_list_by_user_id(user.id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CreateNewPost
############################


@router.post("/new", response_model=Optional[PostModel])
async def create_new_post(form_data: PostForm, user=Depends(get_verified_user)):
    try:
        post = Posts.insert_new_post(user.id, form_data)
        return post
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetAllPosts
############################


@router.get("/all", response_model=list[PostModel])
async def get_user_posts(user=Depends(get_verified_user)):
    return Posts.get_post_list_by_user_id(user.id)


############################
# GetPostById
############################


@router.get("/{id}", response_model=Optional[PostModel])
async def get_post_by_id(id: str, user=Depends(get_verified_user)):
    post = Posts.get_post_by_id(id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    return post


############################
# UpdatePostById
############################


@router.post("/{id}", response_model=Optional[PostModel])
async def update_post_by_id(
    id: str,
    form_data: PostForm,
    user=Depends(get_verified_user),
):
    post = Posts.get_post_by_id(id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    post = Posts.update_post_by_id(id, form_data)
    return post


############################
# DeletePostById
############################


@router.delete("/{id}", response_model=bool)
async def delete_post_by_id(id: str, user=Depends(get_verified_user)):
    post = Posts.get_post_by_id(id)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    result = Posts.delete_post_by_id(id)
    return result


############################
# DeleteAllPosts
############################


@router.delete("/", response_model=bool)
async def delete_all_user_posts(request: Request, user=Depends(get_verified_user)):
    result = Posts.delete_posts_by_user_id(user.id)
    return result

