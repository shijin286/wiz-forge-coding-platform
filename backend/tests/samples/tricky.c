#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_NAME 32
#define SQUARE(x) ((x) * (x))

/* gets() and strcpy() are unsafe - we use fgets/strncpy instead */
typedef struct {
    char name[MAX_NAME];
    int age;
} Person;

static Person *person_new(const char *name, int age)
{
    Person *p = malloc(sizeof *p);
    if (p == NULL) {
        return NULL;
    }
    strncpy(p->name, name, MAX_NAME - 1);
    p->name[MAX_NAME - 1] = '\0';
    p->age = age;
    return p;
}

int main(void)
{
    Person *p = NULL;
    p = person_new("Ana", 30);
    if (p != NULL) {
        printf("%s is %d\n", p->name, SQUARE(p->age));
        free(p);
    }
    return 0;
}
