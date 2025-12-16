#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h>
#include <windows.h>
#include <stdint.h>

#pragma comment(lib, "ws2_32.lib")

#define SERVER_IP "127.0.0.1"
#define SERVER_PORT 9999
#define BUFFER_LENGTH 1024
#define MATRIX_WIDTH 8 // 2D Parity Matrix Width

// Packet Header Structure
typedef struct {
    uint32_t data_len;
    uint32_t crc32;
    uint32_t row_parity; // Simple XOR sum of rows
    uint32_t col_parity; // Simple XOR sum of columns
} PacketHeader;

// --- CRC32 Implementation ---
uint32_t calculate_crc32(const char *data, size_t length) {
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= (unsigned char)data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320;
            else
                crc >>= 1;
        }
    }
    return ~crc;
}

// --- 2D Parity Implementation ---
// We treat the buffer as a matrix of width 8.
void calculate_2d_parity(const char *data, size_t length, uint32_t *row_p, uint32_t *col_p) {
    *row_p = 0;
    *col_p = 0;

    // Column parity array (8 bytes since width is 8)
    unsigned char cols[MATRIX_WIDTH] = {0};

    for (size_t i = 0; i < length; i++) {
        unsigned char byte = data[i];

        // Update Column Parity
        cols[i % MATRIX_WIDTH] ^= byte;

        // Update Row Parity (Accumulate XOR for the current "row" logic, strictly we just XOR everything for a simple hash or do per-row)
        // To stick to strict 2D Matrix definitions in a single integer for transport, we will XOR the bytes.
        // A more complex implementation would send an array, but for this assignment, we hash the rows into one integer.
        *row_p ^= byte;
    }

    // Pack column array into uint32 for transport (just taking first 4 bytes for simplicity of transport struct)
    // Real 2D parity usually appends bytes, but we need to fit requirements into a header.
    // We will pack the first 4 columns into the integer.
    memcpy(col_p, cols, 4);
}

// --- Error Injection (Bit Flip) ---
void inject_error(char *data, size_t length) {
    if (length > 0) {
        printf("\n[!!!] INJECTING ERROR: Flipping bit in first byte...\n");
        data[0] ^= 0x01; // Flip the last bit of the first byte
    }
}

int main() {
    WSADATA wsa_data;
    SOCKET client_socket;
    struct sockaddr_in server_info;
    char message_buffer[BUFFER_LENGTH];
    char send_buffer[BUFFER_LENGTH];
    int received_data_len;

    // Initialize Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        fprintf(stderr, "Winsock init failed.\n");
        return EXIT_FAILURE;
    }

    // Create socket
    if ((client_socket = socket(AF_INET, SOCK_STREAM, 0)) == INVALID_SOCKET) {
        fprintf(stderr, "Socket creation failed.\n");
        WSACleanup();
        return EXIT_FAILURE;
    }

    server_info.sin_family = AF_INET;
    server_info.sin_addr.s_addr = inet_addr(SERVER_IP);
    server_info.sin_port = htons(SERVER_PORT);

    if (connect(client_socket, (struct sockaddr *)&server_info, sizeof(server_info)) < 0) {
        fprintf(stderr, "Connection failed.\n");
        closesocket(client_socket);
        WSACleanup();
        return EXIT_FAILURE;
    }

    printf("Connected to Server. CRC & Parity active.\n");

    while (1) {
        memset(message_buffer, 0, BUFFER_LENGTH);

        // 1. Receive Menu/Message from Python Server
        received_data_len = recv(client_socket, message_buffer, BUFFER_LENGTH - 1, 0);
        if (received_data_len <= 0) break;

        printf("\nSERVER SAYS:\n%s\n", message_buffer);

        // Check if server is saying goodbye
        if (strstr(message_buffer, "Goodbye")) break;

        // 2. Get User Input
        printf("Your Input: ");
        fgets(send_buffer, BUFFER_LENGTH, stdin);
        send_buffer[strcspn(send_buffer, "\n")] = 0; // Remove newline

        // 3. Ask for Error Injection (For Demonstration)
        printf("Inject Error? (y/n): ");
        char choice;
        scanf(" %c", &choice);
        while(getchar() != '\n'); // flush stdin

        // 4. Prepare Packet
        PacketHeader header;
        header.data_len = strlen(send_buffer);

        // Calculate CHECKSUMS BEFORE ERROR INJECTION (To simulate valid sender generation)
        header.crc32 = calculate_crc32(send_buffer, header.data_len);
        calculate_2d_parity(send_buffer, header.data_len, &header.row_parity, &header.col_parity);

        // 5. Inject Error if requested
        if (choice == 'y' || choice == 'Y') {
            inject_error(send_buffer, header.data_len);
        }

        // 6. Send Header + Data
        send(client_socket, (char*)&header, sizeof(header), 0);
        send(client_socket, send_buffer, header.data_len, 0);
    }

    closesocket(client_socket);
    WSACleanup();
    return EXIT_SUCCESS;
}
