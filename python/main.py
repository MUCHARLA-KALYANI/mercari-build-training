import os
import logging
import pathlib
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Dict, List
import json

# Define the path to the images & sqlite3 database
images = pathlib.Path(__file__).parent.resolve() / "images"
db = pathlib.Path(__file__).parent.resolve() / "db" / "mercari.sqlite3"


def get_db():
    if not db.exists():
        yield

    conn = sqlite3.connect(db, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


################## for STEP 4-1: ####################
# import json
# JSON_FILE = 'items.json'
# # Function to read the JSON file
# def read_json_file() -> Dict[str, List[Dict[str,str]]]:
#     if not os.path.exists(JSON_FILE):
#         with open(JSON_FILE, 'w') as f:
#             json.dump({"items": []}, f)  # Initialize with an empty list
#     with open(JSON_FILE, 'r') as f:
#         return json.load(f)

# # Function to write data to the JSON file
# def write_json_file(data):
#     with open(JSON_FILE, 'w') as f:
#         json.dump(data, f, indent=4)

######################################################

################## for STEP 4-4: #####################
import hashlib
# def hash_image(image_file: UploadFile) -> str:
#     try:
#         # Read image
#         image = image_file.file.read()
#         hash_value = hashlib.sha256(image).hexdigest()
#         hashed_image_name = f"{hash_value}.jpg"
#         hashed_image_path = images / hashed_image_name
#         # Save image with hashed value as image name
#         with open(hashed_image_path, 'wb') as f:
#             f.write(image)
#         return hashed_image_name
    
#     except Exception as e:
#         raise RuntimeError(f"An unexpected error occurred: {e}")

######################################################

# STEP 5-1: set up the database connection
def setup_database():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    sql_file = pathlib.Path(__file__).parent.resolve() / "db" / "items.sql"
    with open(sql_file, "r") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn")
# For STEP 4-6
logger.level = logging.DEBUG
images = pathlib.Path(__file__).parent.resolve() / "images"
origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


class HelloResponse(BaseModel):
    message: str


@app.get("/", response_model=HelloResponse)
def hello():
    return HelloResponse(**{"message": "Hello, world!"})


class AddItemResponse(BaseModel):
    message: str



@app.post("/items", response_model=AddItemResponse)
async def add_item(
    name: str = Form(...),
    category: str = Form(...), # For STEP 4-2
    image: UploadFile = File(...), # For STEP 4-4
    db: sqlite3.Connection = Depends(get_db),
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    # for STEP 4-2
    if not category:
        raise HTTPException(status_code=400, detail="category is required")
    # for STEP 4-4
    if not image:
        raise HTTPException(status_code=400, detail="image is required")

    image_name = await hash_and_save_image(image)
    cursor = db.cursor()
    ##STEP 5-3 #######
    cursor.execute("SELECT id FROM categories where name = ?",(category,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO categories (name) VALUES (?)",(category,))
        db.commit()
        category_id = cursor.lastrowid
    else:
        category_id = row[0]
    cursor.execute(
        "INSERT INTO items2 (name, category_id, image_name) VALUES (?, ?, ?)",
        (name, category_id, image_name)
    )
    db.commit()
    return AddItemResponse(**{"message": f"item received: {name}"})

class GetItemsResponse(BaseModel):
    items: list[dict]

@app.get("/items", response_model=GetItemsResponse)
def get_item(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM items2")
    rows = cursor.fetchall()
    for i in range(len(rows)):
        rows[i] = dict(rows[i])    
    return GetItemsResponse(**{"items": rows})

# For STEP 4-5
@app.get("/items/{item_id}")
def get_nth_item(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    if item_id < 1:
        raise HTTPException(status_code=400, detail="ID should be larger than 1")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM items2 WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return row
##########STEP-5.2##############
@app.get("/search")
def search_items(keyword: str, db: sqlite3.Connection = Depends(get_db)):
    if keyword == "":
        raise HTTPException(status_code=400, detail="keyword is null")

    cursor = db.cursor()
    cursor.execute("SELECT * FROM items2 WHERE name LIKE ?", (f"%{keyword}%",))
    rows = cursor.fetchall()
    for i in range(len(rows)):
        rows[i] = dict(rows[i])

    return GetItemsResponse(**{"items": rows})


# get_image is a handler to return an image for GET /images/{filename} .
@app.get("/image/{image_name}")
async def get_image(image_name):
    # Create image path
    image = images / image_name

    if not image_name.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)


class Item(BaseModel):
    name: str
    category: str
    image: str

async def hash_and_save_image(image: UploadFile):
    if not image.filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")
    sha256 = hashlib.sha256()
    contents = await image.read()
    sha256.update(contents)
    res = f"{sha256.hexdigest()}.jpg"
    image_path = images / res
    with open(image_path, "wb") as f:
        f.write(contents)

    return res

# def insert_item(item: Item):
#     current = read_json_file()

#     # for STEP 4-2 
#     # current["items"].append({"name": item.name, "category": item.category})
    

#     #for STEP 4-4 
#     current["items"].append({"name": item.name, "category": item.category, "image_name": item.image})
    
#     write_json_file(current)