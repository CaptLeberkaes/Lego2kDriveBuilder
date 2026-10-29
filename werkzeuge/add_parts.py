"""Append parts to vehicle slot 0 of an ArtemisVehicle.sav by byte splicing.

New parts copy the 8-byte entry and Transform element of a template part,
with design ID, color and translation replaced. Connections are untouched.
Usage: add_parts.py <src.sav> <dst.sav> <template_index> <plan.json>
plan.json: [{"design": 3005, "color": 13, "pos": [x, y, z]}, ...]
"""
import json
import struct
import sys

import gvas


def main(src, dst, tpl_idx, plan_path):
    data = bytearray(open(src, "rb").read())
    plan = json.load(open(plan_path, encoding="utf-8"))
    gvas.TRACE = []
    gvas.load(src)
    tr = gvas.TRACE

    def first(pred):
        return next(t for t in tr if pred(t))

    data_prop = first(lambda t: t.get("name") == "Data" and t["depth"] == 0)
    cv_prop = first(lambda t: t.get("name") == "CustomVehicles")
    cv_arr = first(lambda t: t.get("array_of") == "CustomVehicleInfo")
    pg_prop = first(lambda t: t.get("name") == "PartGraph")
    parts_prop = first(lambda t: t.get("name") == "Parts" and t["depth"] == 3)
    parts_arr = first(lambda t: t.get("array_of") == "LegoGraphPartInstance")
    tf_prop = first(lambda t: t.get("name") == "PartTransforms")
    tf_arr = first(lambda t: t.get("array_of") == "Transform")

    n_old = parts_arr["count"]
    assert tf_arr["count"] == n_old
    tf_len = tf_arr["data_size"] // n_old
    part_tpl = bytes(data[parts_arr["data_start"] + 8 * tpl_idx:][:8])
    tf_tpl = bytes(data[tf_arr["data_start"] + tf_len * tpl_idx:][:tf_len])
    # locate translation vector inside the template transform
    tf_json = gvas.read_struct(gvas.R(tf_tpl), "Transform")
    old_vec = struct.pack("<fff", *tf_json["Translation"])
    vec_off = tf_tpl.find(old_vec)
    assert vec_off > 0 and tf_tpl.find(old_vec, vec_off + 1) == -1

    new_parts, new_tfs = b"", b""
    for p in plan:
        e = bytearray(part_tpl)
        e[0:4] = struct.pack("<I", p["design"])
        e[4] = p["color"]
        new_parts += bytes(e)
        t = bytearray(tf_tpl)
        t[vec_off:vec_off + 12] = struct.pack("<fff", *p["pos"])
        new_tfs += bytes(t)
    n = len(plan)
    d_parts, d_tfs = len(new_parts), len(new_tfs)

    # splice later insertion first so earlier offsets stay valid
    tf_end = tf_arr["data_start"] + tf_arr["data_size"]
    parts_end = parts_arr["data_start"] + parts_arr["data_size"]
    assert parts_end < tf_end
    data[tf_end:tf_end] = new_tfs
    data[parts_end:parts_end] = new_parts

    def add_i32(pos, delta):
        v = struct.unpack_from("<i", data, pos)[0]
        struct.pack_into("<i", data, pos, v + delta)

    # all size fields precede both insertion points
    add_i32(tf_arr["count_pos"] + d_parts, n)
    add_i32(tf_arr["inner_size_pos"] + d_parts, d_tfs)
    add_i32(tf_prop["size_pos"] + d_parts, d_tfs)
    add_i32(parts_arr["count_pos"], n)
    add_i32(parts_arr["inner_size_pos"], d_parts)
    add_i32(parts_prop["size_pos"], d_parts)
    total = d_parts + d_tfs
    for t in (pg_prop, cv_prop, data_prop):
        add_i32(t["size_pos"], total)
    add_i32(cv_arr["inner_size_pos"], total)

    open(dst, "wb").write(data)
    print(f"added {n} parts (+{total} bytes)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
