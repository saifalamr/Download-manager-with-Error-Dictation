# Socket-Based Download Manager with Error Detection (C & Python)

## 📌 Project Overview
This project is a hybrid network application that combines a **C Client** and a **Python Server** to perform file downloads securely. It demonstrates low-level network programming concepts by implementing a custom application-layer protocol with **CRC-32** and **2D Parity** checks to ensure data integrity.

The system allows users to request downloads (Images, Videos, PDFs, etc.) via the C client. The client calculates checksums, packs the request into a binary header, and sends it to the Python server. The server verifies the checksums and, if the data is valid, processes the download.

## 🚀 Key Features
* **Hybrid Architecture:** C (Client) for low-level socket handling and Python (Server) for high-level automation.
* **Custom Binary Protocol:** Uses a 16-byte binary header containing Data Length, CRC32, and Parity bits.
* **Error Detection:**
    * **CRC-32:** Standard IEEE 802.3 polynomial check.
    * **2D Parity Check:** Matrix-based row and column parity verification.
* **Error Injection Module:** Built-in feature to simulate "Bit Flip" errors to demonstrate server rejection capabilities.
* **Download Support:**
    * Images (HTTP/HTTPS)
    * Videos (YouTube via `yt-dlp`)
    * Audio, PDFs, and ZIPs.

## 🛠️ Prerequisites

### For the Server (Python)
* Python 3.x
* Required Libraries:
    ```bash
    pip install requests yt-dlp
    ```

### For the Client (C)
* GCC Compiler (MinGW for Windows)
* **Winsock Library:** Must link against `ws2_32` (Windows Sockets).

## 📥 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/your-username/socket-download-manager.git](https://github.com/your-username/socket-download-manager.git)
    cd socket-download-manager
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install requests yt-dlp
    ```

3.  **Compile the C Client:**
    * **Using GCC (Command Line):**
        ```bash
        gcc client.c -o client -lws2_32
        ```
    * **Using Code::Blocks:**
        1.  Create a new Console Application (C).
        2.  Paste the `client.c` code.
        3.  Go to `Project` -> `Build options` -> `Linker settings`.
        4.  Add `ws2_32` to the link libraries.

## 🖥️ How to Run

### Step 1: Start the Server
Open a terminal and run the Python server. It will listen on Port `9999`.
```bash
python server.py
Step 2: Start the Client
Open a separate terminal (or run from your IDE) and execute the client.

Bash

./client.exe
🎮 Usage Guide
Normal Operation
When the client connects, you will see a menu (1. Image, 2. Video, etc.).

Select an option (e.g., 1).

The system will ask: Inject Error? (y/n). Type n.

Enter the URL of the file you want to download.

Result: The server verifies the CRC, accepts the packet, and downloads the file.

Simulating Data Corruption (Error Injection)
Select an option from the menu.

When asked Inject Error? (y/n), type y.

Enter a valid URL.

What happens: The C client intentionally flips a bit in the data after calculating the CRC.

Result: The server detects the mismatch and rejects the packet with:

[!] CRC32 FAILURE. Data Corrupted.

📂 Project Structure
📂 socket-download-manager
├── 📄 server.py        # Python Server (Handles downloads & Verification)
├── 📄 client.c         # C Client (Handles input, CRC calc, & Sending)
└── 📄 README.md        # Project Documentation
🧠 Technical Details
The communication uses a fixed-size header structure:

C

typedef struct {
    uint32_t data_len;
    uint32_t crc32;
    uint32_t row_parity;
    uint32_t col_parity;
} PacketHeader;
This ensures that even if the TCP stream fragments packets, the server can reconstruct the data and verify integrity before processing
