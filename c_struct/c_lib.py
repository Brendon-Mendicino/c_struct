from dataclasses import Field, dataclass, fields, is_dataclass
from itertools import islice
from typing import Callable, Literal

from .c_types import BaseType, HasBaseType, CPadding


def _get_origin(t: type) -> type:
    return getattr(t, "__origin__", t)


def _get_metadata(t: type) -> tuple | None:
    return getattr(t, "__metadata__", None)


def _get_ctype(t: Field) -> BaseType | None:
    origin = _get_origin(t.type)
    metadata = _get_metadata(t.type) or tuple()

    # The metadata can override the base type if requested
    for t in metadata:
        if isinstance(t, HasBaseType):
            return t.c_get_type()

        if isinstance(t, BaseType):
            return t

    # Metadata has precedence over the origin type
    if isinstance(origin, BaseType):
        return origin

    if isinstance(origin, HasBaseType):
        return origin.c_get_type()

    return None


def _types_from_dataclass(cls: type) -> list[BaseType]:
    ctypes = list[BaseType]()

    for field in fields(cls):
        ctype = _get_ctype(field)

        if ctype is None:
            raise ValueError(
                f"The field of the class is not annotated with a Type, nor the orgigin is a Type! {cls=} {field=}"
            )

        ctypes.append(ctype)

    return ctypes


@dataclass
class _Pipeline:
    pipeline: list[BaseType]
    size: int
    align: int


@dataclass
class _StructTypeHandler[T]:
    """StructTypeHandler"""

    pipeline: _Pipeline
    cls: type[T]

    def c_size(self) -> int:
        return self.pipeline.size

    def c_align(self) -> int:
        return self.pipeline.size

    def c_signed(self) -> bool:
        raise NotImplementedError()

    def c_build(
        self,
        raw: bytes,
        *,
        byteorder: Literal["little", "big"] = "little",
        signed: bool | None = None,
    ) -> T:
        # TODO: handle byteorder, signed, size, align

        raw_slice = islice(raw, None)
        cls_items = []

        for pipe_item in self.pipeline.pipeline:
            raw_bytes = islice(raw_slice, pipe_item.c_size())

            cls_item = pipe_item.c_build(
                bytes(raw_bytes),
                byteorder=byteorder,
                signed=signed,
            )

            print(f"{cls_item}")
            if cls_item is not None:
                cls_items.append(cls_item)

        print(cls_items)

        return self.cls(*cls_items)


def _build_pipeline(ctypes: list[BaseType]):
    pipeline = list[BaseType]()
    current_size = 0
    current_align = 0

    for ctype in ctypes:
        padding = -current_size % ctype.c_align()

        if padding != 0:
            pipeline.append(CPadding(padding))

        current_align = max(current_align, ctype.c_align())
        current_size += ctype.c_size()
        pipeline.append(ctype)

    return _Pipeline(pipeline, current_size, current_align)


def _c_struct[T](cls: type[T], align: int | None) -> type[T]:
    if not is_dataclass(cls):
        cls = dataclass(cls)

    if not is_dataclass(cls):
        raise ValueError(
            f"{cls=} is not a dataclass! {cls=} must be a dataclass in order to use c_struct."
        )

    ctypes = _types_from_dataclass(cls)

    pipeline = _build_pipeline(ctypes)

    @classmethod
    def c_get_type(self):
        _ = self
        return _StructTypeHandler(pipeline, cls)

    setattr(cls, "c_get_type", c_get_type)

    return cls


def c_struct[T](*, align: int | None = None) -> Callable[[T], T]:
    def c_struct_inner(cls: type[T]):
        return _c_struct(cls, align)

    return c_struct_inner
