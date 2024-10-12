import json
from fastapi import APIRouter, HTTPException, Response, Request, status

router_translation = APIRouter(
    tags=["Translation"]
)

SUPPORTED_LANGUAGES = ["en", "ru", "uz"]
default_language = "ru"
translations = {}


def load_translations(language: str):
    try:
        with open(f"translations/{language}.json", "r") as file:
            translations = json.load(file)
        return translations
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Language '{language}' not supported.")


def get_translations(response: Response,
                     language: str):
    global default_language, translations
    if language in SUPPORTED_LANGUAGES:
        if language != default_language:
            try:
                new_translations = load_translations(language)
                translations = new_translations
                default_language = language  # Обновляем язык только если загрузка прошла успешно
                response.set_cookie(key="language", value=default_language)  # Сохраняем выбранный язык в cookie
            except HTTPException as e:
                # Если происходит ошибка загрузки, не меняем текущие переводы
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не поддерживаемый язык.")
    print(f"Текущий перевод: {translations}")
    return f"Язык установлен на {default_language}"


async def get_language_user(request: Request):
    language = request.cookies.get("language", default_language)
    translations = load_translations(language)
    return translations


@router_translation.post("/api/v1/language/{language}/")
async def get_language(language: str,
                       response: Response):
    message = get_translations(response, language)
    return {"detail": message}
