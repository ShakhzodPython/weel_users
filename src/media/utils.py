import os
from uuid import uuid4

import aiofiles
from fastapi import UploadFile, HTTPException, status

from database.settings import ALLOWED_IMAGE_TYPES, UPLOAD_DIR
from logs.logger import logger


async def save_image(image: UploadFile) -> str:
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        logger.error(f"Недопустимый тип файла: {image.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not allowed file type")

    unique_uuid = str(uuid4())

    filename = f"{unique_uuid}_{image.filename}"
    file_location = os.path.join(UPLOAD_DIR, filename)

    try:
        async with aiofiles.open(file_location, "wb") as file:
            content = await image.read()
            await file.write(content)
    except Exception as e:
        logger.error("Ошибка при сохранении файла: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the file"
        )
    return f"uploads/{unique_uuid}_{image.filename}"
