from fastapi import FastAPI, HTTPException, status
import motor.motor_asyncio
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
import time

app = FastAPI()

uri = "mongodb+srv://Tikhon:Tikhon2017@cluster0.fzmxljc.mongodb.net/?retryWrites=true&w=majority"

# Create a new client and connect to the server
client = motor.motor_asyncio.AsyncIOMotorClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

database = client.Docs
docs_collection = database.documents
versions_collection = database.versions


class Docs(BaseModel):
    _id: ObjectId
    header: str
    size: int
    content: str


@app.get("/docs/{doc_id}", response_model=Docs)
async def read_document(doc_id: str):
    document = await docs_collection.find_one({"_id": ObjectId(doc_id)})
    if document:
        return document
    else:
        return {"message": "Document not found"}


@app.post("/docs/")
async def create_document(header: str, size: int, content: str):
    async with await client.start_session() as s:
        async with s.start_transaction():
            document_data = {"header": header, "size": size, "content": content}
            result = await docs_collection.insert_one(document_data)

            version_data = {"document_id": result.inserted_id, "date": datetime.now(), "data": document_data}
            await versions_collection.insert_one(version_data)
    return {"message": "Document created successfully", "document_id": str(result.inserted_id)}


@app.put("/docs/{doc_id}")
async def update_document(doc_id: str, header: str, size: int, content: str):
    async with await client.start_session() as s:
        async with s.start_transaction():
            document_data = {"header": header, "size": size, "content": content}
            result = await docs_collection.update_one({"_id": ObjectId(doc_id)}, {"$set": document_data})

            if result.modified_count == 0:
                return {"message": "Document not found"}

            version_data = {"document_id": ObjectId(doc_id), "date": datetime.now(), "data": document_data}
            await versions_collection.insert_one(version_data)
    return {"message": "Document updated successfully"}


@app.delete("/docs/{doc_id}")
async def delete_document(doc_id: str):
    async with await client.start_session() as s:
        async with s.start_transaction():
            try:
                doc_object_id = ObjectId(doc_id)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document id")

            document = await docs_collection.find_one({"_id": doc_object_id})
            if document:
                await docs_collection.delete_one({"_id": doc_object_id})
                await versions_collection.delete_many({"document_id": doc_object_id})
                return {"message": "Document deleted successfully"}
            else:
                return {"message": "Document not found"}

