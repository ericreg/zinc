# zinc

Regenerate antlr4 Parser
```sh
cd parser/
rm -rf .antlr *.py *.tokens *.interp
antlr -Dlanguage=Python3 -visitor zinc.g4 
```

# TODO

- dynamic variable assignments
- Make single quotes string literals
- arithmetic expressions
- other functions
- async functions
- arrays/lists

