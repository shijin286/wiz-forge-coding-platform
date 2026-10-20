#include <iostream>
#include <memory>
#include <string>
#include <vector>

class Greeter {
public:
    explicit Greeter(std::string name) : name_(std::move(name)) {}
    void greet() const {
        std::cout << "Hello " << name_ << std::endl;
    }

private:
    std::string name_;
};

int main() {
    auto greeter = std::make_unique<Greeter>("world");
    std::vector<int> values(10, 0);
    for (int v : values) {
        if (v > 0) {
            std::cout << v << '\n';
        }
    }
    greeter->greet();
    return 0;
}
