#include <stdio.h>
#include <string.h>

#define BUFFER_SIZE 64

static int read_line(char *buf, size_t size) {
    if (fgets(buf, (int)size, stdin) == NULL) {
        return -1;
    }
    buf[strcspn(buf, "\n")] = '\0';
    return 0;
}

int main(void) {
    char name[BUFFER_SIZE];
    char line[BUFFER_SIZE];
    if (read_line(name, sizeof name) != 0) {
        return 1;
    }
    snprintf(line, sizeof line, "Hello %s", name);
    printf("%s\n", line);
    return 0;
}
