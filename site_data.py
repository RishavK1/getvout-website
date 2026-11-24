"""Read and write the site's byte-counted React Server Component payloads."""
import json
import re


def records(source):
    raw, pos = source.encode(), 0
    while pos < len(raw):
        match = re.match(rb"([0-9a-f]+):T([0-9a-f]+),", raw[pos:])
        if match:
            start = pos + match.end()
            end = start + int(match[2], 16)
            if end > len(raw):
                raise ValueError("Truncated text record")
            yield match[1].decode(), "T", raw[start:end].decode()
            pos = end
            continue
        end = raw.find(b"\n", pos)
        end = len(raw) if end < 0 else end + 1
        line = raw[pos:end].decode()
        match = re.match(r"^([0-9a-f]+):(.*)", line)
        if match:
            try:
                yield match[1], "J", json.loads(match[2])
            except ValueError:
                yield match[1], "R", match[2]
        elif line.strip():
            yield None, "H", line.rstrip("\n")
        pos = end


def encode(rows):
    output = []
    for key, kind, value in rows:
        if kind == "T":
            output.append(f"{key}:T{len(value.encode()):x}," + value)
        elif kind == "J":
            output.append(key + ":" + json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        elif kind == "R":
            output.append(key + ":" + value + "\n")
        else:
            output.append(value + "\n")
    return "".join(output)
