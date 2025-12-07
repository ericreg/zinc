# zinc

Regenerate antlr4 Parser
```sh
cd parser/
rm -rf .antlr *.py *.tokens *.interp
antlr -Dlanguage=Python3 -visitor zinc.g4 
```