
import java.util.*;

class Employee {
    String name;
    double salary;

    Employee(String name, double salary) {
        this.name = name;
        this.salary = salary;
    }

    double calculateBonus() {
        if (salary >= 50000) {
            return salary * 0.20;
        } else {
            return salary * 0.10;
        }
    }
}

public class Main {
    public static void main(String[] args) {

        ArrayList<Employee> employees = new ArrayList<>();

        employees.add(new Employee("Arun", 60000));
        employees.add(new Employee("Meera", 45000));
        employees.add(new Employee("Rahul", 75000));

        double totalBonus = 0;

        for (Employee emp : employees) {
            double bonus = emp.calculateBonus();

            totalBonus += bonus;

            System.out.println("Employee: " + emp.name);
            System.out.println("Salary: " + emp.salary);
            System.out.println("Bonus: " + bonus);
            System.out.println("-------------------");
        }

        System.out.println("Total Bonus: " + totalBonus);

        Employee e = employees.get(0);
        System.out.println(e.name);
    }
}
