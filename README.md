# cimple

A simple, yet extendable programming language, built for educational purposes that compiles to RISC-V assembly.

Built during [cs.uoi.gr](https://www.cs.uoi.gr/) compilers course.

## Index Tree

1. [Hello World](#1-hello-world)
2. [Using The Compiler](#2-using-the-compiler)
3. [Input / Output](#3-input--output)
4. [Data Types](#4-data-types)
5. [Variables](#5-variables)
6. [Operators](#6-operators)
7. [Decision Making](#7-decision-making)
8. [Loops](#8-loops)
9. [Subprograms](#9-subprograms)
10. [Scopes](#10-scopes)
11. [Compilation Errors](#11-compilation-errors)
12. [Technical Details](#12-technical-details)
13. [Development](#13-development)

<div style="page-break-after: always;"></div>

## 1. Hello world

We are going to start learning cimple by writing the traditional `hello world` program. This is the simplest program
someone can write.

```
# examples/01_hello_world.ci #

program helloWorld {
    print(1);
}.
```

Let's see all the parts of this program:

1. The first line of this program is a comment, comments in cimple start and end with a `#` character.

2. A program starts with the `program` keyword followed by its name, we decided to name our program `helloWorld`.

3. Code is nested in blocks that start with `{` and end with `}`, similar to C, Java and others.

4. In our code we called the built-in `print` function with the constant *1* as argument.

5. Statements should end with a `;` but this is optional for the last statement of the block. Based on that
   in our `print(1);` statement, `;` wasn't required.

7. All cimple programs should end with a `. (dot)` character.

<div style="page-break-after: always;"></div>

## 2. Using the compiler

The compiler is written in a single file, following the course instructions.
You can install it globally with `cp cc.py /usr/local/bin/uoicc` and then run it with `uoicc`.

### Compiling to RISC-V assembly

You can compile the 'hello world' program by running:

```
uoicc examples/01_hello_world.ci
```

Congratulations, you just compiled your first cimple program.
The resulting RISC-V instructions should be at `examples/01_hello_world.ci.asm`

### Generating C-Equivalent code

You can also generate C equivalent code by appending the `--gen-c` flag to the compiler

```
# run the compiler with --gen-c flag
uoicc examples/01_hello_world.ci --gen-c

# compile and run the C-equivalent code with gcc
gcc -o hello_world ./examples/01_hello_world.ci.c
./hello_world
```

This is essentially useful if you want to debug your programs faster.

> Note: Subprograms do not support this feature.

<div style="page-break-after: always;"></div>

## 3. Input / Output

In cimple there are two builtin functions that deal with input and output.

- **print** prints a number to the standard output.
- **input** reads a number from the standard input.

```
program IO {
   declare x;
   input(x);     # read a number and place it in x #
   print(x * 2); # print the number multiplied by two #
}.
```

Reading and writing to files is not supported.


<div style="page-break-after: always;"></div>

## 4. Data types

Cimple is an educational purpose built programming language so it only
supports 32bit integers, but it's easy to extend it with more data types.
> Range of supported numbers: `[-4294967295, 4294967295]`

Try compiling the following program:

```
program numOverflow {
    print(4294967295); # all good #
    print(4294967296); # too large #
}.
```

The compiler will catch the issue in compile-time.
You should see the following compilation error (more on compilation errors later):

```
ERROR: Constant max value is 2^32-1 (4294967295).
(3:21)   near: `...4294967296); # too l...`
```

<div style="page-break-after: always;"></div>

## 5. Variables

In cimple you can declare variables with the `declare` keyword and assign to them with the assignment `:=` operator.

```
program vars {
   declare a, b;
   
   a := 123;
   b := 333;
   
   print(a);
   print(b);
}.
```

By default all variables are mutable. Constants do not exist in cimple.

<div style="page-break-after: always;"></div>

## 6. Operators

### Arithmetic

Cimple supports only the basic arithmetic operators for addition, subtraction, multiplication and division.

```
program arithmeticOps {
   print(8 + 2);
   print(12 - 2);
   print(2 * 5);
   print(1000 / 100);
}.
```

The **precedence** of the operators is similar to other programming languages.
`Multiplication, Division > Addition, Subtraction`. You can use parenthesis to make some operation first.

```
program precedence {
   print(1 + 2 * 6 / 4)
   # should print 4: 1 + ((2*6) / 4) #

   print((1 + 2) * (6 / 4)) # should print 3 #
   # cimple doesn't support floating point numbers, so 6/4 results to 1 #
}.
```

### Relational

The relational operators are

- `=` equal
- `<>` not equal
- `>` greater than
- `>=` greater than or equal
- `<` less than
- `<=` less than or equal

The following program will print `1` if `x` is equal to `123`.

```
program relationalOper {
   declare x;
   x := 123;

   if (x = 123) {
      print(1)
   }
}.
```

### Conditional

Cimple supports the `and`, `not` and `or` operators similar to python.

The precedence is `not > and > or`. You can override this behavior by wraping some sub-conditions in brackets `[`, `]`.

Here is an example program with such conditions.

This program asks user for two numbers `x` and `y` and if `z` is not `0` increments both until both are non-negative.

```
program Conditions {
   declare x, y, z;
   input(x);
   input(y);
   z := 0;

   while (not [z = 0] and [x < 0 or y < 0]) {
      x := x + 1;
      y := y + 1;
   };

   print(x);
   print(y);
}.
```

<div style="page-break-after: always;"></div>

## 7. Decision-making

In the previous example we've seen the `if` keyword, which is similar to most programming languages.
Let's see all the decision-making concepts that cimple offers.

1. If

As we've already seen, *if* will check the condition and if it is true all the statements will be executed.

```
if (x < y) {
   print(1);
}
```

2. If-Else

You can use an *else* block to execute some statements when the `if` condition is false.

```
if (x < y) {
   print(1);
} else {
   print(2);
}
```

3. Switchcase

Cimple also supports a more special conditional building block, Switchcase. *switchcase*, will execute the statements of
the first matched case and then exit.

If none of the cases were matched then the *default* case will be executed.

This is much better than chaining multiple if-else blocks.

```
switchcase
   case (x=1)
      print(100);
   case (x=2) {
      print(123);
      print(200);
   }
   default {
      print(123);
      print(999);
   }
```

Note: The default case is always required.

<div style="page-break-after: always;"></div>

## 8. Loops

Loops are useful if you want to execute some statements until a certain condition is met.
Cimple supports three looping mechanisms.

1. While

The most common loop mechanism, supported by most programming languages. The statements are executed while the condition
is true.

```
while(x < 100) {
   x := x + 1;
}
```

2. Forcase

Cases are matched in order, if any case is matched, the statements of it are executed and after that we repeat.
If none of the cases is matched then the default statements are executed and the loop ends.

```
# the following code will increase x and y until they reach 10, if they are less than 10 #
# in the end the values of x and y will be printed at the default case #
# one of x, y is incremented per iteration #

forcase
   case (x < 10)
      x := x + 1;
   case (y < 10)
      y := y + 1;
   default {
      print(x);
      print(y)
   }
```

<div style="page-break-after: always;"></div>

3. Incase

Cases are matched in order, if a case is matched the statements are executed.
We stop when there wasn't any case that matched.

```
# the following code will increase x and y until they reach 10, if they are less than 10 #
# both x and y are incremented in a single iteration #

incase
   case (x < 10)
      x := x + 1;
   case (y < 10)
      y := y + 1;

print(x);
print(y);
```

Note: The syntax is similar to `forcase` but their meaning is different.

<div style="page-break-after: always;"></div>

## 9. Subprograms

Imagine that you want to write a program that takes as input two numbers and if they are positive it prints their square
root, what you would write is something similar to the following:

```
program SubProgs {
   declare x;
   declare y;

   input(x);
   input(y);

   if (x > 0) {
      print(x*x);
   };

   if (y > 0) {
      print(y*y);
   };
}.
```

You can get rid of this repetition by creating and re-using subprograms.

### Procedures

Procedures are subprograms that are not returning any value and can be called by using the `call` keyword.

The program above would become something like the following if we were using procedures:

```
program SubProgs {
   declare x;
   declare y;

   procedure sqrt(in x) {
      if (x > 0) {
         print(x*x);
      }
   }

   input(x);
   input(y);

   call sqrt(in x);
   call sqrt(in y);
}.
```

> You might have noticed the `in` keyword, we'll explain that later.

### Functions

Functions are similar to procedures but they should return a result.

```
program SubProgs {
   declare x;
   declare y;

   function sqrt(in x) {
      if (x > 0) {
         return (x*x);
      };
      return (0);
   }

   input(x);
   input(y);

   print(sqrt(in x));
   print(sqrt(in y));
}.
```

It looks like a procedure was a better choice for our square-root program.

Some general rule for choosing between a procedure and a function is the following:

> Use a procedure if you don't care about the result otherwise use a function.

<div style="page-break-after: always;"></div>

### Arguments

In the previous examples you might have noticed the `in` keyword. Arguments can either be of `in` or `inout` type.

Arguments passed with the `in` keyword are passed by value, altering their value inside the subprogram does not alter
the value on the caller.

```
procedure f(in x) {
   x := x + 1;
   print(x);    # 11 #
}

x := 10;
call f(in x);
print(x);       # 10 #
```

Alternatively you can use the `inout` keyword to pass by reference. Passing arguments with this method will allow the
subprograms to alter the value on the caller.

```
procedure f(inout x) {
   x := x + 1;
   print(x);    # 11 #
}

x := 10;
call f(inout x);
print(x);       # 11 #
```

<div style="page-break-after: always;"></div>

## 10. Scopes

Cimple scopes are following the same approach as most programming languages do.

A scope starts when a block starts with the `{` symbol and a scope stops when the block ends, with the `}` symbol.

Subprograms can view and edit values that were declared in their scope or some parent scope.

Let's see an example.

```
program P {
   declare x;

   function f1(in y) {
      declare z;

      function f12(in w) {
         # has access to: f1, f12, x, y, z, w #
      }

      # has access to: f1, f12, x, y, z #
   }

   # has access to: x, f1 #
}
```

<div style="page-break-after: always;"></div>

## 11. Compilation Errors

The cimple compiler provides useful errors that help you debug your code easily.

Let's see some examples:

```
program SomeErr {
   print(1)
}
```

The program above looks fine but after compiling we see the following error:

```
ERROR: Program should end with a dot (.)
```

The compiler will find the problem and most times will suggest a fix.

<div style="page-break-after: always;"></div>

Let's see some other common syntax error.

```
program SomeErr {
   procedure f(in x) {
      print x;
   };

   call f(in 1234);
}.
```

We forgot to wrap `x` in parenthesis after calling `print`. The compiler gave us:

```
ERROR: Unexpected: 'x', closest expected value: '('.
(5:13)   near: `...    print x;...`
```

The compiler found the exact line and column of the issue, displayed the source code near the error, and explained that
the `(` character is missing.

Some other common error is using some undeclared variable, the compiler is also able to catch such errors.

Compiling the following program:

```
program SomeErr {
   procedure f(in y) {
      print (x);
   };

   call f(in 1234);
}.
```

Will give us:

```
ERROR: Symbol 'x' does not belong to variables or parameters.
(3:15)   near: `...  print (x);...`
```

So we can immediately find the root cause of the problem.

<div style="page-break-after: always;"></div>

## 12. Technical Details

### Grammar

The cimple grammar follows the [Backus–Naur form](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form) and is LL-1.

```
program -> program ID
           <block>
           .

block -> {
            <declarations>
            <subprograms>
            <statements>
         }

declarations ->  (declare <varlist>;)*

varlist -> ID
           (, ID)*
           | e

subprograms -> (<subprogram>)*

subprogram -> function ID ( <formalparlist> )
              <block>
              | procedure ID ( <formalparlist> )
              <block>

formalparlist -> <formalparitem> (, <formalparitem>)*
                 | e

statements -> <statement>;
              | { <statement> (;<statement>)* }

blockstatements -> <statement> (; <statement>)*

statement -> <assignStat>
            | <ifStat>
            | <whileStat>
            | <switchCaseStat>
            | <forCaseStat>
            | <inCaseStat>
            | <callStat>
            | <returnStat>
            | <inputStat>
            | <printStat>
            | e

assignStat -> ID := <expression>

ifStat -> if (<condition>) <statements> <elsepart>

elsePart -> else <statements> | e

whileStat -> while (<condition>) <statements>

switchCaseStat -> switchcase (case(<condition>) <statements>)*
                  default <statements>

forCaseStat -> forcase (case(<condition>) <statements>)*
               default <statements>

inCaseStat -> incase (case(<condition>) <statements>)*

returnStat -> return(<expression>)

callStat -> call ID(<actualparlist>)

printStat -> print(<expression>)

inputStat -> input(ID)

actualparlist -> <actualparitem> (,<actualparitem>)* | e

actualparitem -> in <expression> | inout ID

condition -> <boolterm> (or <boolterm>)*

boolterm -> <boolfactor> (and <boolfactor>)*

boolfactor -> not [<condition>] | [<condition>]
              | <expression> <relop> <expression>

expression -> <optionalSign> <term> (<addop> <term>)*

term -> <factor> (<mulop> <factor>)*

factor -> INTEGER | (<expression>) | ID <idtail>

idtail -> (<actualparlist>) | e

optionalSign -> <addop> | e

relop -> = | <= | >= | > | < | <>

addop -> + | -

mulop -> * | /

INTEGER -> [0-9]+

ID -> [a-zA-Z][a-zA-Z0-9]*
```

### Architecture

The code related to the compilation is organized in the following classes:

**Lex**

Responsible for parsing the source code and extracting all the tokens.

**Parser**

Parser is performing the core logic of the compiler, is responsible for the syntax analysis, raising errors, generating
intermediate code and providing all the tooling for generating the final RISC-V assembly code.

**SymbolTable**

Symbols table is storing metadata related to the code, like variable memory offsets, declared variables,
scopes, etc.

Symbols table is used during error handling for findings undeclared variables, functions, etc. and during RISC-V
compilation for generating assembly instructions.

**AsmGenerator**

Assembly Generator is responsible for converting the intermediate code to RISC-V assembly instructions.

---

Apart from that there are some other helper Classes like `Quad` to store intermediate code quads,
`TrueFalse` for storing quads while parsing conditions, `Token` to store lex tokens and `FilePos` for keeping track of
source code position.

<div style="page-break-after: always;"></div>

### Compilation process

The compilation flow starts by initializing a Lex instance and providing it the cimple source code.

*Reading all the source code in-mem would not be ideal in a production-grade compiler but we want to keep it simple with
this educational compiler.*

```
lex = Lex(source_code)
```

After that we can create a parser instance and trigger the `parse_program` method to parse the code.

```
lex = Lex(source_code)
parser = Parser(lex)
parser.parse_program()
```

At this point our parser internally parsed all the source code, and generated all the intermediate and RISC-V code to
its internal state.

We can simply write the RISC-V code to a file with:

```
with open(filename + ".asm", "w") as f:
   f.write(parser.asm_generator.gen_asm_equivalent())
```

The code is self-explanatory and it doesn't make much sense to explain more in-depth all the internal compilation steps
in this doc.

<div style="page-break-after: always;"></div>

## 13. Development

### Testing

You can run the unit tests with:

```
python3 -m unittest
```

### Linting

The code is linted with [autopep8](https://pypi.org/project/autopep8/)

You can lint your code with:

```
autopep8 --max-line-length 120 -i cc.py
```
