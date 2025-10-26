import logging
import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON
from sqlalchemy import or_, func, select

####################
# Post DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Post(Base):
    __tablename__ = "post"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    
    # Post content and data
    post_content = Column(Text)  # The AI generated post text
    flight_data = Column(JSON)  # All flight information
    ai_analysis = Column(JSON)  # AI analysis data
    
    # Images stored as base64
    scenic_image = Column(Text, nullable=True)  # Final composed image with text overlays
    original_scenic_image = Column(Text, nullable=True)  # Original Pollinations.ai image without overlays
    flight_info_image = Column(Text, nullable=True)  # Flight info screenshot
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class PostModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    
    post_content: str
    flight_data: dict
    ai_analysis: dict
    
    scenic_image: Optional[str] = None
    original_scenic_image: Optional[str] = None
    flight_info_image: Optional[str] = None
    
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class PostForm(BaseModel):
    title: str
    post_content: str
    flight_data: dict
    ai_analysis: dict
    scenic_image: Optional[str] = None
    original_scenic_image: Optional[str] = None
    flight_info_image: Optional[str] = None


class PostTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int


class PostTable:
    def insert_new_post(self, user_id: str, form_data: PostForm) -> Optional[PostModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time())
            
            post = PostModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": form_data.title,
                    "post_content": form_data.post_content,
                    "flight_data": form_data.flight_data,
                    "ai_analysis": form_data.ai_analysis,
                    "scenic_image": form_data.scenic_image,
                    "original_scenic_image": form_data.original_scenic_image,
                    "flight_info_image": form_data.flight_info_image,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )
            
            result = Post(**post.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return PostModel.model_validate(result) if result else None

    def get_post_list_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 60
    ) -> list[PostModel]:
        with get_db() as db:
            return [
                PostModel.model_validate(post)
                for post in db.query(Post)
                .filter(Post.user_id == user_id)
                .order_by(Post.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            ]

    def get_post_title_id_list_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 60
    ) -> list[PostTitleIdResponse]:
        with get_db() as db:
            return [
                PostTitleIdResponse(id=post.id, title=post.title, updated_at=post.updated_at)
                for post in db.query(Post)
                .filter(Post.user_id == user_id)
                .order_by(Post.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            ]

    def get_post_by_id(self, id: str) -> Optional[PostModel]:
        with get_db() as db:
            post = db.get(Post, id)
            return PostModel.model_validate(post) if post else None

    def update_post_by_id(self, id: str, form_data: PostForm) -> Optional[PostModel]:
        with get_db() as db:
            post = db.get(Post, id)
            if not post:
                return None
                
            post.title = form_data.title
            post.post_content = form_data.post_content
            post.flight_data = form_data.flight_data
            post.ai_analysis = form_data.ai_analysis
            post.scenic_image = form_data.scenic_image
            post.original_scenic_image = form_data.original_scenic_image
            post.flight_info_image = form_data.flight_info_image
            post.updated_at = int(time.time())
            
            db.commit()
            db.refresh(post)
            return PostModel.model_validate(post)

    def delete_post_by_id(self, id: str) -> bool:
        with get_db() as db:
            post = db.get(Post, id)
            if not post:
                return False
                
            db.delete(post)
            db.commit()
            return True

    def delete_posts_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            db.query(Post).filter(Post.user_id == user_id).delete()
            db.commit()
            return True


Posts = PostTable()

