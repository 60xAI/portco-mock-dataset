"""Content JSON schemas (one per family). Validated on submit."""
from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InlineTable(M):
    columns: list[str]
    rows: list[list[Any]]
    caption: Optional[str] = None


class TableRef(M):
    table_ref: str = Field(description="PRJnnnn:table_key, e.g. PRJ0012:herg or PRJ0012:benchmark")
    max_rows: Optional[int] = None
    start_row: int = Field(0, description="skip this many data rows (e.g. 12 to show rows 13-24)")
    columns: Optional[list[int]] = Field(None, description="subset of column indexes to show")
    caption: Optional[str] = None


Table = Union[TableRef, InlineTable]


class ChartSeries(M):
    name: str
    values: list[float]


class Chart(M):
    kind: Literal["dose_response", "bar", "hbar", "scatter", "stability", "chromatogram", "line", "pie", "stacked_bar"]
    title: Optional[str] = None
    ref: Optional[str] = Field(None, description="PRJnnnn:table_key to plot from numbers (dose_response, stability, bar of a column)")
    column: Optional[int] = Field(None, description="column index to plot when ref is given")
    labels: Optional[list[str]] = None
    series: Optional[list[ChartSeries]] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None


class Image(M):
    kind: Literal["molecule_grid", "chart", "org_chart", "timeline", "logo_text"]
    ref: Optional[str] = Field(None, description="for molecule_grid: PRJnnnn (draws that project's compounds) or SERnn")
    n: int = 6
    chart: Optional[Chart] = None
    boxes: Optional[list[str]] = Field(None, description="org_chart/timeline labels, 'Parent > Child' for org charts")
    text: Optional[str] = None


Bullet = Union[str, "BulletObj"]


class BulletObj(M):
    text: str
    level: int = 0


class Slide(M):
    layout: Literal["title", "title_content", "two_content", "section", "table", "chart", "image", "title_only", "blank", "quote"]
    title: Optional[str] = None
    subtitle: Optional[str] = None
    bullets: list[Union[str, BulletObj]] = []
    bullets_right: list[Union[str, BulletObj]] = []
    table: Optional[Table] = None
    chart: Optional[Chart] = None
    image: Optional[Image] = None
    notes: Optional[str] = None
    footer: Optional[str] = None
    hidden: bool = False


class Properties(M):
    title: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    category: Optional[str] = None
    comments: Optional[str] = None


class Deck(M):
    family: Literal["deck"]
    summary: str = Field(description="2-4 sentence factual summary of the file for related files")
    properties: Properties = Properties()
    slides: list[Slide]


class CellObj(M):
    v: Any = None
    ref: Optional[str] = Field(None, description="PRJnnnn:value_key; the cell value must equal the world value")
    bold: bool = False
    italic: bool = False
    fill: Optional[str] = None
    color: Optional[str] = None
    fmt: Optional[str] = None


class DataRef(M):
    table_ref: str
    at: str = Field("A1", description="top-left cell for the header row")
    max_rows: Optional[int] = None
    columns: Optional[list[int]] = None
    header: bool = True


class CellComment(M):
    cell: str
    text: str
    author: Optional[str] = None


class Sheet(M):
    name: str
    rows: list[list[Any]] = Field([], description="cells: str|number|null|'=FORMULA'|CellObj; starts at `start`")
    start: str = "A1"
    data_refs: list[DataRef] = []
    merged: list[str] = []
    col_widths: dict[str, float] = {}
    number_formats: dict[str, str] = {}
    hidden: bool = False
    comments: list[CellComment] = []
    freeze: Optional[str] = None
    chart: Optional[Chart] = None
    chart_at: Optional[str] = None
    tab_color: Optional[str] = None


class Workbook(M):
    family: Literal["workbook"]
    summary: str
    properties: Properties = Properties()
    sheets: list[Sheet]


class Block(M):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    p: Optional[str] = None
    style: Optional[Literal["normal", "quote", "note", "small", "bold"]] = None
    items: Optional[list[Union[str, BulletObj]]] = Field(None, alias="list")
    ordered: bool = False
    table: Optional[Table] = None
    chart: Optional[Chart] = None
    image: Optional[Image] = None
    page_break: bool = False


class Section(M):
    heading: Optional[str] = None
    level: int = 1
    blocks: list[Block] = []


class TitleBlock(M):
    title: str
    subtitle: Optional[str] = None
    lines: list[str] = []


class Signature(M):
    name: str
    role: str
    date: Optional[str] = None
    signed: bool = True


class TrackedChange(M):
    find: str = Field(description="exact text that appears in one paragraph")
    insert: Optional[str] = None
    delete: bool = False
    author: str
    date: Optional[str] = None


class DocComment(M):
    anchor: str = Field(description="exact text that appears in one paragraph")
    text: str
    author: str


class Document(M):
    family: Literal["document"]
    summary: str
    properties: Properties = Properties()
    header: Optional[str] = None
    footer: Optional[str] = None
    watermark: Optional[str] = None
    title_block: Optional[TitleBlock] = None
    sections: list[Section]
    signature_block: list[Signature] = []
    appendices: list[Section] = []
    tracked_changes: list[TrackedChange] = []
    comments: list[DocComment] = []
    orientation: Literal["portrait", "landscape"] = "portrait"


class ScanSettings(M):
    skew_deg: float = Field(0.6, ge=-1.5, le=1.5)
    noise: float = Field(0.25, ge=0, le=1)
    blur: float = Field(0.5, ge=0, le=1.5)
    stamp: Optional[str] = None
    handwriting: Optional[str] = None
    pages: Optional[int] = None


class Scan(M):
    family: Literal["scan"]
    summary: str
    document: Document
    scan: ScanSettings = ScanSettings()


FAMILY_MODELS = {"deck": Deck, "workbook": Workbook, "document": Document, "scan": Scan}

BulletObj.model_rebuild()
Slide.model_rebuild()
Block.model_rebuild()


def schema_text(family: str) -> str:
    """Compact human-readable schema for packs."""
    return SCHEMA_DOCS[family]


SCHEMA_DOCS = {
"deck": """{"family":"deck","summary":"2-4 sentences","properties":{"title":"..","subject":"..","keywords":".."},
 "slides":[{"layout":"title|title_content|two_content|section|table|chart|image|title_only|blank|quote",
   "title":"..","subtitle":"..","bullets":["text",{"text":"sub-point","level":1}],"bullets_right":[..two_content only..],
   "table":{"columns":[..],"rows":[[..]]} OR {"table_ref":"PRJnnnn:key","max_rows":12,"columns":[0,4]},
   "chart":{"kind":"dose_response|bar|hbar|scatter|stability|chromatogram|line|pie|stacked_bar","title":"..","ref":"PRJnnnn:key","column":4}
          OR {"kind":"bar","labels":[..],"series":[{"name":"..","values":[..]}]},
   "image":{"kind":"molecule_grid","ref":"PRJnnnn","n":6} | {"kind":"org_chart|timeline","boxes":["A > B",..]},
   "notes":"speaker notes","footer":"..","hidden":false}]}""",
"workbook": """{"family":"workbook","summary":"2-4 sentences","properties":{"title":".."},
 "sheets":[{"name":"<=31 chars","start":"A1","rows":[["Header",..],["text",1.5,null,"=SUM(B2:B9)",{"v":"..","bold":true,"fill":"#FFFF00"},{"ref":"PRJnnnn:value_key"}]],
   "data_refs":[{"table_ref":"PRJnnnn:key","at":"A6","max_rows":null,"columns":null,"header":true}],
   "merged":["A1:F1"],"col_widths":{"A":24},"number_formats":{"C2:C50":"0.0"},"hidden":false,
   "comments":[{"cell":"B4","text":"..","author":"Firstname Surname"}],"freeze":"A2",
   "chart":{..same as deck chart..},"chart_at":"H2","tab_color":"#1F4E79"}]}""",
"document": """{"family":"document","summary":"2-4 sentences","properties":{"title":".."},"header":"..","footer":"..","watermark":"DRAFT"|null,
 "title_block":{"title":"..","subtitle":"..","lines":["Report no. ..","Date: .."]},
 "sections":[{"heading":"1 Introduction","level":1,"blocks":[{"p":"paragraph text"},{"p":"..","style":"note|quote|small|bold"},
    {"list":["a",{"text":"b","level":1}],"ordered":false},{"table":{"columns":[..],"rows":[[..]],"caption":".."}},
    {"table":{"table_ref":"PRJnnnn:key","max_rows":45,"caption":"Table 2 .."}},{"chart":{..}},{"image":{"kind":"molecule_grid","ref":"PRJnnnn","n":8}},{"page_break":true}]}],
 "signature_block":[{"name":"..","role":"..","date":"..","signed":true}],"appendices":[..sections..],
 "tracked_changes":[{"find":"exact text in a paragraph","insert":"new text","delete":false,"author":"..","date":"YYYY-MM-DD"}],
 "comments":[{"anchor":"exact text in a paragraph","text":"..","author":".."}],"orientation":"portrait|landscape"}""",
"scan": """{"family":"scan","summary":"2-4 sentences","document":{..document schema..},
 "scan":{"skew_deg":-1.5..1.5,"noise":0..1,"blur":0..1.5,"stamp":"RECEIVED 12 MAR 2004"|null,"handwriting":"short note"|null,"pages":null}}""",
}
