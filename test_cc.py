import subprocess
import unittest
import uuid

from cc import *


class TestParser(unittest.TestCase):
    def parse(self, src):
        my_cool_parser = Parser(Lex(src))
        my_cool_parser.parse_program()

    def test_long_varname(self):
        try:
            self.parse("""
            program longvarname {
                declare asdfghjklasdfghjklasdfghjklasdfghjlk;
                asdfghjklasdfghjklasdfghjklasdfghjlk := 1;
                print(asdfghjklasdfghjklasdfghjklasdfghjlk);
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Variable name cannot be more than 30 chars." in str(e)

    def test_var_that_starts_with_num(self):
        try:
            self.parse("""
            program invalidvarname {
                declare 123myCoolVar;
                print(123myCoolVar);
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Variable name cannot start with a number." in str(e)

    def test_invalid_char(self):
        try:
            self.parse("""
            program InvalidChar {
                declare x;
                x := 15 ^ 4;
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Invalid character" in str(e)

    def test_large_number(self):
        try:
            self.parse("""
            program largenumber {
                declare x;
                x := 4294967295;             # this should be ok #
                x := 99999999999999999999999 # this should raise an error #
                print(x);
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Constant max value is 2^32-1" in str(e)

    def test_cimple_constructs(self):
        self.parse("""
        # this program covers all the programming constructs that cimple offers #
        program coverage {
            declare a, b, c;
            declare d, e, f;
            declare ;
            
            procedure log(in y) {
                print(y);
            }
        
            function sqr(in y) {
                y := 1 * y * y + 0 + 0 * 1;
                call log(in y);
                return (y);
            }

            # f1 receives a number x, multiplies it by 2, squares it and returns the result #
            function f1(in x) {
                function mul(in x) {
                    return (2 * x);
                }
        
                x := mul(in x);
                return (sqr(in x));
            }
                
            # incr_by increments the given val by n #
            procedure incrBy(inout val, in n) {
                val := val + n;
            }
        
            input(a);                   # 10 #
            b := f1(in a);              # 400 #
            call incrBy(inout a, in b); # 410 #
        
            if (a < 500) print(0);
            else if (a>=500 and b<400) {
                print(1)
            }
            else if ([a<>1 or b=2 and c=3] or f=4) {
                print(2)
            }
            else if (not [a=1 or b>2 and c>=3] or f=4) {
                print(3)
            };;;;
        
            while (a > 0) {
                a := a - 1;
            };
        
            switchcase
                case (a > 0)
                    print(0);
                default {
                    a := -100;
                };
        
            forcase
                case (a < 0)
                    a := a + 10;
                default {
                    a := -0;
                };
        
            incase
                case (a <> 0)
                    a := (0);
        }.
        """)

    def test_complex_args(self):
        self.parse("""
        program largenumber {
            declare x;

            function f1(in x, inout y) {
                return (x + y)
            }
            x := 5;
            x := f1(
                in f1(in 3, inout x), # f1(3, 5)=8 #
                inout x               # x=5 #
            ); # x=8+5=13 #
        }.
        """)


class TestGeneratedCCode(unittest.TestCase):
    def assert_c_output_is(self, expected_outputs, src):
        my_cool_parser = Parser(Lex(src))
        my_cool_parser.parse_program()
        c_equivalent = my_cool_parser.gen_c_equivalent()

        c_src = "/tmp/" + str(uuid.uuid4()) + ".c"
        c_bin = "/tmp/" + str(uuid.uuid4())

        with open(c_src, "w") as fp:
            fp.write(c_equivalent)

        subprocess.check_output(["gcc", "-o", c_bin, c_src])
        actual_outputs = (subprocess.check_output(c_bin).decode("utf-8")).strip().split("\n")
        self.assertEqual(expected_outputs, actual_outputs)

    def test_basic_math(self):
        self.assert_c_output_is(["25", "-5", "1", "150"], src="""
        program BasicMath {
            declare a, b;
            
            a := 10;
            b := 15;

            print(a + b);
            print(a - b);
            print(b / a);
            print(b * a);
        }.
        """)

    def test_math_precedence(self):
        self.assert_c_output_is(["26", "30", "6", "-20", "-40"], src="""
        program MathPrecedence {
            print(1 + 5 * 5);
            print((1 + 5) * 5);
            print(1 + 5 / 5 * 5);
            print(-5 * 5 + 5);
            print((10 + 20 * 5 / 5) / 3 - 5 * 10);
        }.
        """)

    def test_if(self):
        self.assert_c_output_is(["2", "3", "4", "6"], src="""
        program IfSomethingDoSomething{
            declare a, b;
            
            a := 10;
            b := 5;
            
            if (a < b) { print(1); };
            
            if (a > b) { print(2); };
            
            if (a < b or a > b) { print(3); };
            
            if (a > b or a < b and a = 100) { print(4); };
            
            if ([a > b or a < b] and [a = 100]) { print(5); };
            
            if (not[a = b or a < b] and not[a = 100]) { print(6); };
        }.
        """)

    def test_else(self):
        self.assert_c_output_is(["1", "3", "5", "6"], src="""
        program IfSomethingDoSthElseDoSthElse {
            declare a, b;
            
            a := 10;
            b := 100;
            
            if (a < b) {
                print(1);
            } else {
                print(2);
            };
            print(3);
            
            if (a = b) {
                print(4);
            } else {
                print(5);
            };
            print(6);
        }.
        """)

    def test_while(self):
        self.assert_c_output_is(["1", "2", "3", "4"], src="""
        program WhileSomethingDoSomething {
            declare a, b;
            
            a := 1;
            b := 5;
            
            while (a < b) {
                print(a);
                a := a + 1;
            };
        }.
        """)

    def test_switchcase(self):
        self.assert_c_output_is(["2", "8"], src="""
        program SwitchCaseGtIfElseBlocks {
            declare a;
            declare b;
            
            a := 11; b := 11;
            switchcase
                case(a < b) { print(1); }
                case(a = b) { print(2); }
                case(a > b) { print(3); }
                default { print(4); };
            
            switchcase
                case(a = 1) { print(5); }
                case(a = 2) { print(6); }
                case(a = 3) { print(7); }
                default { print(8); }
        }.
        """)

    def test_forcase(self):
        self.assert_c_output_is(["1", "3", "2", "3", "100"], src="""
        program ForCaseGtForWithIfElse {
            declare a;
            declare b;
            
            a := 1;
            b := 3;
            
            forcase
                case(a < b) {
                    print(a); print(b);
                    a := a + 1;
                    
                }
                case(b > a) {
                    print(a); print(b);
                    b := b - 1;
                }
                default {
                    print(100);
                }
        }.
        """)

    def test_incase(self):
        self.assert_c_output_is(["1", "5", "2", "5", "2", "4", "3", "4", "100"], src="""
        program InCaseIsLit {
            declare a;
            declare b;
            
            a := 1;
            b := 5;

            incase
                case(a < b) {
                    print(a); print(b);
                    a := a + 1;
                }
                case(b > a) {
                    print(a); print(b);
                    b := b - 1;
                };

            print(100);
        }.
        """)


class TestStValidations(unittest.TestCase):
    def parse(self, src):
        my_cool_parser = Parser(Lex(src))
        my_cool_parser.parse_program()

    def test_undeclared_variable(self):
        try:
            self.parse("""
            program test {
                print(1);
                a := 10;
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'a' does not" in str(e)

    def test_undeclared_function(self):
        try:
            self.parse("""
            program test {
                declare a;
                
                a := f(in 123);
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'f' does not" in str(e)

    def test_assign_to_function(self):
        try:
            self.parse("""
            program test {
                declare a;
                
                function f() {
                    print(1);
                }

                f := a + 10;
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'f' does not" in str(e)

    def test_calling_a_function_declared_later(self):
        try:
            self.parse("""
            program test {
                declare a;

                function f() {
                    f2(); # error, f2 should be declared above f() to be callable. #
                }
                
                function f2() {
                    print(2);
                };

                f()
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'f2' does not" in str(e)

    def test_redeclaring_var_with_var(self):
        try:
            self.parse("""
            program test {
                declare a, b, c, a, d; # a is declared twice #
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'a' is already declared" in str(e)

    def test_redeclaring_var_with_fn(self):
        try:
            self.parse("""
            program test {
                declare a, b;
                
                function f1() {
                    print(1);
                }
                
                function a() { # error a is already declared #
                    print(2);
                }
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'a' is already declared" in str(e)

    def test_shadowing_is_not_raising_an_error(self):
        self.parse("""
        program test {
            declare a, b;

            function f1() {
                declare a;  # shadows 'a' from main scope (no problem) #
                a := 1;
                print(a);
            }
        }.
        """)

    def test_calling_a_proc_like_a_func(self):
        try:
            self.parse("""
            program test {
                declare a;
                procedure p1() {
                    print(1);
                }

                a := p1();
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'p1' does not" in str(e)

    def test_calling_a_func_like_a_proc(self):
        try:
            self.parse("""
            program test {
                function f1() {
                    print(1);
                }

                call f1();
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'f1' does not" in str(e)

    def test_ignoring_func_result(self):
        try:
            self.parse("""
            program test {
                function f1() {
                    print(1);
                }

                f1(); # this is not allowed, you should use a procedure instead #
            }.
            """)
            assert False
        except CompilationError as e:
            assert "Symbol 'f1' does not" in str(e)

    def test_using_var_from_outer_scope(self):
        self.parse("""
        program test {
            declare a;
            procedure p1() {
                declare b, y;
                function f1() {
                    declare c;
                    procedure p2() {
                        declare d, x;                            
                        function f2() {
                            print(a + b + c + d);
                            return (1);
                        }
                        x := f2();
                    }
                    call p2();
                    return (2);
                }
                y := f1();
            }
            
            call p1();
        }.
        """)
