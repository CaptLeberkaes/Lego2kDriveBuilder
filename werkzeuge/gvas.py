"""Minimal UE4 GVAS (SaveGame) reader for LEGO 2K Drive files.

Parses tagged properties into plain Python dicts/lists. Unknown binary
payloads are kept as hex so nothing is silently lost.
"""
import json
import struct
import sys

# Structs that UE4 serializes natively (no property tags)
NATIVE = {
    "Vector": "<fff", "Vector2D": "<ff", "Rotator": "<fff", "Quat": "<ffff",
    "LinearColor": "<ffff", "IntPoint": "<ii", "Color": "<BBBB",
    "DateTime": "<q", "Timespan": "<q",
}


TRACE = None  # set to a list to record offsets of size fields
STACK = []


class R:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def take(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) != n:
            raise EOFError(self.p)
        self.p += n
        return b

    def u8(self): return self.take(1)[0]
    def i32(self): return struct.unpack("<i", self.take(4))[0]
    def u32(self): return struct.unpack("<I", self.take(4))[0]
    def i64(self): return struct.unpack("<q", self.take(8))[0]
    def guid(self): return self.take(16).hex()

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            return self.take(-n * 2)[:-2].decode("utf-16-le")
        return self.take(n)[:-1].decode("utf-8", "replace")


def read_header(r):
    h = {"magic": r.take(4).decode(), "save_ver": r.i32(), "pkg_ver": r.i32()}
    h["engine"] = (struct.unpack("<HHH", r.take(6)), r.u32(), r.fstr())
    h["custom_fmt"] = r.i32()
    h["custom"] = [(r.guid(), r.i32()) for _ in range(r.i32())]
    h["class"] = r.fstr()
    return h


def read_props(r, end=None):
    out = {}
    while True:
        name = r.fstr()
        if name == "None":
            return out
        typ = r.fstr()
        size_pos = r.p
        size = r.i32()
        idx = r.i32()
        if TRACE is not None:
            TRACE.append({"name": name, "type": typ, "size_pos": size_pos, "size": size, "depth": len(STACK)})
            STACK.append(name)
        try:
            val = read_tagged_value(r, typ, size)
        finally:
            if TRACE is not None:
                STACK.pop()
        key = name if idx == 0 else f"{name}[{idx}]"
        out[key] = val
        if end is not None and r.p >= end:
            return out


def read_tagged_value(r, typ, size):
    if typ == "StructProperty":
        sname = r.fstr(); r.guid(); r.u8()
        start = r.p
        v = read_struct(r, sname, size)
        r.p = start + size
        return v
    if typ == "BoolProperty":
        v = r.u8(); r.u8()
        return bool(v)
    if typ in ("ByteProperty", "EnumProperty"):
        ename = r.fstr(); r.u8()
        if typ == "ByteProperty" and ename == "None":
            return r.take(size)[0] if size == 1 else r.take(size).hex()
        return R(r.take(size)).fstr()
    if typ == "ArrayProperty":
        inner = r.fstr(); r.u8()
        start = r.p
        v = read_array(r, inner, size)
        r.p = start + size
        return v
    if typ == "MapProperty":
        kt = r.fstr(); vt = r.fstr(); r.u8()
        start = r.p
        try:
            v = read_map(r, kt, vt)
        except Exception as e:  # keep raw on failure
            r.p = start
            v = {"_raw": r.take(size).hex(), "_err": repr(e), "_kt": kt, "_vt": vt}
        r.p = start + size
        return v
    if typ == "SetProperty":
        inner = r.fstr(); r.u8()
        return {"_set_raw": r.take(size).hex(), "_inner": inner}
    r.u8()  # hasGuid
    return read_simple(R(r.take(size)), typ, size)


def read_simple(r, typ, size=None):
    if typ == "IntProperty": return r.i32()
    if typ == "UInt32Property": return r.u32()
    if typ == "Int64Property": return r.i64()
    if typ == "UInt64Property": return struct.unpack("<Q", r.take(8))[0]
    if typ == "UInt16Property": return struct.unpack("<H", r.take(2))[0]
    if typ == "Int16Property": return struct.unpack("<h", r.take(2))[0]
    if typ == "Int8Property": return struct.unpack("<b", r.take(1))[0]
    if typ == "FloatProperty": return struct.unpack("<f", r.take(4))[0]
    if typ == "DoubleProperty": return struct.unpack("<d", r.take(8))[0]
    if typ in ("StrProperty", "NameProperty", "EnumProperty"): return r.fstr()
    if typ == "ObjectProperty": return r.fstr()
    if typ == "SoftObjectProperty":
        path = r.fstr(); sub = r.fstr()
        return path + (":" + sub if sub else "")
    if typ == "ByteProperty": return r.u8()
    if typ == "BoolProperty": return bool(r.u8())
    if size is not None:
        return {"_raw_" + typ: r.take(size).hex()}
    raise ValueError("unknown simple type " + typ)


def read_struct(r, sname, size=None):
    if sname in NATIVE:
        fmt = NATIVE[sname]
        return list(struct.unpack(fmt, r.take(struct.calcsize(fmt))))
    if sname == "Guid":
        return r.guid()
    return read_props(r)


def read_array(r, inner, size):
    n = r.i32()
    if inner == "StructProperty":
        count_pos = r.p - 4
        r.fstr(); r.fstr(); inner_pos = r.p; total = r.i32(); r.i32()  # name, type, size, index
        sname = r.fstr(); r.guid(); r.u8()
        start = r.p
        if TRACE is not None:
            TRACE.append({"array_of": sname, "path": list(STACK), "count_pos": count_pos,
                          "count": n, "inner_size_pos": inner_pos, "data_start": start, "data_size": total})
        try:
            items = [read_struct(r, sname) for _ in range(n)]
            if r.p != start + total:
                raise ValueError("size mismatch")
        except Exception:
            # Natively serialized struct: keep raw bytes, split evenly
            r.p = start
            raw = r.take(total)
            step = total // n if n else 0
            items = [raw[i * step:(i + 1) * step].hex() for i in range(n)]
            return {"_struct": sname, "_native": True, "_elem_size": step, "items": items}
        return {"_struct": sname, "items": items}
    if inner == "ByteProperty" and size - 4 == n:
        return {"_bytes": r.take(n).hex()}
    return [read_simple(r, inner) for _ in range(n)]


def read_map(r, kt, vt):
    r.i32()  # removed count
    n = r.i32()
    out = []
    for _ in range(n):
        k = read_map_item(r, kt)
        v = read_map_item(r, vt)
        out.append([k, v])
    return out


def read_map_item(r, t):
    if t == "StructProperty":
        # Map structs carry no type info; Guid keys are common, else tagged
        save = r.p
        try:
            return read_props(r)
        except Exception:
            r.p = save
            return r.guid()
    return read_simple(r, t)


def load(path):
    data = open(path, "rb").read()
    r = R(data)
    h = read_header(r)
    body = read_props(r)
    tail = data[r.p:]
    return {"header": h, "body": body, "tail_hex": tail.hex()}


if __name__ == "__main__":
    res = load(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    s = json.dumps(res, indent=1, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(s)
    else:
        print(s)
