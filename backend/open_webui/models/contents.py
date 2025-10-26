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
# Content DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Content(Base):
    __tablename__ = "content"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    
    # Content data
    generated_content = Column(Text)  # The AI generated content/post
    urls = Column(JSON)  # Array of URLs used
    model_id = Column(String, nullable=True)  # AI model used
    
    # Photos stored as JSON array of base64 or paths
    photos = Column(JSON, nullable=True)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ContentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    
    generated_content: str
    urls: list
    model_id: Optional[str] = None
    
    photos: Optional[list] = None
    
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class ContentForm(BaseModel):
    title: str
    generated_content: str
    urls: list
    model_id: Optional[str] = None
    photos: Optional[list] = None


class ContentTitleIdResponse(BaseModel):
    id: str
    title: str
    updated_at: int


class ContentTable:
    def insert_new_content(self, user_id: str, form_data: ContentForm) -> Optional[ContentModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time())
            
            content = ContentModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "title": form_data.title,
                    "generated_content": form_data.generated_content,
                    "urls": form_data.urls,
                    "model_id": form_data.model_id,
                    "photos": form_data.photos,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )
            
            result = Content(**content.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return ContentModel.model_validate(result) if result else None

    def get_content_list_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 60
    ) -> list[ContentModel]:
        with get_db() as db:
            return [
                ContentModel.model_validate(content)
                for content in db.query(Content)
                .filter(Content.user_id == user_id)
                .order_by(Content.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            ]

    def get_content_title_id_list_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 60
    ) -> list[ContentTitleIdResponse]:
        with get_db() as db:
            return [
                ContentTitleIdResponse(id=content.id, title=content.title, updated_at=content.updated_at)
                for content in db.query(Content)
                .filter(Content.user_id == user_id)
                .order_by(Content.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            ]

    def get_content_by_id(self, id: str) -> Optional[ContentModel]:
        with get_db() as db:
            content = db.get(Content, id)
            return ContentModel.model_validate(content) if content else None

    def update_content_by_id(self, id: str, form_data: ContentForm) -> Optional[ContentModel]:
        with get_db() as db:
            content = db.get(Content, id)
            if not content:
                return None
                
            content.title = form_data.title
            content.generated_content = form_data.generated_content
            content.urls = form_data.urls
            content.model_id = form_data.model_id
            content.photos = form_data.photos
            content.updated_at = int(time.time())
            
            db.commit()
            db.refresh(content)
            return ContentModel.model_validate(content)

    def delete_content_by_id(self, id: str) -> bool:
        with get_db() as db:
            content = db.get(Content, id)
            if not content:
                return False
                
            db.delete(content)
            db.commit()
            return True

    def delete_contents_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            db.query(Content).filter(Content.user_id == user_id).delete()
            db.commit()
            return True


Contents = ContentTable()

