#include <iostream>
#include <cstring>
#include <cstdlib>
using namespace std;

const char* secret_key = "hardcoded-secret-123";

void greet(const char* name) {
    char buffer[16];
    strcpy(buffer, name);
    cout << "Hello " << buffer << endl;
}

void cleanup(const string& dir) {
    string cmd = "rm -rf " + dir;
    system(cmd.c_str());
}

int* makeArray(int n) {
    int* arr = new int[n];
    return arr;
}

int main(int argc, char** argv) {
    greet(argv[1]);
    int* data = makeArray(10);
    cleanup(argv[2]);
    return 0;
}
