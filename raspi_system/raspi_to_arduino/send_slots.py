import os
import socket
from typing import Iterable, List

# Default destination for the PC receiving slot strings. Override with env vars if needed.
HOST = os.environ.get("SLOT_HOST", "172.20.10.6")
PORT = int(os.environ.get("SLOT_PORT", "5050"))


def build_slot_string(slots: Iterable[int], total_slots: int = 24) -> str:
    """Return a string of length `total_slots` with '1' at positions in `slots` (1-based).

    Example: slots=[3] -> '001000...'
    """
    bitlist: List[str] = ["0"] * total_slots
    for s in slots:
        try:
            si = int(s)
        except Exception:
            continue
        if 1 <= si <= total_slots:
            bitlist[si - 1] = "1"
    return "".join(bitlist)


def send_slot_string(slots: Iterable[int], host: str = HOST, port: int = PORT) -> str:
    """Builds the slot string and sends it to (host, port). Returns the string sent.

    Errors are caught and printed but not raised to avoid breaking caller threads.
    """
    s = build_slot_string(slots)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            sock.connect((host, port))
            sock.sendall(s.encode())
        print(f"Sent slot string to {host}:{port} -> {s}")
    except Exception as e:
        print(f"Error sending slot string to {host}:{port}: {e}")
    return s


if __name__ == "__main__":
    # Simple CLI for manual testing: enter comma-separated slots or a single number
    raw = input("Enter slot numbers (comma-separated), e.g. 3 or 3,5,7: ")
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    slots = []
    for p in parts:
        try:
            slots.append(int(p))
        except Exception:
            pass
    send_slot_string(slots)
