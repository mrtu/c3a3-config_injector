"""Expression parser for conditional expressions in the Configuration Wrapping Framework.

This module provides a proper expression parser that supports:
- Logical operators: AND, OR, NOT
- Comparison operators: ==, !=, <, >, <=, >=, =~, !~
- Parentheses for grouping
- String literals with proper quoting
- Numeric comparisons
- Regular expression matching
- Better error handling and validation
"""

from __future__ import annotations

import re
import operator
from typing import Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Token types for expression parsing."""
    LITERAL = "LITERAL"
    STRING = "STRING"
    NUMBER = "NUMBER"
    IDENTIFIER = "IDENTIFIER"
    OPERATOR = "OPERATOR"
    LOGICAL = "LOGICAL"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass
class Token:
    """A token in the expression."""
    type: TokenType
    value: str
    position: int


class ExpressionError(Exception):
    """Exception raised for expression parsing or evaluation errors."""
    pass


class ExpressionLexer:
    """Lexer for tokenizing conditional expressions."""

    # Operators and their precedence
    OPERATORS = {
        '==': ('eq', 2),
        '!=': ('ne', 2),
        '<': ('lt', 2),
        '>': ('gt', 2),
        '<=': ('le', 2),
        '>=': ('ge', 2),
        '=~': ('match', 2),  # regex match
        '!~': ('not_match', 2),  # regex not match
    }

    LOGICAL_OPERATORS = {
        'AND': ('and', 1),
        'OR': ('or', 0),
        'NOT': ('not', 3),
        '&&': ('and', 1),
        '||': ('or', 0),
        '!': ('not', 3),
    }

    def __init__(self, expression: str):
        self.expression = expression
        self.position = 0
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """Tokenize the expression into a list of tokens."""
        self.tokens = []
        self.position = 0

        while self.position < len(self.expression):
            self._skip_whitespace()

            if self.position >= len(self.expression):
                break

            char = self.expression[self.position]

            # String literals
            if char in ('"', "'"):
                self._read_string(char)
            # Numbers
            elif char.isdigit() or (char == '-' and self._peek().isdigit()):
                self._read_number()
            # Parentheses
            elif char == '(':
                self.tokens.append(Token(TokenType.LPAREN, char, self.position))
                self.position += 1
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, char, self.position))
                self.position += 1
            # Multi-character operators (including logical operators)
            elif self._check_multi_char_operator():
                pass  # handled in _check_multi_char_operator
            # Multi-character logical operators
            elif self._check_multi_char_logical_operator():
                pass  # handled in _check_multi_char_logical_operator
            # Single character operators
            elif char in '!<>=':
                self._read_operator()
            # Identifiers and keywords
            elif char.isalpha() or char == '_':
                self._read_identifier()
            else:
                raise ExpressionError(f"Unexpected character '{char}' at position {self.position}")

        self.tokens.append(Token(TokenType.EOF, '', self.position))
        return self.tokens

    def _skip_whitespace(self):
        """Skip whitespace characters."""
        while self.position < len(self.expression) and self.expression[self.position].isspace():
            self.position += 1

    def _peek(self, offset: int = 1) -> str:
        """Peek at the next character without advancing position."""
        pos = self.position + offset
        return self.expression[pos] if pos < len(self.expression) else ''

    def _read_string(self, quote_char: str):
        """Read a string literal."""
        start_pos = self.position
        self.position += 1  # Skip opening quote
        value = ''

        while self.position < len(self.expression):
            char = self.expression[self.position]
            if char == quote_char:
                self.position += 1  # Skip closing quote
                self.tokens.append(Token(TokenType.STRING, value, start_pos))
                return
            elif char == '\\' and self._peek() in (quote_char, '\\'):
                # Handle escaped quotes and backslashes
                self.position += 1
                value += self.expression[self.position]
            else:
                value += char
            self.position += 1

        raise ExpressionError(f"Unterminated string literal starting at position {start_pos}")

    def _read_number(self):
        """Read a numeric literal."""
        start_pos = self.position
        value = ''

        # Handle negative numbers
        if self.expression[self.position] == '-':
            value += '-'
            self.position += 1

        # Read digits and decimal point
        while self.position < len(self.expression):
            char = self.expression[self.position]
            if char.isdigit() or char == '.':
                value += char
                self.position += 1
            else:
                break

        self.tokens.append(Token(TokenType.NUMBER, value, start_pos))

    def _check_multi_char_operator(self) -> bool:
        """Check for multi-character operators."""
        for op in sorted(self.OPERATORS.keys(), key=len, reverse=True):
            if self.expression[self.position:self.position + len(op)] == op:
                self.tokens.append(Token(TokenType.OPERATOR, op, self.position))
                self.position += len(op)
                return True
        return False

    def _check_multi_char_logical_operator(self) -> bool:
        """Check for multi-character logical operators like && and ||."""
        # Check for && and ||
        if self.position + 1 < len(self.expression):
            two_char = self.expression[self.position:self.position + 2]
            if two_char in ('&&', '||'):
                self.tokens.append(Token(TokenType.LOGICAL, two_char, self.position))
                self.position += 2
                return True
        return False

    def _read_operator(self):
        """Read a single-character operator."""
        start_pos = self.position
        char = self.expression[self.position]

        # Check for compound operators
        if char == '=' and self._peek() == '=':
            self.tokens.append(Token(TokenType.OPERATOR, '==', start_pos))
            self.position += 2
        elif char == '!' and self._peek() == '=':
            self.tokens.append(Token(TokenType.OPERATOR, '!=', start_pos))
            self.position += 2
        elif char == '<' and self._peek() == '=':
            self.tokens.append(Token(TokenType.OPERATOR, '<=', start_pos))
            self.position += 2
        elif char == '>' and self._peek() == '=':
            self.tokens.append(Token(TokenType.OPERATOR, '>=', start_pos))
            self.position += 2
        elif char == '!' and self._peek() == '~':
            self.tokens.append(Token(TokenType.OPERATOR, '!~', start_pos))
            self.position += 2
        elif char == '=' and self._peek() == '~':
            self.tokens.append(Token(TokenType.OPERATOR, '=~', start_pos))
            self.position += 2
        elif char in '<>':
            self.tokens.append(Token(TokenType.OPERATOR, char, start_pos))
            self.position += 1
        elif char == '!':
            self.tokens.append(Token(TokenType.LOGICAL, '!', start_pos))
            self.position += 1
        else:
            raise ExpressionError(f"Unknown operator '{char}' at position {start_pos}")

    def _read_identifier(self):
        """Read an identifier or keyword."""
        start_pos = self.position
        value = ''

        while self.position < len(self.expression):
            char = self.expression[self.position]
            if char.isalnum() or char == '_':
                value += char
                self.position += 1
            else:
                break

        # Check if it's a logical operator
        if value.upper() in self.LOGICAL_OPERATORS:
            self.tokens.append(Token(TokenType.LOGICAL, value.upper(), start_pos))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER, value, start_pos))


class ExpressionParser:
    """Parser for conditional expressions using recursive descent parsing."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = self.tokens[0] if tokens else Token(TokenType.EOF, '', 0)

    def parse(self) -> 'ExpressionNode':
        """Parse the tokens into an abstract syntax tree."""
        expr = self._parse_or_expression()
        if self.current_token.type != TokenType.EOF:
            raise ExpressionError(f"Unexpected token '{self.current_token.value}' at position {self.current_token.position}")
        return expr

    def _advance(self):
        """Move to the next token."""
        if self.position < len(self.tokens) - 1:
            self.position += 1
            self.current_token = self.tokens[self.position]

    def _parse_or_expression(self) -> 'ExpressionNode':
        """Parse OR expressions (lowest precedence)."""
        left = self._parse_and_expression()

        while self.current_token.type == TokenType.LOGICAL and self.current_token.value in ('OR', '||'):
            op = self.current_token.value
            self._advance()
            right = self._parse_and_expression()
            left = BinaryOpNode(left, op, right)

        return left

    def _parse_and_expression(self) -> 'ExpressionNode':
        """Parse AND expressions."""
        left = self._parse_not_expression()

        while self.current_token.type == TokenType.LOGICAL and self.current_token.value in ('AND', '&&'):
            op = self.current_token.value
            self._advance()
            right = self._parse_not_expression()
            left = BinaryOpNode(left, op, right)

        return left

    def _parse_not_expression(self) -> 'ExpressionNode':
        """Parse NOT expressions (highest precedence for logical operators)."""
        if self.current_token.type == TokenType.LOGICAL and self.current_token.value in ('NOT', '!'):
            op = self.current_token.value
            self._advance()
            operand = self._parse_not_expression()
            return UnaryOpNode(op, operand)

        return self._parse_comparison_expression()

    def _parse_comparison_expression(self) -> 'ExpressionNode':
        """Parse comparison expressions."""
        left = self._parse_primary_expression()

        if self.current_token.type == TokenType.OPERATOR:
            op = self.current_token.value
            self._advance()
            right = self._parse_primary_expression()
            return BinaryOpNode(left, op, right)

        return left

    def _parse_primary_expression(self) -> 'ExpressionNode':
        """Parse primary expressions (literals, identifiers, parentheses)."""
        token = self.current_token

        if token.type == TokenType.STRING:
            self._advance()
            return LiteralNode(token.value)
        elif token.type == TokenType.NUMBER:
            self._advance()
            # Try to parse as int first, then float
            try:
                value = int(token.value)
            except ValueError:
                value = float(token.value)
            return LiteralNode(value)
        elif token.type == TokenType.IDENTIFIER:
            self._advance()
            # Handle boolean literals
            if token.value.lower() in ('true', 'false'):
                return LiteralNode(token.value.lower() == 'true')
            return IdentifierNode(token.value)
        elif token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_or_expression()
            if self.current_token.type != TokenType.RPAREN:
                raise ExpressionError(f"Expected ')' at position {self.current_token.position}")
            self._advance()
            return expr
        else:
            raise ExpressionError(f"Unexpected token '{token.value}' at position {token.position}")


# AST Node classes
class ExpressionNode:
    """Base class for expression AST nodes."""

    def evaluate(self, context: dict) -> Any:
        """Evaluate the expression node with the given context."""
        raise NotImplementedError


class LiteralNode(ExpressionNode):
    """Node for literal values."""

    def __init__(self, value: Any):
        self.value = value

    def evaluate(self, context: dict) -> Any:
        return self.value


class IdentifierNode(ExpressionNode):
    """Node for identifiers (variables)."""

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, context: dict) -> Any:
        if self.name not in context:
            raise ExpressionError(f"Undefined variable: {self.name}")
        return context[self.name]


class BinaryOpNode(ExpressionNode):
    """Node for binary operations."""

    def __init__(self, left: ExpressionNode, operator: str, right: ExpressionNode):
        self.left = left
        self.operator = operator
        self.right = right

    def evaluate(self, context: dict) -> Any:
        left_val = self.left.evaluate(context)

        # Short-circuit evaluation for logical operators
        if self.operator in ('OR', '||'):
            if self._is_truthy(left_val):
                return True
            right_val = self.right.evaluate(context)
            return self._is_truthy(right_val)
        elif self.operator in ('AND', '&&'):
            if not self._is_truthy(left_val):
                return False
            right_val = self.right.evaluate(context)
            return self._is_truthy(right_val)

        # Regular binary operations
        right_val = self.right.evaluate(context)

        if self.operator == '==':
            return self._compare_values(left_val, right_val, operator.eq)
        elif self.operator == '!=':
            return self._compare_values(left_val, right_val, operator.ne)
        elif self.operator == '<':
            return self._compare_values(left_val, right_val, operator.lt)
        elif self.operator == '>':
            return self._compare_values(left_val, right_val, operator.gt)
        elif self.operator == '<=':
            return self._compare_values(left_val, right_val, operator.le)
        elif self.operator == '>=':
            return self._compare_values(left_val, right_val, operator.ge)
        elif self.operator == '=~':
            return self._regex_match(left_val, right_val)
        elif self.operator == '!~':
            return not self._regex_match(left_val, right_val)
        else:
            raise ExpressionError(f"Unknown operator: {self.operator}")

    def _is_truthy(self, value: Any) -> bool:
        """Determine if a value is truthy."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on') and value != ''
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            return bool(value)

    def _compare_values(self, left: Any, right: Any, op) -> bool:
        """Compare two values with type coercion."""
        # Handle boolean/string comparisons specially
        if isinstance(left, bool) and isinstance(right, str):
            # Convert boolean to string for comparison
            left_str = 'true' if left else 'false'
            return op(left_str, right)
        elif isinstance(left, str) and isinstance(right, bool):
            # Convert boolean to string for comparison
            right_str = 'true' if right else 'false'
            return op(left, right_str)

        # Try numeric comparison first
        try:
            if isinstance(left, str) and isinstance(right, str):
                # Try to convert both to numbers
                try:
                    left_num = float(left)
                    right_num = float(right)
                    return op(left_num, right_num)
                except ValueError:
                    # Fall back to string comparison
                    pass
            elif isinstance(left, (int, float)) and isinstance(right, str):
                try:
                    right_num = float(right)
                    return op(left, right_num)
                except ValueError:
                    pass
            elif isinstance(left, str) and isinstance(right, (int, float)):
                try:
                    left_num = float(left)
                    return op(left_num, right)
                except ValueError:
                    pass

            # Direct comparison
            return op(left, right)
        except TypeError:
            # Fall back to string comparison
            return op(str(left), str(right))

    def _regex_match(self, text: Any, pattern: Any) -> bool:
        """Perform regex matching."""
        try:
            text_str = str(text)
            pattern_str = str(pattern)
            return bool(re.search(pattern_str, text_str))
        except re.error as e:
            raise ExpressionError(f"Invalid regex pattern '{pattern}': {e}")


class UnaryOpNode(ExpressionNode):
    """Node for unary operations."""

    def __init__(self, operator: str, operand: ExpressionNode):
        self.operator = operator
        self.operand = operand

    def evaluate(self, context: dict) -> Any:
        operand_val = self.operand.evaluate(context)

        if self.operator in ('NOT', '!'):
            return not self._is_truthy(operand_val)
        else:
            raise ExpressionError(f"Unknown unary operator: {self.operator}")

    def _is_truthy(self, value: Any) -> bool:
        """Determine if a value is truthy."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on') and value != ''
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            return bool(value)


def parse_expression(expression: str) -> ExpressionNode:
    """Parse a conditional expression string into an AST."""
    if not expression or not expression.strip():
        raise ExpressionError("Empty expression")

    lexer = ExpressionLexer(expression.strip())
    tokens = lexer.tokenize()

    parser = ExpressionParser(tokens)
    return parser.parse()


def evaluate_expression(expression: str, context: dict) -> bool:
    """Parse and evaluate a conditional expression."""
    try:
        ast = parse_expression(expression)
        result = ast.evaluate(context)

        # Convert result to boolean
        if isinstance(result, bool):
            return result
        elif isinstance(result, str):
            return result.lower() in ('true', '1', 'yes', 'on') and result != ''
        elif isinstance(result, (int, float)):
            return result != 0
        else:
            return bool(result)
    except Exception as e:
        raise ExpressionError(f"Expression evaluation failed: {e}")
