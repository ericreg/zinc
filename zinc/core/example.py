from antlr4 import *
from zinc.parser.zincLexer import zincLexer as ZincLexer
from zinc.parser.zincParser import zincParser as ZincParser
from zinc.parser.zincVisitor import zincVisitor as ZincVisitor
from pathlib import Path


class Visitor(ZincVisitor):

    def visitProgram(self, ctx):
        print("Visiting program")
        return self.visitChildren(ctx)



file_path = Path("programs/variable_assignment.zinc")
input_text = file_path.read_text()

input_stream = InputStream(input_text)
lexer = ZincLexer(input_stream)
stream = CommonTokenStream(lexer)
parser = ZincParser(stream)

tree = parser.program()

visitor = Visitor()
visitor.visit(tree)

print(tree.toStringTree(recog=parser))



# from ..core.parser.zincLexer import zincLexer
# from ..core.parser.zincParser import zincParser


# input_text = input("> ")
# lexer = HelloLexer(InputStream(input_text))
# stream = CommonTokenStream(lexer)
# parser = HelloParser(stream)

# tree = parser.r()

# print(tree.toStringTree(recog=parser))