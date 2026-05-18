"""
sender_udp.py — Send a file via UDP with sequence numbers and redundancy.

Usage:
    python sender_udp.py <ip> <port> <filepath> [repeats] [delay_ms]

Arguments:
    ip        : destination IP address
    port      : destination UDP port
    filepath  : path to file to send
    repeats   : how many times each data packet is sent (default: 3)
    delay_ms  : milliseconds between repeated packets (default: 5)

Example:
    python sender_udp.py 192.168.1.100 5001 data/metcm_message.bin 3 5

Packet format (data packets):
    Bytes 0-3  : sequence number    (uint32, big-endian)
    Bytes 4-7  : total packet count (uint32, big-endian)
    Bytes 8+   : payload            (up to MAX_PAYLOAD bytes)

End-of-transfer (EOT) packet:
    Bytes 0-3  : 0xFFFFFFFF         (magic — marks EOT)
    Bytes 4-7  : total packet count (uint32, big-endian)
    Bytes 8-71 : SHA-256 checksum   (64 bytes ASCII hex)

Rationale:
    UDP has no ACK and no return channel (required for diode compatibility).
    Each packet is sent REPEATS times to compensate for random packet loss.
    The EOT packet is sent EOT_REPEATS times so the receiver reliably detects
    end-of-transfer even if some EOT packets are lost.
"""

import socket
import hashlib
import struct
import sys
import os
import time


MAX_PAYLOAD = 1400      # bytes per packet well below typical 1500-byte MTU
EOT_MAGIC = 0xFFFFFFFF  # sequence number that signals end-of-transfer
EOT_REPEATS = 5         # EOT is critical


def compute_sha256(filepath: str) -> str:
    """Return the hex-encoded SHA-256 digest of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def build_data_packet(seq_nr: int, total_packets: int, payload: bytes) -> bytes:
    """Pack a data packet: [seq_nr 4B][total 4B][payload]."""
    header = struct.pack(">II", seq_nr, total_packets)
    return header + payload


def build_eot_packet(total_packets: int, checksum: str) -> bytes:
    """Pack the end-of-transfer packet: [0xFFFFFFFF][total][checksum 32B]."""
    header = struct.pack(">II", EOT_MAGIC, total_packets)
    return header + checksum.encode("ascii")


def send_file(ip: str, port: int, filepath: str,
              repeats: int = 3, delay_ms: int = 5) -> None:
    """Fragment and transmit file via UDP."""

    if not os.path.isfile(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    # Read entire file into memory (METCM/METGM files are small — typically < 1 MB)
    with open(filepath, "rb") as f:
        file_data = f.read()

    file_size = len(file_data)
    checksum = compute_sha256(filepath)

    # Split file into chunks of MAX_PAYLOAD bytes
    chunks = [file_data[i:i + MAX_PAYLOAD]
              for i in range(0, file_size, MAX_PAYLOAD)]
    total_packets = len(chunks)

    print(f"[INFO] File        : {filepath}")
    print(f"[INFO] Size        : {file_size} bytes")
    print(f"[INFO] Packets     : {total_packets} x up to {MAX_PAYLOAD} bytes")
    print(f"[INFO] Repeats     : {repeats} per packet")
    print(f"[INFO] Delay       : {delay_ms} ms between repeats")
    print(f"[INFO] SHA-256     : {checksum}")
    print(f"[INFO] Destination : {ip}:{port}")

    delay_sec = delay_ms / 1000.0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

        # Send each data packet REPEATS times
        for seq_nr, chunk in enumerate(chunks):
            packet = build_data_packet(seq_nr, total_packets, chunk)
            for _ in range(repeats):
                sock.sendto(packet, (ip, port))
                if delay_ms > 0:
                    time.sleep(delay_sec)

            # Progress indicator every 10 packets
            if (seq_nr + 1) % 10 == 0 or (seq_nr + 1) == total_packets:
                print(f"[INFO] Sent {seq_nr + 1}/{total_packets} packets", end="\r")

        print()  # newline after progress line

        # Send EOT packet EOT_REPEATS times
        eot_packet = build_eot_packet(total_packets, checksum)
        for i in range(EOT_REPEATS):
            sock.sendto(eot_packet, (ip, port))
            time.sleep(0.05)  # 50 ms between EOT packets
            print(f"[INFO] EOT packet {i + 1}/{EOT_REPEATS} sent")

    print("[OK] Transfer complete.")
    print(f"[OK] SHA-256: {checksum}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python sender_udp.py <ip> <port> <filepath> [repeats] [delay_ms]")
        sys.exit(1)

    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    target_file = sys.argv[3]
    pkt_repeats = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    pkt_delay = int(sys.argv[5]) if len(sys.argv) > 5 else 5

    send_file(target_ip, target_port, target_file, pkt_repeats, pkt_delay)
