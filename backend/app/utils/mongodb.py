import os 
import json
from datetime import datetime
from typing import List
from bson.objectid import ObjectId

from pymongo.mongo_client import MongoClient
from pymongo import ReturnDocument


from app.langchain.schema import Documents

from app.schemas.schemas import Review, User, Vendor, State, ParallelState

uri = f"mongodb+srv://qmsoqm2:{os.environ["MONGO_DB_PASSWORD"]}@chathistory.tmp29wl.mongodb.net/?retryWrites=true&w=majority&appName=chatHistory"

def fetch_document(review_id: str, user_id: str) -> Documents:
    client = MongoClient(uri)

    db = client.get_database('ernest')
    
    user_collection = db.get_collection('user')
    user = user_collection.find_one_and_update(
            {"_id": user_id},
            {"$setOnInsert": User().to_dict()}, 
            upsert=True, 
            return_document=ReturnDocument.AFTER
        )
    if user is None:
        raise ValueError(f"User with id {user_id} not found")
    
    review_collection: Review = db.get_collection('review')
    review = review_collection.find_one_and_update(
        {"_id": review_id},
        {"$setOnInsert": Review(user_id=user_id).to_dict()},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    if review is None:
        raise ValueError(f"Review with id {review_id} not found")

    vendor_id = review.get("vendor_id", ObjectId())
    vendor_collection: Vendor = db.get_collection('vendor')
    vendor = vendor_collection.find_one_and_update(
            {"_id": ObjectId(vendor_id)},
            {"$setOnInsert": Vendor().to_dict()}, 
            upsert=True, 
            return_document=ReturnDocument.AFTER
        )
    if vendor is None:
        raise ValueError(f"Vendor with id {vendor_id} not found")
    
    print(f"\n==>> fetch_document ran successfully")

    return Documents(
        review=Review(**review),
        user=User(**user),
        vendor=Vendor(**vendor),
        state=State(),
        parallel_state=ParallelState()
    )

def update_document(documents: Documents) -> bool:
    client = MongoClient(uri)

    db = client.get_database('ernest')

    if hasattr(documents, 'user'):
        user_id = documents.user._id
        user_collection= db.get_collection('user')
        result = user_collection.update_one({"_id": user_id}, {"$set": documents.user.to_dict()})
        if not result:
            raise ValueError(f"User with id {user_id} update failed")
    
    if hasattr(documents, 'vendor'):
        vendor_id = documents.vendor._id
        vendor_collection= db.get_collection('vendor')
        result = vendor_collection.update_one({"_id": vendor_id}, {"$set": documents.vendor.to_dict()})
        if not result:
            raise ValueError(f"Vendor with id {vendor_id} update failed")

    if hasattr(documents, 'review'):
        review_id = documents.review._id
        review_collection= db.get_collection('review')
        result = review_collection.update_one({"_id": review_id}, {"$set": documents.review.to_dict()})
        if not result:
            raise ValueError(f"Review with id {review_id} update failed")

    return True

def delete_document(review_id: str) -> bool:
    client = MongoClient(uri)

    db = client.get_database('ernest')
    review_collection= db.get_collection('review')
    review_collection.delete_one(
        {"_id": review_id}
    )

    print(f"\n==>> delete_document ran successfully")
    return True


def fetch_user(user_id: str, name: str, email: str):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    user_collection = db.get_collection('user')
    user = user_collection.find_one_and_update(
            {"_id": user_id},
            {"$setOnInsert": User(name=name, email=email).to_dict()}, 
            upsert=True, 
            return_document=ReturnDocument.AFTER
        )
    
    review_ids = user.get("review_ids", [])
    reviews = []
    if len(review_ids) != 0:
        review_collection = db.get_collection('review')
        for review_id in review_ids:
            review = review_collection.find_one({"_id": review_id})
            reviews.append(review)
            if review is None:
                raise ValueError(f"Review with id {review_id} not found")

    result = {
        "reviews": reviews,
        "user": user
    }

    return json.dumps(result)

def fetch_review(review_id: str):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    review_collection = db.get_collection('review')
    review = review_collection.find_one({"_id": review_id})
    if review is None:
        raise ValueError(f"Review with id {review_id} not found")
    
    return review

def fetch_reviews_by_user_id(user_id: str):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    review_collection = db.get_collection('review')
    reviews = review_collection.find({"user_id": user_id})
    reviews = list(reviews)

    if reviews is None or len(reviews) == 0:
        raise ValueError(f"reviews with user_id {user_id} not found")
    
    return reviews

def save_review(review: dict):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    review_collection = db.get_collection('review')
    review_id = review_collection.update_one(
            {"_id": review.id},
            {"$set": review}
        )

    user_id = review.get("user_id")
    user_collection = db.get_collection('user')
    user_collection.update_one(
        {"_id": user_id},
        {"$push": {"review_ids": review_id}}
    )

    return review_id

def delete_reviews_by_user_id(user_id: str):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    review_collection = db.get_collection('review')
    review_collection.delete_many({"user_id": user_id})

    user_collection = db.get_collection('user')
    user_collection.update_one({"_id": user_id}, {"$unset": {"review_ids": []}})

    return True


def add_new_user(user: dict):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    user_collection = db.get_collection('user')
    user_id = user_collection.insert_one(user)

    return user_id

def authenticate_user(email: str, password: str):
    client = MongoClient(uri)

    db = client.get_database('ernest')
    user_collection = db.get_collection('user')
    user = user_collection.find_one(
        {"email": email, "password": password}
    )
    print("user: ", user)
    if user is None:
        return False
    return True

def add_vendor(vendor: dict):
    review_id_to_update = vendor.get("review_ids")[0]

    client = MongoClient(uri)
    db = client.get_database('ernest')
    vendor_collection = db.get_collection('vendor')

    if "review_ids" in vendor:
        first_review_id = vendor["review_ids"][0]
        # remove review_ids from vendor to prevent conflicts with the update operation(setOnInsert & addToSet)
        del vendor["review_ids"]
    else:
        first_review_id = None

    update_operation = {
        "$setOnInsert": vendor
    }
    if first_review_id is not None:
        update_operation["$addToSet"] = {"review_ids": first_review_id}

    result = vendor_collection.find_one_and_update(
        {"name": vendor["name"], "address": vendor["address"]},
        update_operation, 
        upsert=True, 
        return_document=ReturnDocument.AFTER
    )

    vendor_id = result.get("_id")

    # add vendor_id to the review
    review_collection = db.get_collection('review')
    review_collection.update_one(
        {"_id": review_id_to_update},
        {"$set": {"vendor_id": str(vendor_id)}}
    )
    
    return vendor_id
