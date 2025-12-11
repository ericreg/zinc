# zinc

Regenerate antlr4 Parser
```sh
cd parser/
rm -rf .antlr *.py *.tokens *.interp &&  antlr -Dlanguage=Python3 -visitor zinc.g4 
```

# TODO

- [x] dynamic variable assignments
- [x] function/ monomorphic overloading
- [x] arithmetic expressions
- [x] if / else if / else
- [ ] channels
- [ ] make single quotes string literals
- [ ] async functions
- [ ] arrays/lists
- [ ] dictionaries/maps/sets
- [ ] structs/objects
- [ ] loops (for, while, loop)
- [ ] error handling
- [ ] modules and imports
