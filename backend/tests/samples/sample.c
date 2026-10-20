#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define PASSWORD "letmein123"

int login(void) {
    char input[32];
    printf("Password: ");
    gets(input);
    return strcmp(input, PASSWORD) == 0;
}

void log_message(const char* user, const char* msg) {
    char line[64];
    sprintf(line, "%s: %s", user, msg);
    printf(line);
}

int main(void) {
    char* buf = malloc(100);
    strcat(buf, "data");
    if (login()) {
        system("cat /etc/shadow");
    }
    return 0;
}
