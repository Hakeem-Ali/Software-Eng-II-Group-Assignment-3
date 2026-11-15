"""Render Class Diagram PNG with Windows GDI+ (no extra packages)."""

from __future__ import annotations

import ctypes
from ctypes import POINTER, byref, c_float, c_int, c_uint, c_void_p, c_wchar_p
from pathlib import Path

ARGB_WHITE = 0xFFFFFFFF
ARGB_BLACK = 0xFF000000
OK = 0


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class StartupInput(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", ctypes.c_uint32),
        ("DebugEventCallback", c_void_p),
        ("SuppressBackgroundThread", ctypes.c_int),
        ("SuppressExternalCodecs", ctypes.c_int),
    ]


class PointF(ctypes.Structure):
    _fields_ = [("X", c_float), ("Y", c_float)]


class RectF(ctypes.Structure):
    _fields_ = [("X", c_float), ("Y", c_float), ("Width", c_float), ("Height", c_float)]


PNG_CLSID = GUID(0x557CF406, 0x1A04, 0x11D3, (0x9A, 0x73, 0x00, 0x00, 0xF8, 0x1E, 0xF3, 0x2E))

gdiplus = ctypes.windll.gdiplus


def _chk(status: int, what: str) -> None:
    if status != OK:
        raise RuntimeError(f"GDI+ {what} failed: {status}")


class Gdi:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.token = ctypes.c_ulong()
        inp = StartupInput(1, None, 0, 0)
        _chk(gdiplus.GdiplusStartup(byref(self.token), byref(inp), None), "startup")
        self.bitmap = c_void_p()
        _chk(
            gdiplus.GdipCreateBitmapFromScan0(
                width, height, 0, 0x26200A, None, byref(self.bitmap)
            ),
            "bitmap",
        )
        self.graphics = c_void_p()
        _chk(gdiplus.GdipGetImageGraphicsContext(self.bitmap, byref(self.graphics)), "gfx")
        _chk(gdiplus.GdipSetSmoothingMode(self.graphics, 4), "smooth")
        _chk(gdiplus.GdipSetTextRenderingHint(self.graphics, 4), "text")
        _chk(gdiplus.GdipGraphicsClear(self.graphics, ARGB_WHITE), "clear")
        self._pens: dict[tuple[float, bool], c_void_p] = {}
        self._fonts: dict[tuple[str, float, int], c_void_p] = {}
        self._families: dict[str, c_void_p] = {}
        self.brush = c_void_p()
        _chk(gdiplus.GdipCreateSolidFill(ARGB_BLACK, byref(self.brush)), "brush")
        self.white = c_void_p()
        _chk(gdiplus.GdipCreateSolidFill(ARGB_WHITE, byref(self.white)), "white")
        self.fmt = c_void_p()
        _chk(gdiplus.GdipCreateStringFormat(0, 0, byref(self.fmt)), "fmt")
        # StringAlignmentCenter = 1 for horizontal when needed
        self.fmt_center = c_void_p()
        _chk(gdiplus.GdipCreateStringFormat(0, 0, byref(self.fmt_center)), "fmtc")
        gdiplus.GdipSetStringFormatAlign(self.fmt_center, 1)
        gdiplus.GdipSetStringFormatLineAlign(self.fmt_center, 1)

    def pen(self, width: float = 1.2, dashed: bool = False) -> c_void_p:
        key = (width, dashed)
        if key not in self._pens:
            p = c_void_p()
            _chk(gdiplus.GdipCreatePen1(ARGB_BLACK, c_float(width), 0, byref(p)), "pen")
            if dashed:
                gdiplus.GdipSetPenDashStyle(p, 1)
            self._pens[key] = p
        return self._pens[key]

    def font(self, size: float, bold: bool = False, family: str = "Segoe UI") -> c_void_p:
        style = 1 if bold else 0
        key = (family, size, style)
        if key not in self._fonts:
            if family not in self._families:
                fam = c_void_p()
                _chk(
                    gdiplus.GdipCreateFontFamilyFromName(
                        c_wchar_p(family), None, byref(fam)
                    ),
                    "family",
                )
                self._families[family] = fam
            f = c_void_p()
            _chk(
                gdiplus.GdipCreateFont(
                    self._families[family], c_float(size), style, 2, byref(f)
                ),
                "font",
            )
            self._fonts[key] = f
        return self._fonts[key]

    def text_size(self, text: str, size: float, bold: bool = False) -> tuple[float, float]:
        layout = RectF(0, 0, 4000, 400)
        bounding = RectF()
        _chk(
            gdiplus.GdipMeasureString(
                self.graphics,
                c_wchar_p(text),
                len(text),
                self.font(size, bold),
                byref(layout),
                self.fmt,
                byref(bounding),
                None,
                None,
            ),
            "measure",
        )
        return bounding.Width, bounding.Height

    def draw_text(
        self,
        x: float,
        y: float,
        text: str,
        size: float = 11,
        bold: bool = False,
        center_w: float | None = None,
    ) -> None:
        if center_w is not None:
            tw, th = self.text_size(text, size, bold)
            x = x + (center_w - tw) / 2
        rect = RectF(x, y, 1800, 80)
        _chk(
            gdiplus.GdipDrawString(
                self.graphics,
                c_wchar_p(text),
                len(text),
                self.font(size, bold),
                byref(rect),
                self.fmt,
                self.brush,
            ),
            "string",
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        dashed: bool = False,
        width: float = 1.2,
    ) -> None:
        _chk(
            gdiplus.GdipDrawLine(
                self.graphics,
                self.pen(width, dashed),
                c_float(x1),
                c_float(y1),
                c_float(x2),
                c_float(y2),
            ),
            "line",
        )

    def fill_rect(self, x: float, y: float, w: float, h: float) -> None:
        _chk(
            gdiplus.GdipFillRectangle(
                self.graphics, self.white, c_float(x), c_float(y), c_float(w), c_float(h)
            ),
            "fillrect",
        )

    def rectangle(self, x: float, y: float, w: float, h: float, width: float = 1.2) -> None:
        _chk(
            gdiplus.GdipFillRectangle(
                self.graphics, self.white, c_float(x), c_float(y), c_float(w), c_float(h)
            ),
            "fill",
        )
        _chk(
            gdiplus.GdipDrawRectangle(
                self.graphics,
                self.pen(width),
                c_float(x),
                c_float(y),
                c_float(w),
                c_float(h),
            ),
            "rect",
        )

    def polygon(self, pts: list[tuple[float, float]], fill_white: bool = True) -> None:
        arr = (PointF * len(pts))(*[PointF(p[0], p[1]) for p in pts])
        if fill_white:
            _chk(
                gdiplus.GdipFillPolygon(
                    self.graphics, self.white, arr, len(pts), 0
                ),
                "fillpoly",
            )
        _chk(
            gdiplus.GdipDrawPolygon(self.graphics, self.pen(1.2), arr, len(pts)),
            "poly",
        )

    def diamond(self, x: float, y: float, r: float = 7, filled: bool = False) -> None:
        pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
        arr = (PointF * 4)(*[PointF(p[0], p[1]) for p in pts])
        brush = self.brush if filled else self.white
        _chk(gdiplus.GdipFillPolygon(self.graphics, brush, arr, 4, 0), "diafill")
        _chk(gdiplus.GdipDrawPolygon(self.graphics, self.pen(1.2), arr, 4), "dia")

    def save(self, path: Path) -> None:
        _chk(
            gdiplus.GdipSaveImageToFile(
                self.bitmap, c_wchar_p(str(path)), byref(PNG_CLSID), None
            ),
            "save",
        )


def class_box(
    g: Gdi,
    x: float,
    y: float,
    w: float,
    title: str,
    stereo: str | None,
    attrs: list[str],
    methods: list[str],
    line_h: float = 19,
) -> tuple[float, float, float, float]:
    pad = 7
    header_h = 26 + (18 if stereo else 0)
    body_lines = (attrs or []) + (methods or [])
    n_div = 0
    if attrs:
        n_div += 1
    if methods:
        n_div += 1
    h = pad + header_h + n_div * 2 + len(body_lines) * line_h + pad + 4
    if not body_lines:
        h = pad + header_h + pad
    g.rectangle(x, y, w, h)
    cy = y + 4
    if stereo:
        g.draw_text(x, cy, stereo, 10, center_w=w)
        cy += 18
    g.draw_text(x, cy, title, 13, bold=True, center_w=w)
    cy = y + header_h
    if attrs:
        g.line(x, cy, x + w, cy)
        cy += 3
        for a in attrs:
            g.draw_text(x + 8, cy, a, 11)
            cy += line_h
    if methods:
        g.line(x, cy, x + w, cy)
        cy += 3
        for m in methods:
            g.draw_text(x + 8, cy, m, 11)
            cy += line_h
    return x, y, w, h


def draw_label(g: Gdi, x: float, y: float, text: str, size: float = 10) -> None:
    tw, th = g.text_size(text, size)
    g.fill_rect(x - 2, y - 1, tw + 4, th + 2)
    g.draw_text(x, y, text, size)


def cx(box: tuple[float, float, float, float]) -> float:
    return box[0] + box[2] / 2


def cy(box: tuple[float, float, float, float]) -> float:
    return box[1] + box[3] / 2


def top(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return cx(box), box[1]


def bottom(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return cx(box), box[1] + box[3]


def left(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return box[0], cy(box)


def right(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return box[0] + box[2], cy(box)


def arrow_open(g: Gdi, x: float, y: float, dx: float, dy: float) -> None:
    # open arrowhead at (x,y) pointing along (dx,dy) unit-ish
    import math

    ang = math.atan2(dy, dx)
    a = 0.45
    L = 10
    x1 = x - L * math.cos(ang - a)
    y1 = y - L * math.sin(ang - a)
    x2 = x - L * math.cos(ang + a)
    y2 = y - L * math.sin(ang + a)
    g.line(x, y, x1, y1)
    g.line(x, y, x2, y2)


def hollow_triangle(g: Gdi, tip: tuple[float, float], base_dir: str) -> None:
    tx, ty = tip
    s = 9
    if base_dir == "down":
        pts = [(tx, ty), (tx - s, ty + 14), (tx + s, ty + 14)]
    elif base_dir == "up":
        pts = [(tx, ty), (tx - s, ty - 14), (tx + s, ty - 14)]
    elif base_dir == "left":
        pts = [(tx, ty), (tx - 14, ty - s), (tx - 14, ty + s)]
    else:
        pts = [(tx, ty), (tx + 14, ty - s), (tx + 14, ty + s)]
    g.polygon(pts, fill_white=True)


def finish_head(
    g: Gdi,
    p1: tuple[float, float],
    p2: tuple[float, float],
    kind: str,
) -> tuple[float, float]:
    """Return the line endpoint, drawing an arrow/triangle at p2 if needed."""
    x2, y2 = p2
    dx, dy = x2 - p1[0], y2 - p1[1]
    if kind in {"gen", "real"}:
        if abs(dx) >= abs(dy):
            hollow_triangle(g, p2, "left" if dx > 0 else "right")
            return (x2 - (14 if dx > 0 else -14), y2)
        hollow_triangle(g, p2, "down" if dy < 0 else "up")
        return (x2, y2 + (14 if dy < 0 else -14))
    if kind in {"dep", "create"}:
        arrow_open(g, x2, y2, dx if dx else 0, dy if dy else 1)
    return p2


def vline(
    g: Gdi,
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    kind: str = "assoc",
    label: str | None = None,
) -> None:
    p1 = bottom(a)
    p2 = top(b)
    end = finish_head(g, p1, p2, kind)
    dashed = kind in {"dep", "real", "create"}
    g.line(p1[0], p1[1], p1[0], (p1[1] + end[1]) / 2, dashed=dashed)
    g.line(p1[0], (p1[1] + end[1]) / 2, end[0], (p1[1] + end[1]) / 2, dashed=dashed)
    g.line(end[0], (p1[1] + end[1]) / 2, end[0], end[1], dashed=dashed)
    if label:
        draw_label(g, min(p1[0], end[0]) + 6, (p1[1] + end[1]) / 2 - 8, label)


def hline(
    g: Gdi,
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    kind: str = "assoc",
    label: str | None = None,
    from_side: str = "right",
) -> None:
    p1 = right(a) if from_side == "right" else left(a)
    p2 = left(b) if from_side == "right" else right(b)
    end = finish_head(g, p1, p2, kind)
    dashed = kind in {"dep", "real", "create"}
    g.line(p1[0], p1[1], end[0], end[1], dashed=dashed)
    if label:
        draw_label(g, (p1[0] + end[0]) / 2 - 24, p1[1] - 17, label)


def poly(
    g: Gdi,
    pts: list[tuple[float, float]],
    kind: str = "assoc",
    label: str | None = None,
    label_at: tuple[float, float] | None = None,
) -> None:
    dashed = kind in {"dep", "real", "create"}
    end = finish_head(g, pts[-2], pts[-1], kind)
    route = pts[:-1] + [end]
    for i in range(len(route) - 1):
        g.line(route[i][0], route[i][1], route[i + 1][0], route[i + 1][1], dashed=dashed)
    if label:
        lx, ly = label_at or route[len(route) // 2]
        draw_label(g, lx + 4, ly - 14, label)


def elbow(
    g: Gdi,
    p1: tuple[float, float],
    p2: tuple[float, float],
    kind: str = "assoc",
    via_y: float | None = None,
    via_x: float | None = None,
    label: str | None = None,
    label_at: tuple[float, float] | None = None,
) -> None:
    pts: list[tuple[float, float]] = [p1]
    if via_y is not None and via_x is not None:
        pts += [(via_x, p1[1]), (via_x, via_y), (p2[0], via_y), p2]
    elif via_y is not None:
        pts += [(p1[0], via_y), (p2[0], via_y), p2]
    elif via_x is not None:
        pts += [(via_x, p1[1]), (via_x, p2[1]), p2]
    else:
        pts += [p2]
    poly(g, pts, kind, label, label_at)


def note_box(g: Gdi, x: float, y: float, w: float, lines: list[str], title: str | None = None) -> tuple:
    line_h = 19
    h = 10 + (20 if title else 0) + len(lines) * line_h + 8
    g.rectangle(x, y, w, h)
    # dog-ear
    ear = 12
    g.line(x + w - ear, y, x + w - ear, y + ear)
    g.line(x + w - ear, y + ear, x + w, y + ear)
    g.line(x + w - ear, y, x + w, y + ear)
    cy_ = y + 6
    if title:
        g.draw_text(x + 8, cy_, title, 12, bold=True)
        cy_ += 20
    for ln in lines:
        g.draw_text(x + 8, cy_, ln, 11)
        cy_ += line_h
    return x, y, w, h


def render(path: Path) -> None:
    W, H = 3000, 1820
    g = Gdi(W, H)
    g.draw_text(0, 14, "Class Diagram", 28, bold=True, center_w=W)
    g.draw_text(
        0,
        52,
        "Application lifecycle tracking \u2014 inherited procedural tracker vs proposed State-pattern redesign",
        12,
        center_w=W,
    )

    g.rectangle(20, 86, 740, 1704, width=1.6)
    g.rectangle(800, 86, 2180, 1704, width=1.6)
    g.draw_text(36, 96, "Before: inherited structure (lifecycle.py)", 14, bold=True)
    g.draw_text(816, 96, "After: State pattern redesign", 14, bold=True)
    g.draw_text(816, 120, "routes -> services -> repositories -> models", 11)

    # ---------------------------------------------------------------- BEFORE
    life = class_box(
        g,
        40,
        150,
        620,
        "lifecycle  (procedural module)",
        "<<module  app.services.lifecycle>>",
        ["ACTIONS : tuple  {mark_reviewed, shortlist, reject, hire, reopen}"],
        [
            "+ snapshot(app) : dict",
            "+ apply_action(app, action) : dict",
            "+ derived_status_from_flags(app) : str",
        ],
    )
    app_old = class_box(
        g,
        40,
        360,
        620,
        "Application",
        "<<model  app.models.application>>",
        [
            "+ id : int",
            "+ listing_id : int",
            "+ graduate_id : int",
            "+ cover_letter : str",
            "+ resume_text : str",
            "+ status : str",
            "+ flag_reviewed : int",
            "+ flag_shortlisted : int",
            "+ flag_rejected : int",
            "+ flag_hired : int",
        ],
        [],
    )
    trans_old = class_box(
        g,
        40,
        680,
        620,
        "applications.transition_application()",
        "<<service  app.services.applications>>",
        ["actor_id : int", "application_id : int", "action : str"],
        [
            "+ allows role in {employer, admin}",
            "+ does not check listing.employer_id",
            "+ writes status AND four flags",
        ],
    )
    vline(g, life, app_old, "dep", "mutates status + flags")
    poly(
        g,
        [(610, 680), (610, bottom(app_old)[1])],
        "dep",
        "persist flags",
        (618, 638),
    )
    elbow(
        g,
        (right(trans_old)[0], cy(trans_old)),
        (right(life)[0], cy(life)),
        "dep",
        via_x=720,
        label="apply_action()",
        label_at=(664, 198),
    )

    note_box(
        g,
        40,
        980,
        620,
        [
            "Nested if/elif on mixed status + boolean flags.",
            "Illegal jumps: submitted -> hired / shortlisted.",
            "reject does not clear flag_shortlisted.",
            "hire does not clear flag_rejected.",
            "reopen sets status=submitted, leaves terminal flags.",
            "derived_status_from_flags() disagrees with status.",
            "Silent no-op on some illegal actions (changed=False).",
            "Admin or any employer may change any application.",
            "No ApplicationHistory (audit) rows.",
            "No notification to the graduate on status change.",
            "Applicants can see conflicting labels vs flags.",
            "reopen is an undefined escape hatch.",
        ],
        title="Defects to replace",
    )
    note_box(
        g,
        40,
        1330,
        620,
        [
            "Generalization   solid line, hollow triangle",
            "Association      solid line, role + multiplicities",
            "Dependency       dashed line, open arrow",
            "Creation         dashed dependency labelled <<create>>",
            "Derived method   shown as is_active() on Application",
        ],
        title="Relationship legend",
    )
    note_box(
        g,
        40,
        1560,
        620,
        [
            "Revised from the stakeholder interview transcript (Q1-Q22),",
            "ASSIGNMENT.md (State pattern) and docs/ACCEPTANCE.md",
            "(AC 8-13). Every change is tied to its transcript point",
            "in docs/diagrams/changes.md.",
            "PNG rendered by the repo's GDI+ renderer; PlantUML is",
            "not installed, so the .puml is the structural source.",
        ],
        title="Sources",
    )

    # ----------------------------------------------------------------- AFTER
    router = class_box(
        g,
        820,
        150,
        400,
        "BoardRouter",
        "<<route  app.routers.board>>",
        [],
        [
            "+ POST /applications/{id}/transition",
            "+ POST /applications/{id}/reopen  ' admin only",
        ],
    )
    app_svc = class_box(
        g,
        820,
        300,
        400,
        "ApplicationService",
        "<<service  app.services.applications>>",
        [],
        [
            "+ transition_application(...)  ' delegates",
            "+ apply(...) starts at SubmittedState",
            "+ read_application(actor, app_id)",
            "+ list_applicants(actor, listing_id)",
            "+ my_active(graduate_id) : list",
            "+ my_history(graduate_id) : list",
        ],
    )
    life_svc = class_box(
        g,
        1260,
        300,
        400,
        "LifecycleService",
        "<<service  app.services.lifecycle>>",
        [],
        [
            "+ apply_transition(actor, app_id, action)",
            "+ reopen(actor, app_id)  ' admin only",
            "- persist_status()",
            "- record_history()",
            "- notify_applicant()",
        ],
    )
    policy = class_box(
        g,
        1780,
        300,
        380,
        "ListingOwnerPolicy",
        "<<service>>",
        [],
        [
            "+ can_advance(actor, listing) : bool",
            "+ can_read(actor, application) : bool",
            "+ can_list(actor, listing) : bool",
            "employer only; not admin; not other employers",
            "AC 12 covers advancing, not reopening",
        ],
    )
    reopen = class_box(
        g,
        2200,
        300,
        360,
        "ReopenPolicy",
        "<<service>>",
        [],
        [
            "+ can_reopen(actor) : bool",
            "administrator only: staff correction",
            "checked separately from employer advance",
        ],
    )
    notif_svc = class_box(
        g,
        2600,
        300,
        330,
        "NotificationService",
        "<<service>>",
        [],
        [
            "+ notify_status_change(user_id, app, status)",
            "- compose_text(status) : str",
            "email primary; on-platform optional",
        ],
    )

    app_new = class_box(
        g,
        860,
        550,
        400,
        "Application",
        "<<model / context>>",
        [
            "+ id : int",
            "+ listing_id : int",
            "+ graduate_id : int",
            "+ cover_letter : str",
            "+ resume_text : str",
            "+ status : str  {single source of truth}",
        ],
        [
            "+ current_state() : ApplicationState",
            "+ apply(action) : str  ' thin: store handle(action) name",
            "+ is_active() : bool  ' derived from current state",
        ],
    )
    iface = class_box(
        g,
        1360,
        550,
        420,
        "ApplicationState",
        "<<abstract>>",
        [],
        [
            "+ name() : str",
            "+ allowed_actions() : FrozenSet[str]",
            "+ handle(action) : ApplicationState",
            "+ is_active() : bool",
        ],
    )
    repo = class_box(
        g,
        1800,
        550,
        380,
        "ApplicationRepository",
        "<<repository>>",
        [],
        [
            "+ get(id) : Application",
            "+ save(app) : Application",
            "+ add_history(row) : ApplicationHistory",
        ],
    )
    factory = class_box(
        g,
        2220,
        550,
        340,
        "StateFactory",
        "<<factory>>",
        [],
        ["+ from_status(status) : ApplicationState"],
    )
    unauth = class_box(
        g,
        2580,
        550,
        330,
        "UnauthorizedTransitionError",
        "<<exception>>",
        [],
        ["listing employer only; admin only for reopen"],
    )

    # concrete-state group (factory product boundary)
    g.rectangle(1180, 810, 1720, 180, width=1.2)
    g.draw_text(1190, 816, "Concrete states", 11, bold=True)
    states = []
    state_data = [
        ("SubmittedState", ["+ allowed_actions() : {mark_reviewed}", "+ handle(action) : ApplicationState", "' -> ReviewedState", "+ is_active() : bool  ' true"]),
        ("ReviewedState", ["+ allowed_actions() : {shortlist}", "+ handle(action) : ApplicationState", "' -> ShortlistedState", "+ is_active() : bool  ' true"]),
        ("ShortlistedState", ["+ allowed_actions() : {hire, reject}", "+ handle(action) : ApplicationState", "' -> HiredState | RejectedState", "+ is_active() : bool  ' true"]),
        ("RejectedState", ["+ allowed_actions() : {reopen}", "+ handle(action) : ApplicationState", "' -> ReviewedState (admin)", "+ is_active() : bool  ' false"]),
        ("HiredState", ["+ allowed_actions() : {}  ' terminal", "+ handle(action) : ApplicationState", "' raises IllegalTransitionError", "+ is_active() : bool  ' false"]),
    ]
    for i, (name, methods) in enumerate(state_data):
        states.append(class_box(g, 1215 + i * 338, 850, 320, name, None, [], methods))
    submitted, reviewed, shortlisted, rejected, hired = states

    hist = class_box(
        g,
        820,
        1030,
        400,
        "ApplicationHistory",
        "<<model>>",
        [
            "+ id : int",
            "+ application_id : int",
            "+ from_status : str",
            "+ to_status : str",
            "+ action : str",
            "+ actor_id : int",
            "+ occurred_at : datetime",
        ],
        [],
    )
    listing = class_box(
        g,
        1260,
        1030,
        260,
        "Listing",
        "<<model>>",
        ["+ id : int", "+ employer_id : int"],
        [],
    )
    user = class_box(
        g,
        1640,
        1030,
        280,
        "User",
        "<<model>>",
        ["+ id : int", "+ role : str", "+ programme : str"],
        [],
    )
    notif = class_box(
        g,
        1980,
        1030,
        340,
        "Notification",
        "<<model>>",
        [
            "+ id : int",
            "+ user_id : int",
            "+ application_id : int",
        ],
        [
            "+ status() : str  {from Application}",
            "+ text() : str  {built from status}",
        ],
    )
    ill = class_box(
        g,
        2400,
        1030,
        400,
        "IllegalTransitionError",
        "<<exception>>",
        [],
        ["action not in allowed_actions"],
    )
    channel = class_box(
        g,
        1980,
        1260,
        340,
        "NotificationChannel",
        "<<enumeration>>",
        ["EMAIL  {primary}", "ON_PLATFORM  {optional}"],
        [],
    )

    # ------------------------------------------------------- AFTER relations
    vline(g, router, app_svc, "dep", "transition")
    poly(
        g,
        [(right(router)[0], 201), (1460, 201), (1460, 300)],
        "dep",
        "reopen",
        (1230, 183),
    )
    poly(
        g,
        [(1020, 478), (1020, 485), (1300, 485), (1300, 459)],
        "dep",
        "delegates",
        (1224, 481),
    )
    poly(
        g,
        [(1120, 300), (1120, 285), (1970, 285), (1970, 300)],
        "dep",
        "ownership check",
        (1450, 269),
    )
    poly(
        g,
        [(1660, 390), (1780, 390)],
        "dep",
        "authorize advance",
        (1660, 376),
    )
    poly(
        g,
        [(1460, 459), (1460, 520), (1550, 520), (1550, 550)],
        "dep",
        "handle(action)",
        (1470, 504),
    )
    poly(
        g,
        [(1320, 459), (1320, 500), (1040, 500), (1040, 550)],
        "dep",
        "updates status",
        (1080, 521),
    )
    poly(
        g,
        [(1620, 459), (1620, 515), (1990, 515), (1990, 550)],
        "dep",
        "save",
        (1700, 499),
    )
    poly(
        g,
        [(1660, 459), (1660, 535), (2380, 535), (2380, 421)],
        "dep",
        "authorize reopen",
        (2100, 519),
    )
    poly(
        g,
        [(1360, 300), (1360, 270), (2780, 270), (2780, 300)],
        "dep",
        "notify",
        (2200, 254),
    )
    poly(
        g,
        [(1305, 459), (1305, 492), (840, 492), (840, 1030)],
        "create",
        "<<create>> history",
        (852, 511),
    )

    # explicit generalization: solid line + hollow triangle at the parent
    bus_y = 825
    for st in states:
        g.line(cx(st), top(st)[1], cx(st), bus_y)
    g.line(cx(submitted), bus_y, cx(hired), bus_y)
    g.line(cx(iface), bottom(iface)[1], cx(iface), bus_y)
    hollow_triangle(g, (cx(iface), bottom(iface)[1]), "down")

    # factory creates the concrete-state group; Application asks the factory
    poly(g, [(2400, 633), (2400, 810)], "create", "<<create>>", (2410, 700))
    poly(
        g,
        [(1260, 760), (1790, 760), (1790, 690), (2250, 690), (2250, 633)],
        "dep",
        "current_state()",
        (1285, 758),
    )

    # Application -> ApplicationState (plain association to the class edge)
    g.line(right(app_new)[0], 620, left(iface)[0], 620)
    draw_label(g, 1261, 626, "current state")
    draw_label(g, 1264, 596, "1")
    draw_label(g, 1352, 596, "1")

    # Application associations with role names and multiplicities
    g.line(900, 787, 900, 1030)
    draw_label(g, 910, 900, "history")
    draw_label(g, 905, 795, "1")
    draw_label(g, 905, 1012, "0..*")

    poly(
        g,
        [(1050, 787), (1050, 1015), (1390, 1015), (1390, 1030)],
        "assoc",
        "listing",
        (1120, 999),
    )
    draw_label(g, 1055, 791, "0..*")
    draw_label(g, 1395, 1012, "1")

    poly(
        g,
        [(1150, 787), (1150, 1020), (1780, 1020), (1780, 1030)],
        "assoc",
        "graduate",
        (1300, 1004),
    )
    draw_label(g, 1155, 791, "0..*")
    draw_label(g, 1785, 1012, "1")

    g.line(right(listing)[0], cy(listing), left(user)[0], cy(user))
    draw_label(g, 1530, 1063, "employer")
    draw_label(g, 1525, 1085, "0..*")
    draw_label(g, 1625, 1085, "1")

    g.line(cx(notif), bottom(notif)[1], cx(notif), top(channel)[1])
    draw_label(g, 2105, 1196, "0..*")
    draw_label(g, 2105, 1237, "1")
    draw_label(g, 2160, 1215, "channel")

    # notification and exception dependencies
    poly(
        g,
        [(2930, 421), (2930, 1140), (2320, 1140)],
        "create",
        "<<create>>",
        (2500, 1165),
    )
    poly(
        g,
        [(2380, 421), (2380, 500), (2860, 500), (2860, 550)],
        "dep",
        "throws",
        (2450, 484),
    )
    poly(
        g,
        [(1970, 459), (1970, 520), (2700, 520), (2700, 550)],
        "dep",
        "throws",
        (2000, 504),
    )
    poly(g, [(2780, 990), (2780, 1030)], "dep", "throws", (2790, 1010))

    # ---------------------------------------------------------------- notes
    note_box(
        g,
        820,
        1460,
        1080,
        [
            "submitted --mark_reviewed--> reviewed",
            "reviewed --shortlist--> shortlisted",
            "shortlisted --hire--> hired",
            "shortlisted --reject--> rejected",
            "Admin reopen: rejected --reopen--> reviewed (staff only)",
            "hired is terminal; submitted/reviewed/shortlisted have no reopen.",
            "Each state implements handle(action) : ApplicationState.",
            "HiredState.handle(action) raises IllegalTransitionError.",
            "One status field only. is_active() is derived from the current",
            "state (false for rejected/hired), keeping active list and history",
            "consistent. History + applicant notification on each change.",
        ],
        title="Legal transitions (strict chain), reopen and active vs history",
    )
    note_box(
        g,
        1940,
        1460,
        1000,
        [
            "One status field (AC 11): Application.status is the only persisted",
            "label; State objects encode behaviour, not extra booleans.",
            "Advancing (AC 12): ListingOwnerPolicy \u2014 listing employer only,",
            "checked for transitions, reading an application, and listing applicants.",
            "Administrators may export packages, never advance a lifecycle.",
            "Reopen: ReopenPolicy.can_reopen(actor) \u2014 administrator only, checked",
            "separately from the employer advance check.",
            "Notification: status() is derived from Application.status, so email,",
            "dashboard and API agree; email primary, on-platform optional.",
            "Audit: ApplicationHistory row on each successful handle().",
            "On-platform apply starts SubmittedState (AC 9).",
            "External-link listings never create an in-app Application (AC 13).",
        ],
        title="Consistency, authorization, audit, notify",
    )

    g.save(path)


if __name__ == "__main__":
    out = Path(__file__).with_name("class-diagram.png")
    render(out)
    print(f"wrote {out}")
