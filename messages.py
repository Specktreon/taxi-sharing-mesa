"""Lightweight messages exchanged between passengers and taxis.

Mesa has no built-in agent messaging, so this module defines a minimal
Message record. The model delivers a message by appending it to the
receiver's inbox (see TaxiModel.send).

Protocol (one round per simulated minute, similar to Contract Net):
    passenger --REQUEST--> every taxi      (call for proposals)
    taxi      --PROPOSE--> passenger       (estimated pickup time, can_accept)
    passenger --ACCEPT---> best taxi       (lowest estimated pickup time)
    taxi      --CONFIRM/REJECT--> passenger
"""

from dataclasses import dataclass, field

REQUEST = "REQUEST"
PROPOSE = "PROPOSE"
ACCEPT = "ACCEPT"
CONFIRM = "CONFIRM"
REJECT = "REJECT"


@dataclass
class Message:
    sender: int  # unique_id of the sending agent
    receiver: int  # unique_id of the receiving agent
    type: str  # one of the constants above
    data: dict = field(default_factory=dict)
    time: int = 0  # simulation minute when sent
