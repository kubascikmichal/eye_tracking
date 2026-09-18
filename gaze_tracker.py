import time
import socket
import numpy as np
import xml.etree.ElementTree as ET
import pylsl
from pylsl import StreamInfo, StreamOutlet


def read_7bit_int(sock):
    # .NET BinaryReader 7-bit encoded int
    result = 0
    shift = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise ConnectionError("Socket closed while reading 7-bit int")
        byte = b[0]
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return result
        shift += 7

def recv_readstring(sock):
    n = read_7bit_int(sock)
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed while reading string")
        data += chunk
    return data.decode("utf-8", errors="replace")

def send_readstring(sock, s):
    # .NET BinaryWriter.Write(string):
    # write 7-bit encoded length of UTF-8 bytes, then bytes
    b = s.encode("utf-8")
    length = len(b)

    # 7-bit encode
    out = bytearray()
    v = length
    while True:
        byte = v & 0x7F
        v >>= 7
        if v:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break

    sock.sendall(out + b)

def parse_gazedata_xml(xml_text):
    # Expected XML produced by XmlSerializer(typeof(CGazeData))
    # We’ll be flexible: search elements by tag name.
    root = ET.fromstring(xml_text)

    def get_float(tag):
        el = root.find(f".//{tag}")
        return float(el.text) if el is not None and el.text is not None else None

    return {
        "GazeX": get_float("GazeX"),
        "GazeY": get_float("GazeY"),
    }

def main():
    # TCP connection to GazePointer
    adress = "127.0.0.1"
    port = 43333
    appkey = "AppKeyDemo"
    result_format = "xml"

    # LSL connection to BrainAccessBoard
    info = StreamInfo(
        name="Eye_tracking",
        type="Gaze",
        channel_count=2,
        nominal_srate=5,
        channel_format="float32",
        source_id="gazeflowapi-tcp"
    )
    channels = info.desc().append_child("channels")
    for label in ["GazeX", "GazeY"]:
        ch = channels.append_child("channel")
        ch.append_child_value("label", label)
    outlet = StreamOutlet(info)

    print("now sending data...")

    with socket.create_connection((adress, port)) as sock:
        sock.sendall(result_format.encode("utf-8"))
        send_readstring(sock, appkey)

        connection_info = recv_readstring(sock)
        print("connectionStatus raw:", connection_info)
        if not connection_info[:2] == "ok":
            raise RuntimeError(f"Authorization failed (response starts with {connection_info[:2]!r})")

        while True:
            # extracting sample data
            xml_text = recv_readstring(sock)
            data = parse_gazedata_xml(xml_text)
            x = data["GazeX"]
            y = data["GazeY"]
            sample = np.array([x, y])
            stamp = pylsl.local_clock() - 0.18437674999586307 # latency term as estimated in latency.py

            # sending data over lsl
            outlet.push_sample(sample, stamp)

            # waiting for a bit before trying again
            time.sleep(0.02)

            print(sample)


if __name__ == "__main__":
    main()