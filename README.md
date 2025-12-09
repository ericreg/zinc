# zinc

Regenerate antlr4 Parser
```sh
cd parser/
rm -rf .antlr *.py *.tokens *.interp
antlr -Dlanguage=Python3 -visitor zinc.g4 
```

# TODO

- [x] dynamic variable assignments
- [ ] other functions
- [ ] arithmetic expressions
- [ ] make single quotes string literals
- [ ] async functions
- [ ] arrays/lists
- [ ] dictionaries/maps
- [ ] control flow (if/else, loops)
- [ ] error handling
- [ ] modules and imports
