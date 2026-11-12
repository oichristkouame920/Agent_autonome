#define UNICODE
#define _UNICODE

#include <windows.h>
#include <fcntl.h>
#include <io.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define MAX_MESSAGE_BYTES (1024 * 1024)
#define MAX_FILE_BYTES (1024 * 1024)

static int read_exact(FILE *stream, void *buffer, size_t size) {
    unsigned char *cursor = (unsigned char *)buffer;
    size_t total = 0;

    while (total < size) {
        size_t count = fread(cursor + total, 1, size - total, stream);

        if (count == 0) {
            return 0;
        }

        total += count;
    }

    return 1;
}

static int write_exact(FILE *stream, const void *buffer, size_t size) {
    const unsigned char *cursor = (const unsigned char *)buffer;
    size_t total = 0;

    while (total < size) {
        size_t count = fwrite(cursor + total, 1, size - total, stream);

        if (count == 0) {
            return 0;
        }

        total += count;
    }

    return fflush(stream) == 0;
}

static char *read_native_message(void) {
    uint32_t length = 0;

    if (!read_exact(stdin, &length, sizeof(length))) {
        return NULL;
    }

    if (length == 0 || length > MAX_MESSAGE_BYTES) {
        return NULL;
    }

    char *message = (char *)malloc((size_t)length + 1);

    if (!message) {
        return NULL;
    }

    if (!read_exact(stdin, message, length)) {
        free(message);
        return NULL;
    }

    message[length] = '\0';
    return message;
}

static int write_native_message(const char *message) {
    size_t length_size = strlen(message);

    if (length_size == 0 || length_size > MAX_MESSAGE_BYTES) {
        return 0;
    }

    uint32_t length = (uint32_t)length_size;

    if (!write_exact(stdout, &length, sizeof(length))) {
        return 0;
    }

    return write_exact(stdout, message, length);
}

static int build_bridge_path(wchar_t *buffer, size_t buffer_count, const wchar_t *file_name) {
    DWORD length = GetEnvironmentVariableW(L"LOCALAPPDATA", buffer, (DWORD)buffer_count);

    if (length == 0 || length >= buffer_count) {
        return 0;
    }

    size_t used = wcslen(buffer);
    const wchar_t *suffix = L"\\AgentLocalBridge\\";
    size_t suffix_len = wcslen(suffix);
    size_t file_len = wcslen(file_name);

    if (used + suffix_len + file_len + 1 >= buffer_count) {
        return 0;
    }

    wcscat_s(buffer, buffer_count, suffix);
    wcscat_s(buffer, buffer_count, file_name);
    return 1;
}

static char *read_entire_file(const wchar_t *path) {
    FILE *file = NULL;

    if (_wfopen_s(&file, path, L"rb") != 0 || !file) {
        return NULL;
    }

    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }

    long size = ftell(file);

    if (size <= 0 || size > MAX_FILE_BYTES) {
        fclose(file);
        return NULL;
    }

    if (fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }

    char *buffer = (char *)malloc((size_t)size + 1);

    if (!buffer) {
        fclose(file);
        return NULL;
    }

    size_t count = fread(buffer, 1, (size_t)size, file);
    fclose(file);

    if (count != (size_t)size) {
        free(buffer);
        return NULL;
    }

    buffer[size] = '\0';
    return buffer;
}

static int write_file_atomic(const wchar_t *target_path, const char *content) {
    wchar_t temp_path[MAX_PATH * 4];

    if (swprintf_s(
            temp_path,
            sizeof(temp_path) / sizeof(temp_path[0]),
            L"%ls.tmp.%lu.%lu",
            target_path,
            GetCurrentProcessId(),
            GetTickCount()) < 0) {
        return 0;
    }

    FILE *file = NULL;

    if (_wfopen_s(&file, temp_path, L"wb") != 0 || !file) {
        return 0;
    }

    size_t length = strlen(content);
    size_t written = fwrite(content, 1, length, file);
    int flush_ok = fflush(file) == 0;
    fclose(file);

    if (written != length || !flush_ok) {
        DeleteFileW(temp_path);
        return 0;
    }

    if (!MoveFileExW(
            temp_path,
            target_path,
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        DeleteFileW(temp_path);
        return 0;
    }

    return 1;
}

static int message_contains(const char *message, const char *needle) {
    return message && needle && strstr(message, needle) != NULL;
}

static void handle_poll(void) {
    wchar_t command_path[MAX_PATH * 4];
    wchar_t inflight_path[MAX_PATH * 4];

    if (!build_bridge_path(
            command_path,
            sizeof(command_path) / sizeof(command_path[0]),
            L"command.json")) {
        write_native_message("{\"type\":\"noop\"}");
        return;
    }

    if (!build_bridge_path(
            inflight_path,
            sizeof(inflight_path) / sizeof(inflight_path[0]),
            L"command.inflight.json")) {
        write_native_message("{\"type\":\"noop\"}");
        return;
    }

    if (!MoveFileExW(
            command_path,
            inflight_path,
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        write_native_message("{\"type\":\"noop\"}");
        return;
    }

    char *content = read_entire_file(inflight_path);

    if (!content) {
        DeleteFileW(inflight_path);
        write_native_message("{\"type\":\"noop\"}");
        return;
    }

    write_native_message(content);
    free(content);
}

static void handle_result(const char *message) {
    wchar_t response_path[MAX_PATH * 4];
    wchar_t inflight_path[MAX_PATH * 4];

    if (build_bridge_path(
            response_path,
            sizeof(response_path) / sizeof(response_path[0]),
            L"response.json")) {
        write_file_atomic(response_path, message);
    }

    if (build_bridge_path(
            inflight_path,
            sizeof(inflight_path) / sizeof(inflight_path[0]),
            L"command.inflight.json")) {
        DeleteFileW(inflight_path);
    }

    write_native_message("{\"type\":\"ack\"}");
}

int wmain(void) {
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);

    for (;;) {
        char *message = read_native_message();

        if (!message) {
            break;
        }

        if (message_contains(message, "\"type\"") &&
            message_contains(message, "\"poll\"")) {
            handle_poll();
        } else if (message_contains(message, "\"type\"") &&
                   message_contains(message, "\"result\"")) {
            handle_result(message);
        } else if (message_contains(message, "\"type\"") &&
                   message_contains(message, "\"hello\"")) {
            write_native_message("{\"type\":\"hello_ack\"}");
        } else {
            write_native_message("{\"type\":\"ack\"}");
        }

        free(message);
    }

    return 0;
}
