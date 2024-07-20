from bson import ObjectId
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, List


# ? Should I change this to pydantic BaseModel?
# ? Pydantic provides built-in to_dict() method
# ? But Pydantic requires an adjustment for MongoDB ObjectId


class Base:
    def __init__(self) -> None:
        pass

    def to_dict(self):
        """Recursively convert the object to a dictionary."""
        result_dict = {}
        primitive_types = (int, str, bool, float, bytes, ObjectId)

        for key, value in self.__dict__.items():
            if isinstance(value, primitive_types) or value is None:
                result_dict[key] = value
            elif isinstance(value, list):
                if key not in result_dict:
                    result_dict[key] = []
                for item in value:
                    if isinstance(item, primitive_types):
                        result_dict[key].append(item)
                    elif isinstance(item, Base):
                        result_dict[key].append(item.to_dict())
            elif isinstance(value, dict):
                if key not in result_dict:
                    result_dict[key] = {}
                for k, v in value.items():
                    if isinstance(v, primitive_types):
                        result_dict[key][k] = v
                    elif isinstance(v, Base):
                        result_dict[key][k] = v.to_dict()
            elif isinstance(value, datetime):
                result_dict[key] = value.isoformat()
            else:
                result_dict[key] = value.to_dict()

        return result_dict


class ParallelState(Base):
    pending_items: list

    def __init__(self):
        self.pending_items = []


class StateItem:
    attribute: str
    key: str
    value: Any

    def __init__(self, attribute: str, key: str, value: Any):
        self.attribute = attribute
        self.key = key
        self.value = value


class Reply:
    reaction: str
    question: str


class State(Base):
    reply_message: StateItem
    candidate_reply_message: Reply
    context: StateItem
    criticizm: StateItem
    instruction: StateItem
    missing_details: List[str]
    stories: List[str]
    tournament: dict[str, Any]
    ui_type: str

    def __init__(self, **kwargs):
        self.tournament = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)


class Role(str, Enum):
    USER = "user"
    AI = "assistant"


# There is no id for message. We use order of the message in the conversation to identify it. In order to keep the order, we never delete messages. We just mark them as deleted.
class Message(Base):
    role: Role
    content: str
    created_at: str
    deleted: bool

    def __init__(self, role: Role, content: str, **kwargs):
        self.role = Role(role)
        self.content = content
        self.created_at = datetime.now().isoformat()
        self.deleted = False
        for key, value in kwargs.items():
            setattr(self, key, value)


class Report(Base):
    title: str
    content: str
    relevant_msg_orders: list[int]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Payment(Base):
    item_name: str
    amount: float
    currency: str
    paid_at: str

    def __init__(self, item_name: str, amount: float, **kwargs):
        self.item_name = item_name
        self.amount = amount
        self.currency = "CAD"
        self.paid_at = datetime.now().isoformat()
        for key, value in kwargs.items():
            setattr(self, key, value)


class Review(Base):
    _id: ObjectId
    user_id: ObjectId
    vendor_id: ObjectId
    payment_info: list[Payment]
    messages: list[Message]
    reports: list[Report]
    created_at: str
    state: State
    story: str
    title: str

    def __init__(self, user_id: str, **kwargs):
        self.user_id = user_id
        self.vendor_id = None
        self.payment_info = []
        self.messages = []
        self.reports = []
        self.created_at = datetime.now().isoformat()
        self.state = State()
        self.story = ""
        self.title = ""
        for key, value in kwargs.items():
            if key == "messages":
                messages = []
                for item in value:
                    messages.append(Message(**item))
                setattr(self, key, messages)
            elif key == "payment_info":
                payments = []
                for item in value:
                    payments.append(Payment(**item))
                setattr(self, key, payments)
            elif key == "reports":
                reports = []
                for item in value:
                    reports.append(Report(**item))
                setattr(self, key, reports)
            elif key == "state":
                setattr(self, key, State(**value))
            else:
                setattr(self, key, value)


class Bio(Base):
    title: str
    content: str
    reference: list[
        (ObjectId, int)
    ]  # first element is the review id, second element is the message order

    def __init__(self, title: str, content: str, **kwargs):
        self.title = title
        self.content = content
        self.reference = []
        for key, value in kwargs.items():
            setattr(self, key, value)


class User(Base):
    _id: ObjectId
    name: str
    pronouns: str
    email: str
    password: str
    username: str
    created_at: str
    updated_at: str
    review_ids: list[ObjectId]
    bios: list[Bio]

    def __init__(self, **kwargs):
        self._id = ObjectId()
        self.name = None
        self.email = None
        self.password = None
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.review_ids = []
        self.bios = []
        # self.username = None
        # self.pronouns = None
        for key, value in kwargs.items():
            if key == "bios":
                bios = []
                for item in value:
                    bios.append(Bio(**item))
                setattr(self, key, bios)
            else:
                setattr(self, key, value)


class Vendor(Base):
    _id: ObjectId
    name: str
    address: str
    created_at: str
    updated_at: str
    review_ids: list[ObjectId]

    def __init__(self, **kwargs):
        self.name = None
        self.address = None
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.review_ids = []
        for key, value in kwargs.items():
            setattr(self, key, value)
