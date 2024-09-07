# This micro service is for users weel app

# Installation
Create a virtual environment:
```py -m venv venv```

Installation Requirements:
```pip install -r requirements.txt```

Migrations:
Edit settings and config database
```alembic upgrade head```

Launch Local Server:
```uvicorn main:app --reload```
