# Generated from zinc.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .zincParser import zincParser
else:
    from zincParser import zincParser

# This class defines a complete generic visitor for a parse tree produced by zincParser.

class zincVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by zincParser#program.
    def visitProgram(self, ctx:zincParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#statement.
    def visitStatement(self, ctx:zincParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#functionDeclaration.
    def visitFunctionDeclaration(self, ctx:zincParser.FunctionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#parameterList.
    def visitParameterList(self, ctx:zincParser.ParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#parameter.
    def visitParameter(self, ctx:zincParser.ParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#type.
    def visitType(self, ctx:zincParser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#typeList.
    def visitTypeList(self, ctx:zincParser.TypeListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#variableAssignment.
    def visitVariableAssignment(self, ctx:zincParser.VariableAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#assignmentTarget.
    def visitAssignmentTarget(self, ctx:zincParser.AssignmentTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#expressionStatement.
    def visitExpressionStatement(self, ctx:zincParser.ExpressionStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#matchStatement.
    def visitMatchStatement(self, ctx:zincParser.MatchStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#matchArm.
    def visitMatchArm(self, ctx:zincParser.MatchArmContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#pattern.
    def visitPattern(self, ctx:zincParser.PatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#rangePattern.
    def visitRangePattern(self, ctx:zincParser.RangePatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#fieldPattern.
    def visitFieldPattern(self, ctx:zincParser.FieldPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#returnStatement.
    def visitReturnStatement(self, ctx:zincParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#breakStatement.
    def visitBreakStatement(self, ctx:zincParser.BreakStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#continueStatement.
    def visitContinueStatement(self, ctx:zincParser.ContinueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#block.
    def visitBlock(self, ctx:zincParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#logicalAndExpr.
    def visitLogicalAndExpr(self, ctx:zincParser.LogicalAndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#additiveExpr.
    def visitAdditiveExpr(self, ctx:zincParser.AdditiveExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#awaitExpr.
    def visitAwaitExpr(self, ctx:zincParser.AwaitExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#relationalExpr.
    def visitRelationalExpr(self, ctx:zincParser.RelationalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#parenExpr.
    def visitParenExpr(self, ctx:zincParser.ParenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#logicalOrExpr.
    def visitLogicalOrExpr(self, ctx:zincParser.LogicalOrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#unaryExpr.
    def visitUnaryExpr(self, ctx:zincParser.UnaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#primaryExpr.
    def visitPrimaryExpr(self, ctx:zincParser.PrimaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#indexAccessExpr.
    def visitIndexAccessExpr(self, ctx:zincParser.IndexAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#memberAccessExpr.
    def visitMemberAccessExpr(self, ctx:zincParser.MemberAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx:zincParser.MultiplicativeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#rangeExpr.
    def visitRangeExpr(self, ctx:zincParser.RangeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#equalityExpr.
    def visitEqualityExpr(self, ctx:zincParser.EqualityExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#primaryExpression.
    def visitPrimaryExpression(self, ctx:zincParser.PrimaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#literal.
    def visitLiteral(self, ctx:zincParser.LiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#booleanLiteral.
    def visitBooleanLiteral(self, ctx:zincParser.BooleanLiteralContext):
        return self.visitChildren(ctx)



del zincParser