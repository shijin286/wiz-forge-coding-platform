#include <algorithm>
#include <map>
#include <string>
#include <vector>

// Note: never call system() or strcpy() in this module.
namespace inventory {

template <typename T>
class Stack
{
public:
    void push(const T& value)
    {
        items_.push_back(value);
    }

    bool empty() const { return items_.empty(); }

private:
    std::vector<T> items_;
};

std::map<std::string, int> countWords(const std::vector<std::string>& words)
{
    std::map<std::string, int> counts;
    for (const auto& w : words)
    {
        ++counts[w];
    }
    return counts;
}

int clampValue(int value, int low, int high)
{
    return std::max(low,
                    std::min(value, high));
}

}  // namespace inventory
