from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Union

from .activity import Activity
from .base import COMMON_SCHEMA_ORDER
from .base import DEFAULT_LANG
from .base import SchemaBase


class Protocol(SchemaBase):
    """
    class to deal with reproschema protocols
    """

    def __init__(
        self,
        name: Optional[str] = "protocol",
        schemaVersion: Optional[str] = None,
        prefLabel: Optional[str] = "protocol",
        altLabel: Optional[Dict[str, str]] = None,
        description: Optional[str] = "",
        preamble: Optional[str] = None,
        landingPage: Optional[dict] = None,
        citation: Optional[str] = None,
        image: Optional[Union[str, Dict[str, str]]] = None,
        messages: Optional[Dict[str, str]] = None,
        suffix: Optional[str] = "_schema",
        ext: Optional[str] = ".jsonld",
        output_dir: Optional[Union[str, Path]] = Path.cwd(),
        lang: Optional[str] = DEFAULT_LANG(),
    ):

        schema_order = COMMON_SCHEMA_ORDER() + [
            "landingPage",
            "citation",
            "compute",
            "messages",
        ]

        super().__init__(
            at_id=name,
            at_type="reproschema:Protocol",
            schemaVersion=schemaVersion,
            prefLabel={lang: prefLabel},
            altLabel=altLabel,
            description=description,
            landingPage=landingPage,
            preamble=preamble,
            citation=citation,
            messages=messages,
            image=image,
            schema_order=schema_order,
            suffix=suffix,
            ext=ext,
            output_dir=output_dir,
            lang=lang,
        )
        self.ui.shuffle = False
        self.update()

    def append_activity(self, activity: Activity):
        self.ui.append(
            obj=activity, variableName=activity.get_basename().replace("_schema", "")
        )
