from datetime import datetime
from enum import IntEnum

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, conlist, Field, root_validator, validator


class VIA3_ATTRIBUTES(IntEnum):
    TEXT = 1
    RADIO = 3
    SELECT = 4


class VIA3_FILE_TYPE(IntEnum):
    IMAGE = 2
    VIDEO = 4
    AUDIO = 8


class VIA3_FILE_SOURCE_TYPE(IntEnum):
    LOCAL = 1
    URIHTTP = 2
    URIFILE = 3
    INLINE = 4


class VIA3_SHAPE(IntEnum):
    RECT = 2


class VIA_ATTRIBUTE(BaseModel):
    aname: str
    anchor_id: Literal["FILE1_Z0_XY1", "FILE1_Z2_XY0"]
    type: Literal[1, 3, 4] = 1
    desc: str = ""
    options = {}
    default_option_id = ""


class VIA_METADATA(BaseModel):
    vid: str
    flg: int = 0
    z: List[float] = []
    xy: List[Union[float, int]] = []
    av: Dict[str, Union[str, int]]

    @validator("z")
    def validate_z(cls, v):
        if not v:
            return []

        if len(v) > 2:
            raise ValueError(
                "z metadata, if provided, cannot have more than two values"
            )

        return v

    @validator("xy")
    def validate_xy(cls, v):
        if not v:
            return []

        if len(v) != 5:
            raise ValueError("xy metadata, if provided, must have 5 values")

        supported_shapes = [x.value for x in VIA3_SHAPE]
        supported_shape_names = [x.name for x in VIA3_SHAPE]
        if v[0] not in supported_shapes:
            raise ValueError(
                f"Metadata other than {supported_shape_names} are not supported"
            )

        return v


class VIA_VIEW(BaseModel):
    fid_list: List[str]


class VIA_PROJECT(BaseModel):
    pid: str = "__VIA_PROJECT_ID__"
    rev: str = "__VIA_PROJECT_REV_ID__"
    rev_timestamp: Union[str, datetime] = "__VIA_PROJECT_REV_TIMESTAMP__"
    pname: str = ""
    creator: str = ""
    created: Optional[datetime] = None
    data_format_version: str = "3.1.0"
    vid_list: List[str] = []

    class Config:
        json_encoders = {datetime: lambda v: round(v.timestamp())}

    @validator("created", pre=True, always=True)
    def add_created(cls, v):
        return v or datetime.utcnow()


class VIA_FILE_CONFIG(BaseModel):
    loc_prefix: Dict[Literal["1", "2", "3", "4"], str] = {
        "1": "",
        "2": "",
        "3": "",
        "4": "",
    }


class VIA_CONFIG(BaseModel):
    file = VIA_FILE_CONFIG()
    ui = {}


class VIA_FILE(BaseModel):
    fid: str
    fname: str
    type: VIA3_FILE_TYPE
    loc: VIA3_FILE_SOURCE_TYPE
    src: str


class VIA3_ANNOTATION(BaseModel):
    project: VIA_PROJECT
    config: VIA_CONFIG = VIA_CONFIG()
    attribute: Dict[str, VIA_ATTRIBUTE]
    file: Dict[str, VIA_FILE]
    view: Dict[str, VIA_VIEW]
    metadata: Dict[str, VIA_METADATA]

    class Config:
        use_enum_values = True

    @root_validator
    def validate_all(cls, values):

        # metadata vid must map to some fid, else ignore
        vid_to_fid = {k: v.fid_list[0] for k, v in values.get("view").items()}
        fid_list = values.get("file").keys()
        attribute_list = values.get("attribute").keys()

        metadata = values.get("metadata")
        invalid_metadata = [
            k
            for k, x in metadata.items()
            if (x.vid not in vid_to_fid or vid_to_fid[x.vid] not in fid_list)
        ]
        for k in invalid_metadata:
            del metadata[k]

        # Ignore metadata that are not listed as attributes
        for k, m in metadata.items():
            invalid_attributes = [av for av in m.av.keys() if av not in attribute_list]
            for invalid_av in invalid_attributes:
                del m.av[invalid_av]

        # TODO For type radio and select, the value must be in attribute options

        # TODO Attribute values must match attribute type

        return values

    @property
    def vid_to_fid(self):
        return {k: v.fid_list[0] for k, v in self.view.items()}
