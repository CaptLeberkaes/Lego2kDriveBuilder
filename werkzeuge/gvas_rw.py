"""UE4 GVAS reader/writer that keeps enough type info to write files back.

Properties are Prop objects; struct values are lists of Props (tagged) or raw
bytes (native structs). Arrays of structs keep their element list; everything
we never edit (maps, sets, simple arrays) stays as raw payload bytes.
load() + dump() reproduce the original file byte for byte.
"""
import os
from pathlib import Path
import struct
import tempfile
import time
import uuid

NATIVE = {"Vector", "Vector2D", "Rotator", "Quat", "LinearColor", "Color",
          "IntPoint", "Guid", "DateTime", "Timespan", "Box", "Box2D"}


class Prop:
    def __init__(self, name, type, value, idx=0, hdr=None):
        self.name, self.type, self.value, self.idx = name, type, value, idx
        self.hdr = hdr or {}

    def __repr__(self):
        return f"Prop({self.name}:{self.type})"


class StructArray:
    def __init__(self, inner_name, struct_name, struct_guid, elems):
        self.inner_name, self.struct_name = inner_name, struct_name
        self.struct_guid, self.elems = struct_guid, elems


class R:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def take(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) != n:
            raise EOFError(self.p)
        self.p += n
        return b

    def i32(self):
        return struct.unpack("<i", self.take(4))[0]

    def u8(self):
        return self.take(1)[0]

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            return self.take(-n * 2)[:-2].decode("utf-16-le")
        return self.take(n)[:-1].decode("latin-1")


def wstr(s):
    if s == "":
        return struct.pack("<i", 0)
    try:
        # Nicht-ASCII immer als UTF-16 schreiben: eindeutig für UE und beide Leser.
        b = s.encode("ascii") + b"\0"
        return struct.pack("<i", len(b)) + b
    except UnicodeEncodeError:
        b = s.encode("utf-16-le") + b"\0\0"
        return struct.pack("<i", -(len(b) // 2)) + b


# ---------------------------------------------------------------- reading

def read_props(r):
    out = []
    while True:
        name = r.fstr()
        if name == "None":
            return out
        typ = r.fstr()
        size = r.i32()
        idx = r.i32()
        hdr = {}
        if typ == "StructProperty":
            hdr["struct"] = r.fstr()
            hdr["guid"] = r.take(16)
        elif typ == "BoolProperty":
            hdr["bool"] = r.u8()
        elif typ in ("ByteProperty", "EnumProperty"):
            hdr["enum"] = r.fstr()
        elif typ in ("ArrayProperty", "SetProperty"):
            hdr["inner"] = r.fstr()
        elif typ == "MapProperty":
            hdr["key"] = r.fstr()
            hdr["val"] = r.fstr()
        has_guid = r.u8()
        assert has_guid == 0, "property guid not supported"
        payload = r.take(size)
        out.append(Prop(name, typ, decode(typ, hdr, payload), idx, hdr))


def decode(typ, hdr, payload):
    if typ == "StructProperty":
        return decode_struct(hdr["struct"], payload)
    if typ == "ArrayProperty" and hdr["inner"] == "StructProperty":
        r = R(payload)
        n = r.i32()
        inner_name = r.fstr()
        assert r.fstr() == "StructProperty"
        total = r.i32()
        r.i32()
        sname = r.fstr()
        sguid = r.take(16)
        r.u8()
        body = r.take(total)
        assert r.p == len(payload)
        return StructArray(inner_name, sname, sguid, split_elems(sname, body, n))
    return payload  # raw: simple values, simple arrays, maps, sets


def decode_struct(sname, payload):
    if sname in NATIVE:
        return payload
    try:
        r = R(payload)
        props = read_props(r)
        if r.p == len(payload):
            return props
    except Exception:
        pass
    return payload


def split_elems(sname, body, n):
    if n == 0:
        return []
    if sname not in NATIVE:
        try:
            r = R(body)
            elems = [read_props(r) for _ in range(n)]
            if r.p == len(body):
                return elems
        except Exception:
            pass
    step = len(body) // n
    assert step * n == len(body)
    return [body[i * step:(i + 1) * step] for i in range(n)]


# ---------------------------------------------------------------- writing

def write_props(props):
    out = bytearray()
    for p in props:
        payload = encode(p)
        out += wstr(p.name) + wstr(p.type)
        out += struct.pack("<ii", 0 if p.type == "BoolProperty" else len(payload), p.idx)
        h = p.hdr
        if p.type == "StructProperty":
            out += wstr(h["struct"]) + h["guid"]
        elif p.type == "BoolProperty":
            out += bytes([h["bool"]])
        elif p.type in ("ByteProperty", "EnumProperty"):
            out += wstr(h["enum"])
        elif p.type in ("ArrayProperty", "SetProperty"):
            out += wstr(h["inner"])
        elif p.type == "MapProperty":
            out += wstr(h["key"]) + wstr(h["val"])
        out += b"\0" + payload
    out += wstr("None")
    return bytes(out)


def encode(p):
    v = p.value
    if p.type == "BoolProperty":
        return b""
    if isinstance(v, StructArray):
        body = b"".join(e if isinstance(e, bytes) else write_props(e) for e in v.elems)
        return (struct.pack("<i", len(v.elems)) + wstr(v.inner_name) + wstr("StructProperty")
                + struct.pack("<ii", len(body), 0) + wstr(v.struct_name) + v.struct_guid
                + b"\0" + body)
    if isinstance(v, list):
        return write_props(v)
    return v


# ---------------------------------------------------------------- file

class SaveFile:
    def __init__(self, path):
        self.source_path = Path(path).resolve()
        data = self.source_path.read_bytes()
        self._read(data)

    @classmethod
    def from_bytes(cls, data):
        result = cls.__new__(cls)
        result.source_path = None
        result._read(data)
        return result

    def _read(self, data):
        if not data.startswith(b"GVAS"):
            raise ValueError("Keine GVAS-Speicherdatei")
        self.source_bytes = data
        r = R(data)
        r.take(4 + 4 + 4 + 6 + 4)
        r.fstr()
        r.i32()
        n = r.i32()
        r.take(n * 20)
        r.fstr()
        self.header = data[:r.p]
        self.props = read_props(r)
        self.tail = data[r.p:]

    def dump(self):
        return self.header + write_props(self.props) + self.tail

    def save(self, path):
        """Erneut prüfen, vorhandenes Ziel sichern, dann atomar ersetzen.

        Bei zwischenzeitlichen Zieländerungen abbrechen. Die Quelle wird nur
        ersetzt, wenn ihr Inhalt noch dem eingelesenen Snapshot entspricht.
        """
        destination = Path(path).resolve()
        payload = self.dump()
        if self.from_bytes(payload).dump() != payload:
            raise ValueError("GVAS-Rückleseprüfung fehlgeschlagen")
        previous = destination.read_bytes() if destination.exists() else None
        if destination == self.source_path and previous != self.source_bytes:
            raise ValueError("Spielstand wurde seit dem Einlesen verändert; erneut einlesen")
        self.last_backup = None
        if previous is not None:
            backup_dir = (Path(__file__).resolve().parent.parent / "_sicherungen" /
                          (time.strftime("geschrieben_%Y-%m-%d_%H-%M-%S") + "_" + uuid.uuid4().hex[:8]))
            backup_dir.mkdir(parents=True)
            self.last_backup = backup_dir / destination.name
            self.last_backup.write_bytes(previous)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix="."+destination.name+".", suffix=".tmp", delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            current = destination.read_bytes() if destination.exists() else None
            if current != previous:
                raise ValueError("Zieldatei wurde während der Vorbereitung verändert; nichts ersetzt")
            os.replace(temp_path, destination)
            if destination == self.source_path:
                self.source_bytes = payload
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()


def get(props, name):
    return next(p for p in props if p.name == name)


def val(props, name):
    return get(props, name).value
