# Generated from zinc.g4 by ANTLR 4.13.2
from antlr4 import *

if "." in __name__:
    from .zincParser import zincParser
else:
    from zincParser import zincParser


# This class defines a complete listener for a parse tree produced by zincParser.
class zincListener(ParseTreeListener):
    # Enter a parse tree produced by zincParser#program.
    def enterProgram(self, ctx: zincParser.ProgramContext):
        pass

    # Exit a parse tree produced by zincParser#program.
    def exitProgram(self, ctx: zincParser.ProgramContext):
        pass

    # Enter a parse tree produced by zincParser#statement.
    def enterStatement(self, ctx: zincParser.StatementContext):
        pass

    # Exit a parse tree produced by zincParser#statement.
    def exitStatement(self, ctx: zincParser.StatementContext):
        pass

    # Enter a parse tree produced by zincParser#useStatement.
    def enterUseStatement(self, ctx: zincParser.UseStatementContext):
        pass

    # Exit a parse tree produced by zincParser#useStatement.
    def exitUseStatement(self, ctx: zincParser.UseStatementContext):
        pass

    # Enter a parse tree produced by zincParser#modulePath.
    def enterModulePath(self, ctx: zincParser.ModulePathContext):
        pass

    # Exit a parse tree produced by zincParser#modulePath.
    def exitModulePath(self, ctx: zincParser.ModulePathContext):
        pass

    # Enter a parse tree produced by zincParser#structDeclaration.
    def enterStructDeclaration(self, ctx: zincParser.StructDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#structDeclaration.
    def exitStructDeclaration(self, ctx: zincParser.StructDeclarationContext):
        pass

    # Enter a parse tree produced by zincParser#structBody.
    def enterStructBody(self, ctx: zincParser.StructBodyContext):
        pass

    # Exit a parse tree produced by zincParser#structBody.
    def exitStructBody(self, ctx: zincParser.StructBodyContext):
        pass

    # Enter a parse tree produced by zincParser#structMember.
    def enterStructMember(self, ctx: zincParser.StructMemberContext):
        pass

    # Exit a parse tree produced by zincParser#structMember.
    def exitStructMember(self, ctx: zincParser.StructMemberContext):
        pass

    # Enter a parse tree produced by zincParser#functionDeclaration.
    def enterFunctionDeclaration(self, ctx: zincParser.FunctionDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#functionDeclaration.
    def exitFunctionDeclaration(self, ctx: zincParser.FunctionDeclarationContext):
        pass

    # Enter a parse tree produced by zincParser#asyncFunctionDeclaration.
    def enterAsyncFunctionDeclaration(
        self, ctx: zincParser.AsyncFunctionDeclarationContext
    ):
        pass

    # Exit a parse tree produced by zincParser#asyncFunctionDeclaration.
    def exitAsyncFunctionDeclaration(
        self, ctx: zincParser.AsyncFunctionDeclarationContext
    ):
        pass

    # Enter a parse tree produced by zincParser#parameterList.
    def enterParameterList(self, ctx: zincParser.ParameterListContext):
        pass

    # Exit a parse tree produced by zincParser#parameterList.
    def exitParameterList(self, ctx: zincParser.ParameterListContext):
        pass

    # Enter a parse tree produced by zincParser#parameter.
    def enterParameter(self, ctx: zincParser.ParameterContext):
        pass

    # Exit a parse tree produced by zincParser#parameter.
    def exitParameter(self, ctx: zincParser.ParameterContext):
        pass

    # Enter a parse tree produced by zincParser#type.
    def enterType(self, ctx: zincParser.TypeContext):
        pass

    # Exit a parse tree produced by zincParser#type.
    def exitType(self, ctx: zincParser.TypeContext):
        pass

    # Enter a parse tree produced by zincParser#typeList.
    def enterTypeList(self, ctx: zincParser.TypeListContext):
        pass

    # Exit a parse tree produced by zincParser#typeList.
    def exitTypeList(self, ctx: zincParser.TypeListContext):
        pass

    # Enter a parse tree produced by zincParser#variableAssignment.
    def enterVariableAssignment(self, ctx: zincParser.VariableAssignmentContext):
        pass

    # Exit a parse tree produced by zincParser#variableAssignment.
    def exitVariableAssignment(self, ctx: zincParser.VariableAssignmentContext):
        pass

    # Enter a parse tree produced by zincParser#assignmentTarget.
    def enterAssignmentTarget(self, ctx: zincParser.AssignmentTargetContext):
        pass

    # Exit a parse tree produced by zincParser#assignmentTarget.
    def exitAssignmentTarget(self, ctx: zincParser.AssignmentTargetContext):
        pass

    # Enter a parse tree produced by zincParser#expressionStatement.
    def enterExpressionStatement(self, ctx: zincParser.ExpressionStatementContext):
        pass

    # Exit a parse tree produced by zincParser#expressionStatement.
    def exitExpressionStatement(self, ctx: zincParser.ExpressionStatementContext):
        pass

    # Enter a parse tree produced by zincParser#ifStatement.
    def enterIfStatement(self, ctx: zincParser.IfStatementContext):
        pass

    # Exit a parse tree produced by zincParser#ifStatement.
    def exitIfStatement(self, ctx: zincParser.IfStatementContext):
        pass

    # Enter a parse tree produced by zincParser#forStatement.
    def enterForStatement(self, ctx: zincParser.ForStatementContext):
        pass

    # Exit a parse tree produced by zincParser#forStatement.
    def exitForStatement(self, ctx: zincParser.ForStatementContext):
        pass

    # Enter a parse tree produced by zincParser#whileStatement.
    def enterWhileStatement(self, ctx: zincParser.WhileStatementContext):
        pass

    # Exit a parse tree produced by zincParser#whileStatement.
    def exitWhileStatement(self, ctx: zincParser.WhileStatementContext):
        pass

    # Enter a parse tree produced by zincParser#loopStatement.
    def enterLoopStatement(self, ctx: zincParser.LoopStatementContext):
        pass

    # Exit a parse tree produced by zincParser#loopStatement.
    def exitLoopStatement(self, ctx: zincParser.LoopStatementContext):
        pass

    # Enter a parse tree produced by zincParser#matchStatement.
    def enterMatchStatement(self, ctx: zincParser.MatchStatementContext):
        pass

    # Exit a parse tree produced by zincParser#matchStatement.
    def exitMatchStatement(self, ctx: zincParser.MatchStatementContext):
        pass

    # Enter a parse tree produced by zincParser#matchArm.
    def enterMatchArm(self, ctx: zincParser.MatchArmContext):
        pass

    # Exit a parse tree produced by zincParser#matchArm.
    def exitMatchArm(self, ctx: zincParser.MatchArmContext):
        pass

    # Enter a parse tree produced by zincParser#pattern.
    def enterPattern(self, ctx: zincParser.PatternContext):
        pass

    # Exit a parse tree produced by zincParser#pattern.
    def exitPattern(self, ctx: zincParser.PatternContext):
        pass

    # Enter a parse tree produced by zincParser#rangePattern.
    def enterRangePattern(self, ctx: zincParser.RangePatternContext):
        pass

    # Exit a parse tree produced by zincParser#rangePattern.
    def exitRangePattern(self, ctx: zincParser.RangePatternContext):
        pass

    # Enter a parse tree produced by zincParser#fieldPattern.
    def enterFieldPattern(self, ctx: zincParser.FieldPatternContext):
        pass

    # Exit a parse tree produced by zincParser#fieldPattern.
    def exitFieldPattern(self, ctx: zincParser.FieldPatternContext):
        pass

    # Enter a parse tree produced by zincParser#returnStatement.
    def enterReturnStatement(self, ctx: zincParser.ReturnStatementContext):
        pass

    # Exit a parse tree produced by zincParser#returnStatement.
    def exitReturnStatement(self, ctx: zincParser.ReturnStatementContext):
        pass

    # Enter a parse tree produced by zincParser#breakStatement.
    def enterBreakStatement(self, ctx: zincParser.BreakStatementContext):
        pass

    # Exit a parse tree produced by zincParser#breakStatement.
    def exitBreakStatement(self, ctx: zincParser.BreakStatementContext):
        pass

    # Enter a parse tree produced by zincParser#continueStatement.
    def enterContinueStatement(self, ctx: zincParser.ContinueStatementContext):
        pass

    # Exit a parse tree produced by zincParser#continueStatement.
    def exitContinueStatement(self, ctx: zincParser.ContinueStatementContext):
        pass

    # Enter a parse tree produced by zincParser#block.
    def enterBlock(self, ctx: zincParser.BlockContext):
        pass

    # Exit a parse tree produced by zincParser#block.
    def exitBlock(self, ctx: zincParser.BlockContext):
        pass

    # Enter a parse tree produced by zincParser#logicalAndExpr.
    def enterLogicalAndExpr(self, ctx: zincParser.LogicalAndExprContext):
        pass

    # Exit a parse tree produced by zincParser#logicalAndExpr.
    def exitLogicalAndExpr(self, ctx: zincParser.LogicalAndExprContext):
        pass

    # Enter a parse tree produced by zincParser#additiveExpr.
    def enterAdditiveExpr(self, ctx: zincParser.AdditiveExprContext):
        pass

    # Exit a parse tree produced by zincParser#additiveExpr.
    def exitAdditiveExpr(self, ctx: zincParser.AdditiveExprContext):
        pass

    # Enter a parse tree produced by zincParser#awaitExpr.
    def enterAwaitExpr(self, ctx: zincParser.AwaitExprContext):
        pass

    # Exit a parse tree produced by zincParser#awaitExpr.
    def exitAwaitExpr(self, ctx: zincParser.AwaitExprContext):
        pass

    # Enter a parse tree produced by zincParser#relationalExpr.
    def enterRelationalExpr(self, ctx: zincParser.RelationalExprContext):
        pass

    # Exit a parse tree produced by zincParser#relationalExpr.
    def exitRelationalExpr(self, ctx: zincParser.RelationalExprContext):
        pass

    # Enter a parse tree produced by zincParser#parenExpr.
    def enterParenExpr(self, ctx: zincParser.ParenExprContext):
        pass

    # Exit a parse tree produced by zincParser#parenExpr.
    def exitParenExpr(self, ctx: zincParser.ParenExprContext):
        pass

    # Enter a parse tree produced by zincParser#logicalOrExpr.
    def enterLogicalOrExpr(self, ctx: zincParser.LogicalOrExprContext):
        pass

    # Exit a parse tree produced by zincParser#logicalOrExpr.
    def exitLogicalOrExpr(self, ctx: zincParser.LogicalOrExprContext):
        pass

    # Enter a parse tree produced by zincParser#unaryExpr.
    def enterUnaryExpr(self, ctx: zincParser.UnaryExprContext):
        pass

    # Exit a parse tree produced by zincParser#unaryExpr.
    def exitUnaryExpr(self, ctx: zincParser.UnaryExprContext):
        pass

    # Enter a parse tree produced by zincParser#primaryExpr.
    def enterPrimaryExpr(self, ctx: zincParser.PrimaryExprContext):
        pass

    # Exit a parse tree produced by zincParser#primaryExpr.
    def exitPrimaryExpr(self, ctx: zincParser.PrimaryExprContext):
        pass

    # Enter a parse tree produced by zincParser#selectExpr.
    def enterSelectExpr(self, ctx: zincParser.SelectExprContext):
        pass

    # Exit a parse tree produced by zincParser#selectExpr.
    def exitSelectExpr(self, ctx: zincParser.SelectExprContext):
        pass

    # Enter a parse tree produced by zincParser#lambdaExpr.
    def enterLambdaExpr(self, ctx: zincParser.LambdaExprContext):
        pass

    # Exit a parse tree produced by zincParser#lambdaExpr.
    def exitLambdaExpr(self, ctx: zincParser.LambdaExprContext):
        pass

    # Enter a parse tree produced by zincParser#indexAccessExpr.
    def enterIndexAccessExpr(self, ctx: zincParser.IndexAccessExprContext):
        pass

    # Exit a parse tree produced by zincParser#indexAccessExpr.
    def exitIndexAccessExpr(self, ctx: zincParser.IndexAccessExprContext):
        pass

    # Enter a parse tree produced by zincParser#functionCallExpr.
    def enterFunctionCallExpr(self, ctx: zincParser.FunctionCallExprContext):
        pass

    # Exit a parse tree produced by zincParser#functionCallExpr.
    def exitFunctionCallExpr(self, ctx: zincParser.FunctionCallExprContext):
        pass

    # Enter a parse tree produced by zincParser#memberAccessExpr.
    def enterMemberAccessExpr(self, ctx: zincParser.MemberAccessExprContext):
        pass

    # Exit a parse tree produced by zincParser#memberAccessExpr.
    def exitMemberAccessExpr(self, ctx: zincParser.MemberAccessExprContext):
        pass

    # Enter a parse tree produced by zincParser#multiplicativeExpr.
    def enterMultiplicativeExpr(self, ctx: zincParser.MultiplicativeExprContext):
        pass

    # Exit a parse tree produced by zincParser#multiplicativeExpr.
    def exitMultiplicativeExpr(self, ctx: zincParser.MultiplicativeExprContext):
        pass

    # Enter a parse tree produced by zincParser#rangeExpr.
    def enterRangeExpr(self, ctx: zincParser.RangeExprContext):
        pass

    # Exit a parse tree produced by zincParser#rangeExpr.
    def exitRangeExpr(self, ctx: zincParser.RangeExprContext):
        pass

    # Enter a parse tree produced by zincParser#equalityExpr.
    def enterEqualityExpr(self, ctx: zincParser.EqualityExprContext):
        pass

    # Exit a parse tree produced by zincParser#equalityExpr.
    def exitEqualityExpr(self, ctx: zincParser.EqualityExprContext):
        pass

    # Enter a parse tree produced by zincParser#primaryExpression.
    def enterPrimaryExpression(self, ctx: zincParser.PrimaryExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#primaryExpression.
    def exitPrimaryExpression(self, ctx: zincParser.PrimaryExpressionContext):
        pass

    # Enter a parse tree produced by zincParser#memberAccess.
    def enterMemberAccess(self, ctx: zincParser.MemberAccessContext):
        pass

    # Exit a parse tree produced by zincParser#memberAccess.
    def exitMemberAccess(self, ctx: zincParser.MemberAccessContext):
        pass

    # Enter a parse tree produced by zincParser#indexAccess.
    def enterIndexAccess(self, ctx: zincParser.IndexAccessContext):
        pass

    # Exit a parse tree produced by zincParser#indexAccess.
    def exitIndexAccess(self, ctx: zincParser.IndexAccessContext):
        pass

    # Enter a parse tree produced by zincParser#literal.
    def enterLiteral(self, ctx: zincParser.LiteralContext):
        pass

    # Exit a parse tree produced by zincParser#literal.
    def exitLiteral(self, ctx: zincParser.LiteralContext):
        pass

    # Enter a parse tree produced by zincParser#booleanLiteral.
    def enterBooleanLiteral(self, ctx: zincParser.BooleanLiteralContext):
        pass

    # Exit a parse tree produced by zincParser#booleanLiteral.
    def exitBooleanLiteral(self, ctx: zincParser.BooleanLiteralContext):
        pass

    # Enter a parse tree produced by zincParser#arrayLiteral.
    def enterArrayLiteral(self, ctx: zincParser.ArrayLiteralContext):
        pass

    # Exit a parse tree produced by zincParser#arrayLiteral.
    def exitArrayLiteral(self, ctx: zincParser.ArrayLiteralContext):
        pass

    # Enter a parse tree produced by zincParser#structInstantiation.
    def enterStructInstantiation(self, ctx: zincParser.StructInstantiationContext):
        pass

    # Exit a parse tree produced by zincParser#structInstantiation.
    def exitStructInstantiation(self, ctx: zincParser.StructInstantiationContext):
        pass

    # Enter a parse tree produced by zincParser#fieldInit.
    def enterFieldInit(self, ctx: zincParser.FieldInitContext):
        pass

    # Exit a parse tree produced by zincParser#fieldInit.
    def exitFieldInit(self, ctx: zincParser.FieldInitContext):
        pass

    # Enter a parse tree produced by zincParser#argumentList.
    def enterArgumentList(self, ctx: zincParser.ArgumentListContext):
        pass

    # Exit a parse tree produced by zincParser#argumentList.
    def exitArgumentList(self, ctx: zincParser.ArgumentListContext):
        pass

    # Enter a parse tree produced by zincParser#selectExpression.
    def enterSelectExpression(self, ctx: zincParser.SelectExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#selectExpression.
    def exitSelectExpression(self, ctx: zincParser.SelectExpressionContext):
        pass

    # Enter a parse tree produced by zincParser#selectCase.
    def enterSelectCase(self, ctx: zincParser.SelectCaseContext):
        pass

    # Exit a parse tree produced by zincParser#selectCase.
    def exitSelectCase(self, ctx: zincParser.SelectCaseContext):
        pass

    # Enter a parse tree produced by zincParser#lambdaExpression.
    def enterLambdaExpression(self, ctx: zincParser.LambdaExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#lambdaExpression.
    def exitLambdaExpression(self, ctx: zincParser.LambdaExpressionContext):
        pass


del zincParser
