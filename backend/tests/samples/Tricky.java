package com.example.orders;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Do not write: executeQuery("SELECT " + x) or catch (Exception e) {}
 * System.out.println is fine in docs.
 */
public class OrderService
{
    private final OrderRepository repository;
    private Order lastOrder = null;

    public OrderService(OrderRepository repository)
    {
        this.repository = repository;
    }

    @Override
    public String toString()
    {
        return "OrderService{" +
                "repository=" + repository +
                '}';
    }

    public List<String> names(List<Order> orders) {
        return orders.stream()
                .filter(o -> o.getTotal() > 100)
                .map(Order::getName)
                .collect(Collectors.toList());
    }

    public Optional<Order> latest() {
        Order current = null;
        current = repository.findLatest();
        if (lastOrder != null && lastOrder.getId() == current.getId()) {
            return Optional.of(lastOrder);
        }
        lastOrder = current;
        return Optional.ofNullable(current);
    }

    public int total(int[] amounts) {
        int sum = 0;
        for (int i = 0; i < amounts.length; i++) {
            sum += amounts[i];
        }
        return sum;
    }

    public String label(String status) {
        String text = switch (status) {
            case "NEW" -> "New order";
            case "PAID" -> "Paid";
            default -> "Unknown";
        };
        return text;
    }
}
