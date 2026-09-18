import pygame
import time
import pylsl
import socket
import numpy as np
import xml.etree.ElementTree as ET
from PIL import Image

def init_images(
    image_a_path,
    image_b_path,
    image_c_path,
):
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080), pygame.HWSURFACE | pygame.DOUBLEBUF)

    img_a = pygame.image.load(image_a_path).convert()
    img_b = pygame.image.load(image_b_path).convert()
    img_c = pygame.image.load(image_c_path).convert()

    img_a = pygame.transform.scale(img_a, screen.get_size())
    img_b = pygame.transform.scale(img_b, screen.get_size())
    img_c = pygame.transform.scale(img_c, screen.get_size())

    return screen, img_a, img_b, img_c

def change_image(screen, img_a, img_b, img_c, image_number):

    # two images
    if image_number % 2 == 0:
        # Draw A and present
        screen.blit(img_a, (0, 0))
    elif image_number % 1 == 0:
        # Draw C and present
        screen.blit(img_c, (0, 0))

    # # three images
    # if image_number % 3 == 0:
    #     # Draw A and present
    #     screen.blit(img_a, (0, 0))
    # elif image_number % 2 == 0:
    #     # Draw B and present
    #     screen.blit(img_b, (0, 0))
    # elif image_number % 1 == 0:
    #     # Draw C and present
    #     screen.blit(img_c, (0, 0))

    pygame.display.flip()
    time_flip = pylsl.local_clock()

    return time_flip


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

    print("now sending data...")

    with socket.create_connection((adress, port)) as sock:
        sock.sendall(result_format.encode("utf-8"))
        send_readstring(sock, appkey)

        connection_info = recv_readstring(sock)
        print("connectionStatus raw:", connection_info)
        if not connection_info[:2] == "ok":
            raise RuntimeError(f"Authorization failed (response starts with {connection_info[:2]!r})")

        image_a_path = r"images\left.jpg"
        image_b_path = r"images\middle.jpg"
        image_c_path = r"images\right.jpg"

        screen, img_a, img_b, img_c = init_images(image_a_path, image_b_path, image_c_path)

        image_number = 0

        times = []

        # while True:
        for _ in range(200):
            time_flip = change_image(screen, img_a, img_b, img_c, image_number)

            # extracting sample data
            xml_text = recv_readstring(sock)
            stamp = pylsl.local_clock()  # add local latency term here

            data = parse_gazedata_xml(xml_text)
            x = data["GazeX"]
            y = data["GazeY"]
            sample = np.array([x, y])

            image_number += 1
            times.append(stamp-time_flip)

            # print("Flip", time_flip)
            # print("Detect", stamp)
            # print(sample)

            # waiting for a bit before trying again
            time.sleep(0.01)

        pygame.quit()

        average_latency = float(np.median(times))
        print(average_latency)


if __name__ == "__main__":
    main()
