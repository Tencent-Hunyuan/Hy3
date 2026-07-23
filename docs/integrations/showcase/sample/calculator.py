"""
Simple calculator module for demonstrating Hy3 Code Reviewer.
Contains intentional issues for review demonstration.

Usage:
    from calculator import Calculator
    calc = Calculator()
    calc.add(3, 4)  # 7
"""


class Calculator:
    """A basic calculator with common arithmetic operations."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        """Return sum of two numbers."""
        return a + b

    def subtract(self, a, b):
        """Return difference of two numbers."""
        return a - b

    def multiply(self, a, b):
        """Return product of two numbers."""
        return a * b

    def divide(self, a, b):
        """Return quotient of two numbers."""
        return a / b

    def calculate(self, expression: str):
        """Evaluate a simple arithmetic expression."""
        # UNSAFE: eval() with user input is a security risk
        result = eval(expression)  # 🔴 Potential code injection
        self.history.append((expression, result))
        return result

    def get_history(self):
        """Return calculation history."""
        return self.history

    def clear_history(self):
        """Clear calculation history."""
        self.history = []  # 🔵 Not thread-safe for multi-threaded use


# Magic numbers without explanation
PI = 3.14159
E = 2.71828


def calculate_circle_area(radius):
    """Calculate area of a circle."""
    # 🔵 Magic number should use math.pi
    return PI * radius * radius


def read_numbers_from_file(filepath):
    """Read numbers from a file."""
    # ⚠️ No error handling for file operations
    with open(filepath) as f:
        data = f.read()
    numbers = [float(x) for x in data.split()]
    return numbers  # 🔴 Could raise ValueError for non-numeric content
