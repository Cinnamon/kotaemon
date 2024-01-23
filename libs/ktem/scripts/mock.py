import time

from ktem.db.models import Conversation, Source, engine
from sqlmodel import Session


def add_conversation():
    """Add conversation to the manager."""
    with Session(engine) as session:
        c1 = Conversation(name="Conversation 1")
        c2 = Conversation()
        session.add(c1)
        time.sleep(1)
        session.add(c2)
        time.sleep(1)
        session.commit()


def add_files():
    with Session(engine) as session:
        s1 = Source(name="Source 1", path="Path 1")
        s2 = Source(name="Source 2", path="Path 2")
        session.add(s1)
        session.add(s2)
        session.commit()


# add_conversation()
add_files()
