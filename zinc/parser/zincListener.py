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

    # Enter a parse tree produced by zincParser#importStatement.
    def enterImportStatement(self, ctx: zincParser.ImportStatementContext):
        pass

    # Exit a parse tree produced by zincParser#importStatement.
    def exitImportStatement(self, ctx: zincParser.ImportStatementContext):
        pass

    # Enter a parse tree produced by zincParser#importPath.
    def enterImportPath(self, ctx: zincParser.ImportPathContext):
        pass

    # Exit a parse tree produced by zincParser#importPath.
    def exitImportPath(self, ctx: zincParser.ImportPathContext):
        pass

    # Enter a parse tree produced by zincParser#importNameList.
    def enterImportNameList(self, ctx: zincParser.ImportNameListContext):
        pass

    # Exit a parse tree produced by zincParser#importNameList.
    def exitImportNameList(self, ctx: zincParser.ImportNameListContext):
        pass

    # Enter a parse tree produced by zincParser#qualifiedName.
    def enterQualifiedName(self, ctx: zincParser.QualifiedNameContext):
        pass

    # Exit a parse tree produced by zincParser#qualifiedName.
    def exitQualifiedName(self, ctx: zincParser.QualifiedNameContext):
        pass

    # Enter a parse tree produced by zincParser#constDeclaration.
    def enterConstDeclaration(self, ctx: zincParser.ConstDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#constDeclaration.
    def exitConstDeclaration(self, ctx: zincParser.ConstDeclarationContext):
        pass

    # Enter a parse tree produced by zincParser#structDeclaration.
    def enterStructDeclaration(self, ctx: zincParser.StructDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#structDeclaration.
    def exitStructDeclaration(self, ctx: zincParser.StructDeclarationContext):
        pass

    # Enter a parse tree produced by zincParser#enumDeclaration.
    def enterEnumDeclaration(self, ctx: zincParser.EnumDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#enumDeclaration.
    def exitEnumDeclaration(self, ctx: zincParser.EnumDeclarationContext):
        pass

    # Enter a parse tree produced by zincParser#attributeBlock.
    def enterAttributeBlock(self, ctx: zincParser.AttributeBlockContext):
        pass

    # Exit a parse tree produced by zincParser#attributeBlock.
    def exitAttributeBlock(self, ctx: zincParser.AttributeBlockContext):
        pass

    # Enter a parse tree produced by zincParser#structComposition.
    def enterStructComposition(self, ctx: zincParser.StructCompositionContext):
        pass

    # Exit a parse tree produced by zincParser#structComposition.
    def exitStructComposition(self, ctx: zincParser.StructCompositionContext):
        pass

    # Enter a parse tree produced by zincParser#orthogonalComposition.
    def enterOrthogonalComposition(self, ctx: zincParser.OrthogonalCompositionContext):
        pass

    # Exit a parse tree produced by zincParser#orthogonalComposition.
    def exitOrthogonalComposition(self, ctx: zincParser.OrthogonalCompositionContext):
        pass

    # Enter a parse tree produced by zincParser#mergeComposition.
    def enterMergeComposition(self, ctx: zincParser.MergeCompositionContext):
        pass

    # Exit a parse tree produced by zincParser#mergeComposition.
    def exitMergeComposition(self, ctx: zincParser.MergeCompositionContext):
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

    # Enter a parse tree produced by zincParser#structField.
    def enterStructField(self, ctx: zincParser.StructFieldContext):
        pass

    # Exit a parse tree produced by zincParser#structField.
    def exitStructField(self, ctx: zincParser.StructFieldContext):
        pass

    # Enter a parse tree produced by zincParser#enumBody.
    def enterEnumBody(self, ctx: zincParser.EnumBodyContext):
        pass

    # Exit a parse tree produced by zincParser#enumBody.
    def exitEnumBody(self, ctx: zincParser.EnumBodyContext):
        pass

    # Enter a parse tree produced by zincParser#enumVariant.
    def enterEnumVariant(self, ctx: zincParser.EnumVariantContext):
        pass

    # Exit a parse tree produced by zincParser#enumVariant.
    def exitEnumVariant(self, ctx: zincParser.EnumVariantContext):
        pass

    # Enter a parse tree produced by zincParser#enumVariantFieldType.
    def enterEnumVariantFieldType(self, ctx: zincParser.EnumVariantFieldTypeContext):
        pass

    # Exit a parse tree produced by zincParser#enumVariantFieldType.
    def exitEnumVariantFieldType(self, ctx: zincParser.EnumVariantFieldTypeContext):
        pass

    # Enter a parse tree produced by zincParser#functionDeclaration.
    def enterFunctionDeclaration(self, ctx: zincParser.FunctionDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#functionDeclaration.
    def exitFunctionDeclaration(self, ctx: zincParser.FunctionDeclarationContext):
        pass

    # Enter a parse tree produced by zincParser#asyncFunctionDeclaration.
    def enterAsyncFunctionDeclaration(self, ctx: zincParser.AsyncFunctionDeclarationContext):
        pass

    # Exit a parse tree produced by zincParser#asyncFunctionDeclaration.
    def exitAsyncFunctionDeclaration(self, ctx: zincParser.AsyncFunctionDeclarationContext):
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

    # Enter a parse tree produced by zincParser#typeAlternative.
    def enterTypeAlternative(self, ctx: zincParser.TypeAlternativeContext):
        pass

    # Exit a parse tree produced by zincParser#typeAlternative.
    def exitTypeAlternative(self, ctx: zincParser.TypeAlternativeContext):
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

    # Enter a parse tree produced by zincParser#tupleType.
    def enterTupleType(self, ctx: zincParser.TupleTypeContext):
        pass

    # Exit a parse tree produced by zincParser#tupleType.
    def exitTupleType(self, ctx: zincParser.TupleTypeContext):
        pass

    # Enter a parse tree produced by zincParser#typedVariableAssignment.
    def enterTypedVariableAssignment(self, ctx: zincParser.TypedVariableAssignmentContext):
        pass

    # Exit a parse tree produced by zincParser#typedVariableAssignment.
    def exitTypedVariableAssignment(self, ctx: zincParser.TypedVariableAssignmentContext):
        pass

    # Enter a parse tree produced by zincParser#typedAssignmentTarget.
    def enterTypedAssignmentTarget(self, ctx: zincParser.TypedAssignmentTargetContext):
        pass

    # Exit a parse tree produced by zincParser#typedAssignmentTarget.
    def exitTypedAssignmentTarget(self, ctx: zincParser.TypedAssignmentTargetContext):
        pass

    # Enter a parse tree produced by zincParser#variableAssignment.
    def enterVariableAssignment(self, ctx: zincParser.VariableAssignmentContext):
        pass

    # Exit a parse tree produced by zincParser#variableAssignment.
    def exitVariableAssignment(self, ctx: zincParser.VariableAssignmentContext):
        pass

    # Enter a parse tree produced by zincParser#assignmentOperator.
    def enterAssignmentOperator(self, ctx: zincParser.AssignmentOperatorContext):
        pass

    # Exit a parse tree produced by zincParser#assignmentOperator.
    def exitAssignmentOperator(self, ctx: zincParser.AssignmentOperatorContext):
        pass

    # Enter a parse tree produced by zincParser#superAssignment.
    def enterSuperAssignment(self, ctx: zincParser.SuperAssignmentContext):
        pass

    # Exit a parse tree produced by zincParser#superAssignment.
    def exitSuperAssignment(self, ctx: zincParser.SuperAssignmentContext):
        pass

    # Enter a parse tree produced by zincParser#assignmentTarget.
    def enterAssignmentTarget(self, ctx: zincParser.AssignmentTargetContext):
        pass

    # Exit a parse tree produced by zincParser#assignmentTarget.
    def exitAssignmentTarget(self, ctx: zincParser.AssignmentTargetContext):
        pass

    # Enter a parse tree produced by zincParser#tupleAssignmentTarget.
    def enterTupleAssignmentTarget(self, ctx: zincParser.TupleAssignmentTargetContext):
        pass

    # Exit a parse tree produced by zincParser#tupleAssignmentTarget.
    def exitTupleAssignmentTarget(self, ctx: zincParser.TupleAssignmentTargetContext):
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

    # Enter a parse tree produced by zincParser#forBinding.
    def enterForBinding(self, ctx: zincParser.ForBindingContext):
        pass

    # Exit a parse tree produced by zincParser#forBinding.
    def exitForBinding(self, ctx: zincParser.ForBindingContext):
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

    # Enter a parse tree produced by zincParser#resultOptionPattern.
    def enterResultOptionPattern(self, ctx: zincParser.ResultOptionPatternContext):
        pass

    # Exit a parse tree produced by zincParser#resultOptionPattern.
    def exitResultOptionPattern(self, ctx: zincParser.ResultOptionPatternContext):
        pass

    # Enter a parse tree produced by zincParser#enumVariantPattern.
    def enterEnumVariantPattern(self, ctx: zincParser.EnumVariantPatternContext):
        pass

    # Exit a parse tree produced by zincParser#enumVariantPattern.
    def exitEnumVariantPattern(self, ctx: zincParser.EnumVariantPatternContext):
        pass

    # Enter a parse tree produced by zincParser#rangePattern.
    def enterRangePattern(self, ctx: zincParser.RangePatternContext):
        pass

    # Exit a parse tree produced by zincParser#rangePattern.
    def exitRangePattern(self, ctx: zincParser.RangePatternContext):
        pass

    # Enter a parse tree produced by zincParser#enumVariantPath.
    def enterEnumVariantPath(self, ctx: zincParser.EnumVariantPathContext):
        pass

    # Exit a parse tree produced by zincParser#enumVariantPath.
    def exitEnumVariantPath(self, ctx: zincParser.EnumVariantPathContext):
        pass

    # Enter a parse tree produced by zincParser#enumVariantFieldPattern.
    def enterEnumVariantFieldPattern(self, ctx: zincParser.EnumVariantFieldPatternContext):
        pass

    # Exit a parse tree produced by zincParser#enumVariantFieldPattern.
    def exitEnumVariantFieldPattern(self, ctx: zincParser.EnumVariantFieldPatternContext):
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

    # Enter a parse tree produced by zincParser#failStatement.
    def enterFailStatement(self, ctx: zincParser.FailStatementContext):
        pass

    # Exit a parse tree produced by zincParser#failStatement.
    def exitFailStatement(self, ctx: zincParser.FailStatementContext):
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

    # Enter a parse tree produced by zincParser#spawnStatement.
    def enterSpawnStatement(self, ctx: zincParser.SpawnStatementContext):
        pass

    # Exit a parse tree produced by zincParser#spawnStatement.
    def exitSpawnStatement(self, ctx: zincParser.SpawnStatementContext):
        pass

    # Enter a parse tree produced by zincParser#selectStatement.
    def enterSelectStatement(self, ctx: zincParser.SelectStatementContext):
        pass

    # Exit a parse tree produced by zincParser#selectStatement.
    def exitSelectStatement(self, ctx: zincParser.SelectStatementContext):
        pass

    # Enter a parse tree produced by zincParser#channelSendStatement.
    def enterChannelSendStatement(self, ctx: zincParser.ChannelSendStatementContext):
        pass

    # Exit a parse tree produced by zincParser#channelSendStatement.
    def exitChannelSendStatement(self, ctx: zincParser.ChannelSendStatementContext):
        pass

    # Enter a parse tree produced by zincParser#block.
    def enterBlock(self, ctx: zincParser.BlockContext):
        pass

    # Exit a parse tree produced by zincParser#block.
    def exitBlock(self, ctx: zincParser.BlockContext):
        pass

    # Enter a parse tree produced by zincParser#membershipExpr.
    def enterMembershipExpr(self, ctx: zincParser.MembershipExprContext):
        pass

    # Exit a parse tree produced by zincParser#membershipExpr.
    def exitMembershipExpr(self, ctx: zincParser.MembershipExprContext):
        pass

    # Enter a parse tree produced by zincParser#powerExpr.
    def enterPowerExpr(self, ctx: zincParser.PowerExprContext):
        pass

    # Exit a parse tree produced by zincParser#powerExpr.
    def exitPowerExpr(self, ctx: zincParser.PowerExprContext):
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

    # Enter a parse tree produced by zincParser#tryExpr.
    def enterTryExpr(self, ctx: zincParser.TryExprContext):
        pass

    # Exit a parse tree produced by zincParser#tryExpr.
    def exitTryExpr(self, ctx: zincParser.TryExprContext):
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

    # Enter a parse tree produced by zincParser#ifExpr.
    def enterIfExpr(self, ctx: zincParser.IfExprContext):
        pass

    # Exit a parse tree produced by zincParser#ifExpr.
    def exitIfExpr(self, ctx: zincParser.IfExprContext):
        pass

    # Enter a parse tree produced by zincParser#channelReceiveExpr.
    def enterChannelReceiveExpr(self, ctx: zincParser.ChannelReceiveExprContext):
        pass

    # Exit a parse tree produced by zincParser#channelReceiveExpr.
    def exitChannelReceiveExpr(self, ctx: zincParser.ChannelReceiveExprContext):
        pass

    # Enter a parse tree produced by zincParser#memberAccessExpr.
    def enterMemberAccessExpr(self, ctx: zincParser.MemberAccessExprContext):
        pass

    # Exit a parse tree produced by zincParser#memberAccessExpr.
    def exitMemberAccessExpr(self, ctx: zincParser.MemberAccessExprContext):
        pass

    # Enter a parse tree produced by zincParser#blockExpr.
    def enterBlockExpr(self, ctx: zincParser.BlockExprContext):
        pass

    # Exit a parse tree produced by zincParser#blockExpr.
    def exitBlockExpr(self, ctx: zincParser.BlockExprContext):
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

    # Enter a parse tree produced by zincParser#ifExpression.
    def enterIfExpression(self, ctx: zincParser.IfExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#ifExpression.
    def exitIfExpression(self, ctx: zincParser.IfExpressionContext):
        pass

    # Enter a parse tree produced by zincParser#tryExpression.
    def enterTryExpression(self, ctx: zincParser.TryExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#tryExpression.
    def exitTryExpression(self, ctx: zincParser.TryExpressionContext):
        pass

    # Enter a parse tree produced by zincParser#blockExpression.
    def enterBlockExpression(self, ctx: zincParser.BlockExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#blockExpression.
    def exitBlockExpression(self, ctx: zincParser.BlockExpressionContext):
        pass

    # Enter a parse tree produced by zincParser#primaryExpression.
    def enterPrimaryExpression(self, ctx: zincParser.PrimaryExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#primaryExpression.
    def exitPrimaryExpression(self, ctx: zincParser.PrimaryExpressionContext):
        pass

    # Enter a parse tree produced by zincParser#builtinTypeQuery.
    def enterBuiltinTypeQuery(self, ctx: zincParser.BuiltinTypeQueryContext):
        pass

    # Exit a parse tree produced by zincParser#builtinTypeQuery.
    def exitBuiltinTypeQuery(self, ctx: zincParser.BuiltinTypeQueryContext):
        pass

    # Enter a parse tree produced by zincParser#typeQueryType.
    def enterTypeQueryType(self, ctx: zincParser.TypeQueryTypeContext):
        pass

    # Exit a parse tree produced by zincParser#typeQueryType.
    def exitTypeQueryType(self, ctx: zincParser.TypeQueryTypeContext):
        pass

    # Enter a parse tree produced by zincParser#builtinResultOptionConstructor.
    def enterBuiltinResultOptionConstructor(self, ctx: zincParser.BuiltinResultOptionConstructorContext):
        pass

    # Exit a parse tree produced by zincParser#builtinResultOptionConstructor.
    def exitBuiltinResultOptionConstructor(self, ctx: zincParser.BuiltinResultOptionConstructorContext):
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

    # Enter a parse tree produced by zincParser#unitLiteral.
    def enterUnitLiteral(self, ctx: zincParser.UnitLiteralContext):
        pass

    # Exit a parse tree produced by zincParser#unitLiteral.
    def exitUnitLiteral(self, ctx: zincParser.UnitLiteralContext):
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

    # Enter a parse tree produced by zincParser#tupleLiteral.
    def enterTupleLiteral(self, ctx: zincParser.TupleLiteralContext):
        pass

    # Exit a parse tree produced by zincParser#tupleLiteral.
    def exitTupleLiteral(self, ctx: zincParser.TupleLiteralContext):
        pass

    # Enter a parse tree produced by zincParser#collectionLiteral.
    def enterCollectionLiteral(self, ctx: zincParser.CollectionLiteralContext):
        pass

    # Exit a parse tree produced by zincParser#collectionLiteral.
    def exitCollectionLiteral(self, ctx: zincParser.CollectionLiteralContext):
        pass

    # Enter a parse tree produced by zincParser#anonymousStructType.
    def enterAnonymousStructType(self, ctx: zincParser.AnonymousStructTypeContext):
        pass

    # Exit a parse tree produced by zincParser#anonymousStructType.
    def exitAnonymousStructType(self, ctx: zincParser.AnonymousStructTypeContext):
        pass

    # Enter a parse tree produced by zincParser#anonymousStructFieldType.
    def enterAnonymousStructFieldType(self, ctx: zincParser.AnonymousStructFieldTypeContext):
        pass

    # Exit a parse tree produced by zincParser#anonymousStructFieldType.
    def exitAnonymousStructFieldType(self, ctx: zincParser.AnonymousStructFieldTypeContext):
        pass

    # Enter a parse tree produced by zincParser#anonymousStructLiteral.
    def enterAnonymousStructLiteral(self, ctx: zincParser.AnonymousStructLiteralContext):
        pass

    # Exit a parse tree produced by zincParser#anonymousStructLiteral.
    def exitAnonymousStructLiteral(self, ctx: zincParser.AnonymousStructLiteralContext):
        pass

    # Enter a parse tree produced by zincParser#dictEntry.
    def enterDictEntry(self, ctx: zincParser.DictEntryContext):
        pass

    # Exit a parse tree produced by zincParser#dictEntry.
    def exitDictEntry(self, ctx: zincParser.DictEntryContext):
        pass

    # Enter a parse tree produced by zincParser#structInstantiation.
    def enterStructInstantiation(self, ctx: zincParser.StructInstantiationContext):
        pass

    # Exit a parse tree produced by zincParser#structInstantiation.
    def exitStructInstantiation(self, ctx: zincParser.StructInstantiationContext):
        pass

    # Enter a parse tree produced by zincParser#enumVariantConstruction.
    def enterEnumVariantConstruction(self, ctx: zincParser.EnumVariantConstructionContext):
        pass

    # Exit a parse tree produced by zincParser#enumVariantConstruction.
    def exitEnumVariantConstruction(self, ctx: zincParser.EnumVariantConstructionContext):
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

    # Enter a parse tree produced by zincParser#argument.
    def enterArgument(self, ctx: zincParser.ArgumentContext):
        pass

    # Exit a parse tree produced by zincParser#argument.
    def exitArgument(self, ctx: zincParser.ArgumentContext):
        pass

    # Enter a parse tree produced by zincParser#selectReceiveCase.
    def enterSelectReceiveCase(self, ctx: zincParser.SelectReceiveCaseContext):
        pass

    # Exit a parse tree produced by zincParser#selectReceiveCase.
    def exitSelectReceiveCase(self, ctx: zincParser.SelectReceiveCaseContext):
        pass

    # Enter a parse tree produced by zincParser#selectSendCase.
    def enterSelectSendCase(self, ctx: zincParser.SelectSendCaseContext):
        pass

    # Exit a parse tree produced by zincParser#selectSendCase.
    def exitSelectSendCase(self, ctx: zincParser.SelectSendCaseContext):
        pass

    # Enter a parse tree produced by zincParser#selectDefaultCase.
    def enterSelectDefaultCase(self, ctx: zincParser.SelectDefaultCaseContext):
        pass

    # Exit a parse tree produced by zincParser#selectDefaultCase.
    def exitSelectDefaultCase(self, ctx: zincParser.SelectDefaultCaseContext):
        pass

    # Enter a parse tree produced by zincParser#selectReceiveBinding.
    def enterSelectReceiveBinding(self, ctx: zincParser.SelectReceiveBindingContext):
        pass

    # Exit a parse tree produced by zincParser#selectReceiveBinding.
    def exitSelectReceiveBinding(self, ctx: zincParser.SelectReceiveBindingContext):
        pass

    # Enter a parse tree produced by zincParser#lambdaExpression.
    def enterLambdaExpression(self, ctx: zincParser.LambdaExpressionContext):
        pass

    # Exit a parse tree produced by zincParser#lambdaExpression.
    def exitLambdaExpression(self, ctx: zincParser.LambdaExpressionContext):
        pass


del zincParser
