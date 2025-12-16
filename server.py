import socket
import requests
import yt_dlp
import os
import threading
import struct
import zlib

# --- ERROR CHECKING UTILS ---

def verify_crc32(data, received_crc):
    # zlib.crc32 returns a signed int in Python 2, unsigned in 3.
    # We insure it matches C's unsigned int logic (mask with 0xFFFFFFFF)
    calc_crc = zlib.crc32(data) & 0xFFFFFFFF
    return calc_crc == received_crc

def verify_2d_parity(data, received_row, received_col):
    calc_row = 0
    cols = [0] * 8
    
    for byte in data:
        calc_row ^= byte # XOR Sum for Row Parity logic
    
    for i, byte in enumerate(data):
        cols[i % 8] ^= byte

    # Pack calculated cols into integer to match C struct
    # We take first 4 bytes of cols array to mimic C memcpy
    calc_col_packed = struct.unpack('<I', bytes(cols[:4]))[0]

    return (calc_row == received_row) and (calc_col_packed == received_col)

# --- DOWNLOADER FUNCTIONS ---

def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def ensure_extension(filename, extension):
    if not filename.endswith(extension):
        filename += extension
    return filename

def download_file(url, directory, filename, extension, download_func):
    try:
        create_directory(directory)
        filename = ensure_extension(filename, extension)
        file_path = os.path.join(directory, filename)

        # --- FIX: ADD HEADERS TO TRICK WEBSITE ---
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, stream=True)
        # -----------------------------------------
        
        response.raise_for_status()

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        return f"{download_func} downloaded successfully as {file_path}"
    except Exception as e:
        return f"Error downloading {download_func}: {e}"

def download_image(url, directory, filename):
    return download_file(url, directory or "Images", filename, '.jpg', "Image")

def download_youtube_video(url, directory, filename):
    try:
        directory = directory or "Videos"
        create_directory(directory)
        filename = ensure_extension(filename, '.mp4')
        file_path = os.path.join(directory, filename)
        ydl_opts = {'outtmpl': file_path, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return f"Video downloaded successfully as {file_path}"
    except Exception as e:
        return f"Error downloading video: {e}"

def download_audio_from_url(url, directory, filename):
    return download_file(url, directory or "Audio", filename, '.mp3', "Audio")

def download_pdf(url, directory, filename):
    return download_file(url, directory or "PDFs", filename, '.pdf', "PDF")

def download_zip(url, directory, filename):
    return download_file(url, directory or "Zips", filename, '.zip', "ZIP file")

# --- SERVER LOGIC ---

def recv_packet(client_socket):
    """
    Receives Header (16 bytes) -> Unpacks -> Receives Body
    Returns: (Decoded String, ErrorMessage or None)
    """
    try:
        # Header is 4 uint32 (4 * 4 = 16 bytes)
        header_data = client_socket.recv(16)
        if not header_data: return None, "Disconnected"

        data_len, crc32, row_p, col_p = struct.unpack('IIII', header_data)
        
        # Receive exact amount of data
        body_data = b''
        while len(body_data) < data_len:
            chunk = client_socket.recv(data_len - len(body_data))
            if not chunk: break
            body_data += chunk

        # 1. CHECK CRC
        if not verify_crc32(body_data, crc32):
            print(f"[!] CRC32 FAILURE. Recv: {zlib.crc32(body_data) & 0xFFFFFFFF:X} vs Exp: {crc32:X}")
            return None, "ERROR: CRC32 Mismatch! Data Corrupted."

        # 2. CHECK 2D PARITY
        if not verify_2d_parity(body_data, row_p, col_p):
            print(f"[!] PARITY FAILURE.")
            return None, "ERROR: 2D Parity Check Failed! Data Corrupted."

        return body_data.decode().strip(), None
    except Exception as e:
        print(f"Packet Error: {e}")
        return None, "Packet Error"

def handle_download(client_socket, file_type, download_func):
    client_socket.send(f"Enter {file_type} URL: ".encode())
    url, err = recv_packet(client_socket)
    if err: return err

    client_socket.send(b"Enter directory (blank for default): ")
    directory, err = recv_packet(client_socket)
    if err: return err

    client_socket.send(f"Enter filename: ".encode())
    filename, err = recv_packet(client_socket)
    if err: return err

    return download_func(url, directory, filename)

def handle_client(client_socket):
    while True:
        menu = (
            "\n--- DOWNLOAD MANAGER SERVER ---\n"
            "1. Download Image\n2. Download Video\n3. Download Audio\n"
            "4. Download PDF\n5. Download ZIP\n6. Exit\n"
            "Enter choice: "
        )
        client_socket.send(menu.encode())
        
        choice, err = recv_packet(client_socket)

        if err:
            # If corruption detected, warn user and restart loop
            client_socket.send(f"\n[SERVER] {err} -> Please Try Again.\n".encode())
            continue

        if choice == "1":
            result = handle_download(client_socket, "image", download_image)
        elif choice == "2":
            result = handle_download(client_socket, "video", download_youtube_video)
        elif choice == "3":
            result = handle_download(client_socket, "audio", download_audio_from_url)
        elif choice == "4":
            result = handle_download(client_socket, "PDF", download_pdf)
        elif choice == "5":
            result = handle_download(client_socket, "ZIP", download_zip)
        elif choice == "6":
            client_socket.send(b"Goodbye! Disconnecting.\n")
            break
        else:
            result = "Invalid choice."

        client_socket.send(result.encode())
    
    client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 9999))
    server.listen(5)
    print("Server listening on port 9999 with CRC & Parity Checks...")

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

if __name__ == "__main__":
    start_server()