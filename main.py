from typing import Annotated
from c_struct import *
from dataclasses import dataclass


print("Hello!")


@c_struct()
@dataclass
class Bella(HasBaseType):
    a: Annotated[int, CType.I32]
    b: Annotated[int, CType.U8]


t = Bella.c_get_type()
a = t.c_build(bytes([1, 0, 0, 0xFF, 2, 0, 0, 0xFF]))
