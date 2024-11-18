from dataclasses import dataclass, field
from enum import Enum
from typing import List

class Etat(Enum):
    ACCEPTED = "ACCEPTED"
    MESSAGE1 = "1ST"
    MESSAGE2 = "2ND"
    MESSAGE3 = "3RD"
    ON_HOLD = "ON HOLD"
    FAILURE = "FAILURE"
    REFUSED = "REFUSED"
    END = "END"
    SENT = "SENT"
    SUCCESS = "SUCCESS"
    NOT_SENT = "NOT SENT"

    def __init__(self, value):
        self._value_ = value

    @property
    def number(self):
        return list(Etat).index(self) + 1

    def suivant(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self)
        if index + 1 < len(members):
            return members[index + 1]
        else:
            return None  # or members[0] if you want to loop back to the beginning

    @classmethod
    def from_number(cls, number):
        if 1 <= number <= len(cls):
            return list(cls)[number - 1]
        else:
            raise ValueError("Numéro invalide")

class EtatObj(Enum):
    FAIL = 1
    RUNNING = 3
    STOP = 4

@dataclass(frozen=True)
class Prospect:
    ID : int
    nom : str 
    lien : str
    corp : str

@dataclass()
class MessageObj:
    ID : int
    corp : str 
    jour : int 
    statut : Etat
    prospect: List[dict] = field(default_factory=list)
