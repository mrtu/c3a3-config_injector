"""Tests for the expression parser module."""

import pytest

from config_injector.expression_parser import (
    ExpressionError,
    ExpressionLexer,
    TokenType,
    evaluate_expression,
    parse_expression,
)


class TestExpressionLexer:
    """Tests for the expression lexer."""

    def test_tokenize_simple_literals(self):
        """Test tokenizing simple literals."""
        lexer = ExpressionLexer("true false 42 3.14 \"hello\" 'world'")
        tokens = lexer.tokenize()

        assert len(tokens) == 7  # 6 tokens + EOF
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "true"
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "false"
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == "42"
        assert tokens[3].type == TokenType.NUMBER
        assert tokens[3].value == "3.14"
        assert tokens[4].type == TokenType.STRING
        assert tokens[4].value == "hello"
        assert tokens[5].type == TokenType.STRING
        assert tokens[5].value == "world"
        assert tokens[6].type == TokenType.EOF

    def test_tokenize_operators(self):
        """Test tokenizing operators."""
        lexer = ExpressionLexer("== != < > <= >= =~ !~")
        tokens = lexer.tokenize()

        assert len(tokens) == 9  # 8 operators + EOF
        assert all(token.type == TokenType.OPERATOR for token in tokens[:-1])
        assert tokens[0].value == "=="
        assert tokens[1].value == "!="
        assert tokens[2].value == "<"
        assert tokens[3].value == ">"
        assert tokens[4].value == "<="
        assert tokens[5].value == ">="
        assert tokens[6].value == "=~"
        assert tokens[7].value == "!~"

    def test_tokenize_logical_operators(self):
        """Test tokenizing logical operators."""
        lexer = ExpressionLexer("AND OR NOT && || !")
        tokens = lexer.tokenize()

        assert len(tokens) == 7  # 6 logical operators + EOF
        assert all(token.type == TokenType.LOGICAL for token in tokens[:-1])
        assert tokens[0].value == "AND"
        assert tokens[1].value == "OR"
        assert tokens[2].value == "NOT"
        assert tokens[3].value == "&&"
        assert tokens[4].value == "||"
        assert tokens[5].value == "!"

    def test_tokenize_parentheses(self):
        """Test tokenizing parentheses."""
        lexer = ExpressionLexer("(true)")
        tokens = lexer.tokenize()

        assert len(tokens) == 4  # ( true ) EOF
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[2].type == TokenType.RPAREN
        assert tokens[3].type == TokenType.EOF

    def test_tokenize_string_escaping(self):
        """Test tokenizing strings with escaping."""
        lexer = ExpressionLexer('"hello \\"world\\"" \'it\\\'s great\'')
        tokens = lexer.tokenize()

        assert len(tokens) == 3  # 2 strings + EOF
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == 'hello "world"'
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "it's great"

    def test_tokenize_negative_numbers(self):
        """Test tokenizing negative numbers."""
        lexer = ExpressionLexer("-42 -3.14")
        tokens = lexer.tokenize()

        assert len(tokens) == 3  # 2 numbers + EOF
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "-42"
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[1].value == "-3.14"

    def test_tokenize_error_unterminated_string(self):
        """Test error on unterminated string."""
        lexer = ExpressionLexer('"unterminated')
        with pytest.raises(ExpressionError, match="Unterminated string literal"):
            lexer.tokenize()

    def test_tokenize_error_unexpected_character(self):
        """Test error on unexpected character."""
        lexer = ExpressionLexer("true @ false")
        with pytest.raises(ExpressionError, match="Unexpected character '@'"):
            lexer.tokenize()


class TestExpressionParser:
    """Tests for the expression parser."""

    def test_parse_simple_literal(self):
        """Test parsing simple literals."""
        # Boolean literal
        ast = parse_expression("true")
        assert ast.evaluate({}) is True

        ast = parse_expression("false")
        assert ast.evaluate({}) is False

        # String literal
        ast = parse_expression('"hello"')
        assert ast.evaluate({}) == "hello"

        # Number literal
        ast = parse_expression("42")
        assert ast.evaluate({}) == 42

        ast = parse_expression("3.14")
        assert ast.evaluate({}) == 3.14

    def test_parse_identifier(self):
        """Test parsing identifiers."""
        ast = parse_expression("myvar")
        context = {"myvar": "hello"}
        assert ast.evaluate(context) == "hello"

        # Test undefined variable
        with pytest.raises(ExpressionError, match="Undefined variable: undefined"):
            ast = parse_expression("undefined")
            ast.evaluate({})

    def test_parse_comparison_operators(self):
        """Test parsing comparison operators."""
        # Equality
        ast = parse_expression('"hello" == "hello"')
        assert ast.evaluate({}) is True

        ast = parse_expression('"hello" == "world"')
        assert ast.evaluate({}) is False

        # Inequality
        ast = parse_expression('"hello" != "world"')
        assert ast.evaluate({}) is True

        # Numeric comparisons
        ast = parse_expression("5 > 3")
        assert ast.evaluate({}) is True

        ast = parse_expression("5 < 3")
        assert ast.evaluate({}) is False

        ast = parse_expression("5 >= 5")
        assert ast.evaluate({}) is True

        ast = parse_expression("3 <= 5")
        assert ast.evaluate({}) is True

    def test_parse_logical_operators(self):
        """Test parsing logical operators."""
        # AND
        ast = parse_expression("true AND true")
        assert ast.evaluate({}) is True

        ast = parse_expression("true AND false")
        assert ast.evaluate({}) is False

        # OR
        ast = parse_expression("true OR false")
        assert ast.evaluate({}) is True

        ast = parse_expression("false OR false")
        assert ast.evaluate({}) is False

        # NOT
        ast = parse_expression("NOT true")
        assert ast.evaluate({}) is False

        ast = parse_expression("NOT false")
        assert ast.evaluate({}) is True

    def test_parse_regex_operators(self):
        """Test parsing regex operators."""
        # Match
        ast = parse_expression('"hello world" =~ "world"')
        assert ast.evaluate({}) is True

        ast = parse_expression('"hello world" =~ "xyz"')
        assert ast.evaluate({}) is False

        # Not match
        ast = parse_expression('"hello world" !~ "xyz"')
        assert ast.evaluate({}) is True

        ast = parse_expression('"hello world" !~ "world"')
        assert ast.evaluate({}) is False

    def test_parse_parentheses(self):
        """Test parsing expressions with parentheses."""
        ast = parse_expression("(true)")
        assert ast.evaluate({}) is True

        ast = parse_expression("(true AND false) OR true")
        assert ast.evaluate({}) is True

        ast = parse_expression("true AND (false OR true)")
        assert ast.evaluate({}) is True

    def test_parse_operator_precedence(self):
        """Test operator precedence."""
        # NOT has higher precedence than AND
        ast = parse_expression("NOT false AND true")
        assert ast.evaluate({}) is True  # (NOT false) AND true = true AND true = true

        # AND has higher precedence than OR
        ast = parse_expression("false OR true AND false")
        assert (
            ast.evaluate({}) is False
        )  # false OR (true AND false) = false OR false = false

        ast = parse_expression("true AND false OR true")
        assert (
            ast.evaluate({}) is True
        )  # (true AND false) OR true = false OR true = true

    def test_parse_complex_expression(self):
        """Test parsing complex expressions."""
        expr = (
            '(status == "active" AND count > 5) OR (debug == true AND NOT production)'
        )
        ast = parse_expression(expr)

        context = {"status": "active", "count": 10, "debug": True, "production": False}
        assert ast.evaluate(context) is True

        context = {"status": "inactive", "count": 3, "debug": True, "production": False}
        assert ast.evaluate(context) is True  # Second part is true

        context = {"status": "inactive", "count": 3, "debug": False, "production": True}
        assert ast.evaluate(context) is False

    def test_parse_error_unexpected_token(self):
        """Test parse error on unexpected token."""
        with pytest.raises(ExpressionError, match="Unexpected token"):
            parse_expression("true ==")

    def test_parse_error_missing_parenthesis(self):
        """Test parse error on missing parenthesis."""
        with pytest.raises(ExpressionError, match="Expected '\\)'"):
            parse_expression("(true")


class TestExpressionEvaluation:
    """Tests for expression evaluation."""

    def test_evaluate_expression_function(self):
        """Test the evaluate_expression convenience function."""
        assert evaluate_expression("true", {}) is True
        assert evaluate_expression("false", {}) is False
        assert evaluate_expression('"hello" == "hello"', {}) is True
        assert evaluate_expression("x > 5", {"x": 10}) is True

    def test_type_coercion_string_to_number(self):
        """Test type coercion from string to number."""
        ast = parse_expression('"10" > "5"')
        assert ast.evaluate({}) is True  # Should compare as numbers

        ast = parse_expression('x > "5"')
        assert ast.evaluate({"x": 10}) is True

        ast = parse_expression('"10" > y')
        assert ast.evaluate({"y": 5}) is True

    def test_type_coercion_fallback_to_string(self):
        """Test fallback to string comparison."""
        ast = parse_expression('"abc" > "def"')
        assert ast.evaluate({}) is False  # String comparison

        ast = parse_expression('"10a" == "10a"')
        assert ast.evaluate({}) is True

    def test_truthy_evaluation(self):
        """Test truthy evaluation for different types."""
        # String truthy values
        for value in ["true", "1", "yes", "on"]:
            ast = parse_expression("x")
            assert ast.evaluate({"x": value}) == value
            # Test in boolean context
            ast = parse_expression("x OR false")
            assert ast.evaluate({"x": value}) is True

        # String falsy values
        for value in ["false", "0", "no", "off", ""]:
            ast = parse_expression("x")
            assert ast.evaluate({"x": value}) == value
            # Test in boolean context
            ast = parse_expression("x AND true")
            assert ast.evaluate({"x": value}) is False

        # Numeric truthy/falsy
        ast = parse_expression("x AND true")
        assert ast.evaluate({"x": 1}) is True
        assert ast.evaluate({"x": 0}) is False
        assert ast.evaluate({"x": -1}) is True

    def test_short_circuit_evaluation(self):
        """Test short-circuit evaluation for logical operators."""
        # OR short-circuit: if left is true, right is not evaluated
        ast = parse_expression("true OR undefined_var")
        assert ast.evaluate({}) is True  # Should not fail on undefined_var

        # AND short-circuit: if left is false, right is not evaluated
        ast = parse_expression("false AND undefined_var")
        assert ast.evaluate({}) is False  # Should not fail on undefined_var

    def test_regex_matching(self):
        """Test regex matching functionality."""
        ast = parse_expression('"test123" =~ "\\\\d+"')
        assert ast.evaluate({}) is True

        ast = parse_expression('"hello" =~ "^h.*o$"')
        assert ast.evaluate({}) is True

        ast = parse_expression('"hello" =~ "^world"')
        assert ast.evaluate({}) is False

        # Test invalid regex
        with pytest.raises(ExpressionError, match="Invalid regex pattern"):
            ast = parse_expression('"test" =~ "["')
            ast.evaluate({})

    def test_empty_expression_error(self):
        """Test error on empty expression."""
        with pytest.raises(ExpressionError, match="Empty expression"):
            parse_expression("")

        with pytest.raises(ExpressionError, match="Empty expression"):
            parse_expression("   ")

    def test_evaluation_error_handling(self):
        """Test error handling during evaluation."""
        with pytest.raises(ExpressionError, match="Expression evaluation failed"):
            evaluate_expression("undefined_var", {})


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing expressions."""

    def test_simple_boolean_expressions(self):
        """Test simple boolean expressions that currently work."""
        assert evaluate_expression("true", {}) is True
        assert evaluate_expression("false", {}) is False
        assert evaluate_expression("1", {}) is True  # Truthy number
        assert evaluate_expression("0", {}) is False  # Falsy number

    def test_simple_equality_expressions(self):
        """Test simple equality expressions that currently work."""
        assert evaluate_expression('"hello" == "hello"', {}) is True
        assert evaluate_expression('"hello" == "world"', {}) is False
        assert evaluate_expression('"hello" != "world"', {}) is True
        assert evaluate_expression('"hello" != "hello"', {}) is False

    def test_token_expansion_compatibility(self):
        """Test that expressions work with token expansion results."""
        # Simulate token expansion results
        context = {"DEBUG": "true", "PRODUCTION": "false", "ENV": "development"}

        # These are the types of expressions used in existing tests
        assert evaluate_expression('DEBUG == "true"', context) is True
        assert evaluate_expression('PRODUCTION == "true"', context) is False
        assert evaluate_expression('ENV == "development"', context) is True


if __name__ == "__main__":
    pytest.main([__file__])
